# 모던 AI 백엔드 아키텍처 - FastAPI (SSE, StreamingResponse)

# FastAPI: Async Traffic Controller

## 이벤트 루프 관리

- FastAPI의 이벤트 루프(Event Loop)는 **ASGI(Asynchronous Server Gateway Interface)** 사양을 기반으로 구축되어 비동기 요청 처리와 동시성(Concurrency)을 효율적으로 관리합니다.

### 1. `async def`와 메인 이벤트 루프

FastAPI의 경로 작업 함수(Path Operation Function)를 `async def`로 선언하면 해당 함수는 메인 이벤트 루프에서 직접 실행됩니다.

- **비동기 대기 (`await`)**: 함수 내부에서 비동기 I/O 작업(예: 비동기 DB 조회, 비동기 HTTP 요청 등)을 다룰 때 `await` 키워드를 사용하여 비동기적으로 대기합니다.
- **동시성 처리**: 한 요청이 I/O 작업을 `await`하며 대기하는 동안, 메인 이벤트 루프는 정지하지 않고 다른 들어오는 요청을 계속 처리합니다.

### 2. 일반 `def` (동기 함수) 처리 방식: 쓰레드풀 위임

`async def`가 아닌 일반 동기 함수 (`def`)로 경로 작업 함수나 의존성을 선언하더라도 FastAPI는 이를 안전하게 동작시킵니다.

- **이벤트 루프 차단(Blocking) 방지**: 동기 함수가 메인 이벤트 루프를 멈추지 않도록, FastAPI는 일반 `def` 함수를 별도의 **쓰레드풀 워커(Threadpool worker)**에 위임하여 실행하고 이를 `await`합니다.
- **유연한 혼용**: 의존성 주입(`Depends`)이나 스트리밍 응답(StreamingResponse, SSE 등) 작성 시 `async def` 함수와 일반 `def` 함수를 자유롭게 섞어서 사용할 수 있으며, FastAPI가 올바르게 실행 방식을 관리합니다.

### 3. 이벤트 루프 관련 주의사항

- **`RuntimeError: Task attached to a different loop` 예방**: 이벤트 루프에 바인딩되는 비동기 객체(예: 비동기 DB 클라이언트 등)를 생성할 때는 반드시 이벤트 루프가 활성화된 비동기 함수 내부나 시작 이벤트 콜백(예: `@app.on_event("startup")` 또는 lifespan 이벤트)에서 인스턴스화해야 에러를 방지할 수 있습니다.

## Async/Await: I/O 바운드 작업 동시성 처리

DB쿼리, LLM 호출 등 I/O 바운드 작업시 블로킹(Blocking) 없이 동시성 요청을 처리함.

```python
@app.get('/generate')
async def generate_response(prompt: str):
	return await process_ai_request(prompt)
```

## Path Operation Decorator

직관적인 라우팅, OpenAPI 스키마 자동 문서화 지원

## FastAPI + Pydantic: Automatic Validation

Pydantic 모델을 통한 복합 데이터 유효성 자동 검사

FastAPI에서는 **Pydantic의 `BaseModel`과 `Field`**를 조합하여 API 요청 본문(Request Body)의 데이터 구조를 정의하고, 자동 타입 변환, 유효성 검증, 데이터 구조화를 효율적으로 처리할 수 있습니다.

### 1. Pydantic `BaseModel`을 통한 요청 본문 기본 정의

클라이언트가 전송하는 JSON 데이터를 수신하려면 `pydantic.BaseModel`을 상속받는 데이터 모델 클래스를 작성하고, 경로 작업 함수(Path Operation Function)의 매개변수로 선언합니다.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 1. 데이터 모델 정의
class Item(BaseModel):
    name: str                           # 필수(Required) 필드
    description: str | None = None      # 선택(Optional) 필드 (기본값 None)
    price: float                        # 필수(Required) 필드
    tax: float | None = None            # 선택(Optional) 필드

# 2. 경로 작업 함수 매개변수로 지정
@app.post("/items/")
async def create_item(item: Item):
    return item
```

- **자동 타입 변환 및 검증**: FastAPI는 요청 본문의 JSON 데이터를 읽어 지정한 Python 타입으로 자동 변환하며, 유효하지 않은 데이터가 들어오면 422 Unprocessable Entity 에러와 상세 메시지를 반환합니다.
- **필수/선택 필드 구분**: 기본값이 작성되지 않은 필드는 필수값으로 취급되며, 기본값이 명시되어 있으면 선택 필드로 처리됩니다.

### 2. `Field`를 활용한 필드 단위 상세 검증 및 메타데이터 설정

Pydantic의 `Field`를 사용하면 각 필드별 제약 조건(최소/최대 길이, 수치 범위 등)과 OpenAPI 스키마용 메타데이터를 세밀하게 설정할 수 있습니다.

> **주의**: `Field`는 `fastapi`가 아니라 **`pydantic` 모듈에서 직접 임포트**해야 합니다.

```python
from typing import Annotated
from fastapi import Body, FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = Field(
        default=None,
        title="상품 설명",
        max_length=300  # 문자열 최대 길이 검증
    )
    price: float = Field(
        gt=0, # 0보다 커야 함 (greater than)
        description="가격은 0보다 큰 숫자여야 합니다."
    )
    tax: float | None = None

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Annotated[Item, Body(embed=True)]):
    return {"item_id": item_id, "item": item}
