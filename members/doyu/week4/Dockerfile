FROM python:3.11-slim
WORKDIR /app
# CPU용 torch를 먼저 깔아 이미지 크기를 줄인다 (기본 torch는 GPU 라이브러리까지 받는다)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY hybrid.py .
COPY app/ app/
# 위키 문서, 모델 캐시, 임베딩 색인은 이미지에 넣지 않고 실행할 때 마운트한다
# M3의 효율 코어까지 쓰면 오히려 느려서 스레드를 4개로 둔다 (청크 8개 41초 → 21초)
ENV DOCS_DIR=/wiki HF_HOME=/models CHROMA_DIR=/index OMP_NUM_THREADS=4
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
