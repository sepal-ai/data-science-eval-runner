# Taiga Evaluations - LibreOffice

This directory contains evaluation environments for testing AI agents' ability to use LibreOffice Calc, an open-source spreadsheet application.

## Available Evaluations

The evaluations are arranged in increasing order of difficulty:

1. **libreoffice-easy1**: Create a simple accounts spreadsheet
2. **libreoffice-hard1**: Analyze transaction data and create a summary spreadsheet
3. **libreoffice-hard2**: Process global customer data and create a summarized report

Each evaluation contains:
- Docker environment with LibreOffice Calc
- Problem specification in problems-metadata.json
- Verification scripts to check solution correctness
- Input files and expected output files

## Environment Features

All evaluation environments include:
- X11 with tint2 taskbar for graphical interface
- NoVNC for debugging and visual monitoring
- Screenshot capabilities for the agent
- File comparison tools to verify solutions

## Building and Running

### Prerequisites
- Docker
- Node.js and npm (for running the agent)
- Anthropic API key (for Claude)
- Sepal AI API key (for MCP computer-use capabilities)

### Building and Running the Evaluations

The most straightforward way to build and run an evaluation is to use a single command from the repository root:

```bash
docker build --platform linux/amd64 -t libreoffice_easy1 -f taiga-evals/libreoffice-easy1/Dockerfile . && docker_id=$(docker run -e VERBOSE=1 -d -i libreoffice_easy1 uv --offline --directory /mcp_server run libreoffice_easy1 mcp) && open -a "Firefox" "http://localhost:5555?container_id=$docker_id&problem_id=libreoffice-easy1&max_tokens=64000"
```

This command:
1. Builds the Docker image with the tag `libreoffice_easy1`
2. Runs the container with the MCP server
3. Opens Firefox to the client page with the appropriate parameters

For other evaluations, replace `libreoffice_easy1` with the appropriate evaluation name (e.g., `libreoffice_hard1` or `libreoffice_hard2`) and update the Dockerfile path accordingly.

If you prefer a different browser, replace "Firefox" with your browser of choice, such as "Google Chrome" or "Safari".

### Alternative: Building and Running Separately

#### Building the Docker Image

```bash
docker build --platform linux/amd64 -t libreoffice_easy1 -f taiga-evals/libreoffice-easy1/Dockerfile .
```

#### Running the Evaluation

```bash
docker_id=$(docker run -e VERBOSE=1 -d -i libreoffice_easy1 uv --offline --directory /mcp_server run libreoffice_easy1 mcp)
open -a "Firefox" "http://localhost:5555?container_id=$docker_id&problem_id=libreoffice-easy1&max_tokens=64000"
```

### Using Claude Desktop

Configure Claude Desktop by adding the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "libreoffice_environment": {
      "command": "docker",
      "args": [
        "run",
        "-e",
        "VERBOSE=1",
        "-i",
        "libreoffice_easy1",
        "uv",
        "--offline",
        "--directory",
        "/mcp_server",
        "run",
        "libreoffice_easy1",
        "mcp"
      ]
    }
  }
}
```

Then prompt Claude Desktop with:
```
Use the libreoffice_environment to solve the libreoffice-easy1 problem.
```

### Debugging

You can add VNC capabilities by adding port mapping when running the container:

```bash
docker_id=$(docker run -p 6080:6080 -e WIDTH=1024 -e HEIGHT=768 -e VERBOSE=1 -d -i libreoffice_easy1 uv --offline --directory /mcp_server run libreoffice_easy1 mcp)
```

You can then monitor the agent's progress visually by connecting to the NoVNC server:
1. Access http://localhost:6080/vnc.html in your browser
2. Connect to view the running environment

## Development Loop

1. Make changes to the evaluation code in the `src` directory
2. Mount the source directory when running Docker to test changes without rebuilding:

```bash
docker run -v $PWD/taiga-evals/libreoffice-easy1/src:/mcp_server/taiga-evals/libreoffice-easy1/src -e VERBOSE=1 -p 6080:6080 -d -i libreoffice_easy1 uv --offline --directory /mcp_server run libreoffice_easy1 mcp
```

## Specification

Each evaluation includes a `problems-metadata.json` file that defines:
- Problem ID and description
- Required tools
- Difficulty level
- Output verification criteria

The evaluation code checks solution correctness by comparing the agent's output with expected results. 
