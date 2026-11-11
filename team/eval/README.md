# 팀 평가 기준 (3주차 v1)

- 문서: `team/wiki/` (개인 위키를 `scripts/merge_wiki.py`로 모은 것). 평가 전에 항상 병합부터 해요.
- `questions.jsonl`: 질문 25개. 한 줄에 `{"id", "question", "answer_pages"}`.
  - 정답은 **팀 위키 파일 이름**(확장자 제외) `파일이름_이름` (예: `docker-compose_mingi`).
  - 같은 주제를 여러 명이 썼으면 `answer_pages`에 모두 적고, 그중 하나만 찾아도 정답이에요.
  - 질문은 페이지 문장을 그대로 베끼지 않고 바꿔 말했어요 (키워드 검색만 유리해지지 않게).
  - 새 주차 위키가 병합되면 그 주 페이지로 질문을 더해요. 청크 단위 채점은 `"answer_chunk_ids"`로 (선택).
- `evaluate.py`: 리트리버를 넣으면 Recall@k, MRR@k, 질문당 평균 검색 시간을 출력해요. 사용법은 파일 맨 위 설명을 봐요.
- 기준선: 임베딩 `bge-m3`, `chunk_size=500`, `chunk_overlap=50`, 벡터 검색 `k=5`, Chroma 거리 `cosine`

## 빠른 실행 (저장소 루트에서)

```bash
pip install langchain langchain-community langchain-text-splitters langchain-chroma langchain-huggingface sentence-transformers
python scripts/merge_wiki.py                                   # 개인 위키 -> team/wiki
python team/eval/evaluate.py                                   # 기준선
python team/eval/evaluate.py --chunk-size 200 --overlap 20     # 청크 비교
python team/eval/evaluate.py --show-misses                     # 틀린 질문 보기
```

## 왜 페이지 단위로 채점하나

청크 ID(`페이지이름-번호`)는 청크 크기를 바꾸면 번호가 달라져요. 청크 크기 200/500/1000을 같은 질문셋으로 비교하려면 정답을 페이지 단위로 두고, 검색된 청크를 페이지 이름으로 바꿔 채점해야 공정해요. 같은 페이지 청크가 여러 개 나오면 처음 것만 순위에 넣어요.
