# 4주차: RAG 고도화(리랭커) + FastAPI `/ask` + Docker

1. **리랭커**: 벡터 검색으로 뽑은 상위 청크(후보 10개, 20개)를 크로스인코더로 다시 채점했다. 팀 `evaluate.py`(질문 25개)로 기준선과 비교했다.
2. **API화**: RAG 체인을 FastAPI `/ask`로 감싸 답과 출처를 돌려주게 했다. 이 서버를 Docker 이미지로 빌드했다.

- 문서: 팀 위키 `team/wiki/` (31페이지 → 청크 174개). 팀 `evaluate.py` 와 같은 청크 규칙을 쓴다.
- 기준선: `bge-m3`, chunk 500 / overlap 50, cosine, k=5
- 리랭커: `BAAI/bge-reranker-v2-m3` (로컬, CPU)
- 생성: `claude-haiku-5-5`
- 환경: Windows 11, Python 3.11.2, CPU

## 1. 리랭커 실험 (`rerank.ipynb`)

| 셀 | 하는 일 |
|---|---|
| 1 | 팀 `team/eval/evaluate.py` 를 import (복사하지 않고 팀 것을 그대로 사용) |
| 2 | 팀 `build_retriever()` 로 후보 20개 검색기 생성. 앞 5개만 채점해 기준선 재현 |
| 3 | 리랭커 로드. q25 하나로 벡터 순위와 리랭커 순위 비교 |
| 4 | `RerankRetriever` (벡터 후보 n개 → 리랭커 점수로 재정렬 → 상위 5개) 전체 채점 |
| 5 | 후보를 10개로 줄여 다시 채점 |

### 결과 (질문 25개, 2026-11-15~16)

| 구성 | Recall@5 | MRR@5 | 질문당 검색 시간 |
|---|---|---|---|
| 기준선 (벡터 k=5) | 1.000 | 0.759 | 259.1 ms |
| 리랭커 (후보 20 → 5) | 1.000 | 0.808 | 26,972.7 ms |
| 리랭커 (후보 10 → 5) | 1.000 | **0.830** | 10,259.9 ms |

- 결과 파일: `results/base_500.json`, `results/rerank_20.json`, `results/rerank_10.json`
- **채택 판단: 보류.** 점수는 +0.071 올랐다. 하지만 CPU에서 질문당 약 10초가 늘어난다. `/ask` 답변 전체가 2~4초이므로 감수하기 어렵다.

**정답 순위가 바뀐 질문 (기준선 → 후보 20 → 후보 10)**

| 질문 | 순위 | 메모 |
|---|---|---|
| q08 localhost로 쓰면 왜 안 돼? | 4 → 1 → 1 | 질문의 의도("왜 안 돼")를 읽어야 하는 질문에서 크게 오름 |
| q13 LLM을 또 부르지 않게 하려면? | 5 → 1 → 1 | |
| q01, q07, q09 | 5→3, 3→2, 3→2 | |
| q21 slim 이미지 크기 | 2 → 2 → 1 | 20개일 때 1위였던 누수 청크가 후보 10개 밖으로 빠짐 |
| q15 결과 파일 남기기 | 3 → 5 → 4 | |
| q19 VM과 컨테이너의 커널 | 1 → 2 → 2 | |
| q25 설계도 비유 | 2 → 3 → 3 | 리랭커가 정답 목록에 없는 페이지를 1위로 올림 (아래 "한계") |

## 2. API (`app/`)

| 파일 | 하는 일 |
|---|---|
| `app/rag.py` | 3주차 `main.py` 를 옮김. 문서를 `team/wiki` 로 바꾸고 청크 규칙을 팀 `evaluate.py` 와 맞춤. `build_rag_chain()`(한 번), `ask()`(질문마다) |
| `app/api.py` | `lifespan` 에서 `build_rag_chain()` 을 한 번 호출. `POST /ask` → `answer`, `sources`, `seconds`. `GET /health` |

**왜 `/ask` 를 `async def` 가 아니라 `def` 로 썼나:** `rag_chain.invoke()` 는 끝날 때까지 기다려야 하는 함수다. 그래서 `async def` 안에서 부르면 이벤트 루프가 멈춰 다른 요청을 받지 못한다. `def` 로 쓰면 FastAPI가 별도 스레드에서 실행해 다른 요청이 막히지 않는다.

`concurrency_test.py` 로 확인했다 (`/ask` 를 보내고 0.3초 뒤 `/health`, 2026-11-16).

| `/ask` 엔드포인트 | `/health` | `/ask` |
|---|---|---|
| `def` | 0.00초 | 2.71초 |
| `async def` | 2.97초 (`/ask` 가 끝날 때까지 막힘) | 3.23초 |

**`/ask` 응답 시간** (같은 질문 "Redis TTL은 몇 초로 정했어?", 서버 안에서 `ask()` 만 잰 값)

| 실행 방식 | 1번째 | 2번째 | 3번째 |
|---|---|---|---|
| 로컬 `uvicorn` | 3.70초 | 3.77초 | 2.65초 |
| Docker 컨테이너 | 25.72초 | 2.39초 | - |

- 출처는 매번 `3-rag-basics_sejin, redis-ttl-cache_mingi` 로 같았다. 답 문장은 매번 조금씩 달랐다.
- 컨테이너는 첫 요청만 느렸다 (2회 측정, 첫 요청 지연으로 보임).
- 3주차에 `main.py` 첫 호출이 느렸던 것(5.08초)은 서버에서는 재현되지 않았다. 서버는 모델을 켤 때 한 번만 올리기 때문이다.

## 3. Docker

