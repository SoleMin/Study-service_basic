# 4주차 실습 메모

환경: M3 맥북 16GB, Python 3.11, LangChain core 1.8.0, langchain-classic 1.0.8 (EnsembleRetriever), rank-bm25 0.2.2, kiwipiepy 0.24.1, sentence-transformers 6.3.0, 임베딩 `BAAI/bge-m3`, 리랭커 `BAAI/bge-reranker-v2-m3`, 생성 `claude-opus-5-5`

## 조건
- 팀 `team/eval/evaluate.py`의 `evaluate()`를 그대로 import해서 채점 (페이지 단위, Recall@5, MRR@5)
- 문서: `team/wiki` (merge_wiki 결과). 청크 500/50, k=5, Chroma 코사인. 청크 ID는 팀 스크립트와 같은 `페이지-번호`
- 질문: `team/eval/questions.jsonl` 25개
- 스크립트: `week4/compare.py` (변형 8가지를 한 번에), `week4/hybrid.py` (검색기)

## 발견 1. 평가 질문이 위키 안에 있었다
- `rag-evaluation_mingi` 페이지에 3주차 채점 결과표가 있고, 못 맞힌 질문 원문(q01, q07, q08, q15, q16, q25 …)이 그대로 적혀 있음
- 이 페이지가 검색 대상이라, 질문과 글자가 똑같은 문장이 있는 이 페이지가 1~2위를 차지하고 진짜 정답이 밀려남
- `--exclude rag-evaluation_mingi`로 빼고 다시 잼 (31페이지·청크 174개 → 30페이지·청크 166개)

| MRR@5 | 포함 | 뺐을 때 |
| --- | --- | --- |
| 벡터 (기준선) | 0.759 | 0.780 |
| BM25 띄어쓰기 | 0.688 | 0.783 |
| 리랭커 (벡터 20 → 5) | 0.808 | 0.863 |

- 키워드 검색이 글자가 똑같은 문장에 가장 크게 속음 (+0.095)
- 제안: 평가 결과 페이지는 merge_wiki에서 빼거나, 질문 원문 대신 id만 적기

## 전체 결과 (평가 결과 페이지 제외, 1회 측정)

| 기법 | Recall@5 | MRR@5 | 기준선 대비 | 질문당 검색 |
| --- | --- | --- | --- | --- |
| 벡터 (기준선) | 1.000 | 0.780 | — | 43ms |
| BM25 띄어쓰기 | 0.960 | 0.783 | +0.003 | 1ms 미만 |
| BM25 형태소 (Kiwi) | 0.920 | 0.750 | −0.030 | 1ms 미만 |
| 하이브리드 0.5 : 0.5 | 1.000 | 0.783 | +0.003 | 71ms |
| 하이브리드 0.7 : 0.3 (벡터 : BM25) | 1.000 | 0.787 | +0.007 | 72ms |
| 하이브리드 0.3 : 0.7 | 0.960 | 0.797 | +0.017 | 75ms |
| 리랭커 (벡터 10 → 5) | 1.000 | 0.863 | +0.083 | 3,237ms |
| 리랭커 (벡터 20 → 5) | 1.000 | 0.863 | +0.083 | 5,071ms |
| 하이브리드 + 리랭커 | 1.000 | 0.863 | +0.083 | 5,099ms |

- 하이브리드: 벡터 20개 + BM25(형태소) 20개를 `EnsembleRetriever(weights, c=60, id_key="id")`로 합침
- 질문 25개라 질문 하나가 2위 → 1위로 오르면 MRR +0.02. 하이브리드 차이(+0.003~+0.017)는 그보다 작음 → 개선으로 보기 어려움
- 1위로 찾은 질문: 기준선 16개, 리랭커 19개

### 질문별 정답 순위 (차이가 난 질문만)

| id | 벡터 | BM25 띄어쓰기 | BM25 형태소 | 하이브리드 0.7:0.3 | 리랭커 |
| --- | --- | --- | --- | --- | --- |
| q01 | 4 | 2 | 4 | 3 | 2 |
| q07 | 2 | 1 | 2 | 2 | 1 |
| q08 | 3 | - | 2 | 3 | 1 |
| q09 | 3 | 1 | 1 | 1 | 2 |
| q13 | 4 | 1 | 1 | 3 | 1 |
| q15 | 3 | 4 | 4 | 3 | 4 |
| q16 | 2 | 1 | 2 | 2 | 2 |
| q19 | 1 | 2 | 4 | 2 | 2 |
| q21 | 2 | 1 | 1 | 2 | 1 |
| q23 | 1 | 3 | - | 1 | 1 |
| q25 | 2 | 2 | - | 3 | 3 |

