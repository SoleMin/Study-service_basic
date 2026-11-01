import asyncio
import hashlib
import os
import time

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from pydantic import BaseModel, Field

load_dotenv()  # 로컬 실행용. compose에서는 env_file로 환경변수가 들어온다

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 초

app = FastAPI(title="doyu week2")
r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)
_client: genai.Client | None = None


def get_client() -> genai.Client:
    # 키가 없어도 /health, /echo는 뜨도록 /chat을 처음 부를 때 만든다
    global _client
    if _client is None:
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(500, "GEMINI_API_KEY가 설정되지 않았어요 (.env 확인)")
        _client = genai.Client()  # GEMINI_API_KEY 환경변수를 읽는다
    return _client


# ── ① GET, POST + Pydantic ──────────────────────
class EchoRequest(BaseModel):
    message: str
    repeat: int = Field(1, ge=1, le=10)


class EchoResponse(BaseModel):
    result: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/echo", response_model=EchoResponse)
def echo(req: EchoRequest):
    return EchoResponse(result=req.message * req.repeat)


# ── ②③ /chat + Redis TTL 캐시 ───────────────────
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    cached: bool
    elapsed_ms: float


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.perf_counter()
    key = "chat:" + hashlib.sha256(req.question.strip().encode()).hexdigest()

    try:
        hit = await r.get(key)
    except redis.ConnectionError:
        hit = None  # Redis가 죽어도 LLM 호출은 되게 한다

    if hit is not None:
        return ChatResponse(answer=hit, cached=True, elapsed_ms=(time.perf_counter() - start) * 1000)

    try:
        response = await get_client().aio.models.generate_content(model=MODEL, contents=req.question)
    except HTTPException:
        raise
    except Exception as e:
        # 키 오류, 한도 초과 등. 키 값이 응답에 섞이지 않도록 예외 종류만 돌려준다
        raise HTTPException(502, f"LLM 호출 실패: {type(e).__name__} {getattr(e, 'code', '')}".strip())

    answer = response.text or ""
    try:
        await r.set(key, answer, ex=CACHE_TTL)
    except redis.ConnectionError:
        pass
    return ChatResponse(answer=answer, cached=False, elapsed_ms=(time.perf_counter() - start) * 1000)


# ── ④ async 실험용 ──────────────────────────────
@app.get("/sync-sleep")
def sync_sleep(n: int = 0):
    time.sleep(3)
    return {"n": n}


@app.get("/async-sleep")
async def async_sleep(n: int = 0):
    await asyncio.sleep(3)
    return {"n": n}


@app.get("/bad-sleep")
async def bad_sleep(n: int = 0):
    time.sleep(3)  # async 안에서 동기 대기 → 이벤트 루프 전체가 멈춘다
    return {"n": n}
