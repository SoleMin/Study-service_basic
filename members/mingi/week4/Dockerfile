FROM python:3.11-slim

WORKDIR /app

# 1) torch를 CPU 버전으로 먼저: 기본 pip torch는 GPU(CUDA) 라이브러리까지 받아서 이미지가 몇 GB 더 커져요
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2) 나머지 패키지: requirements.txt가 안 바뀌면 이 층은 캐시를 써요 (1주차 빌드 캐시 실험과 같은 원리)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) 코드는 가장 자주 바뀌니까 마지막에
COPY app/ app/

# 모델(약 4GB)은 이미지에 넣지 않고, compose에서 볼륨으로 연결한 캐시 폴더에 받아요
ENV WIKI_DIR=/wiki \
    HF_HOME=/root/.cache/huggingface

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
