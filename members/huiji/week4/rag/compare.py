import argparse
import json
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import ConfigDict
from sentence_transformers import CrossEncoder

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 같은 폴더의 HyDERetriever.py (HyDERetriever, HyDERerank, make_hyde_chain)
from HyDERetriever import HyDERetriever, HyDERerank, make_hyde_chain

CHUNK_SIZE, CHUNK_OVERLAP, K = 500, 50, 5   # 팀 기준선(baseline)
RERANK_CANDIDATES = 15
LLM_MODEL = "gemini-3.5-flash-lite"         # 3주차에서 쓰던 모델명 그대로


# ---------------------------------------------------------------- 3주차 파이프라인
def load_docs(wiki_dir: Path) -> List[Document]:
    loader = DirectoryLoader(
        str(wiki_dir), glob="**/*.md", loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    for d in docs:
        d.metadata["page"] = Path(d.metadata["source"]).stem
    return docs


def add_chunk_ids(chunks: List[Document]) -> List[Document]:
    counter = {}
    for c in chunks:
        page = c.metadata["page"]
        counter[page] = counter.get(page, 0) + 1
        c.metadata["id"] = f"{page}::{counter[page]:03d}"
    return chunks


def build_or_load_store(docs, embeddings, name="wiki_500_50") -> Chroma:
    persist = f"./chroma_db/{name}"
    store = Chroma(collection_name=name, embedding_function=embeddings, persist_directory=persist)
    if store._collection.count() > 0:
        print(f"[벡터DB] 기존 저장소 재사용 ({store._collection.count()}개)")
        return store
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = add_chunk_ids(splitter.split_documents(docs))
    ids = [c.metadata["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "중복 chunk ID"
    store = Chroma.from_documents(
        chunks, embeddings, ids=ids, collection_name=name, persist_directory=persist
    )
    print(f"[벡터DB] 새로 생성: 문서 {len(docs)}개 -> 청크 {len(chunks)}개")
    return store


def load_questions(path: Path) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------- 4주차 retriever
class RerankRetriever(BaseRetriever):
    """벡터로 후보를 넉넉히 뽑고 크로스인코더로 다시 채점해 상위 top_n개만 남긴다.
    (HyDERetriever.py 에는 없는 클래스라 여기서 정의)"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    base_retriever: BaseRetriever
    reranker: CrossEncoder
    top_n: int = 5

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        cands = self.base_retriever.invoke(query)
        if not cands:
            return []
        scores = self.reranker.predict([(query, d.page_content) for d in cands])
        ranked = sorted(zip(cands, scores), key=lambda x: x[1], reverse=True)
        return [d for d, _ in ranked[: self.top_n]]


# ---------------------------------------------------------------- 평가
ANSWER_KEYS = ("answer_pages", "answer_page", "page", "expected_page", "answer_id")


def answer_pages(q) -> set:
    for key in ANSWER_KEYS:
        if key in q:
            v = q[key]
            vals = v if isinstance(v, list) else [v]
            return {str(x).split("::")[0] for x in vals}
    raise KeyError(f"정답 키를 못 찾았어요. 질문 항목의 키: {list(q)}")

def run_variant(retriever, questions, k=K):
    """질문마다 (정답 페이지 순위, 걸린 시간)을 기록한다. 순위는 k위 밖이면 None."""
    retriever.invoke("워밍업")   # 첫 호출은 느리니 측정에서 제외
    ranks, times = [], []
    for q in questions:
        t = time.perf_counter()
        docs = retriever.invoke(q["question"])[:k]
        times.append(time.perf_counter() - t)
        pages = [d.metadata["page"] for d in docs]
        ans = answer_pages(q)
        ranks.append(next((i for i, p in enumerate(pages, 1) if p in ans), None))
    return ranks, times


def summarize(ranks, times):
    n = len(ranks)
    hits = [r for r in ranks if r is not None]
    return {
        "Recall@5": len(hits) / n,
        "MRR@5": sum(1 / r for r in hits) / n,
        "응답(초)": sum(times) / n,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki-dir", default="../wiki/pages", help="팀 위키는 ../../team/wiki")
    ap.add_argument("--questions", default="questions.jsonl", help="팀 것은 ../../team/eval/questions.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="질문을 앞에서 N개만 사용 (0=전부)")
    ap.add_argument("--only", nargs="*", help="실행할 변형 이름 일부만")
    ap.add_argument("--show-hyde", action="store_true", help="가짜 문서만 출력하고 종료")
    args = ap.parse_args()

    load_dotenv()   # .env 의 GOOGLE_API_KEY
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0)
    hyde_chain = make_hyde_chain(llm)

    if args.show_hyde:
        for q in ["Docker 이미지와 컨테이너의 차이는?", "도커의 실행 단위는?", "RAG에서 청킹은 왜 해?"]:
            print("Q:", q)
            print("가짜 문서:", hyde_chain.invoke({"question": q}))
            print("-" * 40)
        return

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.exists():
        raise SystemExit(f"위키 폴더가 없어요: {wiki_dir.resolve()}  (--wiki-dir 로 지정)")
    q_path = Path(args.questions)
    if not q_path.exists():
        raise SystemExit(f"질문셋이 없어요: {q_path.resolve()}  (--questions 로 지정)")

    docs = load_docs(wiki_dir)
    print(f"[위키] {len(docs)}개 문서")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3", encode_kwargs={"normalize_embeddings": True}
    )
    vs = build_or_load_store(docs, embeddings)

    questions = load_questions(q_path)
    if args.limit:
        questions = questions[: args.limit]
    print(f"[질문] {len(questions)}개\n")

    print("리랭커 모델 로딩 (첫 실행은 다운로드로 오래 걸려요)...")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)

    vector5 = vs.as_retriever(search_kwargs={"k": K})
    vector15 = vs.as_retriever(search_kwargs={"k": RERANK_CANDIDATES})

    variants = {
        "기준선": vector5,
        "리랭커": RerankRetriever(base_retriever=vector15, reranker=reranker, top_n=K),
        "HyDE(가짜만)": HyDERetriever(base_retriever=vector5, hyde_chain=hyde_chain, include_query=False),
        "HyDE(질문+가짜)": HyDERetriever(base_retriever=vector5, hyde_chain=hyde_chain, include_query=True),
        "HyDE+리랭커": HyDERerank(vector_retriever=vector15, hyde_chain=hyde_chain,
                                 reranker=reranker, top_n=K),
    }
    if args.only:
        variants = {n: r for n, r in variants.items() if n in args.only}
        if not variants:
            raise SystemExit("--only 이름이 하나도 안 맞아요.")

    all_ranks, summary = {}, {}
    for name, r in variants.items():
        print(f"측정 중: {name} ...")
        ranks, times = run_variant(r, questions)
        all_ranks[name] = ranks
        summary[name] = summarize(ranks, times)

    # 점수 표
    print("\n" + "=" * 60)
    print(f"{'기법':<16}{'Recall@5':>10}{'MRR@5':>9}{'응답(초)':>10}")
    for name, s in summary.items():
        print(f"{name:<16}{s['Recall@5']:>10.3f}{s['MRR@5']:>9.3f}{s['응답(초)']:>10.2f}")

    # 질문별 정답 순위 (X = 5위 안에 정답 페이지 없음)
    names = list(variants)
    print("\n" + "=" * 60)
    print("질문별 정답 페이지 순위 (X = 5위 안에 없음)")
    print(f"{'질문':<28}" + "".join(f"{n:>16}" for n in names))
    for i, q in enumerate(questions):
        row = "".join(f"{('X' if all_ranks[n][i] is None else all_ranks[n][i]):>16}" for n in names)
        print(f"{q['question'][:26]:<28}{row}")


if __name__ == "__main__":
    main()
