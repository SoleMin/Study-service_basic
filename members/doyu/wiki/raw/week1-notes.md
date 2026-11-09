# 1주차 실습 메모

환경: macOS (arm64), Docker 29.9.2, Python 3.11.17

## Dockerfile 빌드와 실행
- `docker build -t week1-app .` → `docker run --rm week1-app`
- 출력: `Python: 3.11.17 ...`, `requests: 2.32.3`

## 빌드 캐시 실험
`app.py`에 한 줄 추가한 뒤 다시 빌드했을 때:

| Dockerfile | 레이어 순서 | 재빌드 시간 | pip install |
| --- | --- | --- | --- |
| `Dockerfile` | requirements → pip install → app.py | 0.3s | CACHED |
| `Dockerfile.bad` | app.py → requirements → pip install | 2.6s | 다시 실행 |

- 바뀐 레이어부터 아래는 전부 다시 빌드된다.
- 자주 바뀌는 파일(`app.py`)은 Dockerfile 아래쪽에, 잘 안 바뀌는 의존성 설치는 위쪽에 둔다.
- requests 하나라서 2.6s지만, 패키지가 많아지면 차이가 분 단위로 커진다.

## 포트 매핑 (-p)
- `-p` 없이 `python -m http.server 8000` 실행 → `curl localhost:8000` 연결 실패
- `-p 8000:8000` → HTTP 200, `docker port`: `8000/tcp -> 0.0.0.0:8000`
- 컨테이너 안에서 서버가 떠 있어도 포트를 열어 주지 않으면 호스트에서 못 들어간다.

## 볼륨 마운트 (-v)
- `-v` 없이 컨테이너 안에 파일 생성 → `--rm`으로 지워지면 호스트엔 아무것도 없음 (data/ 파일 0개)
- `-v "$(pwd)/data:/data"`로 `/data/hello.txt` 생성 → 컨테이너가 사라져도 호스트 `data/hello.txt`에 `from container`가 남음

## (선택) .dockerignore + 이미지 크기
| 이미지 | 베이스 | 크기 |
| --- | --- | --- |
| week1-full | python:3.11 | 1.62GB |
| week1-slim | python:3.11-slim | 234MB |

- `.dockerignore`에 `wiki/`, `data/`, `.env` 등을 넣었더니 이미지 `/app`에는 `app.py`, `requirements.txt`만 들어감
- `.env`를 넣어 두면 실수로 API 키가 이미지에 들어가는 걸 막을 수 있다.

## 에러 로그
- Docker Desktop 앱이 꺼져 있으면 `failed to connect to the docker API at unix:///var/run/docker.sock` → 앱 실행 후 해결

## 참고 링크
- https://docs.docker.com/get-started/
- https://docs.docker.com/build/cache/
- https://docs.docker.com/build/concepts/context/#dockerignore-files
