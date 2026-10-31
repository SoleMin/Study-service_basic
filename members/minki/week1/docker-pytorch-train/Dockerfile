# 1) 베이스 이미지: Python만 들어 있는 가벼운 Debian 이미지
FROM python:3.11-slim

# 2) 로그가 버퍼링 없이 바로 찍히도록, .pyc 파일을 만들지 않도록 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 3) 이후 명령이 실행될 작업 폴더
WORKDIR /app

# 4) 의존성 목록만 먼저 복사하고 설치한다.
#    train.py만 고치면 이 레이어는 캐시를 재사용해서 torch를 다시 받지 않는다.
#    CPU 전용 torch 저장소를 써서 이미지 크기를 수 GB 줄인다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu

# 5) 학습 코드 복사
COPY train.py .

# 6) 기본 하이퍼파라미터 (docker run -e 로 덮어쓸 수 있음)
ENV EPOCHS=10 LR=1e-2 BATCH_SIZE=64 OUTPUT_DIR=/app/outputs

# 7) 컨테이너가 시작될 때 실행할 기본 명령
CMD ["python", "train.py"]
