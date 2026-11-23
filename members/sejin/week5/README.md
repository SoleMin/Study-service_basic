# 5주차: Kubernetes 기초

1. kind 클러스터에 nginx Deployment + Service를 배포하고, Pod 삭제·개수 변경으로 정해진 상태 유지하는 것 확인. compose와 비교
2. 2주차 FastAPI + Redis를 k8s로 배포


## 1. 개념

| 객체 | 하는 일 |
|---|---|
| Pod | 컨테이너를 실행하는 가장 작은 단위. 일회용 (죽으면 새 이름으로 새로 생김) |
| Deployment | ReplicaSet을 통해 Pod 개수 및 버전 유지 |
| Service | ClusterIP 하나로 받아서 라벨이 맞는 Ready Pod들에 분배 |
| Namespace | 작업별로 나누는 폴더 |



## 2. 실험 결과

자세한 값과 측정 방법: `results/experiment_A.md`, `results/day2_api_on_k8s.md`

| 실험 | 결과 |
|---|---|
| A. 자동 복구 | k8s: Pod 삭제 후 0.90~0.91초에 새 Pod Ready (3회). compose: 컨테이너 삭제 시 채우지 않음, 안의 프로그램 종료 시 0.60~0.69초에 같은 컨테이너 재시작 (3회) |
| compose 포트 | `ports: "8090:80"` + `--scale web=2` → `port is already allocated` |
| scale | 2 → 3 직후 `READY 2/3`, Endpoints IP 2개 (Ready인 Pod만 들어감). `kubectl diff` 로 파일(2)과 클러스터(3)의 어긋남 확인 |
| `/ask` on k8s | 캐시 미스 1734.6ms / 0.1652원 → 캐시 hit 0.4ms / 0원. api Pod 2개가 설계상 Redis 하나를 같이 씀 |
| B. 교체 중 요청 실패 (800번) | readinessProbe만: 7번 실패. + preStop `sleep 5`: 0번 (각 1회, 도유 님 Mac 실험과 같은 결론) |
| C. Service 분배 (100번) | 53 : 47 (1회) |
| D. 파일 줄 수 | compose 20줄 vs k8s 71줄 |


## 실행

Docker Desktop을 켠 뒤 week5 폴더에서 아래 순서로 한다. 명령은 각 결과 파일(`results/`)에 있다.

1. kind로 클러스터 `study` 만들기 → `kubectl get nodes` 가 Ready
2. `nginx.yaml` 적용 → port-forward로 접속
3. 2주차 이미지를 태그 붙여 빌드 → `kind load` → 2주차 `.env` 로 Secret 만들기 → `k8s/redis.yaml`, `k8s/api.yaml` 적용
4. 정리: `kind delete cluster --name study`

## 한계

- 노드 1개라 컴퓨터 한 대가 죽는 상황은 실험하지 못했다 (kind 노드는 모두 내 PC 안 컨테이너)
- 실험 B, C는 각 1회 측정
- k8s에서 안의 프로그램이 죽을 때 재시작 시간은 재지 않았다

## 알게 된 점

- compose와 k8s의 차이는 다시 켜는 속도가 아니라 개수를 기억하느냐였다
- 롤링 업데이트만으로는 무중단이 아니었다. 옛 Pod의 종료와 Service 명단에서 빠지는 일이 따로 진행돼서, preStop으로 시간을 줘야 했다
- 숫자는 조건이 맞았는지 확인한 뒤에 믿어야 한다 (첫 400번 시험은 교체 구간 밖이었다)

## 막힌 점

- Docker가 cgroup v1이라 kind 클러스터 생성 실패 → `.wslconfig` 로 cgroup v2
- `:latest` 로 처음 만든 Deployment에 `imagePullPolicy: Always` 가 남아, 이미지를 바꾸고 `kind load` 해도 계속 `ErrImagePull` → `IfNotPresent` 를 직접 적음
- port-forward는 Pod 하나에 붙어서, 그 Pod가 지워지면 끊김
- 에러 전체 목록: `wiki/raw/2026-11-22-week5-k8s-errors.md`

## 파일

| 파일 | 내용 |
|---|---|
| `nginx.yaml` | nginx Deployment 2개 + Service |
| `compose-test/docker-compose.yml` | 실험 A의 compose 쪽 |
| `k8s/redis.yaml`, `k8s/api.yaml` | 2주차 api + redis (Secret은 명령으로 만들어 파일 없음) |
| `results/` | 실험 기록 2개 |
