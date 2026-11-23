"""4주차 검색기: 벡터, BM25, 하이브리드(RRF), 리랭커"""
import re
import uuid
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_huggingface import HuggingFaceEmbeddings


# ── 로드 + 분할 ─────────────────────────────────
def team_repo_root():
    # 팀 저장소 members/doyu/week4/ 안이면 그 저장소, 개인 저장소면 옆에 클론한 Study-service_basic
    parents = Path(__file__).resolve().parents
    if len(parents) < 4:  # 컨테이너의 /app처럼 얕은 위치: DOCS_DIR로 지정해야 한다
        return Path("/")
    if parents[2].name == "members":
        return parents[3]
    return parents[2] / "Study-service_basic"


SKIP_FILES = {"index.md", "_template.md", "README.md"}


def load_chunks(docs_dir, chunk_size=500, chunk_overlap=50):
    """팀 evaluate.py의 build_retriever와 같은 방식: 페이지 이름 = 파일 이름, 청크 ID = 페이지이름-번호"""
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    loader = DirectoryLoader(str(docs_dir), glob="*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    pages = [p for p in loader.load() if Path(p.metadata["source"]).name not in SKIP_FILES]
    for p in pages:  # merge_wiki.py가 넣은 자동 생성 표시 줄은 뺀다
        p.page_content = "\n".join(l for l in p.page_content.splitlines() if not l.startswith("<!-- merge_wiki.py"))

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for page in pages:
        name = Path(page.metadata["source"]).stem
        for i, chunk in enumerate(splitter.split_documents([page])):
            chunk.metadata["page"] = name
            chunk.metadata["id"] = f"{name}-{i}"
            chunks.append(chunk)
    return pages, chunks


# ── 벡터 (기준선) ───────────────────────────────
@lru_cache(maxsize=1)
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="BAAI/bge-m3", encode_kwargs={"normalize_embeddings": True})


_STORES = {}


def build_vector(chunks, k=5, persist_dir=None):
    key = tuple(c.metadata["id"] for c in chunks)
    if key not in _STORES:  # 같은 청크면 한 번만 임베딩
        if persist_dir:
            # 디스크에 저장된 색인을 다시 쓴다. CPU만 있는 컨테이너에서 bge-m3로 청크 174개를 임베딩하면 10분이 넘는다
            store = Chroma(
                collection_name="wiki",
                embedding_function=get_embeddings(),
                persist_directory=str(persist_dir),
                collection_metadata={"hnsw:space": "cosine"},
            )
            if sorted(store.get(include=[])["ids"]) != sorted(key):  # 위키가 바뀌었을 때만 다시 임베딩
                store.reset_collection()
                store.add_documents(chunks, ids=list(key))
        else:
            store = Chroma.from_documents(
                chunks,
                get_embeddings(),
                ids=list(key),
                collection_name=f"w4-{uuid.uuid4().hex[:8]}",
                collection_metadata={"hnsw:space": "cosine"},  # 팀 기준선과 같은 거리
            )
        _STORES[key] = store
    return _STORES[key].as_retriever(search_kwargs={"k": k})


# ── BM25 (키워드) ───────────────────────────────
def space_tokens(text):
    # 띄어쓰기로만 자르기: "컨테이너는"과 "컨테이너"가 다른 단어가 된다
    return re.findall(r"\w+", text.lower())


@lru_cache(maxsize=1)
def _kiwi():
    from kiwipiepy import Kiwi

    return Kiwi()


KEEP_TAGS = ("NN", "VV", "VA", "SL", "SN", "XR")  # 명사, 동사·형용사 어간, 영어, 숫자, 어근


def kiwi_tokens(text):
    # 형태소로 자르고 조사·어미는 버린다: "컨테이너는" → "컨테이너"
    tokens = []
    for t in _kiwi().tokenize(text):
        if t.tag.startswith("W_"):  # 8888:8888 같은 일련번호·URL은 W_* 품사라 버리면 포트·버전이 사라진다
            tokens += re.findall(r"\w+", t.form.lower())
        elif t.tag.startswith(KEEP_TAGS):
            tokens.append(t.form.lower())
    return tokens


def build_bm25(chunks, k=5, tokenizer=kiwi_tokens):
    retriever = BM25Retriever.from_documents(chunks, preprocess_func=tokenizer)
    retriever.k = k
    return retriever


# ── 하이브리드 (RRF) ────────────────────────────
def build_hybrid(vector_retriever, bm25_retriever, weights=(0.5, 0.5), c=60):
    # 점수 = Σ weight / (c + 순위). 점수 크기가 다른 두 검색기를 순위만으로 합친다
    return EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=list(weights),
        c=c,
        id_key="id",  # 같은 청크를 청크 ID로 합친다
    )


# ── 리랭커 (크로스인코더) ────────────────────────
@lru_cache(maxsize=1)
def get_reranker():
    import torch
    from sentence_transformers import CrossEncoder

    if torch.backends.mps.is_available():  # 맥 GPU: fp16이면 1.8배 빠르다 (20쌍 12.6초 → 7.0초)
        return CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512, model_kwargs={"torch_dtype": torch.float16})
    return CrossEncoder("BAAI/bge-reranker-v2-m3", device="cpu", max_length=512)


class RerankRetriever:
    """후보를 넉넉히 뽑은 뒤 (질문, 청크) 쌍을 크로스인코더로 다시 채점해 상위 top_n만 남긴다"""

    def __init__(self, base, top_n=5, candidates=20):
        self.base, self.top_n, self.candidates = base, top_n, candidates

    def invoke(self, question):
        docs = self.base.invoke(question)[: self.candidates]  # 리랭커는 후보 하나에 약 0.35초라 개수를 묶어 둔다
        scores = get_reranker().predict([(question, d.page_content) for d in docs], batch_size=32)
        ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        return [d for _, d in ranked[: self.top_n]]
