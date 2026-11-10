<!-- merge_wiki.py 자동 생성: 원본 members/sejin/wiki/pages/1-docker-concepts.md . 수정은 원본에서 하세요 -->

# Docker 핵심 개념: 이미지, 컨테이너, 레이어, 레지스트리

## 한 줄 정의

Dockerfile(설계서)대로 설치까지 끝내 묶은 결과물이 이미지, 그 이미지를 실행한 격리된 프로세스가 컨테이너, 이미지를 이루는 Dockerfile 한 줄 한 줄의 층이 레이어, 이미지를 올리고 받는 원격 창고가 레지스트리다.

## 왜 필요한가

파이썬 버전, 패키지, OS가 조금만 달라도 "내 컴퓨터에선 되는데 다른 컴퓨터에선 안 되는" 문제가 생긴다. Docker는 프로그램과 실행 환경을 이미지 하나로 묶어서, Docker만 있으면 어디서나 똑같이 실행되게 한다. 1주차 실습에서 내 PC는 Windows + Python 3.11.2였지만, 컨테이너 안에서는 이미지에 든 Linux와 Python 3.11.x로 실행됐다.
레이어 덕분에 코드만 고치면 패키지 설치는 캐시로 재사용되어 빌드가 빠르고, 레지스트리 덕분에 팀원이나 서버가 같은 이미지를 받아 그대로 실행할 수 있다.

## 최소 예제

```powershell
# 1_hello: 빌드하고 실행
docker build -t week1-app .
docker run --rm week1-app
docker run -it --rm week1-app bash      # 컨테이너 안에 들어가 보기 (exit로 종료)

# 2_volume: -v로 컨테이너가 쓴 파일을 내 PC에 남기기
docker run --rm week1-volume                          # -v 없이
docker run --rm -v ${PWD}/out:/app/out week1-volume   # -v로 연결

# 4_size: 베이스 이미지와 .dockerignore에 따른 크기
docker images
```

실행 결과 (내 PC, 2026-11-01):

```
# 2_volume
-v 없이 실행  → "저장 완료"가 찍혀도 내 PC에 out 폴더가 생기지 않음
-v로 실행     → out/result.txt 생김: 컨테이너가 쓴 파일 (14:10:22)

# 4_size (docker images SIZE)
size-a  python:3.11,      .dockerignore 없음  1.63GB
size-b  python:3.11-slim, .dockerignore 없음  222MB
size-c  python:3.11-slim, .dockerignore 있음  187MB
```

## 개념 정리 (내 말로)

### 1. 이미지

Dockerfile(설계서)대로 파일·프로그램·패키지·코드를 설치까지 다 끝내서 묶어 놓은 결과물. 켜지면 무엇을 실행할지(CMD)도 들어 있다.

- 만들면 내용으로 계산한 ID가 붙고, 보통은 이름:태그(예: week1-app:latest)로 불러 쓴다.
- 한 번 만들면 바꿀 수 없다. 고치려면 Dockerfile이나 코드를 고쳐 다시 빌드한다. 안 바뀐 레이어는 재사용되고, 새 ID의 이미지가 생긴다.
- 공유: 레지스트리(Docker Hub 등)에 push하면 다른 사람이 pull해서 똑같이 쓸 수 있다.
  - 이미지를 넘기면 받은 사람은 빌드 없이 완전히 같은 결과를 실행한다(크다: 수백 MB).
  - Dockerfile을 넘기면 작고 읽기 쉽지만, 받은 사람이 직접 빌드해야 하고 빌드 시점에 따라 결과가 달라질 수 있다(베이스 이미지 갱신, 버전 안 박은 패키지).
  - 실무에서는 Dockerfile과 코드는 Git에(원본), 이미지는 레지스트리에(배포용) 둔다.
  - 이미지 안의 파일은 받은 사람이 다 꺼내 볼 수 있으니, 올리기 전에 .env 같은 비밀이 빠졌는지 확인한다.

### 2. 컨테이너

