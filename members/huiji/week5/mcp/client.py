"""MCP 클라이언트 예제: 서버를 자식 프로세스로 띄워 툴을 호출한다."""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # 서버 실행 방법: 현재 파이썬으로 server.py 를 실행
    params = StdioServerParameters(command=sys.executable, args=["server.py"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # 핸드셰이크: 프로토콜 버전, 기능 협상

            tools = await session.list_tools()
            for t in tools.tools:
                print("툴:", t.name)
                print("설명:", t.description)
                print("입력 스키마:", t.input_schema)

            result = await session.call_tool("explain_k8s_object", {"name": "Service"})
            print("\n결과:", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())