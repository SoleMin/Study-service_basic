# 팀 위키 색인

개인 위키(`members/<이름>/wiki/pages/`)를 `scripts/merge_wiki.py`로 모은 목록이에요. 이 파일은 스크립트가 다시 만들어요.
페이지를 고치려면 `team/wiki/`가 아니라 원본 개인 위키를 고친 뒤 스크립트를 다시 실행해요.

| 주차 | 페이지 | 한 줄 요약 | 작성자 |
| --- | --- | --- | --- |
| 1 | [컨테이너 관리 명령어 (1주차)](container-commands_mingi.md) | docker ps: 지금 실행 중인 컨테이너 목록확인 (-a: 종료된것 까지 확인) | mingi |
| 1 | [Dockerfile 명령어와 빌드 캐시 (1주차)](dockerfile-instructions_mingi.md) | docker에 사용할 이미지의 빌드 과정을 담은 파일, 작성된 명령어를 한줄한줄 해석하면서 이미지를 빌드한다 | mingi |
| 1 | [이미지, 컨테이너, 레이어, 레지스트리 (1주차)](image-container-layer-registry_mingi.md) | 컨테이너: 도커로 인해 조성된 독립된 환경. VM과 비슷한 개념이지만 VM은 하드웨어 같은 정보들이 포함된… | mingi |
| 1 | [VM, 컨테이너, conda 비교 (1주차)](vm-conda-docker_mingi.md) | VM은 자신의 커널을 가진 OS 전체를 가진 독립된 환경을 만들고, 컨테이너는 그보다 조금 더 가벼운 개념으… | mingi |
| 1 | [볼륨 마운트(-v)와 포트 매핑(-p) (1주차)](volume-port_mingi.md) | docker환경내의 폴더와 내 환경의 폴더를 동기화 시키는 작업 | mingi |
| 1 | [Docker 핵심 개념: 이미지, 컨테이너, 레이어, 레지스트리](1-docker-concepts_sejin.md) | Dockerfile(설계서)대로 설치까지 끝내 묶은 결과물이 이미지, 그 이미지를 실행한 격리된 프로세스가… | sejin |
| 2 | [FastAPI에서 async가 필요한 때](async-fastapi_doyu.md) | async def는 기다리는 동안 다른 요청을 처리할 수 있게 해 주는 함수다. 기다림(I/O)이 많은 작업… | doyu |
| 2 | [이미지와 컨테이너의 차이](image-vs-container_huiji.md) | 이미지는 설계 도면이고 컨테이너는 도면대로 만든 것이다. | huiji |
| 2 | [async 함수는 언제 필요한가](when-to-use-async_huiji.md) | async def는 await로 기다리는 동안 서버가 다른 요청을 처리하게 해주는 함수 형태이다. | huiji |
| 2 | [API 키 관리: .env와 .gitignore (2주차)](api-key-env_mingi.md) | 내가 사용할 모델을 호출하기 위한 일종의 열쇠, 만약 API키를 가지고 있다면 누구든지 모델을 불러쓸 수 있… | mingi |
| 2 | [FastAPI에서 async가 필요한 때 (2주차)](async-fastapi_mingi.md) | async는 기다리는 동안 다른 작업을 처리 하기 위해 사용한다 await는 여기서 기다리는 동안 다른 작업… | mingi |
| 2 | [docker compose: 컨테이너 여러 개를 한 번에 (2주차)](docker-compose_mingi.md) | 여러 컨테이너의 실행설정을 하나에 적어두고 한번에 동작시키기 위해 필요함, run을 여러번 실행하는건 매 실… | mingi |
| 2 | [FastAPI 기본: 엔드포인트, Pydantic, /docs (2주차)](fastapi-basics_mingi.md) | FastAPI: "어떤 주소로 요청이 오면 어떤 함수를 실행할지"를 정하는 프레임워크, 자체로는 요청을 받을… | mingi |
| 2 | [Redis로 LLM 응답 캐시하기 (TTL) (2주차)](redis-ttl-cache_mingi.md) | 서버에서 캐쉬를 저장해서 사용할 수 있는 DB개념의 시스템 | mingi |
| 2 | [2주차: FastAPI, Redis, async](2-fastapi-redis-async_sejin.md) | FastAPI는 함수 위에 @app.get("/주소")를 붙여 인터넷 요청을 받는 창구(엔드포인트)를 만드는… | sejin |
| 3 | [청킹: 문서를 어떻게 자를까 (3주차)](chunking_mingi.md) | 임베딩 모델이 최대 처리할 수 있는 토큰의 수가 한계가 존재하기 떄문에 처리할 수 있는 범위로 문서를 자르는… | mingi |
| 3 | [임베딩과 sentence-transformers (3주차)](embedding-sentence-transformers_mingi.md) | 자연어 정보를 모델이 이해할 수 있는 벡터 형태로 변환하는것. | mingi |
| 3 | [LCEL로 검색 + 생성 체인 만들기, 출처 반환 (3주차)](lcel-rag-chain_mingi.md) | 랭체인에서 파이프라인 구축을 간편하게 하기 위해 사용하는 표현식 언어 | mingi |
| 3 | [검색 평가: Recall@k와 MRR@k (3주차)](rag-evaluation_mingi.md) | RAG의 가장 큰 이점은 문서를 찾는 부분이다. 그래서 LLM 호출없이 빠르게 확인할 수 있는 부분만 체크해… | mingi |
| 3 | [RAG 파이프라인의 흐름 (3주차)](rag-pipeline_mingi.md) | 모든 정보를 LLM에 넣을 수 없고 만약 정보가 최신화라도 되면 학습을 다시 시켜야 하는 비용같은 문제가발생… | mingi |
| 3 | [유사도와 벡터 DB: 코사인, 내적, L2, Chroma, HNSW (3주차)](vector-db-similarity_mingi.md) | 벡터의 거리를 확인한다. 코사인 유사도는 방향, 내적은 곂치는 방향 값의 크기, L2는 방향과 길이까지 확인… | mingi |

## 같은 주제 후보

제목과 파일 이름이 비슷한 페이지예요(자동 추정이라 틀릴 수 있어요). 세션에서 하나로 합칠지 정하고, 합친 페이지는 자동 생성 표시 없이 따로 둬요.

- 2-fastapi-redis-async_sejin, async-fastapi_doyu, async-fastapi_mingi, when-to-use-async_huiji
- 1-docker-concepts_sejin, image-container-layer-registry_mingi, image-vs-container_huiji

## 초안이라 건너뛴 페이지

- addie/async-when-needed: async 함수는 언제 필요한가 (초안)