이미지를 docker run으로 실행한 상태. Dockerfile로 이미지를 만들고, 그 이미지를 실행해 컨테이너를 만든다.

- 실제 작업은 컨테이너 단위로 돈다. 실행 환경을 일정하게 맞추기 위한 격리된 프로세스다.
- 읽기 전용 이미지 위에 쓰기 층을 하나 얹어 돌기 때문에, 실행 중 생긴 파일은 그 층에만 쓰이고 원본 이미지는 그대로다. 그래서 한 이미지로 컨테이너를 여러 개 띄워도 서로 영향이 없다.
- 꺼도(stop) 파일은 남지만, 지우면(rm) 쓰기 층과 함께 파일도 사라진다. 컨테이너는 업데이트할 때마다 지우고 새로 띄우는 "쓰고 버리는 것"이라, 남겨야 할 데이터는 -v로 내 PC 폴더(또는 볼륨)에 연결해 컨테이너 밖에 저장한다.

### 3. 레이어

**정의**
레이어는 Dockerfile의 한 줄 한 줄(파일을 바꾸는 줄)에 의해 만들어지는 층이다. 이미지를 빌드할 때 Dockerfile을 한 줄씩 읽어 오는데, 직전 줄까지 실행한 상태에서 한 줄을 더 읽으면 그 줄의 작업을 수행하고, 직전 상태와 달라진 파일만 새 층으로 저장한다. 같은 파일이 여러 층에 있으면 가장 위(나중에 쌓인) 층의 것이 보인다. 이미지의 층들은 빌드 때 만들어진 읽기 전용이고, 컨테이너를 실행할 때 그 위에 쓰기 층이 하나 얹힌다.

**Dockerfile 명령과 레이어**

| 명령 | 하는 일 | 예시 | 레이어 |
|---|---|---|---|
| FROM | 출발점(베이스 이미지)을 고른다. 항상 첫 줄 | FROM python:3.11-slim | 베이스가 가진 층 여러 개를 그대로 가져와 바닥층으로 깐다 |
| WORKDIR | 이후 명령이 실행될 폴더를 정한다(없으면 만든다) | WORKDIR /app | 빈 폴더가 생긴 만큼의 얇은 층 |
| COPY | 내 PC(빌드 컨텍스트)의 파일을 이미지 안으로 복사한다 | COPY requirements.txt . / COPY . . | 복사한 파일이 담긴 층 |
| RUN | 빌드할 때 명령을 실행한다 | RUN pip install --no-cache-dir -r requirements.txt | 명령이 만들거나 바꾼 파일이 담긴 층(보통 가장 크고 오래 걸림) |
| CMD | 컨테이너가 실행될 때 할 명령을 적어 둔다. 빌드 때는 실행되지 않음 | CMD ["python", "app.py"] | 파일 층은 만들지 않고 이미지 설정으로만 남는다. 여러 번 쓰면 마지막 것만 적용 |

**layer로 나누는 이유**
1. **빌드 캐시로 시간을 아낀다**: 이미 캐시에 저장된 상태까지는 그대로 쓰고, 달라진 줄부터만 새로 빌드한다(달라진 층과 그 위층 전부).
   - Dockerfile은 위에서 아래로 읽는다. 따라서 오래 걸리고 잘 바뀌지 않는 것(패키지 설치)은 위쪽(아래층), 자주 바뀌는 것(코드 복사)은 아래쪽(위층)에 둔다.
2. **공유로 디스크와 다운로드를 아낀다**: 같은 베이스를 쓰는 이미지가 여러 개 있어도 그 베이스 층은 한 번만 저장되고, 이미지마다 다른 층만 따로 저장된다. pull할 때도 내 PC에 이미 있는 층은 건너뛰고 없는 층만 받는다.

