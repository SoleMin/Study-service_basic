import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:8000/ask"

# 캐시에 걸리지 않도록 처음 보는 질문들 (순서대로용 5개, 동시용 5개는 서로 다름)
SEQ = ["도커 이미지와 컨테이너의 차이는?", "Dockerfile의 CMD와 RUN 차이는?",
       "볼륨 마운트는 왜 필요해?", "포트 매핑이 뭐야?", ".dockerignore는 왜 써?"]
CON = ["FastAPI의 엔드포인트가 뭐야?", "Pydantic 모델은 무슨 일을 해?",
       "HTTP 422는 언제 나와?", "Redis의 TTL이 뭐야?", "docker compose의 depends_on은 뭐야?"]


def ask(q):
    """질문 하나를 보내고 (걸린 시간, 캐시 여부, 비용)을 돌려줌"""
    body = json.dumps({"question": q, "level": "초급"}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    data = json.loads(urllib.request.urlopen(req).read())
    return time.perf_counter() - t, data["cached"], data["cost_krw"]


def report(name, results, total):
    times = ", ".join(f"{t:.2f}" for t, _, _ in results)
    hits = sum(c for _, c, _ in results)
    cost = sum(k for _, _, k in results)
    print(f"{name}: 전체 {total:.2f}초 | 요청별 [{times}] | 캐시 히트 {hits}개 | 비용 {cost:.4f}원")


# 1) 순서대로: 하나 끝나야 다음을 보냄
t0 = time.perf_counter()
seq = [ask(q) for q in SEQ]
report("순서대로 5개", seq, time.perf_counter() - t0)

# 2) 동시에: 5개를 한꺼번에 보냄
t0 = time.perf_counter()
with ThreadPoolExecutor(5) as ex:
    con = list(ex.map(ask, CON))
report("동시에 5개  ", con, time.perf_counter() - t0)

