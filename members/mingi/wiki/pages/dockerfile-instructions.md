# Dockerfile 명령어와 빌드 캐시 (1주차)

## 내 정리

### Q. Dockerfile이란 무엇인가?

docker에 사용할 이미지의 빌드 과정을 담은 파일, 작성된 명령어를 한줄한줄 해석하면서 이미지를 빌드한다

### Q. FROM, WORKDIR, COPY, RUN, ENV, CMD는 각각 무엇을 하나?

- **`FROM`**: 이미지 빌드의 기초 파일 현재 1,2주차에서는 `python:3.11-slim`를 사용함
- **`WORKDIR`**: 작업을 진행하는 폴더, 2주차에서는 `/app`를 사용함
- **`COPY`**: 내 pc에 있는 파일 중 docker로 복사해 가져갈 파일들,기본적으론 `requirements.txt`를 복사해서 사용했음
- **`RUN`**: 빌드 중 실행할 명령어, `pip install --no-cache-dir -r requirements.txt` 를 사용해 필요한 라이브러리를 설치함
- **`ENV`**: 환경변수에서 사용할 기본값들
- **`CMD`**: 컨테이너가 켜질 때 실행할 명령어들 2주차에선 `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`을 사용했음

### Q. RUN과 CMD는 언제 실행되나? 둘의 차이는?

RUN 은 build과정에서 한번 CMD는 run 할때마다 실행됨

### Q. 빌드 캐시란 무엇이고, requirements.txt를 코드보다 먼저 COPY하는 이유는?

줄의 입력이 저번과 같으면 다시 실행하지 않고 재사용하기 위해, 한줄이라도 바뀌면 그 아래는 전부 다 다시하게됨

```dockerfile
COPY requirements.txt .        # 1 패키지 목록만
RUN pip install -r requirements.txt   # 2 설치 (오래 걸림)
COPY app/ app/                 # 3 코드
```

위와 같은 구조면 main.py 코드를 고쳐도 3만 다시 동작하지만

```dockerfile
COPY . .                       # 1 코드와 패키지 목록을 한꺼번에
RUN pip install -r requirements.txt   # 2 설치
```

아래와 같은 구조면 코드를 수정하면 1 2를 다시 실행하게된다.

## 내가 막힌 점

(1주차 실습에서 헷갈렸던 것, 에러 났던 것을 내 말로)

## Claude 피드백

- **Q1**: 정확해요. 각 명령 한 줄이 레이어 하나가 돼요.
- **FROM**: "기초 파일"보다 **베이스 이미지**가 정확해요. `python:3.11-slim`은 Docker Hub에 있는, 가벼운 Debian에 Python이 미리 설치된 이미지예요. 그 위에 내 레이어를 쌓아요.
- **COPY**: 맞아요. 2주차는 `COPY app/ app/`로 코드도 따로 복사했어요. 무엇을 보낼지는 `.dockerignore`의 영향을 받아요.
- **ENV**: 이미지 안에 기본 환경변수를 박아 넣어요(예: `PYTHONUNBUFFERED=1`). 이미지 레이어에 그대로 남기 때문에 **API 키 같은 비밀은 ENV에 쓰면 안 돼요.** 비밀은 실행 시점에 `env_file`로 넣어요.
- **CMD**: 맞아요. JSON 배열 형태(exec form)로 쓰는 게 권장이고, `docker run <이미지> <명령>`이나 compose의 `command:`로 덮어쓸 수 있어요.
- **Q3 (RUN vs CMD)**: 정확해요. 한 줄로 "RUN은 이미지를 만들 때, CMD는 컨테이너를 켤 때"예요.
- **Q4 (빌드 캐시)**: 예시까지 정확해요. 보태면 `COPY`는 명령어 글자가 아니라 **복사되는 파일 내용**이 바뀌었는지를 비교해요. 그래서 `COPY . .`는 main.py 한 글자만 고쳐도 레이어가 깨지고, 그 아래 `pip install`이 매번 다시 돌아요. 자주 바뀌는 것일수록 아래에 두는 게 원칙이에요.

## 출처

-
