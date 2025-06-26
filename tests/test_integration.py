import asyncio
import json
import subprocess
from contextlib import AsyncExitStack

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Required tools that should be available in every MCP server
REQUIRED_TOOLS = ["setup_problem", "grade_problem"]


async def all_problems_loading_end_to_end(problems_metadata_path):
    """Test that all problems in the problem list can be successfully loaded and are correctly configured."""
    print("Starting test")

    with open(problems_metadata_path) as f:
        metadata = json.load(f)
        problems = metadata["problem_set"]["problems"]
    print("File opened")

    for problem in problems:
        args = ["run", "-i", problem["image"]]
        args.extend(problem["startup_command"].split(" "))
        server_params = StdioServerParameters(command="docker", args=args)
        exit_stack = AsyncExitStack()

        try:
            stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            session: ClientSession = await exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            tools_result = await session.list_tools()
            assert len(tools_result.tools) > 0, f"No tools found for problem {problem}"

            tools = [tool.name for tool in tools_result.tools]
            for required_tool in REQUIRED_TOOLS:
                assert required_tool in tools, (
                    f"{required_tool} is required but does not exist as a tool on the server."
                )

            tools_result = await session.list_tools()
            assert len(tools_result.tools) > 0, f"No tools found for problem {problem}"

            second_tools = [tool.name for tool in tools_result.tools]
            assert second_tools == tools, "Tools list changed between first and second client connection"

            # Try to setup the problem
            setup_result = await session.call_tool("setup_problem", {"problem_id": problem["id"]})
            assert setup_result is not None, f"Failed to setup problem {problem['id']}"

            # Verify we got a problem statement
            problem_contents = setup_result.content
            assert len(problem_contents) > 0, f"setup_problem result is not text for problem {problem['id']}"
            print(f"Successfully loaded problem {problem['id']}")
        finally:
            subprocess.run(f"docker kill $(docker ps -q --filter ancestor={problem['image']})", shell=True, check=False)
            await exit_stack.aclose()


@pytest.mark.validate_env
def test_all_problems_loading_end_to_end(problems_metadata_path):
    asyncio.run(all_problems_loading_end_to_end(problems_metadata_path))
