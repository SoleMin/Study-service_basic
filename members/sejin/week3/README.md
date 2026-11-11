# 3주차: 팀 위키 RAG (LangChain + Chroma + bge-m3 + Claude)

팀원 위키(`members/*/wiki/pages/*.md`)에서 질문과 가까운 청크 5개를 찾고, Claude가 그 내용만 근거로 답한 뒤 출처 페이지를 함께 돌려준다. 위키에 없는 질문에는 "위키에 없는 내용입니다"라고 답한다.

노트북(`rag.ipynb`)으로 단계별로 확인하고, 같은 코드를 `app/main.py`로 정리해 명령줄에서 질문할 수 있게 했다.

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

## `app/main.py` 구조

| 함수 | 하는 일 | 몇 번 |
|---|---|---|
| `load_chunks()` | 위키 로드 + 분할 + 청크 ID | DB가 비었을 때만 |
| `get_vectordb()` | `chroma_db/` 를 열기만 함. 비어 있으면 처음 한 번 임베딩해서 저장 | 한 번 |
| `build_rag_chain()` | bge-m3 로드, 검색기, Claude, LCEL 체인 조립 (느림) | 프로그램 시작 때 한 번 |
| `ask(rag_chain, 질문)` | 검색 + 답 + 출처. "위키에 없는 내용입니다"면 출처를 비움 | 질문마다 |

준비(`build_rag_chain`)와 질문 처리(`ask`)를 나눠서, 4주차 FastAPI에서는 서버를 켤 때(`lifespan`) 한 번만 준비하고 `/ask` 요청마다 `ask()` 만 부를 수 있게 했다.

## 실행

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # ANTHROPIC_API_KEY, WIKI_ROOT 입력
```

명령줄에서 질문 (week3 폴더에서)

```powershell
python app/main.py "Redis TTL은 몇 초로 정했어?"
```

- `.env` 의 `WIKI_ROOT` 에 팀 저장소 `members` 폴더 경로를 넣는다. 노트북에서 만든 `chroma_db/` 가 있으면 다시 임베딩하지 않는다
- 노트북은 VS Code에서 `rag.ipynb` 를 열고 커널을 `week3\.venv` 로 선택 (목록에 없으면 `Python: Select Interpreter` → `Enter interpreter path` 로 `.venv\Scripts\python.exe` 지정). 1번 셀의 `WIKI_ROOT` 를 내 PC 경로로 바꾼다
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

**답 + 출처** (2026-11-09, 노트북, 검색 + Claude 답변 시간)

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

**`app/main.py` 명령줄 실행** (2026-11-09, 명령마다 프로그램을 새로 켬)

| 질문 | 시간 (`ask()` 만) | 결과 |
|---|---|---|
| Redis TTL은 몇 초로 정했어? | 5.08초 | 3600초, 출처 2개 |
| 쿠버네티스 파드가 뭐야? | 3.06초 | "위키에 없는 내용입니다", 출처 없음 |

노트북(3.62초, 1.13초)보다 느렸다. 프로그램을 켠 직후의 첫 호출이라 그런 것으로 보이지만, 한 번씩만 재서 확인은 못 했다.

## 알게 된 점

- 검색은 관련이 없어도 항상 가장 가까운 5개를 가져온다. 쿠버네티스 질문에도 청크가 검색됐고, 거절은 Claude가 자료를 읽고 프롬프트 지시("자료에 없으면 없다고")를 따른 결과였다. `main.py` 에서는 거절 문구가 나오면 출처를 비우도록 했다
- 응답 시간은 대부분 Claude 답변 시간이다. 답이 짧은 거절이 가장 빨랐다(노트북 1.13초)

## 파일

| 파일 | 내용 |
|---|---|
| `rag.ipynb` | 단계별 실습 (실행 결과 포함) |
| `app/main.py` | 노트북 코드를 정리한 실행 파일 (질문 → 답 + 출처) |
| `requirements.txt` | 버전 고정한 패키지 10개 |
| `.env.example` | 환경 변수 이름 견본 (값은 `.env` 에, `.env` 는 올리지 않음) |

## 남은 것

- 팀 공용 질문셋과 `evaluate.py` 가 생기면 다시 측정
- 청크 크기 200 / 500 / 1000 비교 (세션)
- `langchain-community` 가 지원 종료 예정이라는 경고가 뜸 (`DirectoryLoader`). 지금은 동작함
