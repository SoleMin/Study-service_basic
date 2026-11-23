# 실험 A: 자동 복구 (k8s vs compose)

- 날짜: 2026-11-22
- 환경: Windows 11, Docker Desktop 28.0.1 (WSL2, cgroup v2), kind 0.33.0 (노드 1개, k8s v1.37.0), kubectl v1.32.2 (버전 차이 경고 있음)
- 이미지: `nginx:1.27`, 개수 2개
- 측정 방법: 0.2초마다 kubectl / docker inspect로 상태를 확인. 확인 간격 때문에 오차 약 ±0.5초

## k8s: Pod 삭제 (`kubectl delete pod --wait=false`)

새 Pod가 Ready가 되기까지 걸린 시간. 이미지는 노드에 이미 있는 상태.

| 회차 | 지운 Pod | 새 Pod | 시간 |
|---|---|---|---|
| 1 | nginx-75cc477c85-8p96k | nginx-75cc477c85-nnfsr | 0.91초 |
| 2 | nginx-75cc477c85-bvj7c | nginx-75cc477c85-qb7m7 | 0.90초 |
| 3 | nginx-75cc477c85-nnfsr | nginx-75cc477c85-xc5jc | 0.91초 |

- 처음 apply 때 Pod가 Running이 되기까지: 18초, 20초 (`kubectl get pods -w` 의 AGE). 이미지 다운로드가 포함된 시간
- `-w` 화면에서 옛 Pod의 `Terminating` 과 새 Pod의 `Pending` 이 같은 순간에 찍힘. 옛 Pod는 `Completed` 로 끝남
- `kubectl port-forward service/nginx` 는 처음 연결된 Pod가 지워진 뒤 끊김 (`curl` 결과 `HTTP 000`). 브라우저는 캐시된 페이지를 보여 줘서 끊긴 것을 알 수 없었음. 다시 켠 뒤 `HTTP 200`

## compose: `restart: always`, `--scale web=2`

| 상황 | 결과 |
|---|---|
| (가) 컨테이너 삭제 `docker rm -f compose-test-web-1` | 5초 뒤에도 1개. 다시 채우지 않음 |
| (나) 안의 프로그램 종료 `docker exec ... nginx -s stop` | 같은 컨테이너를 다시 켬 |

(나) 다시 켜지기까지 걸린 시간

| 회차 | 시간 | 재시작 횟수 |
|---|---|---|
| 1 | 0.60초 | 0 → 1 |
| 2 | 0.69초 | 1 → 2 |
| 3 | 0.62초 | 2 → 3 |

- 회차 사이 간격은 약 17초. 연달아 죽였을 때의 재시작 지연(backoff)은 확인하지 않음

## 결론

- 다시 켜는 속도는 둘 다 1초 이내로 비슷하다 (오차 범위 안)
- 차이는 개수를 지키느냐다. compose는 사라진 컨테이너를 채우지 않고, k8s는 replicas 개수로 다시 맞춘다
- k8s는 같은 Pod를 살리지 않고 새 이름의 Pod를 만든다. compose는 같은 컨테이너를 다시 켠다

## 덧붙임: compose에서 포트를 열고 2개로 늘리기 (2026-11-22)

- `ports: "8090:80"` + `docker compose up -d --scale web=2`
- 결과: 1개만 뜸. 두 번째는 `Bind for 0.0.0.0:8090 failed: port is already allocated`

## 측정 예정

- k8s에서 안의 프로그램이 죽었을 때 (재시작, CrashLoopBackOff) → Day 2
