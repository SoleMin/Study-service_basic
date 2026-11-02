# async 함수는 언제 필요한가

## 한 줄 정의
async def는 await로 기다리는 동안 서버가 다른 요청을 처리하게 해주는 함수 형태이다.
## 왜 필요한가
- LLM API, Redis, DB처럼 응답을 기다리는 시간이 긴 작업(I/O)이 많을 때, 기다리는 동안 다른 요청을 받을 수 있다.
- CPU를 오래 쓰는 계산(이미지 처리, 큰 반복문)은 async로 빨라지지 않는다.
- async def 안에서 time.sleep 같은 막는 코드나 동기 라이브러리를 쓰면 서버 전체가 멈춘다.
## 실험 결과
| 엔드포인트 | 5개 동시 요청 |
|---|---|
| async def + await asyncio.sleep(3) | 3.0초 |
| async def + time.sleep(3) | 15.0초 |
| def + time.sleep(3) | 3.1초 |
## 내가 막힌 점
## 출처