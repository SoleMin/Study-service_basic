import hashlib
import os
import time
from fastapi.responses import StreamingResponse

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import errors
from pydantic import BaseModel, Field

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))

app = FastAPI(title="Week2 API")
llm = genai.Client()
cache = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    cached: bool
    elapsed_ms: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.perf_counter()
    key = "chat:" + hashlib.sha256(req.message.encode()).hexdigest()

    hit = await cache.get(key)
    if hit is not None:
        return ChatResponse(
            answer=hit, cached=True,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
        )

    try:
        resp = await llm.aio.models.generate_content(
            model=MODEL,
            contents=req.message,
        )
    except errors.APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM 호출 실패: {e.code}")

    answer = resp.text or ""
    await cache.set(key, answer, ex=CACHE_TTL)
    return ChatResponse(
        answer=answer, cached=False,
        elapsed_ms=int((time.perf_counter() - start) * 1000),
    )
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate():
        try:
            stream = await llm.aio.models.generate_content_stream(
                model=MODEL,
                contents=req.message,
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except errors.APIError as e:
            yield f"\n[LLM 호출 실패: {e.code}]"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")