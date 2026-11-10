# 2주차: 스터디 위키 Q&A API (FastAPI + Redis 캐시 + docker compose)

스터디 개념을 물으면 Claude가 초급/중급 수준에 맞춰 답하는 API. 같은 질문은 Redis에 캐시해서 빠르고 0원으로 답하고, 응답마다 걸린 시간과 비용(원)을 함께 돌려준다.

- 모델: `claude-haiku-5-5` (입력 $0.10, 출력 $0.50 / 100만 토큰)
- 비용(원) = (입력 토큰 × 0.10 + 출력 토큰 × 0.50) ÷ 1,000,000 × 환율(`USD_KRW`, 1400원으로 가정)
- 환경: Windows 11, Docker Desktop(WSL2), Python 3.11

## 엔드포인트

| 메서드 | 주소 | 하는 일 |
|---|---|---|
| GET | `/health` | 서버 상태 확인 |
| GET | `/topics` | 답할 수 있는 스터디 주제 목록 |
| GET | `/topics/{week}` | 주차별 주제 하나 (없으면 404) |
| POST | `/ask` | 질문 → 답 + `cached`, `elapsed_ms`, 토큰 수, `cost_krw` |
| POST | `/ask/stream` | 질문 → 답을 만들어지는 대로 흘려보냄 (StreamingResponse) |

`/ask` 요청 본문 (Pydantic으로 검사, 틀리면 422)

```json
{"question": "도커 레이어가 뭐야?", "level": "초급"}
```

- `question`: 1~500자, 필수
- `level`: `"초급"` 또는 `"중급"`만 허용, 기본값 `"초급"`
- 캐시 열쇠: `ask:{level}:{question}`, 유효기간 600초. 수준에 따라 답이 달라지므로 `level`을 열쇠에 넣음

## 실행

```powershell
copy .env.example .env      # ANTHROPIC_API_KEY 에 키 입력
docker compose up -d --build
docker compose logs api     # "Application startup complete." 가 보이면 준비 완료
# http://localhost:8000/docs
docker compose down         # 끝낼 때
```

- `docker-compose.yml`: api + redis. redis는 healthcheck(`redis-cli ping`)를 통과한 뒤 api가 뜬다(`depends_on: condition: service_healthy`)
- compose 안에서 Redis 주소는 `redis://redis:6379/0`(서비스 이름). `.env`의 `localhost` 값보다 compose의 `environment`가 우선
- redis는 내 PC에 포트를 열지 않음(api만 내부 망으로 접속)
- `.env`가 없어도 compose는 시작됨(`env_file: required: false`). 단 키가 없으면 `/ask`는 실패

Docker 없이 내 PC에서 실행할 때

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
docker run -d --name week2-redis -p 6379:6379 redis
uvicorn main:app --reload
```

## 측정값 (내 PC, 2026-11-02, 직접 실행)

**Claude 연결, 캐시 없음** (질문 "도커 레이어가 뭐야?")

| level | elapsed_ms | 입력/출력 토큰 | cost_krw |
|---|---|---|---|
| 초급 | 2083.6 | 77 / 294 | 0.2166 |
| 중급 | 2265.4 | 77 / 362 | 0.2642 |

**캐시 전/후** (초급)

| 환경 | 질문 | 1번째 (미스) | 2번째 (히트) |
|---|---|---|---|
| 내 PC + Redis 컨테이너 | 도커 컨테이너가 뭐야? | 1716.1ms, 0.1763원 | 1.6ms, 0원 |
| docker compose | docker compose가 뭐야? | 1919.8ms, 0.1876원 | 0.6ms, 0원 |

**스트리밍** (`stream_test.py`, 질문 "FastAPI의 StreamingResponse가 뭐야?")

| | 첫 조각까지(TTFT) | 전체 | 조각 수 |
|---|---|---|---|
| 캐시 미스 | 0.88초 | 2.06초 | 약 60 |
| 캐시 히트 | 0.01초 | 0.01초 | 1 |

`/ask`는 답이 다 만들어진 뒤(약 2초)에 첫 글자를 보지만, `/ask/stream`은 0.88초에 첫 글자를 본다.

**동시 요청** (`async_test.py`, 서로 다른 질문, 캐시 히트 0개)

| | 전체 | 요청별 시간 | 비용 |
|---|---|---|---|
| 순서대로 5개 | 9.04초 | 2.17, 1.77, 2.08, 1.51, 1.52 | 0.9860원 |
| 동시에 5개 | 2.05초 | 1.69, 2.04, 1.79, 1.60, 1.87 | 0.9933원 |

## 파일

| 파일 | 내용 |
|---|---|
| `main.py` | API 서버 |
| `requirements.txt` | 버전 고정한 패키지 5개 |
| `Dockerfile` | requirements 먼저 설치, 코드는 나중에 복사(빌드 캐시) |
| `docker-compose.yml` | api + redis |
| `.dockerignore` | `.venv/`, `.env` 등을 이미지에서 제외 |
| `.env.example` | 환경 변수 이름 견본 (값은 `.env`에, `.env`는 올리지 않음) |
| `stream_test.py` | 스트리밍 조각이 도착하는 시각 출력 |
| `async_test.py` | 순서대로 5개 vs 동시에 5개 비교 |
