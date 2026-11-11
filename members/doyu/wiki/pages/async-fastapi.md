# FastAPI에서 async가 필요한 때

## 한 줄 정의
`async def`는 **기다리는 동안 다른 요청을 처리할 수 있게** 해 주는 함수다. 기다림(I/O)이 많은 작업에서만 이득이고, 그 안에서 동기 함수로 기다리면 서버 전체가 멈춘다.

## 왜 필요한가
- LLM 호출, Redis, DB, 외부 API처럼 **응답을 기다리는 시간이 대부분인 작업**은 `async def` + `await`로 쓰면 그 시간에 다른 요청을 받을 수 있다.
- `async def` 안에서는 **async 라이브러리**를 써야 한다 (`redis.asyncio`, `client.aio`, `httpx`). `time.sleep`이나 `requests`처럼 동기로 기다리면 이벤트 루프가 막혀 모든 요청이 줄을 선다.
- CPU를 계속 쓰는 작업(모델 추론, 큰 계산)은 async로 빨라지지 않는다. 그냥 `def`로 쓰면 FastAPI가 별도 스레드에서 돌려 준다.

| 함수 | 안에서 기다리는 방법 | 동시 요청 3개 |
| --- | --- | --- |
| `def` | `time.sleep(3)` | 3초씩 (스레드풀) |
| `async def` | `await asyncio.sleep(3)` | 3초씩 (이벤트 루프) |
| `async def` | `time.sleep(3)` | **3, 6, 9초** (루프가 막힘) |

## 최소 예제
```python
@app.get("/async-sleep")
async def async_sleep(n: int = 0):
    await asyncio.sleep(3)   # 기다리는 동안 다른 요청 처리
    return {"n": n}

@app.get("/bad-sleep")
async def bad_sleep(n: int = 0):
    time.sleep(3)            # 이벤트 루프 전체가 3초 멈춤
    return {"n": n}
```
```bash
for n in 1 2 3; do curl -s -o /dev/null -w "n=$n %{time_total}s\n" "localhost:8000/bad-sleep?n=$n" & done; wait
```

## 내가 막힌 점
- `def`도 3초씩 동시에 끝나서 처음엔 async가 왜 필요한지 헷갈렸다. `def`는 FastAPI가 스레드풀에서 돌려 주기 때문이고, 스레드 수에는 한계가 있다.
- 같은 주소로 동시에 요청하면 브라우저가 하나씩 보내서 실험이 안 된다. `?n=1,2,3`처럼 주소를 바꾸거나 curl을 썼다.

## 출처
- FastAPI 공식 문서, Concurrency and async / await: https://fastapi.tiangolo.com/async/
- 직접 실습: [week2-notes.md](../raw/week2-notes.md)
