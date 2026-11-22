# 4주차: RAG 고도화 + API화 (mingi)

3주차 팀 위키 RAG에 리랭커(크로스인코더)를 붙여 기준선과 비교하고, 같은 코드를 FastAPI `/ask`로 서빙해 Docker로 띄워요.

## 파일

| 파일 | 내용 |
| --- | --- |
| `app/rag_core.py` | 로드, 분할, 임베딩, Chroma, 검색기 3종(기준선, 리랭커, 하이브리드), 생성, 멀티턴 질문 다시 쓰기 |
| `app/main.py` | FastAPI `/ask`, `/health` |
| `rag_v2.ipynb` | 기준선 재측정, 리랭커와 하이브리드 채점, 위키에 없는 질문 기준값, 멀티턴, 대회 표 |
| `4주차_질문셋_초안.jsonl` | 3주차 페이지용 질문 13개 초안 (팀 확인 후 `team/eval/questions.jsonl`에 추가) |
| `Dockerfile`, `docker-compose.yml` | CPU torch 이미지, 위키 읽기 전용 마운트, 모델 캐시 볼륨 |

## 실행

```bash
# 공통: 저장소 루트에서 팀 위키 최신화
python scripts/merge_wiki.py

# 이 폴더에서
cp .env.example .env          # GEMINI_API_KEY 채우기
pip install -r requirements.txt

# 1) 노트북: rag_v2.ipynb 위에서부터 실행
# 2) API (로컬)
uvicorn app.main:app --reload # http://localhost:8000/docs
# 3) API (Docker)
docker compose up --build
```

`/ask` 예시

```json
POST /ask
{"question": "그럼 compose에서는 어떻게 써?",
 "history": [{"role": "user", "content": "컨테이너가 꺼져도 파일을 남기려면?"},
             {"role": "assistant", "content": "-v 옵션으로 볼륨을 연결해요."}]}
```

응답: `question`, `search_query`(다시 쓴 질문), `answer`, `in_wiki`, `top_score`, `sources[{page, chunk_id, score}]`, `elapsed_ms`

## 대회 표 (질문 38개, 페이지 31개, k=5)

`rag_v2.ipynb` 9번 섹션 결과를 붙여요.

| 구성 | Recall@5 | MRR@5 | 질문당 ms | 채택? |
| --- | --- | --- | --- | --- |
| 기준선 (bge-m3, 500/50, k=5) | | | | 기준 |
| + 리랭커 (후보 20 -> 5) | | | | |
| + 하이브리드 (BM25 + 벡터, RRF) | | | | |

## 설계 메모

- 리랭커는 LangChain `CrossEncoderReranker` 대신 직접 만든 `RerankRetriever`예요. LangChain 것은 점수를 버려서 "위키에 없는 질문" 기준값을 정할 수 없어요.
- `/ask`는 `def`예요. 모델 추론과 LLM 호출이 블로킹이라 `async def`에서 부르면 이벤트 루프가 멈춰요.
- 기준값 `MIN_SCORE`는 리랭커 1위 점수로 판단해요. 기본 0.1은 임시값이고, 노트북 7번 섹션에서 정한 값을 `.env`에 적어요.
