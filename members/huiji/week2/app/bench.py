import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

url = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5


def hit(_):
    urllib.request.urlopen(url).read()


start = time.perf_counter()
with ThreadPoolExecutor(n) as ex:
    list(ex.map(hit, range(n)))
print(f"{n} requests -> {time.perf_counter() - start:.1f}s")