# 임도유 (doyu)

> 전체 작업물은 개인 저장소 [DoyuIm/ai-engineering-study](https://github.com/DoyuIm/ai-engineering-study)에 있어요.

## 주차별 결과물

| 주차 | 폴더 | 내용 | 상태 |
| --- | --- | --- | --- |
| 1 | `week1/` | Python 앱 이미지 빌드·실행, 빌드 캐시 순서 실험, `-p`·`-v` 실습, slim vs full 크기 비교 | 완료 |
| 2 | `week2/` | FastAPI `/chat`(가짜 LLM) + Redis TTL 캐시, compose, async 실험 | 완료 |
| 3 | `week3/` | 팀원 위키 16페이지 RAG: bge-m3 + Chroma + Claude, 출처 반환, 질문 20개로 Recall@5·MRR@5 채점 | 완료 |
| 4 | `week4/` | BM25·하이브리드(RRF)·리랭커 비교, FastAPI `/ask` + Docker, 평가 데이터 누수 발견 (발표) | 완료 |
| 5 | `week5/` | kind 3노드 클러스터, nginx·2주차 API+Redis 배포, 자가 복구·스케일, `ImagePullBackOff`·`CrashLoopBackOff` 재현, 무중단 롤링 업데이트 | 완료 |
| 6 | — | 4주차 `/ask`를 ConfigMap·Secret·PVC로 k8s 배포 | 예정 |

## 주차별 핵심 숫자

| 주차 | 실험 | 결과 |
| --- | --- | --- |
| 1 | 코드만 고치고 재빌드 | 의존성 먼저 COPY 0.3초 vs 코드 먼저 2.6초 |
| 2 | 같은 질문 두 번 | 2,014ms → 캐시 0.6ms |
| 3 | chunk_size 200 / 500 | MRR@5 0.938 / 0.925 |
| 4 | 벡터 → 리랭커(후보 10개) | MRR@5 0.780 → 0.863, 질문당 43ms → 3.2초 |
| 5 | 롤링 업데이트 중 요청 실패 | 설정 없음 1/60 → readiness + preStop 0/80 |

## 위키 페이지

| 페이지 | 주차 | 팀 위키 반영 |
| --- | --- | --- |
| `wiki/pages/image-vs-container.md` | 1 | 반영됨 |
| `wiki/pages/async-fastapi.md` | 2 | 반영됨 |
| `wiki/pages/rag-pipeline.md` | 3 | 반영됨 |
| `wiki/pages/hybrid-search-reranker.md` | 4 | 반영됨 |
| `wiki/pages/k8s-pod-deployment-service.md` | 5 | 반영됨 |
