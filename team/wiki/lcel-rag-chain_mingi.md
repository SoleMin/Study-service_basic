<!-- merge_wiki.py 자동 생성: 원본 members/mingi/wiki/pages/lcel-rag-chain.md . 수정은 원본에서 하세요 -->

# LCEL로 검색 + 생성 체인 만들기, 출처 반환 (3주차)

## 내 측정 결과

| 질문 | 답 요약 | 출처 | 근거가 맞았나 |
| --- | --- | --- | --- |
| docker compose에서 api 컨테이너가 Redis에 접속할 때 주소를 어떻게 써야 해? | `localhost`가 아닌 서비스 이름 `redis://redis:6379` | docker-compose_mingi, 2-fastapi-redis-async_sejin | 맞음 |
| 쿠버네티스 파드란 무엇인가? (위키에 없음) | 위키에 없는 내용이에요 | volume-port_mingi, vm-conda-docker_mingi, 2-fastapi-redis-async_sejin, docker-compose_mingi | 답은 거절했지만 출처는 붙어 나옴 |

## 내 정리

### Q. LCEL이란 무엇인가? `|`로 이어 붙이면 무슨 일이 일어나나?

랭체인에서 파이프라인 구축을 간편하게 하기 위해 사용하는 표현식 언어

대표적으로 파이프 연산자를 사용하면 `프롬프트 | 모델 | 출력 파서` 순으로직관적인 파이프라인을 구축할 수 있다

### Q. 내 체인에서 RunnableParallel과 .assign은 각각 무슨 역할을 하나?

- `RunnableParallel`은 랭체인 과정 중 여러개의 독립적인 Runnable을 구성해 병렬로 실행
- `assign`은 기존 입력 데이터를 유지하면서 새로운 키-벨류 쌍을 추가확장하기 위해 사용한다.

### Q. 출처(페이지 이름)는 어떻게 돌려줬나? 왜 답과 같이 돌려줘야 하나?

`출처: docker-compose_mingi, 2-fastapi-redis-async_sejin` 와 같이 돌려주며 이와 같이 하는 이유는 답변이 환각이 아닌 실제 문서에서 왔다고 표시하는 신뢰성 확보와 사용자의 검증을 위함이다.

### Q. 위키에 없는 질문에는 어떻게 답했나? 프롬프트의 어떤 부분이 영향을 줬나?

정보가 부족해 답을 할 수 없다고 없다고 답변 프롬포트의 `문서에 없으면 "위키에 없는 내용이에요"라고 답해.` 부분이 제어했음

## 내가 막힌 점

(`../raw/week3-troubleshooting.md`에서 이 주제와 관련된 것을 골라 내 말로)

## Claude 피드백 (2026-11-10)

- **Q1 (LCEL)**: 정확해요. 덧붙이면 `|`로 이은 각 단계는 모두 Runnable이고, **앞 단계의 출력이 다음 단계의 입력**이 돼요. 그래서 체인 전체도 `invoke`, `batch`, `stream`을 똑같이 쓸 수 있어요.
- **Q2 (RunnableParallel, assign)**: 둘 다 정확해요. 내 코드에 대입하면 더 좋아요. `RunnableParallel`은 같은 질문을 retriever와 `RunnablePassthrough`에 동시에 넣어 `{context, question}`을 만들고, 첫 `.assign`이 `answer`를, 두 번째 `.assign`이 `sources`를 덧붙여요.
- **Q3 (출처 반환)**: 이유(신뢰성, 사용자 검증)가 정확해요. 방법을 한 줄 더하면 완성이에요. 검색된 청크의 `metadata["page"]`를 **중복 없이 모아서** 돌려줬어요.
- **Q4 (위키에 없는 질문)**: 정확해요. 측정 결과에서 하나 더 볼 점이 있어요. 답은 "위키에 없는 내용이에요"라고 거절했는데 **출처는 4개나 붙어 나왔어요**. 검색은 무조건 5개를 돌려주기 때문이에요. 거절할 때는 출처를 비우거나, 검색 거리가 일정 값 이상이면 아예 문서를 넘기지 않는 방법을 생각해 볼 수 있어요.

## 출처

- [LangChain 문서: LCEL](https://python.langchain.com/docs/concepts/lcel/)
- 실습: `members/mingi/week3/rag.ipynb` 6번 섹션
