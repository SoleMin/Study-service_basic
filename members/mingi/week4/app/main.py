"""4주차: 팀 위키 RAG를 FastAPI /ask로 서빙

실행 (members/mingi/week4 폴더에서)
    로컬:   uvicorn app.main:app --reload       -> http://localhost:8000/docs
    Docker: docker compose up --build

환경변수 (.env)
    GEMINI_API_KEY   필수
    WIKI_DIR         팀 위키 폴더. 기본값: 저장소의 team/wiki (Docker에서는 /wiki)
    RETRIEVER        rerank(기본) | vector | hybrid
    FETCH_K          리랭커/하이브리드 후보 수 (기본 20)
    MIN_SCORE        리랭커 1위 점수가 이보다 낮으면 "위키에 없는 내용" (기본 0.1, 노트북 7번 섹션에서 정해요)
    LLM_MODEL        기본 gemini-3.8-flash
"""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import rag_core

load_dotenv()

# 이 파일 위치: <저장소>/members/mingi/week4/app/main.py -> 네 단계 위가 저장소 루트
_parents = Path(__file__).resolve().parents
DEFAULT_WIKI = _parents[4] / "team" / "wiki" if len(_parents) > 4 else Path("/wiki")
WIKI_DIR = Path(os.getenv("WIKI_DIR", str(DEFAULT_WIKI)))
RETRIEVER = os.getenv("RETRIEVER", "rerank")
FETCH_K = int(os.getenv("FETCH_K", "20"))
TOP_N = 5
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.1"))
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버가 켜질 때 한 번만: 위키 로드, 분할, 모델 2개, Chroma, LLM.
    요청마다 하면 질문 하나에 수십 초가 걸려요."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 없어요. .env를 확인하세요")

    t0 = time.perf_counter()
    docs = rag_core.load_wiki(WIKI_DIR)
    chunks = rag_core.split_docs(docs, 500, 50)
    embeddings, cross_encoder = rag_core.load_models()
    store = rag_core.build_vectorstore(chunks, embeddings, collection_name="wiki-api")

    if RETRIEVER == "vector":
        retriever = store.as_retriever(search_kwargs={"k": TOP_N})
    elif RETRIEVER == "hybrid":
        retriever = rag_core.HybridRetriever(vectorstore=store, chunks=chunks, fetch_k=FETCH_K, top_n=TOP_N)
    else:
        retriever = rag_core.RerankRetriever(vectorstore=store, cross_encoder=cross_encoder,
                                             fetch_k=FETCH_K, top_n=TOP_N)

    app.state.retriever = retriever
    app.state.llm = rag_core.make_llm(api_key, LLM_MODEL)
    app.state.info = {"wiki_dir": str(WIKI_DIR), "pages": len(docs), "chunks": len(chunks),
                      "retriever": RETRIEVER, "fetch_k": FETCH_K, "min_score": MIN_SCORE,
                      "startup_sec": round(time.perf_counter() - t0, 1)}
    print("준비 완료:", app.state.info)
    yield


app = FastAPI(title="팀 위키 RAG", lifespan=lifespan)


class Turn(BaseModel):
    role: str = Field(description="user 또는 assistant")
    content: str


class AskRequest(BaseModel):
    question: str
    history: list[Turn] = Field(default_factory=list, description="이전 대화 (멀티턴, 선택)")


class Source(BaseModel):
    page: str
    chunk_id: str
    score: float | None = None


class AskResponse(BaseModel):
    question: str
    search_query: str          # 멀티턴이면 다시 쓴 질문, 아니면 원래 질문
    answer: str
    in_wiki: bool
    top_score: float | None
    sources: list[Source]
    elapsed_ms: float


@app.get("/health")
def health():
    return {"status": "ok", **app.state.info}


# async def가 아니라 def로 둔 이유: 임베딩, 크로스인코더, LLM 호출이 모두 동기(블로킹) 함수예요.
# async def 안에서 부르면 이벤트 루프가 멈춰 다른 요청을 못 받아요 (2주차 /bad-sleep과 같은 상황).
# def로 두면 FastAPI가 스레드풀에서 실행해 줘요.
@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="질문이 비어 있어요")
    t0 = time.perf_counter()
    out = rag_core.answer(
        app.state.llm, app.state.retriever, req.question,
        history=[t.model_dump() for t in req.history],
        min_score=MIN_SCORE if RETRIEVER == "rerank" else None,
    )
    return AskResponse(**out, elapsed_ms=round((time.perf_counter() - t0) * 1000, 1))