- 벡터와 BM25는 서로 다른 질문을 맞힘 (q09·q13·q21은 BM25, q19·q23·q25는 벡터). RRF로 합치면 한쪽 1위를 그대로 못 가져오고 두 순위 중간으로 끌려감
- 리랭커는 q13 4→1, q08 3→1처럼 크게 올렸지만 q15·q19·q25는 한 칸씩 내려감

## 발견 2. 형태소 BM25가 띄어쓰기보다 낮았던 이유 하나
- 띄어쓰기: `컨테이너는`, `logs로`, `8888번` / Kiwi: `컨테이너`, `logs`, `8888`, `번`
- q16(8888번 서비스 접속)이 형태소 BM25에서만 5위 밖
- 위키의 `-p 8888:8888에서`를 Kiwi가 `8888:8888` 한 덩어리, 품사 `W_SERIAL`로 분류 → 내 품사 필터(NN·VV·VA·SL·SN·XR)가 통째로 버림
- `W_*` 품사는 `\w+`로 쪼개 남기게 고침 → q16 다시 2위. 전체 MRR은 0.750 그대로 (다른 질문 순위가 바뀌어 상쇄)
- 교훈: 분석기 결과에서 어떤 토큰이 버려지는지 직접 찍어 보기

## 리랭커 속도 (20쌍, 긴 청크)

| 장치 | max_length 512 | max_length 256 |
| --- | --- | --- |
| MPS (GPU) fp32 | 12,577ms | 7,428ms |
| MPS fp16 | 7,042ms | — |
| CPU | 27,739ms | 19,601ms |

- 후보 10개면 MPS fp16에서 3,823ms → 후보 하나에 약 0.35초, 개수에 비례
- 후보 20 → 10개로 줄여도 MRR 0.863 그대로 → 서버 기본값은 후보 10개
- 처음 돌렸을 때 하이브리드+리랭커가 질문당 51초: 하이브리드가 후보를 최대 40개 넘겨서. 리랭커 앞에서 후보를 20개로 자르게 고침

## /ask API
- `week4/app/main.py`: 켤 때 청크·색인·리랭커를 한 번만 만들고, `POST /ask`가 답변·출처·검색 시간·전체 시간을 돌려줌
- 검색은 동기 CPU 작업이라 `run_in_threadpool`로 (2주차 async 실험 그대로)
- `RETRIEVER=vector|hybrid|rerank`, 기본 `rerank`
- 호스트 실측: 검색 4,757ms + Claude 3,403ms = 8,160ms. 서버 켠 뒤 첫 요청은 MPS 워밍업으로 검색 18.9초
- 위키에 없는 질문(쿠버네티스 Pod)에는 "위키에 없어요"라고 답함, 빈 질문은 422

## Docker
- `python:3.11-slim` + CPU용 torch(`--index-url https://download.pytorch.org/whl/cpu`) → 이미지 2.77GB (모델 제외)
- **Mac의 Docker는 GPU(MPS)를 못 씀.** 컨테이너 안 CPU로 bge-m3 임베딩: 청크 8개 41초(스레드 8) / 21초(스레드 4)
  - M3는 성능 코어 4 + 효율 코어 4라 스레드 8개면 오히려 느림 → `OMP_NUM_THREADS=4`
- 처음엔 켤 때마다 청크 174개를 임베딩해서 2시간이 넘도록 서버가 안 뜸
- 임베딩 색인을 디스크에 저장하게 바꿈 (`CHROMA_DIR`): 호스트(GPU)에서 1분 26초에 만들고 컨테이너에 마운트 → 시작 91초
- 컨테이너 실측 (`RETRIEVER=vector`): 검색 3,628ms(질문 임베딩을 CPU로) + 생성 → 전체 9,894ms
- 6주차 k8s에서 PVC로 색인과 모델 캐시를 유지해야 하는 이유

```bash
docker run -d -p 8020:8000 --env-file .env -e DOCS_DIR=/wiki -e CHROMA_DIR=/index -e RETRIEVER=vector \
  -v <팀저장소>/team/wiki:/wiki:ro -v ~/.cache/huggingface:/models -v $PWD/chroma_db:/index doyu-week4-ask
```

## 막힌 점
- `.env`의 빈 값(`DOCS_DIR=`)이 Dockerfile의 `ENV DOCS_DIR=/wiki`를 덮어써서 경로를 못 찾음 → `docker run -e`로 다시 지정
- 같은 질문셋에서 희지님 리랭커가 질문당 21초였던 것도 CPU였기 때문으로 보임

## 참고 링크
- https://python.langchain.com/docs/how_to/ensemble_retriever/
- https://huggingface.co/BAAI/bge-reranker-v2-m3
- https://github.com/bab2min/Kiwi
- Cormack, Clarke, Büttcher (2009), Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods
