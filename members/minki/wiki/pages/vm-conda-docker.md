# VM, conda, Docker는 무엇이 다른가

**한 줄 정의**: 셋을 가르는 기준은 "무게"보다 "무엇까지 함께 포장하느냐"예요. VM은 커널이 있는 OS 전체, Docker는 OS 파일과 시스템 라이브러리까지(커널은 호스트 것), conda는 Python 패키지만 묶어요.

## 왜 필요한가

"내 PC에선 되는데 서버에선 안 돼요"가 어디서 생기는지 알면 도구를 고를 수 있어요.

| | VM | Docker 컨테이너 | conda 환경 |
| --- | --- | --- | --- |
| 포장 범위 | 커널 포함 OS 전체 | OS 파일, 시스템 라이브러리, 코드 | Python(과 일부 바이너리) 패키지 |
| 커널 | 자기 커널 | 호스트 커널 공유 | 호스트 그대로 |
| 시작 속도, 크기 | 느림, 수 GB | 빠름, 수백 MB~ | 빠름, 작음 |
| 다른 PC에서 재현 | 잘 됨 | 잘 됨 (커널, GPU 드라이버는 호스트 것) | OS 라이브러리(libGL 등) 차이는 재현 안 됨 |

실무에서는 함께 써요. Docker 이미지 안에서 pip나 conda로 Python 환경을 구성하는 식이에요.

## 최소 예제

```bash
# 같은 Python 3.11 환경을 Docker로 띄우면 OS가 달라도 결과가 같아요
docker run --rm python:3.11-slim python --version
```

## 내가 막힌 점

- 처음엔 "VM보다 가벼운 게 컨테이너, 그보다 가벼운 게 conda"로 정리했어요. 맞는 말이지만, 실제로 중요한 건 시스템 라이브러리까지 묶이느냐였어요.

## 출처

- [Docker 공식 문서: What is a container?](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/)
- 1주차 세션 1 정리와 피드백 (2026-10-14)
