<!-- merge_wiki.py 자동 생성: 원본 members/sejin/wiki/pages/2-fastapi-redis-async.md . 수정은 원본에서 하세요 -->

# 2주차: FastAPI, Redis, async

## Part 1. FastAPI 기초: HTTP 메서드, 엔드포인트, Pydantic, Redis

### 한 줄 정의

FastAPI는 함수 위에 @app.get("/주소")를 붙여 인터넷 요청을 받는 창구(엔드포인트)를 만드는 파이썬 프레임워크이고, 들어온 데이터는 Pydantic 모델로 검사하며, Redis는 답을 메모리에 유효기간(TTL)과 함께 저장해 두는 캐시로 쓴다.

### 왜 필요한가

LLM을 다른 프로그램이나 사용자가 쓰게 하려면, 주소로 요청을 받아 답을 돌려주는 창구가 필요하다. FastAPI는 입력 검사(422)와 API 설명서(/docs)를 코드에서 자동으로 만들어 줘서 창구를 빠르게 만들 수 있다.
LLM 호출은 느리고 돈이 들기 때문에, 같은 질문은 Redis에 저장해 둔 답으로 바로 돌려준다. PR #1을 로컬에서 돌렸을 때 같은 질문이 캐시 미스 2010ms → 캐시 히트 0.7ms였다.

### 최소 예제

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

class EchoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=200)
    repeat: int = Field(default=1, ge=1, le=5)

@app.get("/health")                     # GET /health
def health():
    return {"status": "ok"}

@app.post("/echo")                      # POST /echo, 본문은 EchoRequest 양식으로 검사
def echo(req: EchoRequest):
    return {"result": " ".join([req.message] * req.repeat)}
```

```powershell
uvicorn main:app --reload               # http://localhost:8000/docs 에서 눌러 보기
```

```python
import redis.asyncio as redis

r = redis.from_url("redis://localhost:6379/0", decode_responses=True)   # r은 Redis 서버와 대화하는 창구(클라이언트)
await r.set("chat:abc", "답변", ex=60)   # 저장 + 60초 TTL
answer = await r.get("chat:abc")        # 없으면 None → 캐시 미스
```

실행 결과 (PR #1 코드를 로컬에서 실행, 2026-11-02. 내 코드로는 Day 1·2에 다시 확인 예정):

```
GET  /health                                → {"status":"ok"}
POST /echo  {"message":"hi","repeat":9}      → 422, Input should be less than or equal to 5
POST /chat  같은 질문 2번                      → 2010ms (cached:false) → 0.7ms (cached:true)
redis-cli TTL chat:...                      → 57~59 (60초 설정)
```

### 개념 정리 (내 말로)

#### 0-1. FastAPI

파이썬으로 웹 API 서버를 만드는 프레임워크. 함수 위에 @app.get("/주소")를 붙이면 그 함수가 인터넷으로 요청을 받는 창구가 된다.

- 타입 힌트(message: str)만 적으면 들어온 데이터를 자동으로 검사해 준다 (Pydantic)
- 코드만 쓰면 API 설명서 겸 테스트 화면(/docs)이 자동으로 생긴다
- async def를 지원해서, 기다리는 일(LLM 호출, DB 조회)이 많은 서버에서 여러 요청을 동시에 처리할 수 있다

**구성 요소**

| 이름 | 역할 |
|---|---|
| uvicorn | 네트워크로 들어오는 요청을 받는 서버 프로그램 |
| FastAPI | 주소를 보고 어느 함수가 처리할지 정함 |
| Pydantic | 들어온 데이터가 양식대로인지 검사 |

**요청이 처리되는 흐름**

```
클라이언트 ──요청──▶ uvicorn ──▶ FastAPI(주소로 함수 찾기) ──▶ Pydantic(검사) ──▶ 내 함수 ──▶ JSON 응답
```

**최소 예제**

```python
# main.py
from fastapi import FastAPI

app = FastAPI()                 # 서버(앱) 만들기