```

- **문자열 제약 조건**: `min_length`, `max_length`, `pattern`(정규표현식) 등
- **숫자 제약 조건**: `gt` (크음), `ge` (이상), `lt` (작음), `le` (이하) 등
- **메타데이터**: `title`, `description`, `example` 등을 통해 Swagger UI 문서에 표시될 설명을 추가

### 3. 복합 및 중첩 요청 본문 구조 관리

#### ① 다중 본문 매개변수 (Multiple Body Parameters)

하나의 요청에서 여러 Pydantic 모델을 본문 매개변수로 받는 경우, FastAPI는 JSON 최상위 구조에서 각 매개변수 이름을 키(Key)로 하는 JSON 구조를 요구합니다.

```python
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item, user: User):
    return {"item_id": item_id, "item": item, "user": user}
```

**기대하는 JSON 요청 구조**:

```json
{
  "item": { "name": "Foo", "price": 42.0 },
  "user": { "username": "dave" }
}
```

#### ② 단일 모델의 키 감싸기 (`embed=True`)

단일 Pydantic 모델을 사용할 때도 최상위에 모델명을 키로 두고 싶다면 `Body(embed=True)`를 지정합니다.

```python
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Annotated[Item, Body(embed=True)]):
    return {"item_id": item_id, "item": item}
```

#### ③ 중첩 모델 (Nested Models)

모델 내부 필드의 타입으로 다른 Pydantic 모델이나 그 리스트(`list[SubModel]`)를 선언하여 깊은 계층 구조의 JSON도 손쉽게 검증할 수 있습니다.

```python
class Image(BaseModel):
    url: str
    name: str

class Item(BaseModel):
    name: str
    price: float
    images: list[Image] | None = None  # 중첩된 submodel 리스트
```

### 4. 고급 검증 및 부분 업데이트(PATCH) 활용

- **커스텀 검증기 (`AfterValidator`)**: Pydantic의 `AfterValidator`와 `Annotated`를 조합하여 비즈니스 로직에 맞춘 사용자 지정 검증 함수를 연결할 수 있습니다.
- **부분 업데이트 (`PATCH`)**: `PATCH` 요청 처리 시 `item.model_dump(exclude_unset=True)` 옵션을 사용하면 클라이언트가 명시적으로 전달한 필드만 추출하여 기존 데이터를 안전하게 업데이트할 수 있습니다.

## SSE & Streaming Response

FastAPI에서는 **StreamingResponse**와 Server-Sent Events (SSE)를 통해 대용량 파일이나 AI LLM 생성 텍스트와 같은 비동기 데이터 스트리밍을 효과적으로 구현할 수 있습니다.

### 1. `StreamingResponse`를 활용한 일반 데이터 및 바이너리 스트리밍

순수 문자열(예: LLM 토큰 응답)이나 대용량 이미지·비디오 등 이진 데이터를 조각(chunk) 단위로 클라이언트에 전송할 때 **`StreamingResponse`**를 활용합니다.

- **기본 사용법**: 경로 작업 함수에 `response_class=StreamingResponse`를 지정하고, 제너레이터 함수 내부에서 `yield` 키워드를 사용해 데이터를 순차 전송합니다.
- **커스텀 응답 클래스**: `Content-Type` 헤더를 명시해야 하는 경우 `StreamingResponse`를 상속받아 `media_type`을 설정한 클래스를 정의할 수 있습니다.

```python
from collections.abc import AsyncIterable
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

# 1. 문자열/텍스트 스트리밍
@app.get("/story/stream", response_class=StreamingResponse)
async def stream_story() -> AsyncIterable[str]:
    lines = ["첫 번째 문장입니다.", "두 번째 문장입니다.", "세 번째 문장입니다."]
    for line in lines:
        yield line

# 2. Content-Type(PNG)을 정의한 커스텀 StreamingResponse
class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"

@app.get("/image/stream", response_class=PNGStreamingResponse)
async def stream_image(image_bytes: bytes) -> AsyncIterable[bytes]:
    # 바이너리 바이트 조각(chunk) 단위 스트리밍
    yield image_bytes
