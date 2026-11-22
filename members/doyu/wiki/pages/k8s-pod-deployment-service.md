# Pod, Deployment, Service, Namespace의 관계

## 한 줄 정의
**Pod**는 컨테이너가 실제로 도는 가장 작은 단위, **Deployment**는 "이 Pod를 몇 개 유지해"라는 원하는 상태, **Service**는 계속 바뀌는 Pod들 앞에 놓인 고정된 이름과 주소, **Namespace**는 이것들을 묶어 두는 공간이다.

## 왜 필요한가
- Pod는 죽으면 IP가 바뀐 새 Pod로 대체된다. 그래서 Pod를 직접 만들지 않고 Deployment에 개수를 적어 두면, 컨트롤러가 현재 상태를 원하는 상태에 계속 맞춘다 (Pod를 지우자 0.9초 만에 새로 뜸).
- 다른 Pod는 바뀌는 IP가 아니라 Service 이름(`redis`)으로 찾는다. Service는 라벨(`app: redis`)이 맞는 Pod들로 요청을 나눠 보낸다.
- Namespace로 실습용 리소스를 묶어 두면 `kubectl delete ns study` 한 번으로 정리된다.

```
Namespace study
├── Deployment api (replicas: 2)
│   └── ReplicaSet api-856468fc8f   ← 템플릿이 바뀔 때마다 새로 생김 (롤링 업데이트, 되돌리기용)
│       ├── Pod api-…-bwgvh (worker)
│       └── Pod api-…-xtvzx (worker2)
├── Service api      → selector app=api → 두 Pod로 분산
├── Deployment redis → Pod 1개
└── Service redis    → api Pod가 REDIS_HOST=redis 로 접속
```

| 리소스 | 연결 고리 | 확인 명령 |
| --- | --- | --- |
| Deployment → ReplicaSet → Pod | `selector.matchLabels` = Pod 템플릿의 `labels` | `kubectl get deploy,rs,pod` |
| Service → Pod | Service의 `selector` = Pod의 `labels` | `kubectl get endpointslices` |
| 모두 → Namespace | `metadata.namespace` | `kubectl get all -n study` |

## 최소 예제
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: {name: nginx, namespace: study}
spec:
  replicas: 2
  selector: {matchLabels: {app: nginx}}
  template:
    metadata: {labels: {app: nginx}}
    spec:
      containers: [{name: nginx, image: nginx:1.27-alpine, ports: [{containerPort: 80}]}]
---
apiVersion: v1
kind: Service
metadata: {name: nginx, namespace: study}
spec:
  selector: {app: nginx}
  ports: [{port: 80, targetPort: 80}]
```
```bash
kubectl apply -f nginx.yaml
kubectl -n study port-forward svc/nginx 8080:80   # 내 PC의 8080 → Service 80
```

## 내가 막힌 점
- 로컬에서 만든 이미지를 쓰려면 `kind load docker-image`로 노드에 넣고 `imagePullPolicy: IfNotPresent`로 둬야 한다. 안 넣은 태그를 쓰면 `ImagePullBackOff`, 원인은 `logs`가 아니라 `describe`의 Events에 나온다.
- 환경변수 값이 틀려서 앱이 죽으면 `CrashLoopBackOff`. 직전에 죽은 컨테이너의 에러는 `kubectl logs --previous`로 본다.
- readiness probe만으로는 롤링 업데이트 중 요청이 1개씩 실패했다. 꺼지는 Pod가 Service 목록에서 빠지기 전에 먼저 꺼져서였고, `preStop`에서 5초 기다리게 하자 실패가 0이 됐다.

## 출처
- Kubernetes 문서, Deployments: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Kubernetes 문서, Service: https://kubernetes.io/docs/concepts/services-networking/service/
- Kubernetes 문서, Debug Pods: https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/
- 직접 실습: [week5-notes.md](../raw/week5-notes.md)