@app.get("/health")             # GET /health 창구
def health():
    return {"status": "ok"}
```

```powershell
uvicorn main:app --reload       # main.py 안의 app을 실행. --reload: 코드 고치면 자동 재시작
# 브라우저: http://localhost:8000/health → {"status":"ok"}
#           http://localhost:8000/docs   → 자동 생성된 API 설명서
```

- main:app = "main.py 파일 안의 app 변수"
- 기본 포트는 8000

#### 0-2. Redis

정의: 데이터를 디스크가 아니라 메모리에 저장하는 key-value 저장소. 데이터인 value를 key로 꺼내 쓴다.

**왜 쓰나**
- 메모리에 있다 → 빠르다
- 값마다 유효기간(TTL, Time To Live)을 걸면 시간이 지나면서 자동으로 지워진다
- → 자주 묻는 것을 잠깐 저장해 두는 캐시로 많이 쓴다

기본 명령 (redis-cli에서)

```
SET chat:abc "답변" EX 60    # key=chat:abc, value="답변" 저장, EX 60 = 60초 뒤 자동 삭제
GET chat:abc                 # 값 꺼내기. 없거나 만료됐으면 (nil)
TTL chat:abc                 # 남은 유효기간(초). 만료되면 -2
DEL chat:abc                 # 지우기
```

파이썬에서 (redis 패키지, async 버전)

```python
import redis.asyncio as redis

r = redis.from_url("redis://localhost:6379/0", decode_responses=True)   # r은 Redis 서버와 대화하는 창구(클라이언트)
await r.set("chat:abc", "답변", ex=60)   # 저장 + 60초 TTL
answer = await r.get("chat:abc")        # 없으면 None
```

- 기본 포트는 6379
- decode_responses=True: 꺼낸 값을 바이트가 아니라 글자(str)로 받기

**주의**
- 메모리에 저장하므로 Redis 컨테이너를 지우면 데이터도 사라짐 → 오래 보관할 데이터는 DB에 저장
- 키 이름은 chat:질문해시처럼 용도:값 형식으로 지어서 구분

#### 1. HTTP 메서드

| 메서드 | 뜻 | 본문 | 예 |
|---|---|---|---|
| GET | 조회. 데이터를 가져오기만 함 | 보통 없음 | 서버 상태 확인, 게시글 보기 |
| POST | 처리 요청 / 새로 만들기. 데이터를 보냄 | 있음 | 질문 보내기, 회원가입, 글쓰기 |
| PUT | 통째로 바꾸기 | 있음 | 프로필 전체 수정 |
| PATCH | 일부만 바꾸기 | 있음 | 닉네임만 수정 |
| DELETE | 지우기 | 보통 없음 | 글 삭제 |

```
GET    /posts/1                                          # 1번 글 보기 (본문 없음)
POST   /posts    {"title": "FastAPI", "content": "..."}  # 새 글 쓰기 → 서버가 번호 붙여 201 Created
PUT    /posts/1  {"title": "도커 복습", "content": "..."} # 1번 글을 보낸 내용으로 통째로 교체 (모든 칸 보냄)
PATCH  /posts/1  {"title": "도커 복습 2회차"}             # 1번 글의 제목만 수정 (바꿀 칸만 보냄)
DELETE /posts/1                                          # 1번 글 삭제 → 204 No Content
```

#### 2. 엔드포인트 (endpoint)

정의: "메서드 + 주소" 한 쌍과, 그 요청을 처리할 함수를 묶은 것.
FastAPI에서는 함수 위에 데코레이터(@)를 달아 만든다.

```python
@app.get("/health")          # GET + /health 로 오면
def health():                # 이 함수를 실행해서
    return {"status": "ok"}  # 이걸 JSON으로 돌려줌

@app.post("/echo")           # POST + /echo 로 오면
def echo(req: EchoRequest):  # 이 함수를 실행
    ...