```

### 2. Server-Sent Events (SSE)를 활용한 이벤트 스트리밍

- SSE(Server-Sent Events)는 `text/event-stream` 포맷을 사용하며, 브라우저의 `EventSource` API와 표준으로 호환되어 AI 대화 스트리밍, 실시간 알림, 로그 모니터링 등에 널리 쓰입니다.

FastAPI는 `fastapi.sse` 모듈을 통해 SSE 스트리밍 기능을 제공합니다.

#### ① 기본 SSE 구현

`response_class=EventSourceResponse`를 지정하고 데이터를 `yield`하면 각 데이터가 자동으로 JSON 인코딩되어 `data:` 필드 형태로 전송됩니다. 반환 타입으로 `AsyncIterable[Model]`을 선언하면 Pydantic을 통한 직렬화 성능 및 데이터 검증 이점을 얻을 수 있습니다.

```python
from collections.abc import AsyncIterable
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()

class Message(BaseModel):
    text: str

@app.get("/items/stream", response_class=EventSourceResponse)
async def sse_items() -> AsyncIterable[Message]:
    messages = [Message(text="Hello"), Message(text="World")]
    for msg in messages:
        yield msg
```

#### ② SSE 메타데이터 및 원본 데이터 전송 (`ServerSentEvent`)

이벤트 명칭(`event`), 식별자(`id`), 재연결 간격(`retry`) 등 메타데이터를 추가하거나, JSON 인코딩 없이 순수 텍스트/로그나 종료 신호(`[DONE]`)를 보낼 때는 **`ServerSentEvent`** 인스턴스를 반환합니다.

```python
from collections.abc import AsyncIterable
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()

@app.get("/chat/stream", response_class=EventSourceResponse)
async def stream_chat() -> AsyncIterable[ServerSentEvent]:
    # 1. event, id, retry 등 세부 메타데이터 설정
    yield ServerSentEvent(data={"token": "Hello"}, event="chat_update", id="1", retry=5000)

    # 2. JSON 인코딩이 없는 원본 텍스트 전송 (raw_data)
    yield ServerSentEvent(raw_data="[DONE]", event="done")
```

#### ③ 재연결 제어 및 네트워크 최적화

- **연결 재개 (`Last-Event-ID`)**: 클라이언트 재연결 시 전송되는 `Last-Event-ID` 헤더를 매개변수로 읽어와 중단되었던 위치부터 스트림을 이어 나갈 수 있습니다.
- **POST 요청 지원**: GET 방식뿐만 아니라 POST 방식에서도 SSE 스트리밍이 지원되므로 MCP(Model Context Protocol) 등 프롬프트 데이터를 동반한 스트리밍에 적합합니다.
- **자동 최적화 기능**: 15초 간격의 핑(ping) 주석 전송, `Cache-Control: no-cache`, Nginx 프록시 버퍼링 방지를 위한 `X-Accel-Buffering: no` 헤더가 설정되어 제공됩니다.

## BackgroundTasks 모듈

FastAPI에서는 **`BackgroundTasks`** 모듈을 사용하여 클라이언트에게 응답을 즉시 반환한 후, 백그라운드에서 작업을 후처리할 수 있습니다.

### 1. `BackgroundTasks`를 활용한 기본 후처리

이메일 통지 발송이나 파일 후처리처럼 클라이언트가 작업 완수를 직접 기다릴 필요가 없는 경우에 활용됩니다.

- **매개변수 선언**: 경로 작업 함수(Path operation function) 또는 의존성(Dependency)의 매개변수로 `BackgroundTasks` 타입을 지정합니다.
- **작업 등록**: `background_tasks.add_task()` 메서드에 실행할 함수와 전달할 인자들을 넘겨줍니다.
- **함수 타입**: 작업 함수는 `async def` 함수뿐만 아니라 일반 동기 `def` 함수도 지원되며, FastAPI가 알아서 올바르게 처리합니다.

```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

# 후처리할 백그라운드 작업 함수
def write_log(filename: str, message: str):
    with open("log.txt", mode="a") as log:
        log.write(f"File: {filename}, Status: {message}\n")

@app.post("/process/{filename}")
async def process_file(filename: str, background_tasks: BackgroundTasks):
    # 클라이언트에게 응답을 즉시 반환하면서 백그라운드 작업 등록
    background_tasks.add_task(write_log, filename, message="Processing started")
    return {"message": "요청이 접수되었습니다. 백그라운드에서 후처리됩니다."}
