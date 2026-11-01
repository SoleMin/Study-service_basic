import asyncio
import hashlib
import os
import time
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")  # loaded from .env via docker compose `env_file`
CACHE_TTL = 60  # seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the async client inside the running loop (avoids "attached to a different loop")
    app.state.redis = redis.from_url(REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)


# ── ① GET / POST + Pydantic ─────────────────────────
class EchoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=200)
    repeat: int = Field(default=1, ge=1, le=5)


class EchoResponse(BaseModel):
    result: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/echo", response_model=EchoResponse)
def echo(req: EchoRequest):
    return EchoResponse(result=" ".join([req.message] * req.repeat))


# ── ② /chat (LLM call, mocked) ──────────────────────
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    cached: bool
    elapsed_ms: float


async def call_llm(question: str) -> str:
    # TODO: replace with a real LLM SDK call using LLM_API_KEY, e.g.
    #   client = AsyncAnthropic(api_key=LLM_API_KEY)
    #   msg = await client.messages.create(model=..., max_tokens=..., messages=[...])
    #   return msg.content[0].text
    await asyncio.sleep(2)  # ponytail: mock latency so the cache speedup is visible
    return f"[mock answer] {question}"


# ── ④ Redis cache with TTL ──────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.perf_counter()
    key = "chat:" + hashlib.sha256(req.question.encode()).hexdigest()

    answer = await app.state.redis.get(key)
    cached = answer is not None
    if not cached:
        answer = await call_llm(req.question)
        await app.state.redis.set(key, answer, ex=CACHE_TTL)

    return ChatResponse(
        answer=answer,
        cached=cached,
        elapsed_ms=round((time.perf_counter() - start) * 1000, 1),
    )


# ── ⑤ Token streaming (StreamingResponse) ───────────
async def stream_llm(question: str):
    # TODO: replace with a real streaming SDK call, e.g.
    #   async with client.messages.stream(model=..., max_tokens=..., messages=[...]) as s:
    #       async for text in s.text_stream:
    #           yield text
    for token in f"[mock answer] {question}".split():
        await asyncio.sleep(0.2)  # mock per-token latency
        yield token + " "


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(stream_llm(req.question), media_type="text/plain")
