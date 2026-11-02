import codecs
import json
import time
import urllib.request

body = json.dumps({"question": "FastAPI의 StreamingResponse가 뭐야?", "level": "초급"}).encode()
req = urllib.request.Request("http://localhost:8000/ask/stream", data=body,
                             headers={"Content-Type": "application/json"})
decoder = codecs.getincrementaldecoder("utf-8")()   # 한글이 조각 경계에서 잘려도 안전하게

t0 = time.perf_counter()
with urllib.request.urlopen(req) as r:
    while chunk := r.read1(1024):                   # 도착하는 대로 읽기
        print(f"[{time.perf_counter() - t0:5.2f}초] {decoder.decode(chunk)}")
