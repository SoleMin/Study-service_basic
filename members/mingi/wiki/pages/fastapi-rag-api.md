# RAG를 FastAPI /ask로 서빙하기 (4주차)

## 내 측정 결과

`app/main.py`, `rag_v2.ipynb` 7번 섹션

- 서버 시작 시간 (`/health`의 startup_sec):
- `/ask` 응답 시간: 위키에 있는 질문 ms, 위키에 없는 질문 ms
- 정한 기준값 MIN_SCORE: (위키에 있는 질문 1위 점수 최소 , 없는 질문 최대 )

| 질문 | in_wiki | top_score | 출처 |
| --- | --- | --- | --- |
| | | | |
| | | | |
| (위키에 없는 질문) | | | |

## 내 정리

### Q. 노트북 RAG를 API로 바꿀 때 무엇을 "서버가 켜질 때 한 번만" 하고 무엇을 "요청마다" 하나? lifespan은 무엇인가?

문서를 자르고 저장하고 모델로드, 문서 임베딩, 적재등은 켜질 떄 한번만 하고 요청은 쿼리재작성, 질문 임베딩 등 사용자의 질문이 들어오면 해야하는 동작들이다. lifespan은 앱의 시작과 종료를 감싸는 함수다.

### Q. /ask를 async def가 아니라 def로 만든 이유는? (2주차 async 정리와 연결)

async def로 하게되면 스레드 하나에서 응답을 처리한다. 따라서 다른 질문들이 들어와도 전의 처리가 끝나기 전까지는 동작이 멈추게 되는데 이를 방지하기 위해서

### Q. 요청과 응답 모양(Pydantic 모델)은 어떻게 생겼나? 출처에 page, chunk_id, score를 같이 돌려주는 이유는?

```text
요청 AskRequest
  question: str
  history: list[Turn] = []        Turn = {role: "user"|"assistant", content: str}

응답 AskResponse
  question, search_query, answer, in_wiki, top_score, elapsed_ms
  sources: list[Source]           Source = {page, chunk_id, score}
```

pydantic으로 사용하게 되면 유저의 요청, 출력 형식을 제한할 수 있다.

page, chunk_id,score를 같이 돌려주는 이유는 출력을 확인해서 수정할 부분이 있는지 트레이싱 하기 위함이다.

### Q. 위키에 없는 질문은 어떻게 걸렀나? 기준값은 어떻게 정했고, 기준값이 너무 높거나 낮으면 무슨 일이 생기나?

2차 리랭커의 값을 특정 값 threshold를 설정해 그 값보다 낮으면 탈락, 높다면 채택 방식으로, 기준값은 리랭커의 출력이 0~1사이로 나올것을 예상해서 사용했고 너무 높으면 있는 문서도 걸러낼 수 있고 낮으면 없는 문서도 지어내서 답변할 수 있다.

## 내가 막힌 점

(`../raw/week4-troubleshooting.md`에서 이 주제와 관련된 것을 골라 내 말로)

## Claude 피드백 (2026-11-22)

- **Q1 (한 번 vs 요청마다, lifespan)**: 정확해요. 3주차 "색인 단계 vs 질문마다 하는 단계"를 그대로 코드 구조로 옮긴 거라는 연결을 한 줄 넣으면 좋아요. lifespan은 `yield`를 기준으로 나눠 설명하면 완성이에요: `yield` 전이 서버가 켜질 때 1번, `yield` 후가 꺼질 때 1번, 만든 객체는 `app.state`에 넣어 두고 꺼내 써요
- **Q2 (def로 만든 이유)**: 문장이 "방지하기 위해서"에서 끊겼어요. 이유는 맞게 짚었으니 두 가지만 채우면 돼요
  - 문제의 핵심: `async def` 자체가 아니라, 안에서 부르는 임베딩, 리랭커, `llm.invoke`가 전부 **await 없는 블로킹 함수**라서 루프가 멈춰요. 2주차 `/bad-sleep`(async 안의 `time.sleep`)과 같은 상황이에요
  - 해결: `def`로 두면 FastAPI가 **스레드풀**에서 실행해서, 루프는 다른 요청을 계속 받아요
- **Q3 (요청/응답, 출처)**: 모양 정리가 정확해요. 두 가지를 더하면 좋아요
  - Pydantic의 효과: 형식 제한에 더해, 틀린 요청은 FastAPI가 자동으로 **422**로 돌려주고 `/docs`에 모양이 자동으로 나와요
  - 출처 세 가지는 쓰임이 달라요. `page`는 사람이 원문을 확인할 때, `chunk_id`는 정확히 어느 조각인지 추적할 때(지금 쓰신 트레이싱), `score`는 얼마나 확신하는지 볼 때예요
- **Q4 (위키에 없는 질문)**: 방법과 "높으면 있는 문서도 거른다"는 정확해요. 두 군데를 다듬으면 좋아요
  - "기준값은 0~1로 예상해서 사용했다": 0~1은 점수의 **범위**이고, 기준값은 노트북 7번처럼 위키에 있는 질문의 1위 점수와 없는 질문의 1위 점수를 비교해서 **그 사이**로 정해요. 측정 결과 칸의 MIN_SCORE도 노트북을 돌린 뒤 채워 주세요
  - "낮으면 지어내서 답변": 프롬프트의 "위키에 없는 내용이에요" 문장이 2차로 막아 주기 때문에, 실제로 생기는 문제는 주로 **관련 없는 출처가 붙어 나오는 것**(3주차 문제)과 **불필요한 LLM 호출**이에요
  - 3주차와 무엇이 달라졌는지 한 줄 넣으면 이 페이지의 핵심이 돼요: 3주차는 프롬프트로만 거절해서 출처가 4개씩 붙었고, 이번에는 **검색 단계에서 먼저** 걸러서 출처도 비고 LLM도 안 불러요

## 출처

- [FastAPI 문서: Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [FastAPI 문서: Concurrency and async / await](https://fastapi.tiangolo.com/async/)
- 실습: `members/mingi/week4/app/main.py`
