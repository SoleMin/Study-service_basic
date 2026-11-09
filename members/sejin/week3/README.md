# 3주차: 팀 위키 RAG (LangChain + Chroma + bge-m3 + Claude)

팀원 위키(`members/*/wiki/pages/*.md`)에서 질문과 가까운 청크 5개를 찾고, Claude가 그 내용만 근거로 답한 뒤 출처 페이지를 함께 돌려준다. 위키에 없는 질문에는 "위키에 없는 내용입니다"라고 답한다.

- 임베딩: `BAAI/bge-m3` (내 PC에서 실행, 벡터 1024차원, `normalize_embeddings=True` 라서 내적 = 코사인 유사도)
- 벡터 DB: Chroma (`hnsw:space=cosine`, 컬렉션 `team_wiki_500`, `chroma_db/` 에 저장)
- 생성: `claude-haiku-5-5`, LCEL 체인
- 기준선: `RecursiveCharacterTextSplitter` chunk 500 / overlap 50, k=5
- 환경: Windows 11, Python 3.11, CPU

## 노트북 구성 (`rag.ipynb`)

| 단계 | 하는 일 |
|---|---|
| 1. 로드 | `DirectoryLoader` 로 팀원 위키 16개 페이지를 읽고 `metadata["page"] = "팀원/파일이름"` 을 붙임 |
| 2. 분할 | 500자 / 50자 겹침으로 112개 청크. 청크 ID는 `페이지#번호` (예: `mingi/redis-ttl-cache#2`) |
| 3. 임베딩 | bge-m3로 문장을 벡터로. 뜻이 비슷한 문장이 더 가까운지 실험 |
| 4. 저장 | 112개 청크를 Chroma에 저장 |
| 5. 검색 | `similarity_search_with_score` 로 점수 확인, `as_retriever(k=5)` |
| 6. 생성 | 검색 결과를 `[페이지]` + 내용으로 합쳐 프롬프트에 넣고 답 + 출처 반환 |
| 7. 평가 | 임시 질문 11개로 Recall@5, MRR@5 |

LCEL 체인은 질문 하나에서 칸을 늘려 간다. `.assign` 이 앞 칸을 버리지 않아서 마지막에 `docs` 가 남고, 그 `metadata["page"]` 로 출처를 보여 준다.

```python
rag_chain = (
    {"docs": retriever, "question": RunnablePassthrough()}                  # 검색 + 질문
    | RunnablePassthrough.assign(context=lambda x: format_docs(x["docs"]))  # 청크를 글로
    | RunnablePassthrough.assign(answer=prompt | llm | StrOutputParser())   # 답
)
```

## 실행

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # ANTHROPIC_API_KEY 에 키 입력
```

- VS Code에서 `rag.ipynb` 를 열고 커널을 `week3\.venv` 로 선택 (목록에 없으면 `Python: Select Interpreter` → `Enter interpreter path` 로 `.venv\Scripts\python.exe` 지정)
- 1번 셀의 `WIKI_ROOT` 를 내 PC의 팀 저장소 `members` 경로로 바꾼다
- 처음 실행하면 bge-m3 모델(약 2GB)을 받는다. `chroma_db/`, `.env`, `.venv/` 는 저장소에 올리지 않는다

## 측정값 (내 PC, 직접 실행)

**저장** (2026-11-08)

| 항목 | 값 |
|---|---|
| 문서 / 청크 | 16개 / 112개 |
| 임베딩 + 저장 시간 | 109.1초 (CPU, 청크 1개당 약 1초) |

**임베딩 유사도 실험** (기준 문장 "Redis TTL이 뭐야?")

| 비교 문장 | 코사인 유사도 |
|---|---|
| 캐시에 저장한 값의 유효기간은 어떻게 정해? (뜻 비슷, 단어 다름) | 0.358 |
| 도커 이미지 크기를 줄이는 방법 (상관없음) | 0.27 |

**답 + 출처** (2026-11-09, 검색 + Claude 답변 시간)

| 질문 | 시간 | 출처 페이지 수 | 결과 |
|---|---|---|---|
| Redis TTL은 몇 초로 정했어? | 3.62초 | 2 | 3600초(mingi). 내 페이지의 `EX 60` 은 예시라고 구분 |
| 도커 이미지와 컨테이너의 차이는? | 2.94초 | 4 | 여러 팀원 페이지를 종합 |
| async는 언제 써야 해? | 2.43초 | 5 | 5명 페이지가 모두 출처 |
| docker compose에서 api 컨테이너는 redis에 어떤 주소로 접속해? | 1.83초 | 2 | `redis://redis:6379` |
| 쿠버네티스 파드가 뭐야? | 1.13초 | 4 | "위키에 없는 내용입니다" (거절) |
| **평균** | **2.39초** | | |

**검색 평가** (2026-11-09, 임시 질문 11개)

| 지표 | 값 |
|---|---|
| Recall@5 | 1.000 |
| MRR@5 | 1.000 |

- 팀 `team/eval/evaluate.py` 가 아직 없어 노트북에 임시로 구현했다. 질문셋도 내가 만든 임시본
- 정답 규칙: 그 질문의 내용을 실제로 설명한 페이지 전부 (같은 주제를 여러 명이 썼으면 모두 정답)
- 질문은 페이지 제목 단어를 피해서 썼다 (예: "API 비밀 키를 코드에 직접 안 쓰고 관리하려면?")

## 알게 된 점

- 검색은 관련이 없어도 항상 가장 가까운 5개를 가져온다. 쿠버네티스 질문에도 출처 4개가 붙었고, 거절은 검색이 아니라 프롬프트 지시("자료에 없으면 없다고") 덕분이었다
- 응답 시간은 대부분 Claude 답변 시간이다. 답이 짧은 거절이 가장 빨랐다(1.13초)
- 1위 11개 중 4개가 내 큰 페이지 2개(`sejin/1-docker-concepts`, `sejin/2-fastapi-redis-async`)였다. 두 페이지가 청크의 46%(52/112)라서, 한 주제만 다룬 짧은 페이지가 1위를 뺏겼다. 위키를 개념별로 나누면 나아질 것으로 보고 세션에서 제안할 예정

## 파일

| 파일 | 내용 |
|---|---|
| `rag.ipynb` | 단계별 실습 (실행 결과 포함) |
| `requirements.txt` | 버전 고정한 패키지 10개 |
| `.env.example` | 환경 변수 이름 견본 (값은 `.env` 에, `.env` 는 올리지 않음) |

## 남은 것

- `app/main.py`: 노트북 코드를 실행 파일로 정리 (4주차 `/ask` 엔드포인트에서 쓸 예정)
- 팀 공용 질문셋과 `evaluate.py` 가 생기면 다시 측정
- 청크 크기 200 / 500 / 1000 비교 (세션)
