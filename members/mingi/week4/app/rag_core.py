"""4주차 RAG 공통 모듈: 노트북(rag_v2.ipynb)과 API(app/main.py)가 같은 코드를 써요.

흐름
    로드 -> 분할(+청크 ID) -> 임베딩 -> Chroma(코사인)
    -> 검색기 3종: 기준선(벡터) / 리랭커(벡터 후보 N개 -> 크로스인코더 -> 상위 k개) / 하이브리드(BM25 + 벡터, RRF)
    -> 생성(LCEL, 출처) + 멀티턴 질문 재작성(선택 항목)

3주차 노트북과 다른 점
    - 리랭커는 LangChain CrossEncoderReranker 대신 직접 만든 RerankRetriever를 써요.
      LangChain 것은 점수를 버려서, /ask에서 "위키에 없는 질문"을 거를 기준값을 정할 수 없기 때문이에요.
      점수는 각 Document.metadata["rerank_score"]에 남겨요.
    - 하이브리드의 RRF도 직접 계산해요. EnsembleRetriever는 LangChain 버전마다 위치가 달라서요.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter

EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
SKIP_FILES = {"index.md", "_template.md", "README.md"}


# ---------------------------------------------------------------- 1. 로드, 2. 분할

def load_wiki(wiki_dir: str | Path) -> list[Document]:
    """team/wiki/*.md -> Document 리스트 (index.md, _template.md 제외, 자동 생성 표시 줄 제거)"""
    loader = DirectoryLoader(str(wiki_dir), glob="*.md", loader_cls=TextLoader,
                             loader_kwargs={"encoding": "utf-8"})
    docs = [d for d in loader.load() if Path(d.metadata["source"]).name not in SKIP_FILES]
    for d in docs:
        d.page_content = "\n".join(l for l in d.page_content.splitlines()
                                   if not l.startswith("<!-- merge_wiki.py"))
    if not docs:
        raise FileNotFoundError(f"{wiki_dir}에서 위키 페이지를 찾지 못했어요")
    return docs


def split_docs(docs: list[Document], chunk_size: int = 500, chunk_overlap: int = 50) -> list[Document]:
    """기준선 설정으로 자르고 metadata에 page(페이지 이름)와 id(페이지-번호)를 붙여요."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for doc in docs:
        page = Path(doc.metadata["source"]).stem
        for i, c in enumerate(splitter.split_documents([doc])):
            c.metadata["page"] = page
            c.metadata["id"] = f"{page}-{i}"
            chunks.append(c)
    return chunks


# ---------------------------------------------------------------- 3. 임베딩, 4. 저장

class STEmbeddings(Embeddings):
    """이미 불러온 SentenceTransformer를 LangChain에서 쓰기 위한 얇은 래퍼 (3주차와 같음)"""
    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text):
        return self.model.encode(text, normalize_embeddings=True).tolist()


def load_models(embed_model: str = EMBED_MODEL, rerank_model: str = RERANK_MODEL):
    """임베딩 모델과 크로스인코더를 한 번만 불러와요. 첫 실행 때 둘 합쳐 약 4GB를 내려받아요."""
    from sentence_transformers import CrossEncoder, SentenceTransformer
    embedder = SentenceTransformer(embed_model)
    reranker = CrossEncoder(rerank_model, max_length=512)
    return STEmbeddings(embedder), reranker


def build_vectorstore(chunks: list[Document], embeddings: Embeddings,
                      collection_name: str | None = None) -> Chroma:
    """메모리 Chroma, 거리는 cosine (Chroma 기본값은 L2)"""
    return Chroma.from_documents(
        chunks, embeddings,
        ids=[c.metadata["id"] for c in chunks],
        collection_name=collection_name or f"wiki-{uuid.uuid4().hex[:8]}",
        collection_metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------- 5. 검색기

class RerankRetriever(BaseRetriever):
    """벡터 검색으로 후보 fetch_k개를 뽑고, 크로스인코더로 (질문, 청크) 쌍을 다시 채점해 상위 top_n개만 남겨요.

    bi-encoder(bge-m3): 질문과 청크를 따로 벡터로 만들어 비교 -> 빠르지만 대충
    cross-encoder(bge-reranker): 질문과 청크를 한 입력으로 같이 읽고 점수 하나를 냄 -> 느리지만 정확
    그래서 빠른 쪽으로 후보를 좁히고, 정확한 쪽으로 순서만 다시 매겨요.
    """
    vectorstore: Chroma
    cross_encoder: object
    fetch_k: int = 20
    top_n: int = 5

    def _get_relevant_documents(self, query: str, *,
                                run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        candidates = self.vectorstore.similarity_search(query, k=self.fetch_k)
        if not candidates:
            return []
        scores = self.cross_encoder.predict([(query, d.page_content) for d in candidates])
        ranked = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)
        out = []
        for doc, score in ranked[: self.top_n]:
            doc.metadata["rerank_score"] = float(score)
            out.append(doc)
        return out


def simple_tokenize(text: str) -> list[str]:
    """BM25용 토큰화: 소문자 + 한글/영문/숫자 덩어리로 자르기.
    한국어는 "컨테이너가", "컨테이너를"이 다른 토큰이 되는 한계가 있어요 (형태소 분석기 kiwipiepy로 개선 가능)."""
    return re.findall(r"[0-9a-zA-Z가-힣_\-\.]+", text.lower())


class HybridRetriever(BaseRetriever):
    """BM25(키워드) 순위와 벡터(의미) 순위를 RRF로 합쳐요.
    RRF 점수 = sum( 1 / (rrf_k + 순위) ). 점수 크기가 아니라 순위만 쓰니 두 검색기의 점수 척도가 달라도 합칠 수 있어요."""
    vectorstore: Chroma
    chunks: list
    bm25: object = None
    fetch_k: int = 20
    top_n: int = 5
    rrf_k: int = 60

    def model_post_init(self, __context) -> None:
        if self.bm25 is None:
            from rank_bm25 import BM25Okapi
            self.bm25 = BM25Okapi([simple_tokenize(c.page_content) for c in self.chunks])

    def _get_relevant_documents(self, query: str, *,
                                run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        bm25_scores = self.bm25.get_scores(simple_tokenize(query))
        bm25_top = sorted(range(len(self.chunks)), key=lambda i: bm25_scores[i], reverse=True)[: self.fetch_k]
        bm25_docs = [self.chunks[i] for i in bm25_top]
        vec_docs = self.vectorstore.similarity_search(query, k=self.fetch_k)

        fused: dict[str, float] = {}
        by_id: dict[str, Document] = {}
        for docs in (bm25_docs, vec_docs):
            for rank, d in enumerate(docs, start=1):
                cid = d.metadata["id"]
                fused[cid] = fused.get(cid, 0.0) + 1 / (self.rrf_k + rank)
                by_id.setdefault(cid, d)
        best = sorted(fused, key=fused.get, reverse=True)[: self.top_n]
        return [by_id[cid] for cid in best]


# ---------------------------------------------------------------- 6. 생성 + 멀티턴

ANSWER_PROMPT = ChatPromptTemplate.from_template("""너는 팀 스터디 위키를 바탕으로 답하는 도우미야.
아래 문서에 있는 내용만 사용해서 한국어로 답해. 문서에 없으면 "위키에 없는 내용이에요"라고 답해.

[문서]
{context}

[질문]
{question}""")

CONDENSE_PROMPT = ChatPromptTemplate.from_template("""아래 대화 기록을 보고, 마지막 후속 질문을 대화 기록 없이도 이해할 수 있는 독립된 질문 하나로 다시 써.
질문에 답하지 말고, 다시 쓴 질문만 출력해. 이미 독립된 질문이면 그대로 출력해.

[대화 기록]
{history}

[후속 질문]
{question}""")

NOT_IN_WIKI = "위키에 없는 내용이에요"


def make_llm(api_key: str, model: str = "gemini-3.8-flash"):
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0)


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(f"[{d.metadata['page']}]\n{d.page_content}" for d in docs)


def format_history(history: list[dict]) -> str:
    """history = [{"role": "user"|"assistant", "content": "..."}, ...]"""
    names = {"user": "사용자", "assistant": "도우미"}
    return "\n".join(f"{names.get(t['role'], t['role'])}: {t['content']}" for t in history)


def condense_question(llm, question: str, history: list[dict]) -> str:
    """멀티턴: "그럼 compose에서는?" 같은 후속 질문을 검색 가능한 독립 질문으로 바꿔요. 기록이 없으면 그대로."""
    if not history:
        return question
    chain = CONDENSE_PROMPT | llm | StrOutputParser()
    return chain.invoke({"history": format_history(history), "question": question}).strip()


def answer(llm, retriever: BaseRetriever, question: str, history: list[dict] | None = None,
           min_score: float | None = None) -> dict:
    """질문 하나에 답해요. 리랭커 점수가 min_score보다 낮으면 LLM을 부르지 않고 거절해요.

    돌려주는 값: {"question", "search_query", "answer", "in_wiki", "sources": [{"page", "chunk_id", "score"}]}
    """
    history = history or []
    search_query = condense_question(llm, question, history)
    docs = retriever.invoke(search_query)

    top_score = docs[0].metadata.get("rerank_score") if docs else None
    in_wiki = bool(docs) and (min_score is None or top_score is None or top_score >= min_score)
    if not in_wiki:
        return {"question": question, "search_query": search_query, "answer": NOT_IN_WIKI,
                "in_wiki": False, "top_score": top_score, "sources": []}

    chain = ANSWER_PROMPT | llm | StrOutputParser()
    text = chain.invoke({"context": format_docs(docs), "question": search_query})
    sources = [{"page": d.metadata["page"], "chunk_id": d.metadata["id"],
                "score": d.metadata.get("rerank_score")} for d in docs]
    return {"question": question, "search_query": search_query, "answer": text,
            "in_wiki": True, "top_score": top_score, "sources": sources}