```

---

### 2. 무거운 작업(Heavy Computation) 처리 시 권장 사항

- **`BackgroundTasks`의 유용성**: 애플리케이션과 동일한 프로세스 내에서 메모리나 변수를 공유해야 하거나, 이메일 전송·단순 로그 작성 등의 가벼운 작업에 적합합니다.
- **무거운 작업 분리 필요성**: CPU 자원 소모가 크거나 장시간 실행되는 **무거운 연산 작업(Heavy background computation)**의 경우, FastAPI 서버 프로세스의 자원을 점유할 수 있습니다.
- **분산 큐 도입 (Celery, Redis, RabbitMQ)**: 이러한 무거운 작업은 Celery나 Redis, RabbitMQ 등의 메시지 큐/작업 관리 도구를 활용하여 별도의 워커 프로세스나 독립된 외부 서버로 분산시켜 처리하는 것이 안전합니다.

## Redis: 다중 프로세스 및 다중 서버 환경으로 작업을 분산

FastAPI에서 무거운 CPU 연산이나 장시간 실행되는 작업을 웹 서버 프로세스와 분리하기 위해 Redis와 Celery(전용 워커)를 연동하는 백엔드 아키텍처 구성 방법을 소개합니다.

### 1. 왜 Redis와 외부 워커(Celery)가 필요한가?

FastAPI 내장 `BackgroundTasks`는 웹 애플리케이션과 동일한 프로세스 및 메모리 공간에서 동작합니다. 따라서 CPU 자원 소모가 크거나 장시간 걸리는 연산을 처리할 경우, 메모리를 공유할 필요가 없는 독립된 **Celery**와 같은 작업 큐 도구와 **Redis** 같은 메시지 브로커(Job Queue)를 도입하여 다중 프로세스 및 다중 서버 환경으로 작업을 분산 이관하는 것이 안전합니다.

### 2. 전체 백엔드 아키텍처 구조

전체 아키텍처는 **클라이언트**, **FastAPI (API Server)**, **Redis (Message Broker & Result Store)**, **Celery (Worker Process)**의 4가지 주요 컴포넌트로 구성됩니다.

```
 [Client] ──(1) Heavy Task 요청──> [FastAPI Server]
    │                                  │
    │ (4) task_id 응답 반환            │ (2) Task 메시지 발행 (Producer)
    ▼                                  ▼
[Client]                      [Redis Broker / Job Queue]
    │                                  │
    │ (5) 결과 조회/SSE 수신           │ (3) Task 수신 및 실행 (Consumer)
    ▼                                  ▼
 [FastAPI Server] <──(6) 결과 조회── [Celery Worker Process]
```

1. **Client (클라이언트)**: AI 모델 추론, 대용량 데이터 처리, 동영상 인코딩 등의 무거운 작업을 API로 요청합니다.
2. **FastAPI (API Server)**: 요청 데이터를 검증한 후, 작업을 직접 처리하지 않고 작업 파라미터를 **Redis 큐에 브로커 메시지로 발행(Producer)**합니다.
3. **즉시 응답 반환**: 클라이언트에게 작업 식별자(`task_id`)와 함께 `202 Accepted` 응답을 즉시 반환하여 HTTP 요청/응답 차단(Blocking)을 방지합니다.
4. **Redis (Message Broker & Result Store)**:
   - **Job Queue (브로커)**: FastAPI가 전달한 백그라운드 작업들을 대기열로 안전하게 보관합니다.
   - **Result Backend (결과 저장소)**: 워커가 실행을 완료한 상태(Pending, Success, Failed)와 결과 데이터를 키-값 형태로 저장합니다.
5. **Celery Worker (전용 워커 프로세스)**: FastAPI와 완전히 분리된 독립 프로세스로 동작하며, Redis 큐를 상시 모니터링하다가 들어온 작업을 꺼내어 연산을 수행하고 결과를 Redis에 기록합니다.
6. **결과 확인 (Polling / SSE / WebSockets)**: 클라이언트는 `task_id`를 통해 진행 상태를 주기적으로 조회(Polling)하거나, FastAPI의 **Server-Sent Events(SSE)** 또는 **WebSockets**를 통해 실시간 완료 알림을 수신합니다.

### 3. 간단한 연동 예시 코드

#### ① Celery 워커 및 Redis 브로커 설정 (`tasks.py`)

```python
from celery import Celery

# Redis를 메시지 브로커 및 결과 저장소(Result Backend)로 지정
celery_app = Celery(
    "worker_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task
def heavy_computation_task(data: dict) -> dict:
    import time
    # 무거운 연산/후처리 작업 시뮬레이션
    time.sleep(10)
    return {"status": "completed", "processed_data": data}
```

#### ② FastAPI API 서버 구현 (`main.py`)

```python
from fastapi import FastAPI, status
from pydantic import BaseModel
from tasks import celery_app, heavy_computation_task

app = FastAPI()

class TaskRequest(BaseModel):
    payload: dict

@app.post("/tasks/heavy", status_code=status.HTTP_202_ACCEPTED)
async def submit_heavy_task(request: TaskRequest):
    # Celery 워커로 비동기 작업 전달
    task = heavy_computation_task.delay(request.payload)
    return {"task_id": task.id, "message": "작업이 워커 큐에 제출되었습니다."}

@app.get("/tasks/heavy/{task_id}")
async def get_task_result(task_id: str):
    # Redis 결과 저장소에서 작업 상태 및 결과 확인
    task_result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }
