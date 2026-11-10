import os
import time
from contextlib import asynccontextmanager
from typing import Literal
from fastapi.responses import StreamingResponse
import redis.asyncio as redis                     # ★ async 버전 Redis 클라이언트
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")
USD_KRW = float(os.getenv("USD_KRW", "1400"))                    # 가정한 환율
PRICE_IN, PRICE_OUT = 0.10, 0.50                                 # claude-haiku-5-5: 달러 / 100만 토큰
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")   # ★ 내 PC에선 localhost
CACHE_TTL = 600                                                  # ★ 캐시 유효기간 10분


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = AsyncAnthropic()
    app.state.redis = redis.from_url(REDIS_URL, decode_responses=True)   # ★
    yield
    await app.state.redis.aclose()                                       # ★
    await app.state.llm.close()


app = FastAPI(title="스터디 위키 Q&A", lifespan=lifespan)

TOPICS = {
    1: "Docker 기초: 이미지, 컨테이너, 레이어, 레지스트리",
    2: "FastAPI와 docker compose: 엔드포인트, Pydantic, Redis 캐시",
    3: "RAG 기초: 임베딩, 벡터 DB, 청킹",
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/topics")
def list_topics():
    return TOPICS


@app.get("/topics/{week}")
def get_topic(week: int):
    if week not in TOPICS:
        raise HTTPException(status_code=404, detail=f"{week}주차 주제가 없습니다")
    return {"week": week, "topic": TOPICS[week]}


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    level: Literal["초급", "중급"] = "초급"


class AskResponse(BaseModel):
    question: str
    level: str
    answer: str
    cached: bool = False     # ★ 캐시에서 꺼낸 답인가
    elapsed_ms: float
    input_tokens: int
    output_tokens: int
    cost_krw: float


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    start = time.perf_counter()

    # ★ 1) 캐시 확인: 있으면 LLM 안 부르고 바로 답함
    key = f"ask:{req.level}:{req.question}"          # 수준이 다르면 답도 다르니 level도 열쇠에
    hit = await app.state.redis.get(key)
    if hit is not None:
        return AskResponse(
            question=req.question, level=req.level, answer=hit, cached=True,
            elapsed_ms=round((time.perf_counter() - start) * 1000, 1),
            input_tokens=0, output_tokens=0, cost_krw=0.0,
        )

    # 2) 캐시 미스: LLM 호출 (2-A 코드 그대로)
    msg = await app.state.llm.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "low"},
        system=f"너는 AI 엔지니어링 스터디의 튜터다. {req.level} 학습자가 이해하도록 한국어로 3~5문장으로 답한다.",
        messages=[{"role": "user", "content": req.question}],
    )
    if msg.stop_reason == "refusal":
        answer = "[답변할 수 없는 질문입니다]"
    else:
        answer = next((b.text for b in msg.content if b.type == "text"), "")
    used_in, used_out = msg.usage.input_tokens, msg.usage.output_tokens
    cost = (used_in * PRICE_IN + used_out * PRICE_OUT) / 1_000_000 * USD_KRW

    # ★ 3) 답을 캐시에 저장 (10분 뒤 자동 삭제)
    await app.state.redis.set(key, answer, ex=CACHE_TTL)

    return AskResponse(
        question=req.question, level=req.level, answer=answer, cached=False,
        elapsed_ms=round((time.perf_counter() - start) * 1000, 1),
        input_tokens=used_in, output_tokens=used_out, cost_krw=round(cost, 4),
    )


@app.post("/ask/stream")
async def ask_stream(req: AskRequest):
    key = f"ask:{req.level}:{req.question}"

    async def generate():
        hit = await app.state.redis.get(key)
        if hit is not None:
            yield hit
            return

        parts = []
        async with app.state.llm.messages.stream(
            model=MODEL,
            max_tokens=16000,
            output_config={"effort": "low"},
            system=f"너는 AI 엔지니어링 스터디의 튜터다. {req.level} 학습자가 이해하도록 한국어로 3~5문장으로 답한다.",
            messages=[{"role": "user", "content": req.question}],
        ) as stream:
            async for text in stream.text_stream:
                parts.append(text)
                yield text

        await app.state.redis.set(key, "".join(parts), ex=CACHE_TTL)

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")

