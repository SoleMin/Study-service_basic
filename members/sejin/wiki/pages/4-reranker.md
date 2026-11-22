# reranker

## 한 줄 정의

cross-encoder는 트랜스포머에 질문과 청크를 함께 넣어 score를 계산하고, 이를 사용하여 reranker가 bi-encoder가 낸 상위 청크들에 대해 순서를 다시 매긴다.

## 왜 필요한가

bi-encoder가 내는 상위 청크들은 단순히 cosine-similarity로만 계산되기에, 이를 실제로 질문에 청크로 대답할 수 있는지 질문과 청크를 트랜스포머에 함께 넣어 다시 점수를 매긴다면 순위가 더 정확해질 수 있다.

| | bi-encoder (임베딩) | cross-encoder (리랭커) |
|---|---|---|
| 내가 쓴 모델 | `BAAI/bge-m3` | `BAAI/bge-reranker-v2-m3` |
| 모델 구조 | 트랜스포머 XLM-RoBERTa 24층 → 벡터 1024개 출력 | 같은 XLM-RoBERTa 24층 + 점수 1개를 내는 층 |
| 입력 | 질문 따로, 문서 따로 | 질문 + 문서를 한 입력으로 |
| 점수 | 두 벡터의 코사인 cos(f(q), g(d)) | 모델이 직접 낸 점수 h(q, d) |
| 미리 계산 | 문서 벡터를 저장해 둘 수 있음 → 빠름 | 질문이 올 때마다 쌍마다 계산 → 느림 |
| 역할 | 1차: 후보를 빠르게 넉넉히 | 2차: 상위 후보만 다시 채점 |

## 최소 예제

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
cands = vector_20.invoke(q)                                        # 1차: 벡터로 후보 20개
scores = reranker.predict([(q, d.page_content) for d in cands])    # 2차: (질문, 청크) 쌍마다 점수
top5 = [d for d, _ in sorted(zip(cands, scores), key=lambda x: -x[1])[:5]]
```

실행 결과 (q25 "이미지와 컨테이너를 설계도에 비유하면 각각 무엇에 해당해?", 2026-11-16):

```
벡터 순위 상위 5: ['container-commands_mingi', 'image-vs-container_huiji', 'image-vs-container_doyu', ...]

리랭커 순위 상위 5:
  0.968  image-vs-container_doyu
  0.967  container-commands_mingi
  0.967  image-vs-container_huiji
  0.816  image-container-layer-registry_mingi
  0.732  container-commands_mingi
```

## 내 측정 결과 (팀 `evaluate.py`, 질문 25개)

| 구성 | Recall@5 | MRR@5 | 질문당 검색 시간 |
|---|---|---|---|
| 기준선 (bge-m3 벡터 k=5) | 1.000 | 0.759 | 259.1 ms |
| 리랭커 (후보 20 → 5) | 1.000 | 0.808 | 26,972.7 ms |
| 리랭커 (후보 10 → 5) | 1.000 | 0.830 | 10,259.9 ms |

## 알게 된 점

- bi-encoder도 문장의 의미를 반영해서 벡터화한다. 하지만 reranker로 문맥 파악을 한 번 더 하고 순위를 매기니 MRR이 좋아질 수 있다는 것을 알게 되었다.
- reranker는 정확한 대신 느리다. 미리 계산해 둘 수 없어서 CPU에서 질문당 10~27초가 걸렸다.
- 비교 대상을 20개에서 10개로 줄이니까 MRR이 더 개선되었다. 즉, 비교 대상을 늘린다고 무작정 좋아지는 게 아니다.
- 리랭커 점수는 시그모이드로 0~1 사이로 눌린 값이라 상위 값들이 비슷할 수 있다. 그러므로 절댓값보다 순위가 중요하다.

## 내가 막힌 점

- "bi-encoder가 지금 임베딩이랑 뭐가 다르지?" → bi-encoder가 바로 지금 쓰는 임베딩(bge-m3)이고, 리랭킹은 별개 모델인 cross-encoder가 한다
- 리랭커가 q25에서 정답 목록에 없는 `image-vs-container_doyu` 를 1위로 올려 감점됨 → 페이지를 열어 보니 "읽기 전용 설계도 … 실행한 인스턴스"로 실제로 답하는 문장이었음. 틀린 쪽은 질문셋 정답 목록이었다

## 출처

- bge-reranker-v2-m3 모델 카드: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Sentence-Transformers CrossEncoder 문서: https://sbert.net/docs/cross_encoder/usage/usage.html
- 팀 위키 `embedding-sentence-transformers_mingi` Q4 (bi vs cross 비교)