```

### 4. 아키텍처 도입의 핵심 이점

- **응답성 최적화**: 무거운 연산 중에도 FastAPI 메인 이벤트 루프가 멈추지 않고 신규 HTTP 요청을 계속 처리합니다.
- **독립적 수평 확장**: 작업량 증가 시 FastAPI 웹 서버와 무관하게 Celery 워커 컨테이너/서버만 개별적으로 확장할 수 있습니다.
- **작업 신뢰성 보장**: Redis의 Job Queue를 활용해 작업 유실을 방지하고 실패 시 재시도(Retry) 관리가 가능해집니다.

---

## 번외: Redis로 AI 에이전트 기억망 구축하기

Redis를 단순한 키-값 캐시를 넘어 **AI 에이전트의 통합 Memory Layer**로 활용하면, 단일 Redis 인스턴스 위에서 세션 간 지속되는 에이전트의 작업 기억, 장기적인 의미적 회상, 시간순 이벤트 기록을 모두 효율적으로 처리할 수 있습니다.

### 1. AI 에이전트 기억망의 3가지 핵심 구조

AI 에이전트가 사람처럼 상황을 다단계로 기억하고 활용하기 위해 Redis 데이터 구조를 다음과 같이 3개 계층으로 매핑하여 구축합니다.

#### ① 작업 기억 (Working Memory / Short-term Memory)

- **개념**: 에이전트의 현재 실행 스레드, 대화 세션 컨텍스트, 중간 추론 과정(Chain-of-Thought)을 유지하는 단기 기억 영역입니다.
- **Redis 데이터 구조 및 용법**:
  - **`Hash` / `JSON`**: 각 대화 세션이나 에이전트 스레드별 상태 정보를 구체적인 키-값 혹은 중첩 구조로 관리합니다.
  - **TTL(Time-To-Live)**: 특정 시간 동안 활동이 없는 세션은 자동 만료되도록 설정하여 메모리를 효율적으로 관리합니다.

#### ② 장기 기억 및 의미적 회상 (Long-term Memory & Semantic Recall)

- **개념**: 과거 세션의 경험, 사용자 선호도, 에이전트 지식 베이스 중 현재 상황과 의미상 유사한(Semantically Similar) 정보를 찾아 가져오는 장기 기억 영역입니다.
- **Redis 데이터 구조 및 용법**:
  - **`JSON` + `VECTOR` 필드**: 에이전트가 기억해야 할 텍스트 및 메타데이터를 JSON 문서로 저장하고, 해당 텍스트의 임베딩(Vector)을 함께 관리합니다.
  - **벡터 인덱스 생성 (`FT.CREATE`)**: `FT.CREATE` 명령을 통해 JSON 문서 내의 `VECTOR` 필드(HNSW 또는 FLAT 알고리즘, Cosine 거리 측정)를 secondary index로 등록합니다.
  - **KNN 및 하이브리드 검색 (`FT.SEARCH`, `FT.HYBRID`)**: 에이전트가 유저의 질의를 받으면 임베딩 유사도 검색(`KNN`)을 수행하거나, 키워드 검색과 벡터 유사도를 결합한 하이브리드 검색(`FT.HYBRID`)을 통해 관련된 과거 기억을 정밀하게 회상합니다.

#### ③ 시간순 이벤트 로그 (Time-ordered Event Log)

- **개념**: 에이전트가 어떤 도구(Tool)를 호출했는지, 시스템과 어떤 이벤트를 주고받았는지를 순서대로 기록하는 추적/감사 기억 영역입니다.
- **Redis 데이터 구조 및 용법**:
  - **`Streams`**: 발생 순서대로 덧붙여지는(Append-only) 구조를 제공하여 에이전트의 행동 이력과 이벤트 스트림을 시간순으로 안전하게 로깅하고 재현할 수 있게 합니다.

### 2. 기억망 고도화를 위한 시너지 기능

- **시맨틱 캐싱 (Semantic Cache)**: 클라이언트의 질문이 완전히 동일하지 않더라도 의미상 유사할 경우, LLM을 재호출하지 않고 Redis에 캐싱된 과거 에이전트 답변을 즉시 반환하여 토큰 비용과 추론 지연 시간을 크게 줄일 수 있습니다.
- **구조화된 필터링과 벡터 검색의 결합**: 특정 사용자 ID나 카테고리 태그 조건(`TAG`, `NUMERIC` 필드)과 벡터 유사도 검색을 단 한 번의 Redis 쿼리로 결합(Pre-filtering)하여 정밀한 장기 기억 검색을 구현합니다.

## FastAPI + Redis 아키텍처

FastAPI와 Redis를 함께 활용하여 모던 AI 백엔드 및 에이전트(Agent) 시스템을 구축할 때, 각 도구의 역할과 두 시스템이 연결되는 아키텍처 흐름은 다음과 같이 정리할 수 있습니다.

### 1. 각 도구의 담당 역할 (Role Breakdown)

#### 🌐 **FastAPI (진입점 & 오케스트레이션 / API 게이트웨이 레이어)**

- **입력 검증 및 인터페이스 제공**: Pydantic 모델과 `Field`를 통해 사용자 요청 데이터를 자동 검증하고 API 엔드포인트를 제공합니다.
- **실시간 스트리밍 응답**: AI 모델이 생성하는 토큰(Token)이나 에이전트의 진행 상태를 `EventSourceResponse`(SSE), `StreamingResponse`, 또는 `WebSockets`를 활용해 클라이언트로 지연 없이 실시간 전달합니다.
- **의존성 주입 및 비동기 처리**: `Depends` 시스템을 활용해 Redis 클라이언트나 에이전트 서비스를 수명주기에 맞게 주입받고, 비동기 이벤트 루프 위에서 I/O 요청을 효율적으로 관리합니다.

#### 🧠 **Redis (통합 Memory Layer & 비동기 메시지 브로커 레이어)**

- **AI 에이전트 통합 기억망 (Memory Layer)**:
  - **작업 기억 (Working Memory)**: `Hash`나 `JSON` 구조 및 TTL을 사용하여 대화 세션 상태, 슬롯 정보, 단기 대화 맥락을 빠르게 유지하고 불러옵니다.
  - **장기 기억 & RAG (Long-term Memory)**: `JSON` 문서 내 `VECTOR` 필드와 Redis Search(`FT.SEARCH`, `FT.HYBRID`)를 활용하여 의미적 유사도 검색(Vector KNN) 및 하이브리드 검색을 수행합니다.
  - **시맨틱 캐시 (Semantic Cache)**: 이전 질의응답을 벡터화하여 저장함으로써, 동일/유사 프롬프트 재요청 시 LLM 재호출 없이 빠르게 응답을 반환해 비용과 지연 시간을 단축합니다.
  - **이벤트 스트림 (Streams)**: 에이전트의 다단계 추론(Chain-of-Thought) 과정이나 도구 호출 기록을 시간순 이벤트 로그로 안전하게 관리합니다.
- **비동기 작업 큐 & 메시지 브로커**: 웹 스크래핑, 대용량 문서 임베딩 등 무거운 연산 작업을 백그라운드 워커(Celery 등)로 이관하기 위해 메시지 큐 및 결과 저장소 역할을 수행합니다.

### 2. 두 도구의 연결 및 상호작용 흐름 (How They Connect)

```
[Client] ──(1) Chat / Task 요청──> [FastAPI Server]
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        │                                                                 │
        ▼ (2) 시맨틱 캐시 & Working Memory 조회                           ▼ (4) 무거운 연산 Task 발행
 [Redis (Memory Layer)]                                           [Redis (Job Queue)]
        │                                                                 │
        ▼ (3) RAG 장기 기억 벡터 검색 (FT.SEARCH / FT.HYBRID)             ▼ (5) Task 수신 및 실행
 [Redis Search Engine]                                           [Celery / Async Worker]
        │                                                                 │
        └────────────────────────────────┬────────────────────────────────┘
                                         │
                                  (6) 결과 수신
                                         │
 [Client] <──(7) SSE / WebSocket 스트리밍 ─── [FastAPI Server]
