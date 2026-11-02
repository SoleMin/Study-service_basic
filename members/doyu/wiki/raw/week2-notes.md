# 2주차 실습 메모

환경: macOS (arm64), Docker 29.9.2, Python 3.11, FastAPI 0.162.0, redis:7

## ① GET, POST + Pydantic
- `GET /health` → `{"status":"ok"}`
- `POST /echo` `{"message":"hi ","repeat":3}` → `{"result":"hi hi hi "}`
- `repeat: "abc"` → **422** (Pydantic이 타입을 막아 줌)
- `/docs` → 200 (Swagger UI)

## ② /chat
- 실제 LLM은 3주차에 연결하기로 하고, 지금은 `fake_llm()`이 `asyncio.sleep(2)` 뒤 정해진 답을 돌려줌
- 느린 외부 호출을 흉내 낸 것이라 캐시 효과와 async 동작은 그대로 확인할 수 있음
- 나중에 키를 쓸 때를 대비해 `.env`는 `.gitignore`와 `.dockerignore`에 이미 넣어 둠

## ③ compose + Redis 캐시
- `docker compose up -d --build` 한 번으로 api, redis 같이 뜸
- api 컨테이너는 `REDIS_HOST=redis`(서비스 이름)로 접속. 컨테이너 안의 `localhost`는 자기 자신
- Redis에 직접 넣은 키로 캐시 히트 확인: `cached: true`, 1.8ms, `TTL` 60

| 호출 | cached | elapsed_ms |
| --- | --- | --- |
| 1번째 | false | 2,014 (가짜 LLM, 2초 지연) |
| 2번째 | true | 0.6 (Redis) |

- 같은 질문이면 LLM을 다시 부르지 않아 지연이 거의 0이 됨. 실제 LLM은 지연이 더 길고 비용도 들어서 차이가 더 커짐
- `redis-cli TTL` → 3600. 시간이 지나면서 줄어들고, 0이 되면 키가 사라진다

## ④ async 실험 (3개 동시 요청, 각 3초 대기)
| 엔드포인트 | n=1 | n=2 | n=3 |
| --- | --- | --- | --- |
| `def` + `time.sleep` | 3.0s | 3.0s | 3.0s |
| `async def` + `await asyncio.sleep` | 3.0s | 3.0s | 3.0s |
| `async def` + `time.sleep` | 9.0s | 6.0s | 3.0s |

## 참고 링크
- https://fastapi.tiangolo.com/async/
- https://docs.docker.com/compose/how-tos/networking/
- https://redis.io/docs/latest/commands/set/