```

- 같은 주소라도 메서드가 다르면 다른 창구 (예: GET /items(목록 보기) vs POST /items(새로 만들기))
- 함수가 돌려준 딕셔너리({"status": "ok"})는 FastAPI가 자동으로 JSON으로 바꿔 보냄
- 없는 주소로 오면 404 Not Found, 주소는 있는데 메서드가 틀리면 405 Method Not Allowed
- 엔드포인트 목록이 그대로 /docs 화면에 나타남. API 설명서가 코드에서 자동으로 만들어지는 게 FastAPI의 장점

#### 3. Pydantic 모델

들어오고 나가는 데이터의 모양을 파이썬 클래스로 적은 규칙. FastAPI가 이 규칙으로 요청 본문을 자동 검사하고, 파이썬 객체로 바꾼다.

```python
from pydantic import BaseModel, Field

class EchoRequest(BaseModel):                          # 신청서 양식
    message: str = Field(min_length=1, max_length=200) # 글자, 1~200자
    repeat: int = Field(default=1, ge=1, le=5)         # 정수, 1~5, 안 쓰면 1
```

- message: str, repeat: int: 타입 힌트 (이 칸에 들어갈 값의 종류)
- Field(...): 추가 조건. min_length/max_length(글자 수), ge(이상, greater or equal), le(이하, less or equal), default(기본값)
- 기본값이 없는 칸(message)은 필수, 기본값이 있는 칸(repeat)은 선택

엔드포인트에 연결하면

```python
@app.post("/echo")
def echo(req: EchoRequest):   # ← 매개변수 타입을 모델로 지정하면 "본문을 이 양식으로 검사해라"
    return {"result": " ".join([req.message] * req.repeat)}
```

FastAPI가 대신 해 주는 것

1. 본문 JSON을 읽어서
2. 양식대로인지 검사하고
   - 맞으면 → req.message, req.repeat처럼 꺼내 쓸 수 있는 객체를 함수에 넘김
   - 틀리면 → 함수를 실행하지도 않고 422 Unprocessable Entity와 무엇이 틀렸는지를 알려줌
3. 형 변환도 해 줌. 예: "repeat": "3" → 3, "three"처럼 바꿀 수 없으면 422

### 내가 막힌 점

**헷갈렸던 점**
- compose 안에서 Redis 주소는 localhost가 아니라 서비스 이름 redis(redis://redis:6379/0). 컨테이너 입장에서 localhost는 자기 자신
- Claude 응답의 content[0]이 답이 아닐 수 있음. 최신 모델은 첫 조각이 "생각" 조각일 수 있어서 type == "text"인 조각을 골라 꺼냄

### 출처

- FastAPI 공식 문서(한국어), 첫걸음 — https://fastapi.tiangolo.com/ko/tutorial/first-steps/
- FastAPI 공식 문서(한국어), 요청 본문 — https://fastapi.tiangolo.com/ko/tutorial/body/
- FastAPI 공식 문서(한국어), 본문 - 필드 — https://fastapi.tiangolo.com/ko/tutorial/body-fields/
- Pydantic Docs, Models — https://docs.pydantic.dev/latest/concepts/models/
- MDN, HTTP 요청 메서드 — https://developer.mozilla.org/ko/docs/Web/HTTP/Methods
- MDN, HTTP 상태 코드 — https://developer.mozilla.org/ko/docs/Web/HTTP/Status
- Redis Docs, SET — https://redis.io/docs/latest/commands/set/
- Redis Docs, redis-py guide — https://redis.io/docs/latest/develop/clients/redis-py/
- redis-py, Asyncio Examples — https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
- Docker Docs, Set environment variables (compose env_file) — https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/
- 팀 저장소 PR #1 (addie/week2) 로컬 실행 결과

---

## Part 2. async 함수는 언제 필요한가

### 한 줄 정의

async def 함수는 작업하는 동안 await을 통해 제어권을 다른 작업에 넘겨주어, 서버 하나가 여러 작업을 처리하게 하는 함수다. 

### 왜 필요한가

LLM 호출은 답이 올 때까지 몇 초씩 걸리므로 서버가 멈춰 있으면 요청 n개에 n × (기다리는 시간)이 걸린다. 실험에서 2초 기다리는 요청 5개를 동시에 보냈더니, async def + await은 전체 2.02초, 여러작업을 하나씩 하면 10.01초가 걸렸다. 

### 최소 예제

```python
import asyncio, time
from fastapi import FastAPI