```

#### ① 대화 세션 및 시맨틱 캐싱 흐름

1. 클라이언트가 FastAPI로 메시지를 전송하면, FastAPI는 먼저 Redis의 **시맨틱 캐시**(`FT.HYBRID` 등)를 검색하여 유사한 답변이 존재하는지 확인합니다.
2. 캐시 미스 시, Redis `Hash`/`JSON` 구조에서 해당 사용자의 Working Memory(단기 대화 히스토리)를 읽어와 LLM 프롬프트를 구성합니다.
3. 답변 생성 시 FastAPI의 SSE(`EventSourceResponse`)로 클라이언트에 토큰 단위 실시간 스트리밍을 진행하면서, 새 대화 내역을 Redis에 업데이트합니다.

#### ② 장기 기억 회상 및 RAG 흐름

1. 에이전트가 복잡한 질문을 받으면 질의를 임베딩(Vector)으로 변환합니다.
2. FastAPI 내부 서비스가 Redis Search에 `FT.SEARCH` KNN 쿼리나 키워드+벡터가 결합된 `FT.HYBRID` 쿼리를 보내 관련 장기 기억 문서를 순식간에 회상(Recall)해 옵니다.

#### ③ 비동기 에이전트 작업 이관 흐름

1. 장시간 소요되는 에이전트 멀티스텝 작업(예: 외부 웹 탐색 후 요약)이 들어오면 FastAPI는 작업을 Redis 메시지 큐에 발행하고 `task_id`를 즉시 반환합니다.
2. 전용 워커 프로세스가 Redis 큐에서 작업을 꺼내 연산을 완료하고 결과를 Redis에 저장합니다.
3. FastAPI는 WebSocket이나 SSE, 혹은 Polling 방식으로 작업 상태 변화 및 최종 결과를 클라이언트에 전달합니다.

---

## FastAPI + Redis + Langchain

FastAPI와 Redis, 그리고 **LangChain**을 결합하여 AI 에이전트를 구축할 때의 전체 모듈 구조와 핵심 구현 코드를 단계별로 소개합니다.

Redis는 에이전트의 단기 대화 기억(Chat Message History) 및 장기 데이터 회상(Vector Store)을 제공하며, FastAPI는 `EventSourceResponse`를 통해 에이전트의 응답을 실시간 SSE(Server-Sent Events) 스트리밍으로 전달합니다.

### 1. 모듈 구조 (Directory Layout)

```
app/
├── core/
│   └── config.py        # Redis URL, LLM API Key 등 환경 설정
├── memory/
│   └── redis_memory.py  # LangChain RedisChatMessageHistory 및 Vector Store 설정
├── agent/
│   ├── tools.py         # 에이전트가 사용할 Custom Tools
│   └── agent_builder.py # LangChain Agent Executor / RunnableChain 생성
└── main.py              # FastAPI 웹 애플리케이션 및 SSE 스트리밍 엔드포인트
```

### 2. 단계별 구현 코드

#### ① Redis 기반 메모리 레이어 구축 (`memory/redis_memory.py`)

LangChain의 `RedisChatMessageHistory`를 활용해 대화 세션(`session_id`)별 작업 기억을 유지하고, `Redis` VectorStore를 RAG 장기 기억 요소로 결합합니다.

```python
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_community.vectorstores import Redis
from langchain_openai import OpenAIEmbeddings

