# 쿠버네티스 기본 오브젝트 (Pod, Deployment, Service, Namespace)

## 한 줄 정의
Pod는 컨테이너 실행 단위, Deployment는 Pod 개수를 유지하는 관리자, Service는 Pod 묶음 앞의 고정 주소, Namespace는 클러스터 안의 논리적 구분 단위다.

## 왜 필요한가
Pod는 죽었다 살아날 때마다 이름과 IP가 바뀌어서 직접 관리하거나 주소로 접근할 수 없다. 그래서 개수를 유지해 주는 Deployment와 라벨로 Pod를 찾아 고정 주소를 주는 Service가 필요하고, 같은 클러스터에서 리소스 이름 충돌을 막고 구분하기 위해 Namespace를 쓴다.

## 구조
관계도: Service는 라벨 셀렉터로 Pod를 찾고, Deployment는 ReplicaSet을 통해 Pod 개수를 유지한다.

```
Namespace (default)
 ├─ Deployment "nginx" (replicas: 2)
 │    └─ ReplicaSet (Deployment가 자동 생성)
 │         ├─ Pod nginx-abc-1 (label: app=nginx)
 │         └─ Pod nginx-abc-2 (label: app=nginx)
 └─ Service "nginx" ── selector: app=nginx ──▶ 위 두 Pod로 분산
```

| 개념 | 역할 | Docker 비유 |
|---|---|---|
| Pod | 컨테이너를 감싸는 최소 실행 단위, 같은 Pod의 컨테이너는 IP 공유 | `docker run`으로 뜬 컨테이너 |
| Deployment | Pod를 N개 유지, 죽으면 재생성, 롤링 업데이트 | compose의 replicas + 재시작 정책 |
| Service | Pod 묶음 앞의 고정 주소와 로드밸런서 | compose의 서비스 이름과 포트 매핑 |
| Namespace | 클러스터 안의 논리적 방 구분 | 프로젝트별 compose 네트워크 |

핵심 연결고리는 라벨과 셀렉터다. Service의 `selector`와 Pod의 `labels`가 같아야 연결된다.


## 내가 막힌 점


## 출처
- Kubernetes 기초 튜토리얼 (kubernetes.io/docs/tutorials/kubernetes-basics)
- kind 빠른 시작 (kind.sigs.k8s.io/docs/user/quick-start)
