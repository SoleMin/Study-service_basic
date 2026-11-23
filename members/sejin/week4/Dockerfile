FROM python:3.11-slim
WORKDIR /app

# torch는 CPU 버전을 먼저 설치 (안 하면 리눅스에서 GPU용 수 GB짜리가 깔림)
RUN pip install --no-cache-dir torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

ENV WIKI_DIR=/wiki \
    HF_HUB_OFFLINE=1
EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
