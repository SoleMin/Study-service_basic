# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio

app = FastAPI()

@app.get("/sync-sleep")
def sync_sleep():
    time.sleep(3)
    return {"ok": True}

@app.get("/async-sleep")
async def async_sleep():
    await asyncio.sleep(3)
    return {"ok": True}

@app.get("/bad-sleep")
async def bad_sleep():
    time.sleep(3)        # async 안에서 동기 대기
    return {"ok": True}




class EchoRequest(BaseModel):
    message: str
    repeat: int = 1          # 기본값이 있으면 생략 가능

class EchoResponse(BaseModel):
    result: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/echo", response_model=EchoResponse)
def echo(req: EchoRequest):
    return EchoResponse(result=req.message * req.repeat)
# app/main.py 에 추가


from dotenv import load_dotenv
from google import genai
import os, time, hashlib
import redis.asyncio as redis

# /chat 기본 동작 확인용

# from dotenv import load_dotenv
# from google import genai

# load_dotenv()
# client = genai.Client()

# class ChatRequest(BaseModel):
#     question: str

# class ChatResponse(BaseModel):
#     answer: str

# @app.post("/chat", response_model=ChatResponse)
# async def chat(req: ChatRequest):
#     response = await client.aio.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=req.question,
#     )
#     return ChatResponse(answer=response.text)


load_dotenv()
client = genai.Client()

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
# redis 연결 설정

r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)
CACHE_TTL = 3600  # redis의 cache 유지시간 TTL(초), 1시간

class ChatResponse(BaseModel):
    answer: str
    cached: bool
    elapsed_ms: float

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.perf_counter()
    key = "chat:" + hashlib.sha256(req.question.encode()).hexdigest()
    #만약 redis에 저장된 값이 있다면 캐쉬반환
    if (hit := await r.get(key)) is not None:
        return ChatResponse(answer=hit, cached=True,
                            elapsed_ms=(time.perf_counter() - start) * 1000)

    response = await client.aio.models.generate_content(
        model="gemini-3.8-flash", contents=req.question)
    answer = response.text
    #만약 redis에 값 저장
    await r.set(key, answer, ex=CACHE_TTL)   # ex = TTL(초)
    return ChatResponse(answer=answer, cached=False,
                        elapsed_ms=(time.perf_counter() - start) * 1000)