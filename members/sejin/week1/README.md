# 1주차: Docker 기초 실습

Python 스크립트를 Docker 이미지로 만들어 실행하고, 볼륨(`-v`)과 포트(`-p`)로 컨테이너를 바깥과 연결하고, 베이스 이미지와 `.dockerignore`에 따라 이미지 크기가 어떻게 달라지는지 비교했다.

- 환경: Windows 11, Docker Desktop (WSL2), PowerShell
- 모든 명령은 각 실습 폴더 안에서 실행한다.

| 폴더 | 실습 | 핵심 |
|---|---|---|
| `1_hello/` | Dockerfile 작성 → 빌드 → 실행 | 컨테이너는 이미지 안의 리눅스와 파이썬으로 돈다 |
| `2_volume/` | 볼륨 마운트 `-v` | 컨테이너 안에 쓴 파일은 지우면 사라지고, `-v`로 연결해야 내 PC에 남는다 |
| `3_port/` | 포트 매핑 `-p` | `-p`가 없으면 컨테이너 안 서버에 접속할 수 없다 |
| `4_size/` | (선택) slim + `.dockerignore` 크기 비교 | slim이 크기를 크게 줄이고, `.dockerignore`는 비밀 파일을 막는다 |

---

## 1_hello: Dockerfile 작성 → 빌드 → 실행

컨테이너 안의 파이썬 버전과 OS를 출력해서, 내 PC와 다른 환경인지 확인한다.

```powershell
docker build -t week1-app .
docker run --rm week1-app          # 실행하고 끝나면 컨테이너 삭제
docker run -it --rm week1-app bash # 컨테이너 안에 들어가 보기 (exit로 종료)
```

확인한 것
- 내 PC에서 `python app.py`는 Windows와 내 PC의 파이썬 버전을, 컨테이너에서는 Linux와 이미지 안의 파이썬 3.11 버전을 출력한다.
- `--rm` 없이 실행하면 `docker ps -a`에 `Exited` 상태로 남고, `docker rm`으로 지운다.

## 2_volume: 볼륨 마운트 -v

컨테이너가 `/app/out/result.txt`에 파일을 쓴다.

```powershell
docker build -t week1-volume .
docker run --rm week1-volume                          # 1) -v 없이
docker run --rm -v ${PWD}/out:/app/out week1-volume   # 2) 내 PC의 out 폴더와 연결
```

확인한 것
- 1) "저장 완료"가 출력되지만 내 PC에 `out` 폴더가 생기지 않는다. 파일은 컨테이너의 쓰기 층에 쓰였다가 `--rm`으로 컨테이너와 함께 지워졌다.
- 2) 내 PC에 `out/result.txt`가 생긴다: `컨테이너가 쓴 파일 (14:10:22)`

## 3_port: 포트 매핑 -p

컨테이너 안에서 파이썬 내장 웹 서버를 8000번 포트로 띄운다.

```powershell
docker build -t week1-port .
docker run -d --rm --name port-test -p 8000:8000 week1-port   # 내PC포트:컨테이너포트
# 브라우저에서 http://localhost:8000
docker stop port-test
```

확인한 것
- `-p` 없이 실행하면 서버는 컨테이너 안에서 돌지만 브라우저로 접속되지 않는다.
- `-p 8000:8000`으로 실행하면 접속되고, `docker ps`의 PORTS에 `0.0.0.0:8000->8000/tcp`가 보인다.

## 4_size: (선택) slim + .dockerignore 크기 비교

실제 프로젝트처럼 `.venv`, `data/`, 가짜 키가 든 `.env`를 두고 `COPY . .`로 빌드했다. 한 번에 하나만 바꿔 세 번 쟀다.

```powershell
docker build -t size-a .      # FROM python:3.11, .dockerignore 없음
docker build -t size-b .      # FROM python:3.11-slim, .dockerignore 없음
docker build -t size-c .      # FROM python:3.11-slim, .dockerignore 있음
docker images
docker run --rm size-b ls -A /app       # 이미지 안에 무엇이 들어갔나
docker run --rm size-b cat /app/.env    # 가짜 키가 이미지 안에 있나
```

| 측정 | 베이스 | .dockerignore | 이미지 크기 (`docker images` SIZE) |
|---|---|---|---|
| A | python:3.11 | 없음 | 1.63GB |
| B | python:3.11-slim | 없음 | 222MB |
| C | python:3.11-slim | 있음 | 187MB |

- A → B (slim으로 교체): 1.63GB → 222MB. 크기를 가장 많이 줄였다.
- B → C (`.dockerignore` 추가): 222MB → 187MB. `.venv`와 `data/`가 빠진 만큼 줄었다.
- B는 `/app`에 `.env`까지 들어가 `cat`으로 가짜 키가 그대로 보였다. C는 `.env`가 들어가지 않는다. `.dockerignore`의 더 큰 역할은 크기보다 **비밀 파일이 이미지에 들어가는 것을 막는 것**이다.

`.dockerignore`
```
.venv/
data/
.env
__pycache__/
*.pyc
```

`.env`에는 테스트용 가짜 값만 넣었다. `.env`와 `.venv/`는 `.gitignore`에 있어 저장소에 올라가지 않는다.
