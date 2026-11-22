# 모델을 쓰는 앱의 Docker 이미지: CPU torch와 모델 캐시 볼륨 (4주차)

## 내 측정 결과

`members/mingi/week4/Dockerfile`, `docker-compose.yml`

| 항목 | 값 |
| --- | --- |
| 이미지 크기 (`docker images`) | |
| 첫 `docker compose up` 후 준비까지 걸린 시간 | |
| 컨테이너 다시 올렸을 때 준비 시간 | |

## 내 정리

### Q. torch를 CPU 전용으로 설치하면 이미지가 왜 작아지나? GPU가 없는 서버에서 기본 torch를 쓰면 무엇이 낭비되나?

torch에서 사용하는 gpu 전용 라이브러리들을 받지 않기 때문 cpu전용으로 설치하면 저장공간을 아낄 수 있다.

### Q. 모델 파일(약 4GB)을 이미지 안에 넣지 않고 볼륨으로 연결한 이유는? 이미지에 넣으면 좋은 점은 없나?

모델 파일들은 용량이 크기 때문에 볼륨으로 사용하면 이미지가 작아져 빌드가 빨라지고 모델을 바꿔도 이미지를 다시 빌드하지 않아도 된다.

이미지에 넣게되면 첫 시작때 볼륨에서 불러오는 시간을 아낄 수 있고 인터넷이 막힌 환경에서도 사용할 수 있다.

### Q. 팀 위키 폴더를 COPY가 아니라 읽기 전용 볼륨(:ro)으로 연결하면 무엇이 편해지나?

위키 내용이 바뀌거나 추가되어도 이미지를 다시 빌드할 필요성이 없어진다. 다만 바꿔도 재시작은 해야함.

### Q. Dockerfile에서 torch -> requirements -> 코드 순서로 설치하는 이유는? (1주차 빌드 캐시와 연결)

자주 바뀌는 역순이다. torch는 거의 바뀔일이없고 requirements는 가끔 바뀌고 코드는 자주 바뀐다. 따라서 자주 바뀌는것을 맨 마지막에 두면 빌드 속도가 빨라진다.

## 내가 막힌 점

(`../raw/week4-troubleshooting.md`에서 이 주제와 관련된 것을 골라 내 말로)

## Claude 피드백 (2026-11-22)

- **Q1 (CPU torch)**: 이유가 정확해요. GPU 라이브러리 이름(cuDNN, cuBLAS 같은 `nvidia-*` 패키지)과 크기를 적으면 더 좋고, 크기는 `docker images`로 측정 결과 칸에 채워 주세요. 낭비되는 것도 저장공간 하나 더 있어요: **빌드 시간과 push/pull 시간**. 6주차에 k8s 노드가 이미지를 받을 때도 그만큼 느려져요
- **Q2 (모델을 볼륨으로)**: 정확해요. 한 군데만 고치면 돼요. 이미지에 넣었을 때 아끼는 시간은 "볼륨에서 불러오는 시간"이 아니라 **첫 시작 때 Hugging Face에서 4GB를 내려받는 시간**이에요. 볼륨이든 이미지든 디스크에서 불러오는 시간은 비슷해요. 이미지에 넣는 장점으로 **모델 버전이 고정돼 재현성이 좋다**는 것도 더할 수 있어요. 개발은 볼륨, 배포는 이미지 포함이 자주 쓰이고, 6주차 k8s 때 다시 고를 문제예요
- **Q3 (위키를 :ro 볼륨으로)**: 정확해요. 재시작이 필요한 이유(서버가 켜질 때 색인하니까)까지 짚은 게 좋아요. `:ro`의 의미도 하나 더하면 완성이에요: 컨테이너 안의 코드가 실수로 위키 원본을 고치거나 지울 수 없어요
- **Q4 (설치 순서)**: 빌드 캐시 이유는 정확해요. 더 중요한 이유가 하나 더 있어요. requirements의 `sentence-transformers`는 torch가 있어야 설치되는데, torch 없이 requirements를 먼저 설치하면 pip가 **기본(CUDA) torch를 알아서 받아 버려요.** CPU torch를 먼저 깔아 두면 pip가 "이미 있네" 하고 넘어가요. torch를 requirements.txt에 같이 넣지 않은 이유도 이거예요

## 출처

- [PyTorch 설치 안내 (CPU 휠)](https://pytorch.org/get-started/locally/)
- [Hugging Face 문서: 캐시 위치 (HF_HOME)](https://huggingface.co/docs/huggingface_hub/guides/manage-cache)
- 실습: `members/mingi/week4/Dockerfile`, `docker-compose.yml`
