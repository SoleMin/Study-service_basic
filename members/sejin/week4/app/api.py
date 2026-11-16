"""4주차 RAG API: 서버를 켤 때 RAG 체인을 한 번 만들고, /ask 요청마다 답 + 출처를 돌려준다.
실행 (week4 폴더에서):  uvicorn app.api:app --port 8000
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.rag import ask, build_rag_chain


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_chain = build_rag_chain()   # bge-m3 로드 + chroma_db 열기 + Claude 준비 (느림, 한 번만)
    yield                                     # 여기서부터 요청을 받음


app = FastAPI(title="팀 위키 RAG", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    seconds: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):            # async 없이 def: invoke()가 오래 막히는 함수라서
    t0 = time.perf_counter()
    answer, sources = ask(app.state.rag_chain, req.question)
    return AskResponse(answer=answer, sources=sources, seconds=round(time.perf_counter() - t0, 2))
