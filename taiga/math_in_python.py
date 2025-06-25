import asyncio  # noqa -- swapping to trio would be beneficial, but not blocking atm
import json
import os
from dataclasses import dataclass
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .spec import Grade
from .tools.base import ToolResult

# This is part of the reference impl
# ----------------------------------

mcp = FastMCP("taiga")

TEST_MODE = os.environ.get("MCP_TESTING_MODE", "1") in ["1", "true"]

if TEST_MODE:
    # Note, these tools are only available in testing mode for the purpose of testing
    # If the enviroment performs well with these tools, it will also work with our internal
    # implementation

    from .tools.bash import BashTool
    from .tools.edit import Command, EditTool

    bash_tool = BashTool()

    @mcp.tool()
    async def bash(command: str, restart: bool = False) -> ToolResult:
        return await bash_tool(command, restart)

    edit_tool = EditTool()

    @mcp.tool(
        name="str_replace_editor",
        description="Create and edit files using str_replace_editor.  Please use absolute paths for all file names.  When writing files please work within /workdir.",
    )
    async def str_replace_editor(
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
    ) -> ToolResult:
        return await edit_tool(
            command=command,
            path=path,
            file_text=file_text,
            view_range=view_range,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
        )

# This is the contractor provided environment
# -------------------------------------------


@dataclass
class Problem:
    id: str
    statement: str
    solution: str


template = """
Write a python script into a file using str_replace_editor to
<STATEMENT>
and run it using bashtool to get the results.
"""

problems = [
    Problem(
        id="factorial",
        statement="compute factorial(20)",
        solution="2432902008176640000",
    ),
    Problem(id="gcd", statement="compute gcd(2321, 45364)", solution="11"),
]

current_problem: Problem | None = None


def _get_problem(problem_id: str) -> Problem:
    global current_problem
    assert current_problem is None or current_problem.id == problem_id, (
        f"setup_problem can only be called once with id: {problem_id=}, current_problem.id={current_problem.id}"
    )
    problem = [p for p in problems if p.id == problem_id]
    if len(problem) > 1:
        raise ValueError(f"Multiple problems found for id: {problem_id=}")
    if len(problem) == 0:
        raise ValueError(f"No problem found for id: {problem_id=}")
    current_problem = problem[0]
    return problem[0]


# Implementation notes: setup_problem will only be called once per enviroment instance
@mcp.tool()
async def setup_problem(
    problem_id: str = Field(description="The id of the problem to solve"),
) -> str:
    """Starts the enviroment and returns the problem statement"""
    await asyncio.sleep(0)

    current_problem = _get_problem(problem_id)
    return template.replace("<STATEMENT>", current_problem.statement)


# Implementation note: grade_problem will only be called once per enviroment instance
@mcp.tool()
async def grade_problem(
    problem_id: str,
    transcript: str = Field(description="The entire transcript produced by the model and its tool calls"),
) -> Grade:
    """Check your solution for grading. Returns a Grade object making sure to include all components that make up the score as subscores."""
    # Note that this is a temporary signature and a more complete reference will be provided.
    await asyncio.sleep(0)

    answer = _get_problem(problem_id).solution
    score = float(answer in str(transcript))
    return Grade(
        subscores={"matched_solution": score},
        weights={"matched_solution": 1},
        metadata={"test": "this was graded successfully!"},
    )


# Simple custom tool
# FastMCP uses pydantic to do param validation
@mcp.tool()
async def restricted_echo_tool(
    to_echo: Annotated[Literal["hello", "goodbye", "new"] | None, Field(description="The value to echo")] = "hello",
) -> str | None:
    """Directly returns the value specified by to_echo"""
    await asyncio.sleep(0)

    return to_echo


# More complex custom tool
@dataclass
class TodoItem:
    id: Annotated[str, Field(description="Unique ID for the todo list item")]
    content: Annotated[str, Field(description="Todo list item content")]
    status: Annotated[
        Literal["pending", "in_progress", "completed"], Field(description="Current status of this todo list item")
    ]
    priority: Annotated[
        Literal["high", "medium", "low"], Field(description="The priority level of this todo list item")
    ]

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status,
            "priority": self.priority,
        }


todo_items: list[TodoItem] = []


# FastMCP uses pydantic to do basic param validation
@mcp.tool()
async def todo_tool(
    operation: Annotated[
        Literal["read", "write"],
        Field(
            description="The operation to perform - either 'read' to get the current todo list or 'write' to replace the entire todo list"
        ),
    ],
    todos: Annotated[
        list[TodoItem] | None,
        Field(
            description="Only required for the 'write' operation. Contains the list of todo items to replace the current todo list",
        ),
    ] = None,
) -> str:
    """Manages todo lists - read and write todo items"""
    await asyncio.sleep(0)

    global todo_items

    if operation == "read":
        if not todo_items:
            raise Exception("The todo list is currently empty")

        todo_dicts = [todo.to_dict() for todo in todo_items]
        return json.dumps(todo_dicts, indent=2)
    elif operation == "write":
        if todos is None:
            raise ValueError("The 'todos' parameter is required for write operations")
        todo_items = todos
        return f"Successfully replaced the todo list with the {len(todos)} provided items"
    else:
        raise ValueError(f"Invalid operation '{operation}'. Must be either 'read' or 'write'")


def main():
    # Initialize and run the server as root; you can use files and services that require root permissions
    # once init is done, the server will run as the model user to prevent it from accessing problem data
    os.chdir("/workdir")
    mcp.run(transport="stdio")
