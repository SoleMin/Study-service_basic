"""팀 공통 검색 평가 스크립트 (3주차, v0)

질문셋(questions.jsonl)으로 리트리버를 채점해 Recall@k, MRR@k, 질문당 평균 검색 시간을 출력해요.

사용법 1. 명령줄 (기준선 측정, 청크 크기 비교 실습)
    python scripts/merge_wiki.py                     # 먼저 개인 위키를 team/wiki로 모으기
    python team/eval/evaluate.py                     # 기준선 (문서: team/wiki)
    python team/eval/evaluate.py --chunk-size 200 --overlap 20
    python team/eval/evaluate.py --show-misses

사용법 2. 노트북에서 내가 만든 리트리버 채점
    import sys; sys.path.append("../../../team/eval")   # 노트북 위치에 맞게
    from evaluate import evaluate, load_questions
    result = evaluate(my_retriever, load_questions("../../../team/eval/questions.jsonl"), k=5)

리트리버 조건
    - retriever.invoke(질문) 이 Document 리스트를 돌려줘야 해요 (LangChain retriever면 그대로 돼요).
    - 각 Document.metadata["source"]에 원본 파일 경로가 있어야 해요 (DirectoryLoader가 자동으로 넣어 줘요).
      팀 위키 파일 이름(예: docker-compose_mingi)이 페이지 이름이고, answer_pages와 비교해요.
      그래서 노트북에서도 문서는 merge_wiki.py가 만든 team/wiki/ 를 불러와야 해요.

채점 규칙
    - 정답 단위는 "페이지"예요. 청크 ID는 청크 크기를 바꾸면 달라지기 때문에,
      청크 크기를 비교하려면 페이지 단위로 채점해야 공정해요.
    - answer_pages에 페이지가 여러 개면 그중 하나만 찾아도 정답이에요 (같은 주제를 여러 멤버가 쓴 경우).
    - 검색 결과 상위 k개 청크를 페이지 이름으로 바꾸고, 같은 페이지가 여러 번 나오면 처음 것만 남겨 순위를 매겨요.
    - Recall@k: 정답 페이지가 상위 k개 청크 안에 하나라도 있는 질문의 비율
    - MRR@k: 정답 페이지가 처음 나온 순위의 역수 평균 (1위 1.0, 2위 0.5, 못 찾으면 0)
    - 질문에 answer_chunk_ids가 있으면 청크 단위(metadata["id"])로도 채점해요 (선택).
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

DEFAULT_QUESTIONS = Path(__file__).parent / "questions.jsonl"
DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_DOCS = "team/wiki"
SKIP_FILES = {"index.md", "_template.md", "README.md"}


# ---------------------------------------------------------------- 질문셋

def load_questions(path: str | Path = DEFAULT_QUESTIONS) -> list[dict]:
    """questions.jsonl을 읽어요. 한 줄 = {"id", "question", "answer_pages", ("answer_chunk_ids")}"""
    questions = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


# ---------------------------------------------------------------- 채점

def page_id(source: str | Path) -> str:
    """파일 경로 -> 페이지 이름 = 팀 위키 파일 이름(확장자 제외), 예: docker-compose_mingi
    merge_wiki.py가 만든 team/wiki/ 를 문서로 써야 질문셋 정답과 이름이 맞아요."""
    return Path(source).stem


def page_of(doc) -> str:
    """Document가 어느 페이지에서 왔는지"""
    if "page" in doc.metadata:
        return doc.metadata["page"]
    return page_id(doc.metadata.get("source", ""))


def first_hit_rank(retrieved: list[str], answers: set[str]) -> int | None:
    """중복을 지운 순위 목록에서 정답이 처음 나온 순위(1부터). 없으면 None"""
    seen: list[str] = []
    for item in retrieved:
        if item not in seen:
            seen.append(item)
    for rank, item in enumerate(seen, start=1):
        if item in answers:
            return rank
    return None


def evaluate(retriever, questions: list[dict], k: int = 5, verbose: bool = True,
             show_misses: bool = False) -> dict:
    """리트리버를 질문셋으로 채점해 결과 dict를 돌려줘요."""
    rows = []
    total_time = 0.0
    for q in questions:
        start = time.perf_counter()
        docs = retriever.invoke(q["question"])
        total_time += time.perf_counter() - start
        docs = docs[:k]

        pages = [page_of(d) for d in docs]
        page_rank = first_hit_rank(pages, set(q["answer_pages"]))

        chunk_rank = None
        if q.get("answer_chunk_ids"):
            chunk_ids = [d.metadata.get("id") for d in docs]
            chunk_rank = first_hit_rank(chunk_ids, set(q["answer_chunk_ids"]))

        rows.append({"id": q["id"], "question": q["question"], "answer_pages": q["answer_pages"],
                     "retrieved_pages": pages, "rank": page_rank, "chunk_rank": chunk_rank})

    n = len(rows)
    result = {
        "k": k,
        "n_questions": n,
        "recall": sum(r["rank"] is not None for r in rows) / n,
        "mrr": sum(1 / r["rank"] for r in rows if r["rank"]) / n,
        "avg_ms": total_time / n * 1000,
        "rows": rows,
    }
    chunk_rows = [r for r, q in zip(rows, questions) if q.get("answer_chunk_ids")]
    if chunk_rows:
        m = len(chunk_rows)
        result["chunk_recall"] = sum(r["chunk_rank"] is not None for r in chunk_rows) / m
        result["chunk_mrr"] = sum(1 / r["chunk_rank"] for r in chunk_rows if r["chunk_rank"]) / m

    if verbose:
        print_report(result, show_misses)
    return result


def print_report(result: dict, show_misses: bool = False) -> None:
    k = result["k"]
    print(f"\n질문 {result['n_questions']}개 | Recall@{k} = {result['recall']:.3f} | "
          f"MRR@{k} = {result['mrr']:.3f} | 평균 검색 시간 {result['avg_ms']:.1f} ms")
    if "chunk_recall" in result:
        print(f"(청크 단위) Recall@{k} = {result['chunk_recall']:.3f} | MRR@{k} = {result['chunk_mrr']:.3f}")
    if show_misses:
        print("\n정답을 1위로 못 찾은 질문")
        for r in result["rows"]:
            if r["rank"] != 1:
                got = r["rank"] if r["rank"] else "없음"
                print(f"- {r['id']} 정답 순위 {got} | {r['question']}")
                print(f"    정답: {r['answer_pages']}  검색: {r['retrieved_pages']}")


# ---------------------------------------------------------------- 기준선 리트리버 (명령줄용)

def build_retriever(docs_dir: str | Path, chunk_size: int = 500, chunk_overlap: int = 50,
                    k: int = 5, model: str = DEFAULT_MODEL, embeddings=None):
    """기준선 파이프라인: 로드 -> 분할(+청크 ID) -> 임베딩 -> Chroma(코사인, 메모리) -> retriever"""
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    loader = DirectoryLoader(str(docs_dir), glob="*.md", loader_cls=TextLoader,
                             loader_kwargs={"encoding": "utf-8"})
    pages = [p for p in loader.load() if Path(p.metadata["source"]).name not in SKIP_FILES]
    for p in pages:   # merge_wiki.py가 넣은 자동 생성 표시 줄은 검색 대상에서 빼요
        p.page_content = "\n".join(l for l in p.page_content.splitlines()
                                    if not l.startswith("<!-- merge_wiki.py"))
    if not pages:
        raise SystemExit(f"{docs_dir}에서 .md 파일을 찾지 못했어요. --docs 경로를 확인하세요.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for page in pages:
        name = page_id(page.metadata["source"])
        for i, chunk in enumerate(splitter.split_documents([page])):
            chunk.metadata["page"] = name
            chunk.metadata["id"] = f"{name}-{i}"   # 청크 ID: 페이지이름-번호
            chunks.append(chunk)

    if embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name=model,
                                           encode_kwargs={"normalize_embeddings": True})

    store = Chroma.from_documents(
        chunks, embeddings,
        ids=[c.metadata["id"] for c in chunks],
        collection_name=f"eval-{uuid.uuid4().hex[:8]}",       # 매번 새 컬렉션 (메모리)
        collection_metadata={"hnsw:space": "cosine"},           # Chroma 기본값은 L2
    )
    print(f"페이지 {len(pages)}개 -> 청크 {len(chunks)}개 "
          f"(chunk_size={chunk_size}, overlap={chunk_overlap})")
    return store.as_retriever(search_kwargs={"k": k})


def main() -> None:
    p = argparse.ArgumentParser(description="팀 공통 검색 평가 (Recall@k, MRR@k)")
    p.add_argument("--docs", default=DEFAULT_DOCS, help="문서 폴더 (.md). 기본: team/wiki (merge_wiki.py 결과)")
    p.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    p.add_argument("--chunk-size", type=int, default=500)
    p.add_argument("--overlap", type=int, default=50)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--show-misses", action="store_true", help="1위로 못 찾은 질문 출력")
    p.add_argument("--save", help="결과를 JSON으로 저장할 경로 (선택)")
    args = p.parse_args()

    retriever = build_retriever(args.docs, args.chunk_size, args.overlap, args.k, args.model)
    result = evaluate(retriever, load_questions(args.questions), k=args.k, show_misses=args.show_misses)
    if args.save:
        result["config"] = {"chunk_size": args.chunk_size, "overlap": args.overlap,
                            "k": args.k, "model": args.model}
        Path(args.save).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"저장: {args.save}")


if __name__ == "__main__":
    main()
