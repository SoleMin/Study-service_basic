# RAG 파이프라인

## 한 줄 정의
RAG는 질문과 비슷한 문서 조각을 먼저 **찾아서** 프롬프트에 넣고, LLM이 그 조각을 근거로 **답하게** 하는 방식이다.

## 왜 필요한가
- LLM은 우리 팀 위키 내용을 모른다. 찾아서 넣어 주면 학습 없이도 우리 문서로 답할 수 있다.
- 근거로 쓴 조각을 알 수 있어서 출처(페이지 이름)를 같이 보여줄 수 있다.
- 검색이 틀리면 답도 틀린다. 그래서 생성보다 먼저 검색을 점수(Recall, MRR)로 잰다.

| 단계 | 하는 일 | 이번 실습 |
| --- | --- | --- |
| 로드 | 문서 읽기 | `DirectoryLoader`로 위키 `.md` 16개 |
| 분할 | 문서를 조각(청크)으로 자르기 | `RecursiveCharacterTextSplitter(500, 50)`, 청크마다 `metadata["id"]` |
| 임베딩 | 조각을 숫자 벡터로 바꾸기 | `bge-m3` (정규화해서 내적 = 유사도) |
| 저장 | 벡터를 DB에 넣기 | Chroma |
| 검색 | 질문 벡터와 가까운 조각 k개 찾기 | `as_retriever(k=5)` |
| 생성 | 찾은 조각 + 질문으로 답 만들기 | LCEL 체인 → Claude |

## 최소 예제
```python
chunks = split_docs(load_wiki(), 500, 50)
retriever = build_store(chunks).as_retriever(search_kwargs={"k": 5})
chain = (
    {"question": RunnablePassthrough(), "docs": retriever}
    | RunnablePassthrough.assign(context=lambda x: format_docs(x["docs"]))
    | RunnablePassthrough.assign(answer=RunnableLambda(ask_claude))
)
```

청크 크기별 채점 (질문 20개, k=5):

| chunk_size | Recall@5 | MRR@5 |
| --- | --- | --- |
| 200 | 1.00 | 0.938 |
| 500 | 0.95 | 0.925 |
| 1000 | 0.95 | 0.925 |

## 내가 막힌 점
- 페이지 이름이 겹치는 문서가 있어서(`async-fastapi`가 두 명) 출처가 헷갈렸다. `멤버/페이지`로 이름을 붙여 해결했다.
- 질문에 핵심 단어("compose")가 없으면 비슷한 단어("컨테이너")가 많은 긴 페이지가 먼저 나왔다. 청크를 작게 하면 찾았다.

## 출처
- LangChain 문서, Text splitters: https://python.langchain.com/docs/how_to/recursive_text_splitter/
- bge-m3 모델 카드: https://huggingface.co/BAAI/bge-m3
- 직접 실습: [week3-notes.md](../raw/week3-notes.md)
