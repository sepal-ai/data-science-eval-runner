"""
Data Science Agent with restricted action space for analytical tasks.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
from anthropic import Anthropic
from mcp.server.fastmcp import FastMCP
from pydantic import Field


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    output: str | None = None
    error: str | None = None
    base64_image: str | None = None
    system: str | None = None


@dataclass
class Grade:
    """Grade for evaluation results."""

    subscores: Dict[str, float]
    weights: Dict[str, float]
    metadata: Dict[str, Any] = None


@dataclass
class DatasetInfo:
    """Information about an available dataset."""

    name: str
    columns: List[str]
    row_count: int
    schema: Dict[str, str]
    sample_data: Optional[pd.DataFrame] = None


@dataclass
class RunAgentParams:
    """Parameters for running the data science agent."""

    problem_id: str
    problem_statement: str
    model: str = "claude-3-5-sonnet-20241022"
    system_prompt: Optional[str] = None
    max_iterations: int = 10
    max_tokens: int = 4096
    database_path: str = "./data.db"
    workdir: str = "./workdir"


class DSAgent:
    """
    Data Science Agent with restricted action space for analytical tasks.

    Available actions:
    - write_file(path, content) - Write code/analysis files
    - list_tables() - Discover available datasets
    - describe_table(table_name) - Get schema and basic stats
    - read_table(table_name, limit=None) - Sample or read full table
    - execute_sql(query) - Run SQL queries on datasets
    """

    def __init__(self, db_path: str = "./data.db"):
        self.db_path = db_path
        self.conn = None
        self.anthropic = None
        self._setup_database()

    def _setup_database(self):
        """Initialize DuckDB connection."""
        try:
            self.conn = duckdb.connect(self.db_path)
            # Enable common extensions
            self.conn.execute("INSTALL httpfs")
            self.conn.execute("LOAD httpfs")
        except Exception as e:
            print(f"Database setup error: {e}")

    async def run_agent(self, params: RunAgentParams) -> Dict[str, Any]:
        """Main agent runner with conversation loop."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Initialize system prompt
        system_prompt = params.system_prompt or self._get_default_system_prompt()

        # Start conversation with problem statement
        messages = [
            {
                "role": "user",
                "content": f"Problem: {params.problem_statement}\n\nPlease solve this data science problem step by step.",
            }
        ]

        print(f"🤖 Starting DS Agent: {params.problem_statement}...")

        # Run conversation loop
        result = await self._conversation_loop(
            model=params.model,
            system_prompt=system_prompt,
            messages=messages,
            max_iterations=params.max_iterations,
            max_tokens=params.max_tokens,
        )

        return result

    async def _conversation_loop(
        self,
        model: str,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        max_iterations: int,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Main conversation loop handling tool calls and responses."""

        for iteration in range(max_iterations):
            try:
                print(f"\n🔄 Iteration {iteration + 1}/{max_iterations}")

                # Get available tools
                tools = self._get_tool_definitions()

                # Make API call to Claude
                response = await self._call_claude(
                    model=model, system_prompt=system_prompt, messages=messages, tools=tools, max_tokens=max_tokens
                )

                # Add assistant response to messages
                messages.append({"role": "assistant", "content": response.content})

                # Check if there are tool calls to execute
                tool_calls = self._extract_tool_calls(response)

                if not tool_calls:
                    # No more tool calls, agent is done
                    print("✅ Agent completed")
                    break

                print(f"🔧 Executing {len(tool_calls)} tool(s): {', '.join([tc['name'] for tc in tool_calls])}")

                # Execute tool calls
                tool_results = await self._execute_tool_calls(tool_calls)

                # Add tool results to messages in proper format
                tool_result_content = []
                for i, result in enumerate(tool_results):
                    if i < len(tool_calls):
                        tool_result_content.append(
                            {"type": "tool_result", "tool_use_id": tool_calls[i]["id"], "content": result}
                        )

                if tool_result_content:
                    messages.append({"role": "user", "content": tool_result_content})

                # Check if we should continue
                if iteration == max_iterations - 1:
                    print("⏹️ Reached maximum iterations")
                    break

            except Exception as e:
                print(f"❌ Error in iteration {iteration + 1}: {e}")
                import traceback

                traceback.print_exc()
                return {"success": False, "error": str(e), "messages": messages, "iterations": iteration + 1}

        return {
            "success": True,
            "messages": messages,
            "iterations": iteration + 1,
            "final_response": messages[-1]["content"] if messages else "",
        }

    async def _call_claude(
        self,
        model: str,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int,
    ) -> Any:
        """Make API call to Claude with tools."""
        try:
            return self.anthropic.messages.create(
                model=model, system=system_prompt, messages=messages, tools=tools, max_tokens=max_tokens
            )
        except Exception as e:
            raise Exception(f"Claude API call failed: {e}")

    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from Claude's response."""
        tool_calls = []

        if hasattr(response, "content"):
            for content_block in response.content:
                if hasattr(content_block, "type") and content_block.type == "tool_use":
                    tool_calls.append(
                        {"id": content_block.id, "name": content_block.name, "input": content_block.input}
                    )

        return tool_calls

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[str]:
        """Execute the tool calls and return results."""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]

            print(f"  → {tool_name}({', '.join(f'{k}={v}' for k, v in tool_input.items())})")

            try:
                if tool_name == "write_file":
                    result = await self.write_file(tool_input["path"], tool_input["content"])
                elif tool_name == "list_tables":
                    result = await self.list_tables()
                elif tool_name == "describe_table":
                    result = await self.describe_table(tool_input["table_name"])
                elif tool_name == "read_table":
                    result = await self.read_table(tool_input["table_name"], tool_input.get("limit"))
                elif tool_name == "execute_sql":
                    result = await self.execute_sql(tool_input["query"])
                elif tool_name == "submit_analysis":
                    result = await self.submit_analysis(tool_input["analysis_results"])
                else:
                    result = ToolResult(error=f"Unknown tool: {tool_name}")

                # Format result for message
                if result.error:
                    result_text = f"Error: {result.error}"
                else:
                    result_text = result.output or "Tool executed successfully"

                results.append(result_text)

            except Exception as e:
                error_msg = f"Tool execution error: {e}"
                print(error_msg)
                results.append(error_msg)

        return results

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Claude API."""
        return [
            {
                "name": "write_file",
                "description": "Write code/analysis files to the filesystem",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to write to"},
                        "content": {"type": "string", "description": "Content to write to file"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "list_tables",
                "description": "Discover available datasets in the database",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "describe_table",
                "description": "Get schema and basic statistics for a table",
                "input_schema": {
                    "type": "object",
                    "properties": {"table_name": {"type": "string", "description": "Name of the table to describe"}},
                    "required": ["table_name"],
                },
            },
            {
                "name": "read_table",
                "description": "Sample or read full table data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Name of the table to read"},
                        "limit": {"type": "integer", "description": "Maximum number of rows to return"},
                    },
                    "required": ["table_name"],
                },
            },
            {
                "name": "execute_sql",
                "description": "Execute SQL queries on the database",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "SQL query to execute"}},
                    "required": ["query"],
                },
            },
            {
                "name": "submit_analysis",
                "description": "Submit final analysis results in structured format for evaluation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "analysis_results": {
                            "type": "object",
                            "description": "Structured analysis results",
                            "properties": {
                                "top_customer_total_spent": {
                                    "type": "number",
                                    "description": "Total amount spent by top customer",
                                },
                                "top_customer_name": {"type": "string", "description": "Name of top customer"},
                                "total_revenue": {
                                    "type": "number",
                                    "description": "Total revenue from completed transactions",
                                },
                                "total_transactions": {
                                    "type": "integer",
                                    "description": "Total number of completed transactions",
                                },
                                "unique_customers": {
                                    "type": "integer",
                                    "description": "Number of unique customers who made purchases",
                                },
                                "avg_transaction_value": {"type": "number", "description": "Average transaction value"},
                                "highest_month_sales": {
                                    "type": "number",
                                    "description": "Highest monthly sales amount",
                                },
                                "lowest_month_sales": {"type": "number", "description": "Lowest monthly sales amount"},
                                "months_with_data": {
                                    "type": "integer",
                                    "description": "Number of months with transaction data",
                                },
                                "key_insights": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Key insights from analysis",
                                },
                            },
                            "required": [
                                "top_customer_total_spent",
                                "top_customer_name",
                                "total_revenue",
                                "total_transactions",
                                "unique_customers",
                                "avg_transaction_value",
                            ],
                        }
                    },
                    "required": ["analysis_results"],
                },
            },
        ]

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for data science tasks."""
        return """You are a data science agent with access to a database and file system. Your goal is to solve data science problems systematically.

Available tools:
- write_file: Write code/analysis files
- list_tables: Discover available datasets 
- describe_table: Get schema and basic stats for a table
- read_table: Sample or read full table data
- execute_sql: Run SQL queries on datasets
- submit_analysis: Submit final analysis results in structured JSON format

Approach:
1. Start by exploring the available data using list_tables and describe_table
2. Use SQL queries to analyze and aggregate data
3. Write well-commented Python code for your analysis
4. Create clear output files (CSV, reports) as requested
5. Calculate key metrics and statistics
6. **IMPORTANT**: Always finish by calling submit_analysis with structured results

Best practices:
- Always explore data first before analysis
- Use appropriate SQL for data aggregation
- Write clean, documented code
- Validate your results
- Provide business insights in your reports
- **MUST**: Submit structured analysis results at the end using submit_analysis tool

For analysis problems, ensure you calculate and submit these key metrics:
- Top customer information (name and total spent)
- Total revenue from completed transactions
- Total number of completed transactions
- Number of unique customers
- Average transaction value
- Monthly sales trends (highest/lowest months)
- Key insights from your analysis"""

    async def write_file(self, path: str, content: str) -> ToolResult:
        """Write code/analysis files to the filesystem."""
        try:
            # Ensure we're writing to a safe location (workdir or current dir)
            if not (path.startswith("./") or path.startswith("workdir/") or path.startswith("./workdir/")):
                path = f"./workdir/{path.lstrip('/')}"

            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                f.write(content)

            return ToolResult(output=f"File written successfully to: {path}")
        except Exception as e:
            return ToolResult(error=f"Failed to write file: {str(e)}")

    async def list_tables(self) -> ToolResult:
        """Discover available datasets in the database."""
        try:
            if not self.conn:
                return ToolResult(error="Database connection not available")

            # Get all tables
            result = self.conn.execute("SHOW TABLES").fetchall()
            tables = [row[0] for row in result]

            if not tables:
                return ToolResult(output="No tables found in database")

            output = "Available tables:\n" + "\n".join(f"- {table}" for table in tables)
            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(error=f"Failed to list tables: {str(e)}")

    async def describe_table(self, table_name: str) -> ToolResult:
        """Get schema and basic statistics for a table."""
        try:
            if not self.conn:
                return ToolResult(error="Database connection not available")

            # Get table schema
            schema_result = self.conn.execute(f"DESCRIBE {table_name}").fetchdf()

            # Get row count
            count_result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            row_count = count_result[0] if count_result else 0

            # Get sample data (first 5 rows)
            sample_result = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchdf()

            output = f"Table: {table_name}\n"
            output += f"Row count: {row_count}\n\n"
            output += "Schema:\n"
            output += schema_result.to_string(index=False) + "\n\n"
            output += "Sample data (first 5 rows):\n"
            output += sample_result.to_string(index=False)

            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(error=f"Failed to describe table {table_name}: {str(e)}")

    async def read_table(self, table_name: str, limit: Optional[int] = None) -> ToolResult:
        """Sample or read full table data."""
        try:
            if not self.conn:
                return ToolResult(error="Database connection not available")

            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"

            result = self.conn.execute(query).fetchdf()

            output = f"Data from {table_name}"
            if limit:
                output += f" (limited to {limit} rows)"
            output += f":\n\n{result.to_string(index=False)}"

            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(error=f"Failed to read table {table_name}: {str(e)}")

    async def execute_sql(self, query: str) -> ToolResult:
        """Execute SQL queries on the database."""
        try:
            if not self.conn:
                return ToolResult(error="Database connection not available")

            # Execute query and get results
            result = self.conn.execute(query).fetchdf()

            output = f"Query executed successfully:\n{query}\n\n"
            output += f"Results:\n{result.to_string(index=False)}"

            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(error=f"Failed to execute query: {str(e)}")

    async def submit_analysis(self, analysis_results: dict) -> ToolResult:
        """Submit final analysis results in structured format."""
        try:
            # Store the analysis results for evaluation
            self.analysis_results = analysis_results

            # Save to JSON file for evaluation
            import json

            # During evaluation, we're already in the workdir, so save directly to current directory
            results_path = Path("analysis_results.json")

            with open(results_path, "w") as f:
                json.dump(analysis_results, f, indent=2)

            # Create a summary for display
            summary = f"""
Analysis Results Submitted:
- Top Customer: {analysis_results.get("top_customer_name", "N/A")} (${analysis_results.get("top_customer_total_spent", 0)})
- Total Revenue: ${analysis_results.get("total_revenue", 0)}
- Total Transactions: {analysis_results.get("total_transactions", 0)}
- Unique Customers: {analysis_results.get("unique_customers", 0)}
- Average Transaction Value: ${analysis_results.get("avg_transaction_value", 0)}
- Months with Data: {analysis_results.get("months_with_data", 0)}
            """

            if "key_insights" in analysis_results:
                summary += f"\nKey Insights:\n"
                for i, insight in enumerate(analysis_results["key_insights"], 1):
                    summary += f"  {i}. {insight}\n"

            return ToolResult(output=summary.strip())
        except Exception as e:
            return ToolResult(error=f"Failed to submit analysis: {str(e)}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def create_ds_agent_mcp() -> FastMCP:
    """Create MCP server with DS Agent tools."""
    mcp = FastMCP("ds_agent")
    agent = DSAgent()

    @mcp.tool()
    async def write_file(
        path: str = Field(description="File path to write to"),
        content: str = Field(description="Content to write to file"),
    ) -> ToolResult:
        """Write code/analysis files to the filesystem."""
        return await agent.write_file(path, content)

    @mcp.tool()
    async def list_tables() -> ToolResult:
        """Discover available datasets in the database."""
        return await agent.list_tables()

    @mcp.tool()
    async def describe_table(table_name: str = Field(description="Name of the table to describe")) -> ToolResult:
        """Get schema and basic statistics for a table."""
        return await agent.describe_table(table_name)

    @mcp.tool()
    async def read_table(
        table_name: str = Field(description="Name of the table to read"),
        limit: Optional[int] = Field(default=None, description="Maximum number of rows to return"),
    ) -> ToolResult:
        """Sample or read full table data."""
        return await agent.read_table(table_name, limit)

    @mcp.tool()
    async def execute_sql(query: str = Field(description="SQL query to execute")) -> ToolResult:
        """Execute SQL queries on the database."""
        return await agent.execute_sql(query)

    return mcp
