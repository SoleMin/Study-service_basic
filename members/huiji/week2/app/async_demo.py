import asyncio
import time

from fastapi import FastAPI

app = FastAPI()


@app.get("/async-await")
async def async_await():
    await asyncio.sleep(3)  # 기다리는 동안 양보
    return {"kind": "async def + await"}


@app.get("/async-blocking")
async def async_blocking():
    time.sleep(3)  # 이벤트 루프를 붙잡음 (나쁜 예)
    return {"kind": "async def + time.sleep"}


@app.get("/plain-def")
def plain_def():
    time.sleep(3)  # 스레드풀에서 실행
    return {"kind": "def + time.sleep"}