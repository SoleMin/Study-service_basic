# 2주차 실습 메모

환경: macOS (arm64), Docker 29.9.2, Python 3.11, FastAPI 0.162.0, google-genai 2.34.0, redis:7

## ① GET, POST + Pydantic
- `GET /health` → `{"status":"ok"}`
- `POST /echo` `{"message":"hi ","repeat":3}` → `{"result":"hi hi hi "}`
- `repeat: "abc"` → **422** (Pydantic이 타입을 막아 줌)
- `/docs` → 200 (Swagger UI)

## ② /chat (Gemini)
- 키는 `.env`의 `GEMINI_API_KEY`로만 읽음. 코드·이미지에는 없음 (`.dockerignore`에 `.env`)
- `git check-ignore -v week2/.env` → `.gitignore:2:.env` 에 걸림
- 키가 없을 때 `/chat` → 500 `GEMINI_API_KEY가 설정되지 않았어요`. 서버 자체는 정상으로 뜸
- LLM 호출 에러는 예외 종류만 502로 돌려줌 (에러 메시지에 키가 섞일 수 있어서)

## ③ compose + Redis 캐시
- `docker compose up -d --build` 한 번으로 api, redis 같이 뜸
- api 컨테이너는 `REDIS_HOST=redis`(서비스 이름)로 접속. 컨테이너 안의 `localhost`는 자기 자신
- Redis에 직접 넣은 키로 캐시 히트 확인: `cached: true`, 1.8ms, `TTL` 60

| 호출 | cached | elapsed_ms |
| --- | --- | --- |
| 1번째 | false | 66,139 (LLM 호출) |
| 2번째 | true | 1.4 (Redis) |
| 다른 질문 | false | 55,791 |

- 질문: "Docker 이미지와 컨테이너의 차이를 두 문장으로 설명해줘", 모델 `gemini-3.8-flash`
- 약 **47,000배** 차이. 같은 질문이면 LLM을 다시 부르지 않아 시간과 비용이 0에 가까움
- `redis-cli TTL` → 3599, 5초 뒤 3594. 시간이 지나면서 줄어들고, 0이 되면 키가 사라진다

## 에러 로그
- `gemini-2.5-flash` → 404 `no longer available to new users`. 모델 목록(`client.models.list()`)을 보고 `gemini-3.8-flash`로 변경
- 첫 호출에서 503 (Gemini 서버 혼잡). 잠시 뒤 다시 하니 됨. 실패한 답은 캐시에 저장되지 않는 것도 확인
- 처음엔 에러 응답이 `ClientError`만 보여서 원인을 몰랐다 → 상태 코드(404, 503)도 같이 돌려주도록 수정
- 스크립트에서 `genai.Client().models.list()`처럼 클라이언트를 변수에 안 담으면 `client has been closed` 에러

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
- https://ai.google.dev/gemini-api/docs/quickstart