REDIS_URL = "redis://localhost:6379/0"

# 1. 단기 대화 세션 기억 (Session Memory)
def get_chat_history(session_id: str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(
        session_id=session_id,
        url=REDIS_URL,
        ttl=3600  # 1시간 후 자동 만료 (TTL 설정)
    )

# 2. 장기 기억 / RAG 벡터 저장소 (Vector Store)
def get_redis_vectorstore() -> Redis:
    embeddings = OpenAIEmbeddings()
    return Redis.from_existing_index(
        embedding=embeddings,
        index_name="agent_knowledge",
        redis_url=REDIS_URL
    )
```

#### ② LangChain 에이전트 생성 (`agent/agent_builder.py`)

프롬프트, 도구(Tools), LLM 모델, 그리고 세션 히스토리를 묶어 실행 가능한 체인(`RunnableWithMessageHistory`)을 작성합니다.

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from memory.redis_memory import get_chat_history

def create_agent_executor():
    llm = ChatOpenAI(model="gpt-4o", streaming=True)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 사용자 질문에 친절하게 답변하는 AI 에이전트입니다."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    chain = prompt | llm

    # Redis 히스토리와 체인 결합
    agent_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history=get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    )
    return agent_with_history
```

#### ③ FastAPI SSE 스트리밍 엔드포인트 (`main.py`)

FastAPI의 `response_class=EventSourceResponse`를 활용하여 LangChain 에이전트가 생성하는 토큰을 실시간으로 클라이언트에 전송합니다.

```python
from collections.abc import AsyncIterable
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel
from agent.agent_builder import create_agent_executor

app = FastAPI()
agent = create_agent_executor()

class AgentRequest(BaseModel):
    session_id: str
    message: str

@app.post("/agent/chat", response_class=EventSourceResponse)
async def chat_with_agent(req: AgentRequest) -> AsyncIterable[ServerSentEvent]:
    # 비동기 토큰 스트리밍
    async for chunk in agent.astream(
        {"input": req.message},
        config={"configurable": {"session_id": req.session_id}}
    ):
        if chunk.content:
            yield ServerSentEvent(data=chunk.content, event="token")

    yield ServerSentEvent(raw_data="[DONE]", event="done")
```

### 3. 구조의 핵심 이점

1. **세션 격리 및 자동 메모리 관리**: `session_id`를 기반으로 사용자별 대화 히스토리가 Redis에서 독립적으로 분리·저장되며, TTL 설정을 통해 오래된 세션 데이터가 자동 정리됩니다.
2. **실시간 UX (SSE Streaming)**: `astream()` 메서드와 FastAPI의 `EventSourceResponse`를 연결하여 LLM 응답을 토큰 단위로 실시간 수신할 수 있습니다.
3. **유연한 확장성**: Redis VectorStore나 RedisVL을 추가 연동하면 장기 기억 회상(RAG) 기능까지 동일한 Redis 인스턴스 환경에서 손쉽게 확장 가능합니다.

---

## Docker Compose: FastAPI, Redis 워커를 한 번에 컨테이너 환경으로 묶어 실행하는 환경 구성

Docker Compose를 사용하면 \*\*FastAPI 웹 서버, Redis 브로커, 백그라운드 워커(Celery 등)를 단일 YAML 파일에 선언적으로 정의하여 한 번에 실행하고 관리할 수 있습니다.

### 1. 프로젝트 파일 구조 예시

```
my-project/
├── compose.yaml          # Docker Compose 환경 정의 파일
├── Dockerfile            # FastAPI 및 워커 공용 Dockerfile
├── requirements.txt      # Python 패키지 목록
└── app/
    ├── main.py           # FastAPI 애플리케이션
    └── tasks.py          # Celery 작업(Task) 정의
```

---

### 2. `Dockerfile` 작성

FastAPI 서버와 워커 서비스는 동일한 코드베이스와 패키지 환경을 공유하므로 단일 `Dockerfile`을 사용하여 빌드할 수 있습니다.

```
# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 의존성 패키지 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 복사
COPY . .

EXPOSE 8000

# 기본 실행 명령 (Compose에서 서비스별로 오버라이드 가능)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 3. `compose.yaml` (Docker Compose) 설정

`compose.yaml` 파일에 Redis, FastAPI 웹 서버, 워커 프로세스를 서비스 단위로 묶어 설정합니다.

```
services:
  # 1. Redis 서비스 (메시지 브로커 및 캐시)
  redis:
    image: redis:latest
    container_name: redis_broker
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # 2. FastAPI 웹 API 서버 서비스
  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fastapi_app
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy

  # 3. Celery 전용 워커 서비스
  worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: celery_worker
    # Dockerfile의 기본 CMD를 오버라이드하여 워커 명령 실행
    command: celery -A app.tasks.celery_app worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy

volumes:
  redis_data:
```

#### 핵심 구성 요소 및 동작 방식

- **내부 네트워크 통신**: Docker Compose는 전용 가상 네트워크를 자동으로 구성하여, 컨테이너들이 서비스명(`redis`)을 DNS 호스트 이름으로 사용하여 서로 통신할 수 있게 합니다.
- **명령어 오버라이드 (`command`)**: `web`과 `worker` 서비스가 동일한 이미지를 공유하되, `worker`에는 `command` 옵션을 지정하여 Celery 워커 프로세스로 동작하도록 기본 명령을 변경합니다.
- **의존성 순서 제어 (`depends_on` + `healthcheck`)**: Redis 서비스가 단순히 컨테이너로 켜지는 것뿐만 아니라 `ping` 검사를 통과해 실제 요청을 받을 수 있는 상태(`service_healthy`)가 된 후 `web`과 `worker`를 실행합니다.
- **데이터 영속성 (`volumes`)**: `redis_data` 볼륨을 마운트하여 컨테이너가 멈추거나 재시작되어도 Redis 데이터가 유실되지 않고 보존되도록 합니다.

### 4. 컨테이너 빌드 및 실행 명령어

- **백그라운드 빌드 및 실행**:
  ```
  docker compose up -d --build
  ```
  이미지를 새로 빌드하고 모든 컨테이너를 데몬 모드(`-d`)로 실행합니다.
- **실행 중인 컨테이너 상태 확인**:
  ```
  docker compose ps
  ```
- **실시간 실시간 로그 확인**:
  ```
  docker compose logs -f
  ```
- **전체 컨테이너 종료 및 삭제**:
  ```
  docker compose down
  ```
  볼륨에 저장된 Redis 데이터까지 함께 삭제하려면 `docker compose down --volumes` 옵션을 사용합니다.

이 구성에 **Compose Watch** 기능을 추가하면 코드 수정 시 컨테이너를 자동으로 재적용할 수 있습니다.

# 실습

- [ ] GET, POST 엔드포인트와 Pydantic 모델 만들기, /docs에서 호출
- [ ] LLM API를 호출하는 /chat 엔드포인트, API 키는.env로 관리
- [ ] FastAPI + Redis를 docker compose로 함께 띄우기
- [ ] 띄운 Redis를 실제로 써보기: 같은 질문의 답을 TTL을 두고 캐시해서 첫 번째와 두 번째 응답 속도 비교
- [ ] async 함수가 언제 필요한지 위키 페이지로 정리

# 질문 및 복습

- 아직 이해하지 못한 내용:
- 복습 질문:
- 다음 학습 자료:
