# k8s desired state (원하는 상태와 컨트롤 루프)

## 한 줄 정의

k8s는 docker compose처럼 무엇을 실행할지뿐만 아니라, 그것이 어떤 상태를 유지해야 하는지(예: Pod 2개)까지 관리한다.

## 왜 필요한가

compose는 restart: always 를 넣어도 스스로 죽은 컨테이너만 복구하지만, k8s는 정해진 상태(개수와 버전)를 유지하기 때문에 자동 복구, 확장, 롤링 업데이트를 할 수 있다.


## 최소 예제

```yaml
# nginx.yaml 일부
spec:
  replicas: 2            # 원하는 상태
```

```powershell
kubectl apply -f nginx.yaml
kubectl delete pod <nginx Pod 하나> --wait=false
kubectl get pods -w
```

실행 결과 (2026-11-22, kind 노드 1개, k8s v1.37.0):

```
nginx-75cc477c85-8p96k   1/1   Terminating         11m
nginx-75cc477c85-nnfsr   0/1   Pending             0s     ← 같은 순간 새 Pod
nginx-75cc477c85-nnfsr   0/1   ContainerCreating   0s
nginx-75cc477c85-8p96k   0/1   Completed           11m
nginx-75cc477c85-nnfsr   1/1   Running             0s
```

| 측정 | 결과 |
|---|---|
| k8s: Pod 삭제 후 새 Pod Ready (3회) | 0.91 / 0.90 / 0.91초 |
| compose: 컨테이너 삭제 (`restart: always`, scale 2) | 5초 뒤에도 1개 |
| compose: 안의 프로그램 종료 (3회) | 0.60 / 0.69 / 0.62초에 같은 컨테이너 재시작 |

- 지운 Pod는 살아나지 않고, 새 이름의 Pod가 생긴다
- 옛 Pod가 `Terminating` 인 순간 이미 새 Pod가 생긴다. 지우는 중인 Pod는 없는 것으로 센다

### 선언형이라 생기는 일: 드리프트

- `kubectl scale --replicas=3` 뒤 `kubectl diff -f nginx.yaml` → `replicas: 3` vs `2`, `generation: 2 → 3`
- 파일과 클러스터가 어긋난다. 누가 파일을 다시 apply하면 조용히 2개로 돌아간다 → YAML을 고치고 apply하는 것이 원칙

## 내가 막힌 점

- 롤링 업데이트면 무중단이라고 생각했는데, 교체 중 800번 요청에 7번 실패 → 옛 Pod의 종료(SIGTERM)와 Service 명단에서 빠지는 일이 따로 진행돼서 생기는 틈. `preStop: sleep 5` 를 넣으니 800번 중 0번 실패 (각 1회 측정, 도유 님 Mac 실험과 같은 결론)
- 처음 잰 400번은 교체가 요청 구간 밖이어서 400/400 → 시각을 맞춰 보고 버림
- `kubectl diff` 가 `executable file not found` → Windows에 `diff` 가 없음. Git의 `usr\bin` 을 PATH에 추가
- port-forward로 접속한 뒤 Pod를 지우면 연결이 끊김 (port-forward는 Pod 하나에 붙음). 브라우저는 캐시를 보여 줘서 몰랐고 `curl` 로 `HTTP 000` 확인

## 출처

- https://kubernetes.io/docs/concepts/architecture/controller/
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/
