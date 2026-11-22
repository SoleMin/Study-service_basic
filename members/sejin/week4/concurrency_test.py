"""/ask 처리 중에 /health가 바로 응답하는지 확인 (서버를 먼저 켜 두고 실행)"""
import json, threading, time, urllib.request

URL = "http://127.0.0.1:8000"


def call_ask():
    body = json.dumps({"question": "Redis TTL은 몇 초로 정했어?"}).encode()
    req = urllib.request.Request(URL + "/ask", data=body, headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    urllib.request.urlopen(req).read()
    print(f"/ask    {time.perf_counter() - t:.2f}초")

th = threading.Thread(target=call_ask)    # /ask는 별도 스레드에서 보냄 (응답을 기다리지 않고 다음 줄로)
th.start()
time.sleep(0.3)                           # /ask가 서버에 먼저 도착하도록 잠깐 대기

t = time.perf_counter()
urllib.request.urlopen(URL + "/health").read()
print(f"/health {time.perf_counter() - t:.2f}초")
th.join()                                 # /ask 끝날 때까지 기다렸다가 종료
