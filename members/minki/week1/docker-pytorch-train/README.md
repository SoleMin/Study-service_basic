# PyTorch 학습 컨테이너 (1주차 세션 2)

작은 신경망을 합성 데이터로 학습하고, 학습된 모델을 `outputs/model.pt`로 저장하는 예제예요.

## 파일

| 파일 | 역할 |
| --- | --- |
| `Dockerfile` | 이미지를 만드는 레시피 (줄마다 주석 있음) |
| `train.py` | 학습 스크립트. 데이터를 직접 생성해서 인터넷 없이 돌아감 |
| `requirements.txt` | Python 의존성 (CPU용 torch) |
| `.dockerignore` | 이미지에 넣지 않을 파일 목록 |

## 실행

```bash
# 1. 이미지 빌드 (처음엔 torch 다운로드 때문에 몇 분 걸림)
docker build -t pytorch-train:v1 .

# 2. 학습 실행. 끝나면 컨테이너는 자동 삭제(--rm)
docker run --rm pytorch-train:v1

# 3. 하이퍼파라미터 바꿔서 실행 (ENV 기본값 덮어쓰기)
docker run --rm -e EPOCHS=30 -e LR=5e-3 pytorch-train:v1

# 4. 학습된 모델을 내 PC에 남기기 (바인드 마운트, 세션 3 예습)
docker run --rm -v "$(pwd)/outputs:/app/outputs" pytorch-train:v1
```

## 과제 체크용 실험

- [ ] `train.py`에 print 한 줄을 추가하고 다시 빌드해 보세요. pip install 단계가 `CACHED`로 뜨는지 확인
- [ ] Dockerfile에서 `COPY train.py .`를 `COPY requirements.txt .` 위로 올리고 같은 실험을 해 보세요. 이번엔 torch를 다시 설치하는 이유를 설명할 수 있으면 통과
- [ ] 4번 명령 없이 실행했을 때 `model.pt`가 어디로 사라지는지 설명해 보기

## 참고

- NVIDIA GPU로 학습하려면 `FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`처럼 CUDA가 든 베이스 이미지를 쓰고, NVIDIA Container Toolkit 설치 후 `docker run --gpus all`로 실행해요. Mac에서는 컨테이너가 GPU를 쓸 수 없어요.
- Mac(Apple Silicon)에서도 위 Dockerfile 그대로 빌드돼요. CPU torch는 arm64용도 있어요.
