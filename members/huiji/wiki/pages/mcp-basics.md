# MCP (Model Context Protocol)

## 한 줄 정의
AI 앱이 외부 도구와 데이터에 연결하는 방식을 표준화한 프로토콜 (host가 client를 통해 server의 tool을 호출)

## 왜 필요한가
MCP 이전에는 앱마다 도구 연동을 따로 만들어야 했다. 한 규격(USB-C처럼)으로 맞추면 서버를 한 번 만들어 여러 AI 앱에서 재사용할 수 있다.

- Host: 사용자가 쓰는 AI 앱 (예: Claude Desktop). 어떤 도구를 쓸지 결정한다.
- Client: Host 안에서 서버 하나와 1:1로 연결을 유지하는 부품
- Server: 도구와 데이터를 노출하는 프로그램
- Tool: 모델이 호출하는 함수. 이름, 설명, 입력 스키마(JSON Schema)로 정의되며, docstring과 타입 힌트가 모델에게 주는 사용 설명서가 된다.
- 통신: 로컬은 stdio(JSON-RPC), 원격은 Streamable HTTP. stdio 서버에서는 `print()`를 쓰면 안 된다 (stdout이 프로토콜 통로).

## 예제
mcp/server.py 참고

## 내가 막힌 점
- mcp 2.x에서 `from mcp.server.fastmcp import FastMCP`가
  `ModuleNotFoundError`. 2.x에서는 `FastMCP`가 `MCPServer`로 이름이 바뀜
  (`from mcp.server.mcpserver import MCPServer`). 1.x 코드를 쓰려면 `pip install "mcp<2"`.
- mcp 2.3.0에서 서버/클라이언트 호출(list_tools, call_tool)까지 직접 실행해 확인함.

## 출처
- Model Context Protocol 공식 문서
- MCP Python SDK