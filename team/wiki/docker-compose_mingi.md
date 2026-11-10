<!-- merge_wiki.py 자동 생성: 원본 members/mingi/wiki/pages/docker-compose.md . 수정은 원본에서 하세요 -->

# docker compose: 컨테이너 여러 개를 한 번에 (2주차)

## 내 정리

### Q. docker compose란 무엇인가? docker run을 여러 번 치는 것과 무엇이 다른가?

여러 컨테이너의 실행설정을 하나에 적어두고 한번에 동작시키기 위해 필요함, run을 여러번 실행하는건 매 실행마다 옵션을 기억해서 작성해야하기 때문

### Q. 서비스란 무엇인가? api 컨테이너 안에서 Redis 주소가 localhost가 아니라 redis인 이유는?

서비스는 컨테이너의 이름 같은것, `localhost`는 자기 자신의 이름이라 다른 컨테이너에서 찾기 위해서는 서비스 이름으로 찾아야함

### Q. build, ports, env_file, environment, depends_on은 각각 무엇을 하나?

docker run의 설정들과 같은 역할을 함

- **build**: "`docker build -t 이름`"의 역할들 대체 docker파일 이미지를 저장, `.`으로 사용하면 Dockerfile대로 사용하라는것 2주차에서는 `.`으로 사용했음
- **port**: run의 `-p` 옵션 2주차에서는 `ports: "8000:8000"`로 사용했음
- **env_file**: docker에서 사용할 환경 변수를 불러오기 위해서 사용 `.env`로 사용하면 안의 값들을 환경변수로 넣어줌
- **environment**: env파일과 비슷하지만 비밀로 되어야 하느것, 아닌것을 구분해서 사용할 때. 2주차 에서는 redis를 사용하기 위해서 이 값에 저장함

### Q. --host 0.0.0.0은 왜 필요한가?

모든 곳에서 오는 요청을 받아라 를 설명하기 위해

## 내가 막힌 점

(`../raw/week2-troubleshooting.md`에서 이 주제와 관련된 것을 골라 내 말로)

## Claude 피드백

- **Q1**: 정확해요. 덧붙이면 compose 파일은 Git에 올라가서 팀원 누구나 `docker compose up` 한 줄로 같은 환경을 띄울 수 있어요. 실행 설정 자체가 문서가 되는 게 큰 장점이에요.
- **Q2 (서비스)**: 맞아요. compose는 서비스들을 하나의 네트워크로 묶고, **서비스 이름을 도메인 이름처럼** 쓰게 해 줘요. 그래서 api 컨테이너 안에서 `redis://redis:6379`로 접속돼요. 컨테이너 안의 `localhost`는 그 컨테이너 자신이라 Redis가 없어요.
- **build**: `build: .`는 "현재 폴더를 빌드 재료로, 그 안의 Dockerfile로 이미지를 만들어라"예요. `docker build`를 compose가 대신 해 주는 거예요.
- **ports**: 키 이름은 `ports`(복수)이고 목록으로 적어요. `"호스트:컨테이너"` 순서는 `-p`와 같아요.
- **environment (보완)**: 비밀 여부를 compose가 구분해 주는 기능은 아니에요. yml에 값을 **직접** 적는 방식이라, 보통 비밀은 Git에 안 올라가는 `.env` + `env_file`로, 비밀이 아닌 설정(`REDIS_URL` 같은)은 `environment`에 적는 관례예요. 같은 키가 양쪽에 있으면 `environment`가 이겨요.
- **depends_on (빠짐)**: 실행 순서를 정해요. `redis`를 먼저 켠 뒤 `api`를 켜요. 단 "켜진 순서"만 보장하고 "준비 완료"까지 기다리진 않아요. 기다리게 하려면 `healthcheck` + `condition: service_healthy`를 써요.
- **Q4 (--host 0.0.0.0)**: uvicorn 기본값은 `127.0.0.1`이라 **컨테이너 자기 자신에게서 온 요청만** 받아요. 포트 매핑으로 들어오는 요청은 바깥(컨테이너 네트워크)에서 오기 때문에, `0.0.0.0`으로 "모든 네트워크 인터페이스에서 받기"를 켜야 내 PC 브라우저에서 접속돼요.

## 출처

-
