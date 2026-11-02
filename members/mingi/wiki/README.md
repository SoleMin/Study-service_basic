# mingi 위키 목차

주차별로 어떤 페이지를 썼는지 정리한 목록이에요. 새 페이지를 쓰면 해당 주차 표에 한 줄 추가해요.

- `pages/`: 내 말로 정리한 개념 페이지 (내 정리 → Claude 피드백)
- `raw/`: 실습하면서 겪은 문제 기록

## 1주차: Docker 기초

| 페이지 | 다루는 내용 |
| --- | --- |
| [image-container-layer-registry.md](pages/image-container-layer-registry.md) | 이미지, 컨테이너, 레이어, 레지스트리 |
| [vm-conda-docker.md](pages/vm-conda-docker.md) | VM, 컨테이너, conda 비교 |
| [dockerfile-instructions.md](pages/dockerfile-instructions.md) | Dockerfile 명령어와 빌드 캐시 |
| [volume-port.md](pages/volume-port.md) | 볼륨 마운트(-v)와 포트 매핑(-p) |
| [container-commands.md](pages/container-commands.md) | 컨테이너 관리 명령어 |

## 2주차: FastAPI + docker compose + Redis

| 페이지 | 다루는 내용 |
| --- | --- |
| [fastapi-basics.md](pages/fastapi-basics.md) | FastAPI 기본: 엔드포인트, Pydantic, /docs |
| [api-key-env.md](pages/api-key-env.md) | API 키 관리: .env와 .gitignore |
| [docker-compose.md](pages/docker-compose.md) | docker compose: 컨테이너 여러 개를 한 번에 |
| [redis-ttl-cache.md](pages/redis-ttl-cache.md) | Redis로 LLM 응답 캐시하기 (TTL) |
| [async-fastapi.md](pages/async-fastapi.md) | FastAPI에서 async가 필요한 때 |

문제 기록: [raw/week2-troubleshooting.md](raw/week2-troubleshooting.md)
