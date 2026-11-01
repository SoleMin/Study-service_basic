# 2026-11-02 async 실험 메모 (raw)

> Claude가 이 PC에서 실행한 실험 기록. 코드와 출력 원본: `스터디자료/W02_async실험/`
> 직접 다시 돌려 보고 숫자를 확인할 것.

## 환경
- Windows 11, Python 3.11.2 (venv), fastapi 0.162.0, uvicorn 0.54.0, starlette 1.10.0, anyio 4.16.0
- 서버: `uvicorn app:app --port 8010` (워커 1개, `--reload` 없음)
- 기다림은 LLM 대신 `sleep(2)`로 흉내, 계산은 `for i in range(12_000_000): s += i*i` (한 번에 약 0.7초)

## 실행한 명령
```powershell
cd 스터디자료\W02_async실험
python -m venv .venv
.venv\Scripts\python -m pip install fastapi uvicorn
.venv\Scripts\python -m uvicorn app:app --port 8010      # 터미널 1
.venv\Scripts\python measure.py                          # 터미널 2: 엔드포인트마다 동시 5개
.venv\Scripts\python other_request.py                    # 느린 요청 중에 다른 요청은?
.venv\Scripts\python -W always missing_await.py           # await 빠뜨리기
```

## 결과 1: 동시 요청 5개 (1회차 / 2회차)
```
엔드포인트        요청 1개   동시 5개 전체   요청별 시간(초, 빠른 순)
/wait/async       2.01s       2.02s          2.02, 2.02, 2.02, 2.02, 2.02
/wait/blocking    2.00s      10.01s          2.00, 4.00, 6.01, 8.01, 10.01
/wait/sync        2.00s       2.01s          2.01, 2.01, 2.01, 2.01, 2.01
/cpu/async        0.71s       4.04s          0.74, 1.65, 2.41, 3.24, 4.04
/cpu/sync         0.98s       4.62s          3.94, 3.96, 3.99, 4.61, 4.61

/wait/async       2.00s       2.03s          2.02, 2.02, 2.02, 2.02, 2.02
/wait/blocking    2.00s      10.01s          2.00, 4.01, 6.01, 8.01, 10.01
/wait/sync        2.00s       2.02s          2.01, 2.01, 2.01, 2.02, 2.02
/cpu/async        0.83s       3.54s          0.70, 1.44, 2.11, 2.79, 3.54
/cpu/sync         0.75s       3.91s          2.03, 2.23, 3.75, 3.89, 3.91
```

## 결과 2: 느린 요청 하나가 처리되는 동안 상관없는 요청(/openapi.json)
```
평소 /openapi.json: 0.009초
/wait/async     처리 중에 /openapi.json: 0.002초
/wait/blocking  처리 중에 /openapi.json: 1.703초
/wait/sync      처리 중에 /openapi.json: 0.002초
```
(느린 요청을 보내고 0.3초 뒤에 보냄 → blocking은 남은 1.7초를 그대로 기다림)

## 결과 3: await 빠뜨리기
```
RuntimeWarning: coroutine 'get_answer' was never awaited
await 없이: <coroutine object get_answer at 0x000001B7562D99C0>
await 있으면: 답변
```

## 메모
- `def` + `time.sleep`도 2초에 끝남 → FastAPI가 `def`를 스레드풀에서 돌리기 때문. 동기 라이브러리만 있으면 `def`로 쓰면 됨
- `async def` + `time.sleep`이 최악. 자기 요청뿐 아니라 서버 전체가 멈춤
- CPU 계산은 `async def`도 `def`도 동시 5개에 3.5~4.6초 (≈ 0.7초 × 5) → 둘 다 빨라지지 않음