app = FastAPI()

@app.get("/wait/async")
async def wait_async():
    await asyncio.sleep(2)     # 기다리는 동안 양보 (좋은 예)
    return {"ok": True}

@app.get("/wait/blocking")
async def wait_blocking():
    time.sleep(2)              # async 안에서 양보 없이 멈춤 (나쁜 예)
    return {"ok": True}

@app.get("/wait/sync")
def wait_sync():
    time.sleep(2)              # 일반 def → FastAPI가 스레드풀에서 실행
    return {"ok": True}

@app.get("/cpu/async")
async def cpu_async():
    s = sum(i * i for i in range(12_000_000))   # CPU 계산 (기다림 없음, 약 0.7초)
    return {"ok": True}
```

엔드포인트마다 요청 5개를 동시에 보냄 (이 PC, 2026-11-02, 두 번 측정):

```
엔드포인트        동시 5개 전체   요청별 시간(초)
/wait/async       2.02s / 2.03s   다섯 개 모두 2.02
/wait/blocking   10.01s / 10.01s  2.00, 4.00, 6.01, 8.01, 10.01

```

### 개념 정리



**용어**
- async def: 비동기 함수
- await: 다른 작업에 제어권 줄 때 쓴다. async def 안에서만 사용 가능
- 이벤트 루프: 제어권 넘겨받을 작업을 정한다.. uvicorn이 돌린다

**기다리는 일 vs 계산하는 일**

| 종류 | 시간을 쓰는 곳 | 예 | async 효과 |
|---|---|---|---|
| I/O 대기 | 다른 곳의 답을 기다림 (CPU는 놀고 있음) | LLM API, DB, Redis, 다른 서버 요청 | 있음 (5개 10초 → 2초) |
| CPU 계산 | CPU가 직접 일함 | 임베딩 계산, 큰 반복문, 이미지 처리 | 없음 (async def, def 모두 0.7초 × 5) |

async는 동시성(한 명이 여러 일을 번갈아)이지 병렬성(여러 명이 동시에)이 아니다. 계산을 빠르게 하려면 프로세스나 워커를 여러 개 써야 한다.


**2주차 코드에 적용**

| 엔드포인트 | 선택 | 이유 |
|---|---|---|
| /health, /echo | def (어느 쪽이든) | 기다리는 일 없음 |
| /chat | async def | Redis 조회와 LLM 호출을 기다림. redis.asyncio, AsyncAnthropic 사용 |
| /chat/stream | async def | LLM이 보내는 조각을 기다리며 흘려보냄 |
| (3주차) 임베딩 계산 | async로 해결 안 됨 | CPU 계산 |

### 내가 막힌 점
- await을 빠뜨리면 에러가 아니라 경고(coroutine ... was never awaited)만 뜨고, 값 대신 코루틴 객체가 들어온다 → 결과가 이상하면 await 빠진 곳부터 찾는다
- async 클라이언트(redis.asyncio, AsyncAnthropic)는 서버가 켜진 뒤 lifespan에서 만든다. 파일 맨 위에서 만들면 attached to a different loop 에러가 날 수 있다.

### 출처

- FastAPI 공식 문서(한국어), 동시성과 async / await — https://fastapi.tiangolo.com/ko/async/
- FastAPI 공식 문서(한국어), Lifespan 이벤트 — https://fastapi.tiangolo.com/ko/advanced/events/
- Python 공식 문서(한국어), asyncio — https://docs.python.org/ko/3/library/asyncio.html
- Python 공식 문서(한국어), 코루틴과 태스크 — https://docs.python.org/ko/3/library/asyncio-task.html
