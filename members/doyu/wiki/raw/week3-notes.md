# 3주차 실습 메모

환경: macOS (arm64), Python 3.11, LangChain core 1.7.6, langchain-chroma 1.1.0, sentence-transformers 6.2.0, 임베딩 `BAAI/bge-m3`, 생성 `claude-opus-5-5`

## 문서 데이터
- 팀 저장소 `members/*/wiki/pages/*.md` 16개 페이지 (팀 위키 `team/wiki/`는 아직 비어 있음)
- 팀 저장소 클론을 `main` 브랜치에 두고 실행. 내 `doyu/week3` 브랜치에서는 `rag-pipeline.md`가 더해져 17페이지가 되고 청크 수가 달라짐 (500 기준 112 → 116, 점수는 같음)
- 페이지 이름이 겹침 (`doyu/async-fastapi`, `mingi/async-fastapi`) → `metadata["page"]`를 `멤버/파일이름`으로 붙임
- 청크 ID: `멤버/페이지::001` 형식, 중복 없음을 `assert`로 확인

## 질문셋 (`week3/questions.jsonl`, 20개)
- 위키 페이지를 직접 읽고 만듦. 정답 페이지가 여러 개일 수 있어 `answer_pages` 목록으로 적음 (한 개만 적은 `answer_page` 형식도 채점 가능)
- 질문에 페이지 제목의 단어를 그대로 쓰지 않으려고 바꿔 말함 (예: "compose" 대신 "컨테이너 여러 개를 파일 하나로")

## 청크 크기 비교 (k=5, bge-m3, overlap = size의 10%)

| chunk_size | overlap | 청크 수 | Recall@5 | MRR@5 | 평균 검색(ms) |
| --- | --- | --- | --- | --- | --- |
| 200 | 20 | 305 | **1.00** | **0.938** | 51 |
| 500 (기준선) | 50 | 112 | 0.95 | 0.925 | 30 |
| 1000 | 100 | 55 | 0.95 | 0.925 | 38 |

- 500, 1000에서 같은 질문 하나를 못 찾음: "컨테이너 여러 개를 파일 하나로 같이 띄우는 방법은?" → 정답 `mingi/docker-compose` 대신 `sejin/1-docker-concepts`가 1~2위
  - 질문에 "compose"라는 단어가 없고 "컨테이너"만 겹쳐서, 컨테이너 설명이 긴 페이지가 더 비슷하게 나옴
  - 200자로 잘게 자르면 compose 소개 문단이 따로 청크가 돼서 찾음
- 질문이 20개뿐이라 한 문제가 0.05 차이. 청크 200이 낫다고 결론 내기에는 표본이 작음
- 청크가 작을수록 청크 수가 늘어 검색이 조금 느려짐 (305개 51ms vs 112개 30ms)

## 검색 확인
`python rag.py "컨테이너 안에서 Redis 주소를 localhost로 쓰면 안 되는 이유는?"` (키 없이 검색만)
1. `sejin/2-fastapi-redis-async::016` "compose 안에서 Redis 주소는 localhost가 아…"
2. `mingi/docker-compose::004`
3. `sejin/2-fastapi-redis-async::009`

## 생성 (Claude)
- LCEL: `{"question", "docs": retriever}` → `context` 만들기 → `ask_claude` → `{"answer", "sources"}`
- 시스템 프롬프트로 "문맥 안의 내용만 근거로" 답하게 하고, 출처는 검색된 청크의 `page`를 순서대로 중복 없이 돌려줌
- 안전 분류기가 거절하면 서버가 다른 모델로 다시 시도하도록 `fallbacks="default"` 사용
- 키는 `.env`의 `ANTHROPIC_API_KEY`로만 읽음. 키가 없으면 검색 결과만 출력

| 질문 | 답변 요약 | 출처 | 전체 시간 |
| --- | --- | --- | --- |
| 컨테이너 안에서 Redis 주소를 localhost로 쓰면 안 되는 이유는? | localhost는 컨테이너 자기 자신, compose 서비스 이름 `redis`로 접속 | sejin/2-fastapi-redis-async, mingi/docker-compose | 27.7s |
| async 함수 안에서 time.sleep을 쓰면 왜 다른 요청까지 멈춰? | 이벤트 루프 하나가 처리하고 `await`에서만 양보, 3·6·9초 실험 인용 | doyu/async-fastapi, huiji/when-to-use-async, mingi/async-fastapi | 19.0s |
| 쿠버네티스 Pod는 어떻게 스케일링해? (위키에 없는 질문) | "위키에 쿠버네티스 내용이 없어요"라고 답함 | 검색은 무관한 mingi 페이지 5개 | 17.1s |

- 위키에 없는 질문에도 지어내지 않고 "없다"고 답함. 시스템 프롬프트의 "문맥 안의 내용만 근거로"가 효과가 있었음
- 다만 검색은 항상 k=5개를 돌려주므로, 출처 목록만 보면 관련 없는 페이지도 나옴. 4주차에 유사도 점수 기준을 두는 것을 생각해 볼 것
- 시간에는 bge-m3 로드(몇 초)와 Claude 생성이 다 들어 있음. 4주차에 서버로 띄우면 모델 로드는 한 번만 함

## 막힌 점
- `.env`의 `WIKI_ROOT`에 `members/doyu`를 넣었더니 `Directory not found` 에러 → 빈 값으로 두면 기본 경로(`../../Study-service_basic/members`)를 씀
- `.env`에 `WIKI_ROOT=`처럼 빈 값을 두면 `os.getenv("WIKI_ROOT", 기본값)`이 빈 문자열을 돌려줘서 경로가 현재 폴더가 됨 → `os.getenv(...) or 기본값`으로 수정
- 첫 실행 때 bge-m3 모델(약 2GB)을 내려받느라 1분 넘게 걸림. 두 번째부터는 캐시에서 바로 로드

## 참고 링크
- https://python.langchain.com/docs/how_to/recursive_text_splitter/
- https://huggingface.co/BAAI/bge-m3
- https://docs.trychroma.com/
- https://platform.claude.com/docs/
