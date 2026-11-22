"""툴 하나짜리 MCP 서버: 쿠버네티스 용어 설명기."""
from mcp.server.mcpserver import MCPServer

# 서버 이름. 클라이언트가 연결할 때 이 이름을 보게 된다.
mcp = MCPServer("k8s-helper")

GLOSSARY = {
    "pod": "컨테이너를 감싸는 k8s의 최소 실행 단위. 같은 Pod의 컨테이너는 IP와 볼륨을 공유한다.",
    "deployment": "Pod를 N개 항상 유지하고 롤링 업데이트를 담당하는 컨트롤러.",
    "service": "Pod 묶음 앞에 놓이는 고정 주소 + 로드밸런서. 라벨 셀렉터로 Pod를 고른다.",
    "namespace": "클러스터 안의 논리적 구분 단위. 이름 충돌 방지와 자원 분리에 쓴다.",
    "replicaset": "지정한 개수의 Pod 복제본을 유지하는 객체. 보통 Deployment가 자동 생성한다.",
}


@mcp.tool()
def explain_k8s_object(name: str) -> str:
    """쿠버네티스 오브젝트(Pod, Deployment, Service, Namespace, ReplicaSet)를
    한국어로 한두 문장으로 설명한다.

    Args:
        name: 설명을 듣고 싶은 오브젝트 이름 (대소문자 무관)
    """
    key = name.strip().lower()
    if key in GLOSSARY:
        return f"{name}: {GLOSSARY[key]}"
    known = ", ".join(sorted(GLOSSARY))
    return f"'{name}'은(는) 모릅니다. 지원하는 오브젝트: {known}"


if __name__ == "__main__":
    # 기본 transport는 stdio. print()는 쓰지 말 것 (stdout이 프로토콜 통로).
    mcp.run()