**주의**
1. **위층에서 지워도 아래층에는 남는다 → 이미지 크기가 안 줄어든다**

   층은 "달라진 것"만 기록하므로, 위층에서 파일을 지우면 실제로 지우는 게 아니라 "이 파일은 안 보이게 해"라는 표시만 남긴다. 아래층의 파일은 그대로 이미지에 들어 있다.
   ```dockerfile
   # 나쁜 예: 큰 파일이 첫 RUN 층에 남아 이미지가 그만큼 커진다
   RUN curl -o big.zip https://example.com/big.zip
   RUN unzip big.zip && rm big.zip
   # 좋은 예: 받고, 쓰고, 지우기를 한 RUN(한 층) 안에서 끝낸다
   RUN curl -o big.zip https://example.com/big.zip && unzip big.zip && rm big.zip
   ```
2. **비밀은 지워도 새어 나간다**
   1번과 같은 원리로, .env를 COPY한 뒤 다음 줄에서 rm해도 키는 아래층에 남아 있다. 이미지를 받은 사람은 docker save로 층을 풀어 꺼내 볼 수 있다. 그래서
   - 비밀은 처음부터 이미지에 넣지 않는다: .dockerignore에 .env를 넣는다.
   - 키는 실행할 때 밖에서 넣는다: docker run --env-file .env 이미지 
3. **줄 순서를 거꾸로 두면 캐시가 매번 깨진다**
   COPY . .(코드)를 RUN pip install보다 앞에 두면, 코드 한 줄만 고쳐도 그 뒤의 패키지 설치를 매번 처음부터 다시 한다. 3주차에 torch, sentence-transformers가 들어가면 이 실수 하나로 몇 분씩 기다리게 된다.
4. **COPY . .는 폴더 안 아무 파일이나 바뀌어도 캐시가 깨진다**
   COPY는 복사할 파일 내용이 하나라도 달라지면 다시 실행된다. README 한 글자, .venv, __pycache__, .git 변화도 포함된다. 상관없는 파일은 .dockerignore로 빼야 캐시도 살고 이미지도 작아진다.
5. **RUN의 캐시는 명령 글자만 본다 → 오래된 결과를 계속 쓸 수 있다**
   RUN pip install requests처럼 버전을 안 적으면, 명령 글자가 같으니 Docker는 예전에 설치한 층을 계속 재사용한다. 새 버전이 나와도 반영되지 않고, 반대로 캐시가 없는 다른 사람 PC에서는 최신 버전이 깔려 사람마다 결과가 달라진다. 그래서 requirements.txt에 requests==2.32.3처럼 버전을 박고, 일부러 새로 받고 싶을 때는 docker build --no-cache를 쓴다.

### 4. 레지스트리

**정의**
이미지를 저장해 두고, 올리고(push) 받는(pull) 원격 창고. Dockerfile이 아니라 빌드가 끝난 이미지가 저장된다. 그래서 이미지를 받으면 run으로 바로 실행할 수 있다.

**구조**
```
레지스트리 (창고 건물)         예: Docker Hub (docker.io)
 └ 저장소, repository (선반)   예: python, redis, 내아이디/week1-app
    └ 태그, tag (선반 칸 라벨)  예: 3.11-slim, 3.11, latest
```
- 저장소는 같은 종류의 이미지들을 모아 놓은 곳. 이름은 보통 안에 든 핵심 프로그램 이름으로 짓는다. 예를 들어 python 저장소는 파이썬 프로그램 자체가 아니라 파이썬이 설치된 이미지들을 모아 둔다.
- 태그는 이미지 하나를 직접 가리킨다. 예를 들어 python 저장소 안에는
  - 3.11-slim: 리눅스(Debian) 최소판 + Python 3.11
  - 3.11: 리눅스 전체판 + Python 3.11 + 컴파일러 등
  - 3.12-slim: 리눅스 최소판 + Python 3.12
  - 3.11-alpine: 아주 작은 리눅스(Alpine) + Python 3.11
- library는 Docker 공식 이미지(Docker Official Images) 전용 자리다.
- 내가 python 이미지에서 출발해 내 코드까지 넣어 이미지를 만든다면, 저장소 이름을 week1-app 같은 식으로 지으면 된다. 내 PC 안에서는 week1-app이고, Docker Hub에 올릴 때는 내아이디/week1-app(계정/저장소) 형태가 된다. 수정 사항이 생겨 새 버전을 빌드하면 태그를 1.0, 1.1처럼 단다(docker build -t week1-app:1.1 .).

