# VM, 컨테이너, conda 비교 (1주차)

## 내 정리 (2026-10-14)

VM은 자신의 커널을 가진 OS 전체를 가진 독립된 환경을 만들고, 컨테이너는 그보다 조금 더 가벼운 개념으로 프로세스, 파일, 네트워크 등을 격리하고, conda는 조금 더 가볍게 파이썬 환경만 독립된 환경으로 띄움

## 내가 막힌 점

## Claude 피드백

- 정확함. 한 가지만 더하면, 세 가지를 가르는 기준은 "무게"보다 "무엇까지 함께 포장하느냐"다
- conda는 Python 패키지만 묶어서, OS 시스템 라이브러리(libGL 등)나 OS 차이는 다른 컴퓨터에서 그대로 재현되지 않는다
- Docker 이미지는 OS 파일과 시스템 라이브러리까지 담아서 어느 서버에서나 같게 동작한다. 단, 커널과 GPU 드라이버는 호스트 것을 쓴다
- 실무에서는 둘을 함께 쓰기도 한다. Docker 이미지 안에서 conda나 pip로 Python 환경을 구성하는 식

## 출처

- [Docker 공식 문서: What is a container?](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/)
