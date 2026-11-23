# 5주차 실습 메모

환경: M3 맥북, Docker Desktop, kind v0.33.0 (Kubernetes v1.37.0), kubectl v1.37.1

## 클러스터
- `kind create cluster --config week5/kind-config.yaml` → 컨트롤 플레인 1 + 워커 2, 38초
- 노드가 Ready 되기까지 추가로 약 20초 (CNI인 kindnet이 뜰 때까지 NotReady)

## nginx Deployment + Service (`k8s/nginx.yaml`)
- `kubectl apply -f k8s/00-namespace.yaml -f k8s/nginx.yaml` → Pod 2개가 `study-worker`, `study-worker2`에 하나씩
- 생성 순서: Deployment → ReplicaSet(`nginx-59b667b7bf`) → Pod 2개, Service는 EndpointSlice에 두 Pod IP를 묶음
- `kubectl port-forward svc/nginx 8080:80` → `curl localhost:8080` 200 "Welcome to nginx!" / port-forward를 끄면 연결 실패
- 클러스터 안에서는 Service 이름으로 바로 접속: `wget http://nginx`, `http://nginx.study.svc.cluster.local` 모두 성공

## 자가 복구와 스케일
| 실험 | 결과 |
| --- | --- |
| Pod 하나 삭제 | 0.9초 만에 새 Pod가 떠서 다시 2개 Ready (ReplicaSet 이벤트 `SuccessfulCreate`) |
| 레플리카 2 → 5 | 0.6초 만에 5개 Ready, 워커 3개 / 2개로 나뉨, EndpointSlice에 IP 5개 |
| 레플리카 5 → 1 | 4개가 Terminating 후 1개만 남음 |

- 내가 Pod를 지운 게 아니라 "2개 유지"라는 원하는 상태를 Deployment에 적어 두고, 컨트롤러가 현재 상태를 계속 맞춘다

## 2주차 FastAPI + Redis를 k8s로 (`k8s/redis.yaml`, `k8s/api.yaml`)
- `docker build -t doyu-week2-api:1.0 week2` (262MB) → `kind load docker-image doyu-week2-api:1.0 --name study` (3.4초, 노드 3개에 복사)
- `imagePullPolicy: IfNotPresent`: kind에 넣은 로컬 이미지를 쓰게. `Always`면 Docker Hub에서 찾다가 실패
- compose의 `REDIS_HOST: redis`가 그대로 동작: Service 이름 `redis`가 클러스터 DNS 이름
- api Pod 2개가 Redis 하나를 공유

| 호출 | cached | elapsed_ms |
| --- | --- | --- |
| Pod A 1번째 | false | 2,014.6 |
| Pod A 2번째 | true | 0.9 |
| Pod B 첫 호출 (같은 질문) | **true** | 7.6 |

- `redis-cli TTL` → 3600

## 일부러 고장 내기 (`k8s/broken/`)
| 상태 | 원인 | 확인 명령 | 보인 메시지 |
| --- | --- | --- | --- |
| ErrImagePull → ImagePullBackOff | kind에 넣지 않은 태그 `doyu-week2-api:2.0` | `kubectl describe pod` 이벤트 | `Failed to pull image "doyu-week2-api:2.0"` |
| Error → CrashLoopBackOff | `CACHE_TTL: "1h"` | `kubectl logs <pod> --previous` | `ValueError: invalid literal for int() with base 10: '1h'` |

- ImagePullBackOff는 `logs`로는 아무것도 안 나온다 (컨테이너가 뜬 적이 없어서). `describe`의 Events를 봐야 한다
- CrashLoopBackOff는 재시작 간격이 점점 길어진다 (10초, 20초, 40초 …). 직전에 죽은 컨테이너 로그는 `--previous`
- 처음엔 `logs`가 `unable to retrieve container logs`로 실패 → 재시작 직후라 잠깐 기다렸다 다시 보니 나옴

## 롤링 업데이트와 무중단 배포
`kubectl set env deploy/api FAKE_LLM_DELAY=...`로 업데이트하는 동안, 클러스터 안 busybox Pod에서 0.25초마다 `http://api:8000/health` 호출

| 설정 | 업데이트 중 요청 결과 (3회) |
| --- | --- |
| 아무것도 없음 | 60개 중 1개 실패 |
| readinessProbe(`/health`)만 | 60개 중 1개 실패 × 3 |
| readinessProbe + preStop `sleep 5` | **80개 중 0개 실패 × 3** |

- readiness probe: 새 Pod가 `/health`에 응답할 때까지 Service가 요청을 안 보낸다 (새 Pod 쪽 문제 해결)
- 그래도 남은 실패는 꺼지는 옛 Pod 쪽: Pod는 종료 신호를 받자마자 꺼지는데, Service 목록(EndpointSlice)에서 빠지는 건 조금 늦다. 그 틈에 들어온 요청이 실패
- preStop에서 5초 버티면 그 사이 목록에서 빠져서 실패 0
- `kubectl rollout history` (change-cause 주석), `kubectl rollout undo`로 FAKE_LLM_DELAY 1.0 → 2.0 되돌림. 옛 ReplicaSet이 0개로 남아 있다가 다시 2개가 된다
- `rollout undo` 뒤에는 `last-applied-configuration`과 실제가 달라진다는 경고 → YAML을 고쳐 `kubectl apply`로 되돌리는 게 원칙

## compose와 비교
| | docker compose | Kubernetes |
| --- | --- | --- |
| 정의 | `docker-compose.yml` 한 파일 | Deployment, Service, Namespace 등 리소스별 YAML |
| 서비스 찾기 | 서비스 이름 (`redis`) | Service 이름 (`redis`, `redis.study.svc.cluster.local`) |
| 죽으면 | `restart:` 정책으로 같은 컨테이너 재시작 | 컨트롤러가 새 Pod를 만들어 개수를 맞춤 |
| 여러 개 | `--scale`, 한 컴퓨터 안 | `replicas`, 여러 노드에 흩어짐 |
| 업데이트 | 내렸다 올림 | 롤링 업데이트, 되돌리기 |
| 외부 접속 | `ports:` | Service 타입(NodePort/LoadBalancer) 또는 port-forward |

## 하지 않은 것
- 선택 과제(MCP 맛보기, 에이전트 트랙)
- 4주차 RAG `/ask`는 6주차에 ConfigMap·Secret·PVC와 같이 올림 (Mac kind 노드도 GPU가 없어서 색인을 PVC로 유지해야 함)

## 참고 링크
- https://kind.sigs.k8s.io/docs/user/quick-start/
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- https://kubernetes.io/docs/concepts/services-networking/service/
- https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/
- https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/
