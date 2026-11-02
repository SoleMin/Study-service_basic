import datetime
import requests

print("Hello from container!", datetime.datetime.now())
print("requests version:", requests.__version__)
print("requests location:", requests.__file__)