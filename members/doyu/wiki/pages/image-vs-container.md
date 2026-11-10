# 이미지와 컨테이너의 차이

## 한 줄 정의
이미지는 앱을 실행하는 데 필요한 모든 것을 담은 **읽기 전용 설계도**이고, 컨테이너는 그 이미지를 **실행한 인스턴스**다.

## 왜 필요한가
- "내 컴퓨터에선 되는데"를 없애기 위해. 이미지 하나로 어느 컴퓨터에서든 같은 환경을 띄울 수 있다.
- 이미지는 한 번 만들면 바뀌지 않으므로, 같은 이미지로 컨테이너를 여러 개 띄워도 모두 같은 상태에서 시작한다.
- 컨테이너는 지우고 다시 만들기 쉽다. 대신 안에서 바꾼 내용도 같이 사라지므로, 남겨야 할 데이터는 볼륨(`-v`)으로 호스트에 둔다.

### 관련 개념
| 개념 | 설명 |
| --- | --- |
| 레이어 | Dockerfile 명령 한 줄이 레이어 하나. 바뀐 레이어부터 아래는 다시 빌드된다 |
| 레지스트리 | 이미지를 저장하고 나눠 받는 곳 (Docker Hub). `docker pull`로 받는다 |

## 최소 예제
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["python", "app.py"]
```
```bash
docker build -t week1-app .      # 이미지 만들기 (설계도)
docker run --rm week1-app        # 컨테이너 실행 (인스턴스), 끝나면 삭제
docker images                    # 이미지 목록
docker ps -a                     # 컨테이너 목록
```

## 내가 막힌 점
- Docker Desktop 앱이 꺼져 있으면 `docker` 명령이 `docker.sock`에 연결하지 못한다. 앱을 먼저 켜야 한다.
- `COPY app.py .`를 `pip install`보다 위에 두면, `app.py`만 고쳐도 `pip install`이 매번 다시 실행된다 (0.3s → 2.6s). 레이어 캐시는 바뀐 줄부터 아래를 전부 무효화하기 때문이다.
- 컨테이너 안에서 서버를 띄워도 `-p`가 없으면 호스트에서 접속할 수 없었다.

## 출처
- Docker 공식 문서, What is an image?: https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/
- Docker 공식 문서, What is a container?: https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/
- Docker 공식 문서, Build cache: https://docs.docker.com/build/cache/
- 직접 실습: [week1-notes.md](../raw/week1-notes.md)
