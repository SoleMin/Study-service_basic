# 하이브리드 검색과 리랭커

## 한 줄 정의
**하이브리드 검색**은 키워드 검색(BM25)과 벡터 검색의 결과를 순위로 합치는 것이고, **리랭커**는 넉넉히 뽑은 후보를 질문과 함께 다시 읽어 줄을 새로 세우는 모델이다.

## 왜 필요한가
- 벡터 검색은 뜻이 비슷하면 찾지만 명령어·포트 번호 같은 정확한 단어에 둔하다. BM25는 그 반대다.
- 둘의 점수는 단위가 달라(코사인 0.639 vs BM25 13.3) 더할 수 없어서, **순위**로 합친다 (RRF: `Σ 가중치 / (60 + 순위)`).
- 벡터 검색(바이인코더)은 질문과 청크를 따로 읽어 빠르지만 거칠다. 리랭커(크로스인코더)는 둘을 같이 읽어 정확하지만 후보마다 다시 계산해야 해서 느리다. 그래서 **벡터로 넓게, 리랭커로 좁게** 쓴다.

| | 벡터 (바이인코더) | BM25 | 리랭커 (크로스인코더) |
| --- | --- | --- | --- |
| 보는 것 | 뜻 | 겹치는 단어 (TF, IDF, 길이 보정) | 질문과 청크를 함께 |
| 미리 계산 | 청크 벡터 | 단어 색인 | 불가 |
| 우리 팀 MRR@5 | 0.780 | 0.783 (띄어쓰기) | 0.863 |
| 질문당 시간 | 43ms | 1ms 미만 | 3.2초 (후보 10개, M3 GPU) |

## 최소 예제
```python
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from sentence_transformers import CrossEncoder

bm25 = BM25Retriever.from_documents(chunks, preprocess_func=kiwi_tokens)   # 한국어는 형태소로 자르기
bm25.k = 20
vector = store.as_retriever(search_kwargs={"k": 20})
hybrid = EnsembleRetriever(retrievers=[vector, bm25], weights=[0.7, 0.3], c=60, id_key="id")

reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
cands = vector.invoke(q)[:10]
scores = reranker.predict([(q, d.page_content) for d in cands])
top5 = [d for _, d in sorted(zip(scores, cands), key=lambda x: -x[0])][:5]
```

우리 팀 질문 25개 결과: 하이브리드 +0.003~+0.017 (질문 하나 분량인 0.02보다 작음), 리랭커 +0.083 (1위 16개 → 19개).

## 내가 막힌 점
- 평가 질문 원문이 적힌 위키 페이지(`rag-evaluation_mingi`)가 검색 대상에 섞여 모든 점수를 끌어내렸다. 평가 데이터는 검색 대상과 분리해야 한다.
- Kiwi가 `8888:8888`을 `W_SERIAL` 품사로 묶었는데, 품사 필터가 이를 버려서 포트 번호 키워드가 사라졌다.
- 하이브리드 뒤에 리랭커를 붙였더니 후보가 최대 40개라 질문당 51초가 걸렸다. 리랭커 앞에서 후보 수를 묶어야 한다.

## 출처
- Cormack, Clarke, Büttcher (2009), Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods, SIGIR
- LangChain 문서, EnsembleRetriever: https://python.langchain.com/docs/how_to/ensemble_retriever/
- 모델 카드: https://huggingface.co/BAAI/bge-reranker-v2-m3
- 직접 실습: [week4-notes.md](../raw/week4-notes.md)