모델과 DB는 이미지에 넣지 않고 볼륨으로 연결한다. 이미지에는 코드와 실행 환경만 들어 있다.

| 구분 | 내용 |
|---|---|
| 이미지 `rag-api` (2.83GB) | Python 3.11, torch 2.15.0 CPU 등 패키지, `app/rag.py`, `app/api.py` |
| 볼륨: Hugging Face 캐시 | bge-m3 모델 |
| 볼륨: `week4/chroma_db` | 벡터 DB |
| 볼륨: `team/wiki` | 위키 원문 (DB가 비었을 때만 사용) |

- torch는 CPU용 주소(`--index-url .../whl/cpu`)에서 먼저 설치한다. 그러지 않으면 리눅스에서 GPU용 torch가 깔려 이미지가 커진다
- `.dockerignore` 로 `.env`(API 키), `.venv`, `chroma_db` 를 이미지에서 뺐다 (이미지 안에 `.env` 가 없는 것을 확인함)
- Windows에서 만든 `chroma_db` 를 리눅스 컨테이너가 그대로 열었다 (다시 임베딩하지 않음)
- 6주차 k8s에서는 이 볼륨들을 PVC로 바꿀 예정

## 실행

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # ANTHROPIC_API_KEY, WIKI_DIR(팀 저장소 team\wiki 경로) 입력
```

**명령줄** (week4 폴더에서, 처음 실행하면 `chroma_db/` 를 만든다)

```powershell
python app/rag.py "Redis TTL은 몇 초로 정했어?"
```

**API 서버**

```powershell
uvicorn app.api:app --port 8000
```

브라우저에서 http://127.0.0.1:8000/docs → `POST /ask` → `{"question": "Redis TTL은 몇 초로 정했어?"}`

**Docker** (명령줄이나 API로 `chroma_db/` 를 먼저 만들어 둔다)

```powershell
docker build -t rag-api .
docker run --rm -p 8000:8000 --env-file .env -e WIKI_DIR=/wiki `
  -v "$env:USERPROFILE\.cache\huggingface:/root/.cache/huggingface" `
  -v "${PWD}\chroma_db:/app/chroma_db" `
  -v "<팀 저장소 경로>\team\wiki:/wiki:ro" `
  rag-api
```

- `-e WIKI_DIR=/wiki`: `.env` 의 Windows 경로를 컨테이너 안 경로로 덮어쓴다
- **리랭커 노트북**: VS Code에서 `rerank.ipynb` 를 열고 커널을 `week4\.venv` 로 선택한다. 셀 1의 `REPO` 를 팀 저장소 경로로 바꾼다. 리랭커 모델은 처음 실행할 때 받는다 (약 2GB)

## 한계

- **데이터 누수 1**: `team/wiki/rag-evaluation_mingi.md` 의 표에 평가 질문 원문이 들어 있다. 질문과 똑같은 문장이라 검색 1~2위를 차지하지만 답은 없다.
  - 기준선: q01·q13에서 1위, q07·q08·q16에서 2위
  - 리랭커: q01·q07·q16·q21에서 1위
  - 리랭커도 이 문제는 못 막았다
- **데이터 누수 2**: 내 위키 `3-rag-basics_sejin` 에 적어 둔 3주차 실행 결과 예시가 검색되었다. 그래서 `/ask` 답 본문에 옛 페이지 이름(`mingi/redis-ttl-cache`)이 따라 나왔다
- **정답 목록 누락**: `image-vs-container_doyu` 는 팀 위키에 늦게 들어와 질문셋 정답 목록에 없다.
  - q25(설계도 비유)에서 리랭커는 이 페이지("읽기 전용 설계도 … 실행한 인스턴스")를 1위로 올렸지만 감점되었다
  - `container-commands_mingi` 에도 "이미지는 컨테이너를 띄우기 위한 설계도"라는 문장이 있다
- 위 문제들 때문에 MRR 숫자는 실제 검색 품질과 차이가 있을 수 있다.

## 알게 된 점

- 리랭커는 순서를 더 잘 매기는 대신 미리 계산해 둘 수 없어서 CPU에서는 질문당 10~27초가 걸렸다
- 후보는 많을수록 좋은 것이 아니었다. 20개보다 10개가 점수도 높고 빨랐다.
- `async def` 안에서 동기 함수를 부르면 서버 전체가 멈춘다는 것을 숫자로 확인했다 (`/health` 0.00초 vs 2.97초)

## 막힌 점
- Windows에서 `localhost` 로 요청하면 약 2초가 더 걸림 (`/health` 2.05초). IPv6(`::1`)를 먼저 시도하기 때문 → `127.0.0.1` 로 해결
- `os.getenv("WIKI_DIR", 기본값)` 은 환경 변수가 있어도 기본값을 먼저 계산한다. 컨테이너(`/app`)에서 `BASE_DIR.parents[2]` 가 없어 IndexError → `os.getenv("WIKI_DIR") or 기본값` 으로 수정

## 파일

| 파일 | 내용 |
|---|---|
| `rerank.ipynb` | 리랭커 실험 (실행 결과 포함) |
| `results/*.json` | 기준선, 리랭커 20, 리랭커 10 채점 결과 (질문별 순위 포함) |
| `app/rag.py`, `app/api.py` | RAG 체인, FastAPI 서버 |
| `concurrency_test.py` | `def` vs `async def` 확인 스크립트 |
| `Dockerfile`, `.dockerignore` | 이미지 빌드 |
| `requirements.txt` | 버전 고정한 패키지 12개 |
| `.env.example` | 환경 변수 이름 견본 (`.env` 는 올리지 않음) |
