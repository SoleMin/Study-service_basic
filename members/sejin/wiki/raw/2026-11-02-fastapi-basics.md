# FastAPI 기초 개념 (내 말로)

> Claude 설명을 바탕으로 내가 정리한 내용.
> 확인 상태: 실습 전 (Day 1·2 실습 후 "실습 근거" 채우기)

## 0-1. FastAPI

파이썬으로 웹 API 서버를 만드는 프레임워크. 함수 위에 `@app.get("/주소")`를 붙이면 그 함수가 인터넷으로 요청을 받는 창구가 된다.

- 타입 힌트(`message: str`)만 적으면 들어온 데이터를 자동으로 검사해 준다 (Pydantic)
- 코드만 쓰면 API 설명서 겸 테스트 화면(`/docs`)이 자동으로 생긴다
- `async def`를 지원해서, 기다리는 일(LLM 호출, DB 조회)이 많은 서버에서 여러 요청을 동시에 처리할 수 있다

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

- `main:app` = "main.py 파일 안의 `app` 변수"
- 기본 포트는 8000

## 0-2. Redis

**정의**: 데이터를 디스크가 아니라 메모리에 저장하는 key-value 저장소. 데이터인 value를 key로 꺼내 쓴다.

**왜 쓰나**
- 메모리에 있다 → 빠르다
- 값마다 유효기간(TTL, Time To Live)을 걸면 시간이 지나면서 자동으로 지워진다
- → 자주 묻는 것을 잠깐 저장해 두는 캐시로 많이 쓴다

**기본 명령** (`redis-cli`에서)

```
SET chat:abc "답변" EX 60    # key=chat:abc, value="답변" 저장, EX 60 = 60초 뒤 자동 삭제
GET chat:abc                 # 값 꺼내기. 없거나 만료됐으면 (nil)
TTL chat:abc                 # 남은 유효기간(초). 만료되면 -2
DEL chat:abc                 # 지우기
```

**파이썬에서** (`redis` 패키지, async 버전)

```python
import redis.asyncio as redis

r = redis.from_url("redis://localhost:6379/0", decode_responses=True)   # r은 Redis 서버와 대화하는 창구(클라이언트)
await r.set("chat:abc", "답변", ex=60)   # 저장 + 60초 TTL
answer = await r.get("chat:abc")        # 없으면 None
```

- 기본 포트는 6379
- `decode_responses=True`: 꺼낸 값을 바이트가 아니라 글자(str)로 받기

**주의**
- 메모리에 저장하므로 Redis 컨테이너를 지우면 데이터도 사라짐 → 오래 보관할 데이터는 DB에 저장
- 키 이름은 `chat:질문해시`처럼 `용도:값` 형식으로 지어서 구분

## 1. HTTP 메서드

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

## 2. 엔드포인트 (endpoint)

**정의**: "메서드 + 주소" 한 쌍과, 그 요청을 처리할 함수를 묶은 것.
FastAPI에서는 함수 위에 데코레이터(`@`)를 달아 만든다.

```python
@app.get("/health")          # GET + /health 로 오면
def health():                # 이 함수를 실행해서
    return {"status": "ok"}  # 이걸 JSON으로 돌려줌

@app.post("/echo")           # POST + /echo 로 오면
def echo(req: EchoRequest):  # 이 함수를 실행
    ...
```

- 같은 주소라도 메서드가 다르면 다른 창구 (예: `GET /items`(목록 보기) vs `POST /items`(새로 만들기))
- 함수가 돌려준 딕셔너리(`{"status": "ok"}`)는 FastAPI가 자동으로 JSON으로 바꿔 보냄
- 없는 주소로 오면 404 Not Found, 주소는 있는데 메서드가 틀리면 405 Method Not Allowed
- 엔드포인트 목록이 그대로 `/docs` 화면에 나타남. API 설명서가 코드에서 자동으로 만들어지는 게 FastAPI의 장점

## 3. Pydantic 모델

들어오고 나가는 데이터의 모양을 파이썬 클래스로 적은 규칙. FastAPI가 이 규칙으로 요청 본문을 자동 검사하고, 파이썬 객체로 바꾼다.

```python
from pydantic import BaseModel, Field

class EchoRequest(BaseModel):                          # 신청서 양식
    message: str = Field(min_length=1, max_length=200) # 글자, 1~200자
    repeat: int = Field(default=1, ge=1, le=5)         # 정수, 1~5, 안 쓰면 1
```

- `message: str`, `repeat: int`: 타입 힌트 (이 칸에 들어갈 값의 종류)
- `Field(...)`: 추가 조건. `min_length`/`max_length`(글자 수), `ge`(이상, greater or equal), `le`(이하, less or equal), `default`(기본값)
- 기본값이 없는 칸(`message`)은 필수, 기본값이 있는 칸(`repeat`)은 선택

엔드포인트에 연결하면

```python
@app.post("/echo")
def echo(req: EchoRequest):   # ← 매개변수 타입을 모델로 지정하면 "본문을 이 양식으로 검사해라"
    return {"result": " ".join([req.message] * req.repeat)}
```

FastAPI가 대신 해 주는 것

1. 본문 JSON을 읽어서
2. 양식대로인지 검사하고
   - 맞으면 → `req.message`, `req.repeat`처럼 꺼내 쓸 수 있는 객체를 함수에 넘김
   - 틀리면 → 함수를 실행하지도 않고 `422 Unprocessable Entity`와 무엇이 틀렸는지를 알려줌
3. 형 변환도 해 줌. 예: `"repeat": "3"` → `3`, `"three"`처럼 바꿀 수 없으면 422

## 넷의 관계 한 줄

## 내가 만든 비유

## 헷갈렸던 점 / 질문

## 실습 근거 (Day 1·2 직접 돌린 뒤 채우기)
