# 2026-11-22 5주차 k8s 에러 메모

| 에러 | 원인 | 해결 |
|---|---|---|
| `kind create cluster` → `Starting control-plane ✗`, `dial tcp 172.21.0.2:6443: connect: connection refused`, 첫 줄 `cgroup v1 is deprecated` | Docker(WSL2)가 cgroup v1 → k8s v1.37 kubelet이 시작 안 함 → API 서버(static Pod)도 안 뜸 | `%USERPROFILE%\.wslconfig` 에 `[wsl2]` / `kernelCommandLine = cgroup_no_v1=all`, Docker Desktop 종료 → `wsl --shutdown` → 재시작 → `Cgroup=2` |
| 재부팅 후 `kubectl get nodes` → `127.0.0.1:52198 ... actively refused` | Docker Desktop이 안 켜짐 → 노드 컨테이너 꺼짐 | Docker Desktop 켜기. 클러스터는 그대로 돌아옴 (AGE 8h, 부품 RESTARTS 1) |
| `kubectl version` 경고 `client (1.32) and server (1.37) exceeds the supported minor version skew` | kubectl이 오래됨 | 아직 문제 없음. 이상하면 업데이트 |
| `v1 Endpoints is deprecated in v1.33+` | Endpoints → EndpointSlice로 바뀌는 중 | 경고만. `kubectl get endpointslices -l kubernetes.io/service-name=<이름>` |
| port-forward 후 Pod 삭제 → `curl` `HTTP 000` (브라우저는 캐시라 정상처럼 보임) | port-forward는 Pod 하나에 붙음 | 다시 켜기. 분배·무중단 측정은 클러스터 안에서 |
| `kubectl diff` → `failed to run "diff": executable file not found` | Windows에 diff 없음 | `$env:PATH += ";C:\Program Files\Git\usr\bin"` |
| `ErrImagePull` `pull access denied ... docker.io/library/week2-api:latest` | 노드 containerd는 내 PC Docker 이미지를 못 봄 | 태그 붙여 빌드 + `kind load docker-image` |
| 이미지를 넣었는데 계속 `ErrImagePull` (`week2-api:0.1`) | 처음 `:latest` 로 만들 때 `imagePullPolicy: Always` 가 채워져 남음 | YAML에 `imagePullPolicy: IfNotPresent` 직접 적기 |
| PowerShell 5.1 `Invoke-RestMethod` 한글 깨짐 | 응답에 charset 없음 → ISO-8859-1로 읽음 | `Invoke-WebRequest` 바이트를 UTF-8로 디코딩 |
| VS Code 터미널에 여러 줄 붙여 넣기 → 첫 줄만 실행 | 붙여 넣기 동작 | 한 줄씩 |
| `kubectl run ... -i` → `Unknown stream id 1, discarding message`, 첫 출력 사라짐 | 접속보다 출력이 빨랐음 (버전 차이도 의심, 미확인) | 시작 시각은 Events로 |
| `kubectl get pods -w` 가 조용히 끝남 | 오래 둔 watch 연결 종료 | 다시 켜기 |