그래서 이미지의 전체 이름은 다음과 같다.
```
docker.io / library / python : 3.11-slim
 레지스트리   계정      저장소    태그
```

**생략 규칙**

| 생략한 것 | Docker가 채우는 값 |
|---|---|
| 레지스트리 | docker.io (Docker Hub) |
| 계정 | library (공식 이미지 자리) |
| 태그 | latest |

그래서 python:3.11-slim만 써도 docker.io/library/python:3.11-slim으로 해석된다.

**태그와 다이제스트**
- 태그는 이름표일 뿐이라 새 이미지로 옮겨 붙을 수 있다. python:3.11-slim도 보안 패치(3.11.17 → 3.11.18 등)가 나오면 새 이미지를 가리킨다. 그래서 오늘 받은 것과 나중에 받은 것이 다를 수 있다.
  ```
  2026-10-26에 받은 python:3.11-slim  → Python 3.11.17이 든 이미지
  패치 후에 받은     python:3.11-slim  → Python 3.11.18이 든 이미지 (이름은 같은데 내용이 다름)
  ```
- latest는 "최신 보장"이 아니라 태그를 안 적었을 때 붙는 기본 이름이다. 올린 사람이 갱신하지 않으면 옛날 것을 가리킬 수도 있다.
  ```powershell
  docker pull redis                  # = docker pull redis:latest
  docker build -t week1-app .        # = week1-app:latest
  docker build -t week1-app:1.1 .    # 1.1만 새 이미지. latest는 여전히 예전 이미지를 가리킴
  ```
- 절대 안 바뀌게 가리키려면 다이제스트(이미지 내용으로 계산한 해시)를 쓴다. 내용이 1비트만 달라도 값이 바뀌므로, 이걸로 부르면 언제나 같은 이미지가 온다.
  ```dockerfile
  # 태그로 고르기: 빌드하는 날에 따라 다른 이미지가 올 수 있음
  FROM python:3.11-slim
  # 다이제스트로 고르기: 언제 빌드해도 같은 이미지
  FROM python:3.11-slim@sha256:b7a9e5f6a93d6d4a31f129bbd4bdee69efccb6ded0fb230d78aafaf37af98377
  ```
  내 PC에 있는 이미지의 다이제스트는 docker images --digests로 볼 수 있다.

**push / pull이 실제로 하는 일**
- docker pull: 이미지 설명서(매니페스트)를 먼저 받고, 내 PC에 없는 층만 내려받는다. 이미 있는 층은 Already exists로 건너뛴다.
- docker push: 레지스트리에 없는 층만 올린다. 베이스 층은 Docker Hub에 이미 있으니 내 코드가 담긴 작은 층만 올라간다.
- docker run할 때 내 PC에 이미지가 없으면 알아서 pull부터 한다(Unable to find image locally → Pulling from ...).
```powershell
docker login                                  # 창고에 로그인
docker tag week1-app 내아이디/week1-app:1.0   # 창고용 이름표 붙이기 (복사가 아니라 이름만 하나 더)
docker push 내아이디/week1-app:1.0            # 올리기
docker pull 내아이디/week1-app:1.0            # 받기 (다른 사람 PC에서)
docker run --rm 내아이디/week1-app:1.0        # 받은 이미지 실행 (pull을 안 했으면 여기서 자동으로 받음)
```
- 레지스트리 없이 파일로 넘길 때는 docker save -o app.tar week1-app → 받는 쪽에서 docker load -i app.tar.

**레지스트리의 종류**

| 종류 | 예 | 특징 |
|---|---|---|
| 공개 레지스트리 | Docker Hub (기본값) | 공식 이미지가 있는 곳. 무료 저장소는 기본이 공개 |
| 코드 저장소에 붙은 것 | GitHub Container Registry (ghcr.io) | GitHub 저장소와 권한을 함께 관리. 팀 프로젝트에 편함 |
| 클라우드 회사 것 | AWS ECR, Google Artifact Registry, Azure ACR | 회사 서버(클라우드) 가까이에 두고 비공개로 씀 |
| 직접 세우는 것 | Harbor, registry 이미지 | 회사 내부망에 설치. 외부 인터넷과 끊어진 곳에서 씀 |

