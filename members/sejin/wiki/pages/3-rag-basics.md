# RAG 기초: 팀 위키에 질문하기 (3주차)

## 한 줄 정의

RAG는 질문과 관련된 문서를 먼저 검색해 LLM에게 함께 건네고, 그 자료를 근거로 답변하게 하는 시스템이다.

## 왜 필요한가

LLM은 학습한 내용만 안다. 답변의 열쇠가 될 수 있는 문서(사내 문서, 팀 위키, 최근 자료)는 모르기 때문에, 할루시네이션이 발생할 수 있다. RAG는 질문할 때마다 근거 문서를 찾아 같이 알려 주므로, 답이 문서에 기반하고 어떤 문서를 참고했는지 출처도 보여 줄 수 있다.

## 6단계

| 단계 | 하는 일 | 3주차에서 쓴 것 |
|---|---|---|
| 1. 로드 | 문서 읽기 | DirectoryLoader, 팀원 위키 16개 |
| 2. 분할 | 청킹 | RecursiveCharacterTextSplitter 500자 / 50자 오버랩, 청크 112개 |
| 3. 임베딩 | 벡터화 | bge-m3 (글 → 숫자 1024개, 내 PC에서 실행) |
| 4. 저장 | 벡터를 원문, 페이지 이름과 함께 보관 | Chroma |
| 5. 검색 | 질문 벡터와 가까운 청크 k개 찾기 | retriever, k=5 |
| 6. 생성 | 찾은 청크를 프롬프트에 넣고 답하기 | Claude Haiku, LCEL 체인 |

bge-m3와 Chroma는 하는 일이 다르다. bge-m3는 텍스트를 벡터로 바꾸는 함수이고, Chroma는 질문에 가까운 벡터들을 빨리 찾을 수 있게 저장해두는 저장소다. 질문할 때 bge-m3로 질문을 벡터로 바꾼 뒤 Chroma에서 찾는다.

## 최소 예제

LCEL 체인. 질문 하나에서 칸을 늘려 가고, assign은 앞 칸을 버리지 않아서 마지막에 docs가 남아 출처를 보여 줄 수 있다.

```python
rag_chain = (
    {"docs": retriever, "question": RunnablePassthrough()}                  # 검색 + 질문 그대로
    | RunnablePassthrough.assign(context=lambda x: format_docs(x["docs"]))  # 청크를 글로
    | RunnablePassthrough.assign(answer=prompt | llm | StrOutputParser())   # 답
)
out = rag_chain.invoke("Redis TTL은 몇 초로 정했어?")   # {question, docs, context, answer}
```

실행 결과 (app/main.py, 2026-11-09):

```
mingi의 Redis TTL 캐시 자료에 따르면 TTL은 3600초(1시간)로 설정했습니다. ...
같은 위키의 EX 60은 sejin/2-fastapi-redis-async 자료의 문법 예시이므로 이 프로젝트의 설정값이 아닙니다.
출처: mingi/redis-ttl-cache, sejin/2-fastapi-redis-async
```

## 내 측정 결과

| 항목 | 값 |
|---|---|
| 임베딩 + 저장 (청크 112개, CPU) | 109.1초 |
| 유사도: "Redis TTL이 뭐야?" ↔ "캐시 유효기간은 어떻게 정해?" / ↔ "도커 이미지 크기 줄이기" | 0.358 / 0.27 |
| 답 + 출처, 질문 5개 평균 (노트북) | 2.39초 |
| Recall@5 / MRR@5 (임시 질문 11개) | 1.000 / 1.000 |

## 알게 된 점

- TTL을 물었을 때 TTL이라는 단어가 없는 캐시 유효기간 문장의 유사도가 높게 나온 것으로 보아, 의미 기반 검색임을 확인할 수 있었다.
- 상관없는 문장도 유사도가 0.27로 생각보다 크게 나왔다. 즉, 절댓값보다는 순서가 중요하다.
- 검색은 관련 있는 문서가 하나도 없어도 항상 k개를 가져온다. 거절을 위해서는 "자료에 없으면 없다고 답하라"라는 프롬프트 지시가 필요함을 알게 되었다.
- Chroma 점수는 코사인 유사도가 아니라 거리(1 − 코사인 유사도)라서 작을수록 의미가 유사하다.
- 응답 시간은 대부분 LLM 답변 시간이었다.

## 내가 막힌 점

- 노트북 커널이 다른 폴더의 빈 가상환경으로 잡혀 ipykernel 설치 안내가 뜸 → Python: Select Interpreter → Enter interpreter path로 week3\.venv\Scripts\python.exe 지정
- requirements.txt를 저장하지 않아 0바이트 → pip install -r이 아무것도 출력하지 않음
- 평가 질문셋을 다 만들기 전에 돌려서 결과가 섞임 → 질문셋(16개 페이지 모두 포함)부터 완성하고 다시 측정

## 출처

- LangChain 문서: https://docs.langchain.com
- bge-m3 모델 카드: https://huggingface.co/BAAI/bge-m3
- Chroma 문서: https://docs.trychroma.com

