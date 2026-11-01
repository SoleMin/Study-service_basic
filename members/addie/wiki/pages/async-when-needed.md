# async 함수는 언제 필요한가 (초안)

## 한 줄 요약

<!-- TODO: 직접 실습해 보고 한 줄로 정리 -->

## `async def` vs `def` — FastAPI가 각각을 어떻게 실행하나

| 선언 | 실행 위치 | 안에서 해도 되는 것 | 하면 안 되는 것 |
| --- | --- | --- | --- |
| `async def` | 메인 이벤트 루프 | `await` 가능한 I/O (redis.asyncio, httpx, async LLM SDK) | `time.sleep`, `requests`, 동기 DB 드라이버 → 루프 전체가 멈춤 |
| `def` | 쓰레드풀 워커 | 동기 라이브러리 호출 | (CPU 무거운 연산은 둘 다 부적합 → Celery 등 워커로) |

## week2 코드에서의 선택

- `/health`, `/echo` → `def`: I/O가 없어서 어느 쪽이든 상관없음
- `/chat` → `async def`: Redis 조회 + LLM 호출 둘 다 기다리는 I/O
- Redis 클라이언트를 `lifespan`에서 생성한 이유:
  <!-- TODO: "Task attached to a different loop" 에러와 연결해서 설명 -->

## 직접 확인해 볼 실험

1. `call_llm` 안의 `await asyncio.sleep(2)`를 `time.sleep(2)`로 바꾸기
2. 서로 다른 질문으로 `/chat`을 동시에 5번 호출
3. 전체 소요 시간 비교: async ≈ 2초, blocking ≈ 10초 (예상)

```bash
for i in 1 2 3 4 5; do
  curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' \
    -d "{\"question\": \"q$i\"}" &
done; wait
```

결과:
<!-- TODO: 실측값 기록 -->

## 판단 기준 정리

<!-- TODO: 위 실험 결과로 직접 작성 -->
