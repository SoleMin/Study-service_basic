# Day 2: 2주차 FastAPI + Redis를 k8s로

- 날짜: 2026-11-22
- 환경: kind 클러스터 `study` (노드 1개, k8s v1.37.0), kubectl v1.32.2
- 파일: `k8s/redis.yaml` (Deployment 1 + Service), `k8s/api.yaml` (Deployment 2 + Service 80→8000, readinessProbe `/health`)
- 이미지: `redis:7`, `week2-api:0.1` (`docker build` → `kind load docker-image`)
- API 키: `kubectl create secret generic week2-secret --from-env-file=..\week2\.env` (YAML 파일 없음) → `envFrom.secretRef`

## 결과

| 항목 | 결과 |
|---|---|
| redis Pod Running까지 | 13초 (이미지 다운로드 포함) |
| `redis-cli ping` | PONG |
| `REDIS_URL` (Secret에도 있고 `env:` 에도 있음) | `redis://redis:6379/0` → `env:` 가 우선 |
| `/health` | `ok` |

`/ask` (질문 "Service는 왜 필요해?", 서버가 잰 `elapsed_ms`)

| 회차 | cached | elapsed_ms | 토큰 (입력/출력) | cost_krw |
|---|---|---|---|---|
| 1 | False | 1734.6 | 75 / 221 | 0.1652 |
| 2 | True | 0.4 | 0 / 0 | 0.0 |

- 2주차 compose에서 잰 값: 캐시 미스 1919.8ms, 캐시 hit 0.6ms (질문이 달라 직접 비교는 아님)

## 만난 에러

| 순서 | 증상 | 원인 | 해결 |
|---|---|---|---|
| 1 | `ErrImagePull` ↔ `ImagePullBackOff`, Events: `pull access denied ... docker.io/library/week2-api:latest` | 노드 안 containerd는 내 PC Docker 이미지를 못 봄 → Docker Hub에서 찾음 | 태그 `0.1` 로 빌드 + `kind load docker-image` |
| 2 | 이미지를 넣었는데도 `ErrImagePull` (`week2-api:0.1`) | 처음 `:latest` 로 만들 때 API 서버가 `imagePullPolicy: Always` 를 채워 넣음. 이미지만 바꾸고 apply해도 그 값이 남음 | YAML에 `imagePullPolicy: IfNotPresent` 를 직접 적음 |
| 3 | API 키 없이도 Pod가 Ready | `AsyncAnthropic()` 은 만들 때 키를 검사하지 않음. readinessProbe는 `/health` 만 봄 | Secret 추가. probe가 무엇을 확인하는지가 중요하다는 관찰 |
| 4 | PowerShell 5.1 `Invoke-RestMethod` 응답의 한글이 깨짐 | 응답 헤더에 charset이 없어 ISO-8859-1로 읽음 (표시 문제) | `Invoke-WebRequest` 바이트를 UTF-8로 직접 디코딩 |

## Rolling update 기록 (Secret 추가 때, Deployment Events)

| 시각 (UTC) | 내용 |
|---|---|
| 04:06:13 | 새 ReplicaSet `api-55d956cfb5` 0 → 1 |
| 04:06:24 | 옛 ReplicaSet `api-65678487f9` 2 → 1 |
| 04:06:35 | 옛 ReplicaSet 1 → 0 |

- 새 Pod가 Ready가 된 뒤에 옛 Pod를 줄임 (replicas 2: maxSurge 1, maxUnavailable 0)
- ReplicaSet 4개 = 설계도 4번 (`:latest` → `:0.1` Always → IfNotPresent → Secret)
- `kubectl get pods -w` 는 몇 초 안의 순서가 섞여 보일 수 있음. 정확한 순서는 Events로 확인

## 실험 D: 파일 줄 수 (빈 줄·주석만 있는 줄 제외)

| 방식 | 파일 | 줄 수 |
|---|---|---|
| compose | `week2/docker-compose.yml` | 20 |
| k8s | `k8s/redis.yaml` 30 + `k8s/api.yaml` 41 | 71 (+ Secret 만드는 명령 1줄) |

- 약 3.5배. 서비스 하나가 Deployment + Service 두 객체로 나뉘고, 라벨/셀렉터가 세 번씩 들어가기 때문
- 기능이 똑같지는 않다. k8s 쪽에만 있는 것: replicas 2, readinessProbe, Secret 분리. compose 쪽에만 있는 것: redis healthcheck, `depends_on` (k8s redis에는 probe를 넣지 않음)

## 실험 B: rolling update 중 요청 실패 수

- 방법: 클러스터 안에 임시 Pod (`curlimages/curl:8.11.1`)를 띄워 `http://api/health` 에 0.1초 간격으로 요청 (`--max-time 2`). 도는 동안 `kubectl rollout restart deployment api`
- port-forward는 Pod 하나에 붙어서 교체 중에 끊기므로 쓰지 않음
- 옛 Pod 종료 시각(Events `Killing`)이 요청 구간(load Pod `Started` ~ `end=`) 안에 있는지 확인

| 조건 | 요청 수 | `000` (실패) | `200` | 옛 Pod 종료가 구간 안? |
|---|---|---|---|---|
| 1차 시도 | 400 | 0 | 400 | 아니오 (요청 04:17:34 시작, 교체 04:18:16 시작, 옛 Pod 종료 04:18:28·04:18:39 → 400번이 끝난 뒤일 가능성이 큼). 결과로 쓰지 않음 |
| preStop 없음 | 800 | 7 | 793 | 예 (구간 04:20:05~04:21:35, 종료 04:21:19·04:21:30) |
| preStop `sleep 5` | 800 | 0 | 800 | 예 (구간 04:27:00~04:28:25, 종료 04:27:18·04:27:29) |

- 각 조건 1회 측정
- 원인: Pod를 지우면 (1) kubelet의 SIGTERM과 (2) Endpoints에서 빼고 kube-proxy 규칙을 고치는 일이 동시에 따로 진행됨. (1)이 먼저 끝나는 틈에 온 요청이 닫힌 uvicorn으로 감
- 해결: `lifecycle.preStop.exec.command: ["sleep", "5"]` (기본 `terminationGracePeriodSeconds` 30 안에 포함)
- `kubectl run ... -i` 에서 `Unknown stream id 1, discarding message` 경고와 함께 첫 출력(`start=`)이 사라짐 → 시작 시각은 Events로 확인

## 실험 C: Service 분배

- 방법: 클러스터 안 임시 Pod에서 `http://api/topics` 100번 (curl을 매번 새로 실행 → 요청마다 새 연결). api Pod별 로그의 `GET /topics` 줄 수를 셈
- `/topics` 를 쓴 이유: LLM 호출 없음, readinessProbe(`/health`)와 섞이지 않음

| Pod | 받은 요청 |
|---|---|
| api-77d9494498-9f85t | 53 |
| api-77d9494498-w8w2s | 47 |

- 1회 측정. 무작위로 반반 고른다면 B(100, 0.5): 평균 50, 표준편차 5 → 53:47은 1 표준편차 안
- 연결을 재사용하는 클라이언트에서의 분배는 확인하지 않음

## 측정 예정

- 실험 B 반복 (각 조건 2회 이상)