금융권처럼 망 분리 규제가 있는 곳은 외부 Docker Hub를 직접 못 쓰는 경우가 많아, 내부 레지스트리를 세우고 보안 검사(이미지 스캔)를 통과한 이미지만 들여놓는다.

**주의**
1. **공개 저장소에 올린 이미지는 누구나 열어 볼 수 있다.** 층을 풀면 모든 파일이 보이므로, .env나 API 키가 이미지에 들어가지 않게 매우 주의한다(레이어 주의 2번, .dockerignore).
2. **배포할 때는 latest 대신 버전 태그를 명시한다.** week1-app:1.1처럼 버전을 적어 두면 지금 어떤 이미지가 돌고 있는지 명확하고, 문제가 생기면 1.0으로 되돌리기도 쉽다.

## 내가 막힌 점

**에러**
- Dockerfile 첫 줄을 ROM python:3.11-slim(F 빠짐)으로 씀 → Docker는 줄 맨 앞 단어를 명령으로 읽으므로 1번 줄에서 실패 → FROM으로 고침
- FROM python:3.11:3.11-slim → failed to parse stage name "python:3.11:3.11-slim": invalid reference format → 이미지 이름은 저장소:태그라 콜론이 한 번만 들어감. FROM python:3.11-slim으로 고침. 고친 뒤 저장(Ctrl+S)을 안 해서 같은 에러가 한 번 더 났음
- docker run --rm size-b ls -A/app → ls: invalid option -- '/' → 옵션과 경로 사이를 띄어 써야 함(ls -A /app). 에러를 낸 건 Docker가 아니라 컨테이너 안의 ls
- -t에 이름을 잘못 붙임(1_hello를 week1-port로 빌드) → docker tag week1-port week1-app 후 docker rmi week1-port로 이름표만 바꿈(이미지는 그대로, "Untagged"만 나옴)
- --rm 없이 실행한 컨테이너가 docker ps -a에 Exited로 남아 있음 → docker rm <ID 앞 몇 글자>로 삭제

**헷갈렸던 점**
- 설계서는 이미지가 아니라 Dockerfile. 이미지는 설치까지 끝난 결과물.
- 볼륨이 필요한 이유는 "계속 켜 둘 수 없어서"가 아니다. 꺼도(stop) 파일은 남고, 지울 때(rm) 사라진다. 컨테이너는 업데이트마다 지우고 새로 띄우는 것이라 데이터는 밖에 둔다.
- "위/아래"는 기준이 두 개다. Dockerfile 글에서 위쪽에 적은 줄 = 층으로는 아래층(먼저 쌓임). 헷갈리면 "앞/뒤(먼저/나중에 실행)"로 말한다.
- "직전 상태" = 바로 윗줄까지 실행한 결과(지금까지 쌓인 층 전부). 각 줄은 그 위에서 실행되고, 달라진 것만 새 층이 된다.
- 저장소 이름 python은 프로그램이 아니라 "파이썬이 설치된 이미지들을 모아 둔 선반"의 이름표다. 실제 이미지는 태그로 구분되는 각 칸이다.

## 출처

- Docker Docs, What is an image? — https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/
- Docker Docs, What is a container? — https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/
- Docker Docs, What is a registry? — https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-registry/
- Docker Docs, Docker build cache — https://docs.docker.com/build/cache/
- Docker Docs, Dockerfile reference — https://docs.docker.com/reference/dockerfile/
- Docker Docs, Bind mounts — https://docs.docker.com/engine/storage/bind-mounts/
- Docker Docs, Port publishing and mapping — https://docs.docker.com/engine/network/port-publishing/
- Docker Docs, Build context (.dockerignore) — https://docs.docker.com/build/concepts/context/
