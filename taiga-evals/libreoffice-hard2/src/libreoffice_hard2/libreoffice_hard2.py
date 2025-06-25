import asyncio
import json
import os
import platform
import subprocess
import csv
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from taiga.spec import Grade

# This is part of the reference impl
# ----------------------------------

mcp = FastMCP("taiga")

TEST_MODE = os.environ.get("MCP_TESTING_MODE", "1") in ["1", "true"]

if TEST_MODE:
    # Note, these tools are only available in testing mode for the purpose of testing
    # If the enviroment performs well with these tools, it will also work with our internal
    # implementation

    from taiga.tools.computer import (
        Action,
        ComputerTool,
    )

    computer_tool = ComputerTool()

    @mcp.tool()
    async def computer(
        *,
        action: Action,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        start_coordinate: tuple[int, int] | None = None,
        duration: int | float | None = None,
        scroll_direction: str | None = None,
        scroll_amount: int | None = None,
    ) -> CallToolResult:
        return await computer_tool(
            action=action,
            text=text,
            coordinate=coordinate,
            start_coordinate=start_coordinate,
            duration=duration,
            scroll_direction=scroll_direction,
            scroll_amount=scroll_amount,
        )


# This is the contractor provided environment
# -------------------------------------------


async def verify_output_file() -> int:
    """
    Verifies that the output file exists and matches the expected format.
    Returns a score between 0 and 1 based on the correctness of the output.
    """
    output_path = Path("/home/model/global_customers_summarized.ods")
    expected_csv_path = Path("/workdir/image/outputs/global_customers_summarized.csv")
    
    # Check if output file exists
    if not output_path.exists():
        print("Output file does not exist")
        return 0
    
    print(f"Found output file at {output_path}")
    
    # Create temporary directory for conversion
    temp_dir = Path("/tmp/libreoffice_conversion")
    temp_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Use libreoffice to convert ODS to CSV
        cmd = f"libreoffice --headless --convert-to csv --outdir {temp_dir} {output_path}"
        print(f"Running conversion command: {cmd}")
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        # Check if conversion was successful
        if process.returncode != 0:
            print(f"Failed to convert ODS to CSV: {stderr.decode(errors='replace')}")
            return 0
        
        print(f"Conversion successful: {stdout.decode(errors='replace')}")
        
        # Check if the conversion created the expected file
        converted_file = temp_dir / "global_customers_summarized.csv"
        if not converted_file.exists():
            print(f"Conversion didn't create expected file at {converted_file}")
            # Try to list directory contents
            try:
                print(f"Files in {temp_dir}: {list(temp_dir.glob('*'))}")
            except Exception as e:
                print(f"Error listing directory: {e}")
            return 0
        
        # Normalize and compare CSV files
        try:
            user_data = normalize_csv_data(converted_file)
            expected_data = normalize_csv_data(expected_csv_path)
        
            # Compare the two datasets
            diff = compare_csv_data(user_data, expected_data)
            
            # Calculate score based on diff length
            if diff == "":
                print("Perfect match! No differences found.")
                return 1.0  # Perfect match
            else:
                # Calculate a partial score based on diff length
                # The shorter the diff, the higher the score
                max_diff_length = 1000  # Maximum expected diff length
                diff_length = len(diff)
                score = max(0, 1 - (diff_length / max_diff_length))
                print(f"Differences found. Diff length: {diff_length}, Score: {score}")
                print(f"Diff details:\n{diff}")
                return score
        except Exception as e:
            print(f"Error during comparison: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
            
    except Exception as e:
        print(f"Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def normalize_csv_data(csv_path: Path) -> list[list[str]]:
    """
    Normalizes CSV data for comparison.
    Removes whitespace, standardizes number formats, etc.
    """
    normalized_data = []
    try:
        # Try multiple encodings if necessary
        encodings = ['utf-8', 'latin-1', 'cp1252']
        data_read = False
        
        for encoding in encodings:
            try:
                with open(csv_path, 'r', encoding=encoding) as f:
                    reader = csv.reader(f)
                    for row in reader:
                        # Filter out empty rows
                        if any(cell.strip() for cell in row):
                            # Normalize each cell in the row
                            normalized_row = []
                            for cell in row:
                                cell = cell.strip()
                                # If it's a number with commas (e.g. "$1,234.56")
                                if cell and (cell.startswith('$') or cell.startswith('-$')):
                                    # Remove $ and commas, but keep the negative sign if present
                                    is_negative = cell.startswith('-')
                                    clean_cell = cell.replace('$', '').replace(',', '').replace('-', '')
                                    if is_negative:
                                        clean_cell = '-' + clean_cell
                                    normalized_row.append(clean_cell)
                                else:
                                    normalized_row.append(cell)
                            normalized_data.append(normalized_row)
                    data_read = True
                    print(f"Successfully read CSV with {encoding} encoding")
                    break
            except UnicodeDecodeError:
                print(f"Failed to decode with {encoding}, trying next encoding")
                continue
            except Exception as e:
                print(f"Error reading CSV with {encoding}: {str(e)}")
                continue
        
        if not data_read:
            # Last resort: try to read as binary and decode with errors='replace'
            print("Trying binary read with replacement for invalid characters")
            with open(csv_path, 'rb') as f:
                content = f.read()
                text = content.decode('utf-8', errors='replace')
                reader = csv.reader(text.splitlines())
                for row in reader:
                    if any(cell.strip() for cell in row):
                        normalized_row = []
                        for cell in row:
                            cell = cell.strip()
                            if cell and (cell.startswith('$') or cell.startswith('-$')):
                                is_negative = cell.startswith('-')
                                clean_cell = cell.replace('$', '').replace(',', '').replace('-', '')
                                if is_negative:
                                    clean_cell = '-' + clean_cell
                                normalized_row.append(clean_cell)
                            else:
                                normalized_row.append(cell)
                        normalized_data.append(normalized_row)
                print("Successfully read CSV with binary mode and replacement")
    
    except Exception as e:
        print(f"Error normalizing CSV data: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Print the normalized data for debugging
    print(f"Normalized data has {len(normalized_data)} rows")
    if normalized_data:
        print(f"First row: {normalized_data[0]}")
    
    return normalized_data


def compare_csv_data(data1: list[list[str]], data2: list[list[str]]) -> str:
    """
    Compares two normalized CSV datasets and returns a diff string.
    An empty string means the datasets are identical.
    """
    if len(data1) != len(data2):
        return f"Row count mismatch: {len(data1)} vs {len(data2)}"
    
    diff_lines = []
    for i, (row1, row2) in enumerate(zip(data1, data2)):
        if len(row1) != len(row2):
            diff_lines.append(f"Row {i+1}: Column count mismatch: {len(row1)} vs {len(row2)}")
            continue
        
        for j, (cell1, cell2) in enumerate(zip(row1, row2)):
            if cell1 != cell2:
                diff_lines.append(f"Row {i+1}, Col {j+1}: '{cell1}' vs '{cell2}'")
    
    return "\n".join(diff_lines)


@dataclass
class Problem:
    id: str
    statement: str
    solution: Callable[[], Awaitable[int]]


template = f"""
<SYSTEM_CAPABILITY>
* You are utilising an Ubuntu virtual machine using {platform.machine()} architecture without internet access.
* You can feel free to install Ubuntu applications with your bash tool. Use curl instead of wget.
* To open firefox, please just click on the firefox icon.  Note, firefox-esr is what is installed on your system.
* Using bash tool you can start GUI applications, but you need to set export DISPLAY=:1 and use a subshell. For example "(DISPLAY=:1 xterm &)". GUI apps run with bash tool will appear within your desktop environment, but they may take some time to appear. Take a screenshot to confirm it did.
* When using your bash tool with commands that are expected to output very large quantities of text, redirect into a tmp file and use str_replace_editor or `grep -n -B <lines before> -A <lines after> <query> <filename>` to confirm output.
* When viewing a page it can be helpful to zoom out so that you can see everything on the page.  Either that, or make sure you scroll down to see everything before deciding something isn't available.
* When using your computer function calls, they take a while to run and send back to you.  Where possible/feasible, try to chain multiple of these calls all into one function calls request.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* When using Firefox, if a startup wizard appears, IGNORE IT.  Do not even click "skip this step".  Instead, click on the address bar where it says "Search or enter address", and enter the appropriate search term or URL there.
* If the item you are looking at is a pdf, if after taking a single screenshot of the pdf it seems that you want to read the entire document instead of trying to continue to read the pdf from your screenshots + navigation, determine the URL, use curl to download the pdf, install and use pdftotext to convert it to a text file, and then read that text file directly with your StrReplaceEditTool.
</IMPORTANT>

Navigate a browser using computer to
<STATEMENT>
"""

problems = [
    Problem(
        id="libreoffice-hard2",
        statement="""
Given the historical customer account data and currency conversion table, find the minimum COGS in USD after converting to USD using the currency conversion table.
Put your summary table in a tab called ""OUTPUT"" in a file called 'global_customers_summarized.ods'
 Ensure ""Region"" is on A1, and each year (descending) starts on B1 (2024, 2023, 2022, 2021, 2020).
Values should be the minimum USD COGS in the region and year.
 - Put your answer on a tab called ""OUTPUT"" in a file called 'global_customers_summarized.ods in the /home/model directory'
        """,
        solution=verify_output_file,
    )
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
    try:
        await asyncio.sleep(0)

        current_problem = _get_problem(problem_id)

        # Run the entrypoint script to initialize the environment
        try:
            run_entrypoint_script()
        except Exception as e:
            print(f"Error in entrypoint script: {str(e)}")
            # Continue even if entrypoint script fails, don't block the test
        
        return template.replace("<STATEMENT>", current_problem.statement)
    except Exception as e:
        print(f"Error in setup_problem: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return a simple string instead of potentially propagating a binary error
        return f"Error setting up problem {problem_id}: {str(e)}"


# Implementation note: grade_problem will only be called once per enviroment instance
@mcp.tool()
async def grade_problem(
    problem_id: str,
    transcript: str | int = Field(description="The entire transcript produced by the model and its tool calls"),
) -> Grade:
    """Check your solution for grading. Returns a Grade object making sure to include all components that make up the score as subscores."""
    # Note that this is a temporary signature and a more complete reference will be provided.
    try:
        await asyncio.sleep(0)

        current_problem = _get_problem(problem_id)
        
        # Check if output file exists and compare with expected output
        try:
            score = float(await current_problem.solution())  # The answer is collected from the state of the environment
        except Exception as e:
            print(f"Error in solution function: {str(e)}")
            import traceback
            traceback.print_exc()
            score = 0.0  # Default to zero score if there's an error
        
        print(f"Final score for problem {problem_id}: {score}")
        return Grade(subscores={"matched_solution": score}, weights={"matched_solution": 1})
    except Exception as e:
        print(f"Error in grade_problem: {str(e)}")
        import traceback
        traceback.print_exc()
        return Grade(subscores={"matched_solution": 0.0}, weights={"matched_solution": 1})


def run_entrypoint_script():
    """Run the entrypoint.sh script to initialize the environment."""
    try:
        # Run the entrypoint script
        entrypoint_script = Path("/workdir") / "image" / "entrypoint.sh"
        print(f"Running entrypoint script: {entrypoint_script}")
        
        if not entrypoint_script.exists():
            print(f"Warning: Entrypoint script {entrypoint_script} does not exist")
            # Create a mock script for testing purposes
            entrypoint_script.parent.mkdir(exist_ok=True, parents=True)
            with open(entrypoint_script, 'w') as f:
                f.write("#!/bin/bash\necho 'Mock entrypoint script for testing'\n")
            subprocess.run(["chmod", "+x", str(entrypoint_script)])
        
        subprocess.run([str(entrypoint_script)], check=True, env=os.environ.copy())
        
        # Check if input file exists
        input_file = Path("/workdir/image/inputs/global_customers.ods")
        if not input_file.exists():
            print(f"Warning: Input file {input_file} does not exist")
            # Create directory structure for testing
            input_file.parent.mkdir(exist_ok=True, parents=True)
            
            # Don't create a mock file, just report it's missing
            print("Mock input file would be created in a real environment")
        else:
            print(f"Input file {input_file} found")
            
        # Create agent directories
        agent_inputs_dir = Path("/home/model/inputs")
        
        # Use mkdir -p instead of directly creating directories
        subprocess.run(["mkdir", "-p", str(agent_inputs_dir)], check=False)
        print(f"Created agent inputs directory: {agent_inputs_dir}")
        
        # Use cp command instead of directly copying files
        if input_file.exists():
            try:
                subprocess.run(["cp", str(input_file), str(agent_inputs_dir)], check=False)
                print(f"Copied input file to {agent_inputs_dir}")
            except subprocess.SubprocessError as e:
                print(f"Failed to copy input file: {e}")
        
    except subprocess.SubprocessError as e:
        print(f"Failed to run entrypoint script: {e}")
        # Don't raise, just report the error
    except Exception as e:
        print(f"Unexpected error in run_entrypoint_script: {str(e)}")
        import traceback
        traceback.print_exc()
        # Don't raise, just report the error


def main():
    """
    Initialize and run the server as root; you can use files and services that require root permissions
    once init is done, the server will run as the model user to prevent it from accessing problem data
    """
    try:
        # Configure process to handle errors gracefully
        import sys
        import io
        import codecs
        
        # Create a custom stdout wrapper that handles binary data gracefully
        class SafeTextIOWrapper(io.TextIOWrapper):
            def write(self, s):
                try:
                    return super().write(s)
                except UnicodeEncodeError:
                    # Replace any characters that can't be encoded
                    safe_s = str(s).encode(self.encoding, errors='replace').decode(self.encoding)
                    return super().write(safe_s)
        
        # Replace stdout/stderr with safe versions
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = SafeTextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', 
                                          line_buffering=True)
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = SafeTextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace',
                                          line_buffering=True)
        
        # Set default encoding to utf-8 with replace for errors
        if hasattr(codecs, 'register_error'):
            codecs.register_error('strict', codecs.replace_errors)
        
        # Change to working directory
        os.chdir("/workdir")
        
        print("Starting MCP server...")
        
        # Configure MCP with safe encoding settings
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
