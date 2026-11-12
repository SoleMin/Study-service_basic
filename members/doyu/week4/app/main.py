"""4주차: 팀 위키 RAG를 FastAPI /ask로 서빙

POST /ask {"question": "..."} → {"answer", "sources", "retriever", "retrieval_ms", "total_ms"}
"""
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).resolve().parents[1]))  # week4/ 폴더의 hybrid.py
from hybrid import RerankRetriever, build_bm25, build_hybrid, build_vector, kiwi_tokens, load_chunks, team_repo_root  # noqa: E402

load_dotenv()

DOCS_DIR = os.getenv("DOCS_DIR") or str(team_repo_root() / "team" / "wiki")
RETRIEVER = os.getenv("RETRIEVER") or "rerank"  # vector | hybrid | rerank
CHROMA_DIR = os.getenv("CHROMA_DIR") or None  # 임베딩 색인을 저장할 폴더 (없으면 켤 때마다 메모리에 새로 만든다)
MODEL = "claude-opus-5-5"
SYSTEM = (
    "너는 스터디 팀 위키 도우미야. <context> 안의 위키 내용만 근거로 한국어로 짧게 답해. "
    "문맥에 답이 없으면 위키에 없다고 말해."
)

state = {}


def make_retriever(chunks, kind):
    # 팀 질문셋 결과(MRR@5): vector 0.780, hybrid 0.787, rerank 0.863 (후보 10개면 질문당 약 3초)
    if kind == "vector":
        return build_vector(chunks, 5, CHROMA_DIR)
    if kind == "hybrid":
        return build_hybrid(build_vector(chunks, 20, CHROMA_DIR), build_bm25(chunks, 20, kiwi_tokens), [0.7, 0.3])
    if kind == "rerank":
        return RerankRetriever(build_vector(chunks, 10, CHROMA_DIR), top_n=5, candidates=10)
    raise ValueError(f"RETRIEVER는 vector, hybrid, rerank 중 하나여야 해요: {kind}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 임베딩 모델과 색인은 서버를 켤 때 한 번만 만든다 (요청마다 만들면 수십 초)
    _, chunks = load_chunks(DOCS_DIR)
    retriever = make_retriever(chunks, RETRIEVER)
    retriever.invoke("워밍업")
    state.update(retriever=retriever, n_chunks=len(chunks))
    state["claude"] = anthropic.AsyncAnthropic() if os.getenv("ANTHROPIC_API_KEY") else None
    yield


app = FastAPI(title="doyu week4 /ask", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskResponse(BaseModel):
    answer: str | None
    sources: list[str]
    retriever: str
    retrieval_ms: float
    total_ms: float


@app.get("/health")
def health():
    return {"status": "ok", "retriever": RETRIEVER, "chunks": state.get("n_chunks"), "llm": state.get("claude") is not None}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    start = time.perf_counter()
    # 검색은 CPU를 쓰는 동기 코드라 스레드풀에서 돌린다 (async 함수 안에서 그냥 부르면 서버 전체가 멈춤)
    docs = await run_in_threadpool(state["retriever"].invoke, req.question)
    docs = docs[:5]
    retrieval_ms = (time.perf_counter() - start) * 1000
    sources = list(dict.fromkeys(d.metadata["page"] for d in docs))

    answer = None
    if state["claude"] is not None:
        context = "\n\n".join(f"[{d.metadata['page']}]\n{d.page_content}" for d in docs)
        try:
            resp = await state["claude"].beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # 안전 분류기가 거절하면 서버가 다른 모델로 다시 시도
                system=SYSTEM,
                messages=[{"role": "user", "content": f"<context>\n{context}\n</context>\n\n질문: {req.question}"}],
            )
        except anthropic.APIStatusError as e:
            raise HTTPException(502, f"LLM 호출 실패: {e.status_code}")
        except anthropic.APIConnectionError:
            raise HTTPException(502, "LLM 연결 실패")
        if resp.stop_reason == "refusal":
            answer = "(답변이 거절됐어요)"
        else:
            answer = "".join(b.text for b in resp.content if b.type == "text")

    return AskResponse(
        answer=answer,
        sources=sources,
        retriever=RETRIEVER,
        retrieval_ms=retrieval_ms,
        total_ms=(time.perf_counter() - start) * 1000,
    )
