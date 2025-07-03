import asyncio
import os
import sys
from pathlib import Path

import typer

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

app = typer.Typer(help="Data Science Agent Evaluation System")


@app.command()
def generate_csv_data(data_dir: str = typer.Option("data", help="Directory to save CSV files")):
    """Generate and save consistent mock data to CSV files for rubric development."""
    try:
        from data_generator import save_data_to_csv

        save_data_to_csv(data_dir)
        print(f"✅ CSV data generated and saved to {data_dir}/")
        print("💡 This data will be used consistently for all evaluations")
        print("💡 Commit these CSV files to your repo for reproducible rubrics")
    except ImportError as e:
        print(f"Error importing data generator: {e}")
        sys.exit(1)


@app.command()
def setup_data(
    db_path: str = typer.Option("./data.db", help="Database path"),
    use_csv: bool = typer.Option(True, help="Use consistent CSV data if available"),
    data_dir: str = typer.Option("data", help="Directory containing CSV files"),
):
    """Setup mock data for evaluation."""
    try:
        from data_generator import setup_database_with_mock_data

        print(f"Setting up mock data at {db_path}...")
        if use_csv and Path(data_dir).exists():
            print(f"📁 Using consistent data from {data_dir}/")
        else:
            print("🎲 Generating new random data")
            if use_csv:
                print(f"💡 Run 'python -m ds_runner generate-csv-data' to create consistent data")

        setup_database_with_mock_data(db_path, use_csv=use_csv, data_dir=data_dir)
        print("Mock data setup complete!")
    except ImportError as e:
        print(f"Error importing data generator: {e}")
        sys.exit(1)


@app.command()
def eval_agent(
    agent: str = typer.Argument(..., help="Agent module to evaluate"),
    problem: str = typer.Option(None, help="Specific problem ID"),
    suite: str = typer.Option(None, help="Problem suite to run"),
    config: str = typer.Option("config.yaml", help="Configuration file"),
    output: str = typer.Option(None, help="Output file for results"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Evaluate a data science agent."""
    try:
        from cli_runner import main as cli_main

        # Build arguments for CLI runner
        args = ["--agent", agent]
        if problem:
            args.extend(["--problem", problem])
        if suite:
            args.extend(["--suite", suite])
        args.extend(["--config", config])
        if output:
            args.extend(["--output", output])
        if verbose:
            args.append("--verbose")

        # Override sys.argv for the CLI runner
        old_argv = sys.argv
        sys.argv = ["ds-eval"] + args

        try:
            cli_main()
        finally:
            sys.argv = old_argv

    except ImportError as e:
        print(f"Error importing CLI runner: {e}")
        sys.exit(1)


@app.command()
def run_agent(
    problem_id: str = typer.Argument(..., help="Problem ID to solve"),
    problem_statement: str = typer.Argument(..., help="Problem statement"),
    model: str = typer.Option("claude-3-5-sonnet-20241022", help="Claude model to use"),
    max_iterations: int = typer.Option(10, help="Maximum iterations"),
    db_path: str = typer.Option("./data.db", help="Database path"),
):
    """Run a data science agent directly on a problem."""
    try:
        # Setup database first
        from data_generator import setup_database_with_mock_data
        from ds_agent import DSAgent, RunAgentParams

        setup_database_with_mock_data(db_path)

        # Create agent and run
        agent = DSAgent(db_path)
        params = RunAgentParams(
            problem_id=problem_id,
            problem_statement=problem_statement,
            model=model,
            max_iterations=max_iterations,
            database_path=db_path,
        )

        async def run():
            result = await agent.run_agent(params)
            print("\n" + "=" * 60)
            print("AGENT EXECUTION COMPLETE")
            print("=" * 60)
            print(f"Success: {result['success']}")
            print(f"Iterations: {result['iterations']}")
            if result.get("error"):
                print(f"Error: {result['error']}")
            if result.get("final_response"):
                print(f"\nFinal Response:\n{result['final_response']}")

        asyncio.run(run())

    except ImportError as e:
        print(f"Error importing DS agent: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running agent: {e}")
        sys.exit(1)


@app.command()
def list_problems(problems_dir: str = typer.Option("problems", help="Problems directory")):
    """List available evaluation problems."""
    try:
        from cli_runner import load_problem_definitions

        problems = load_problem_definitions(problems_dir)

        if not problems:
            print("No problems found.")
            return

        print(f"Available Problems ({len(problems)}):")
        print("=" * 40)

        for problem_id, problem_data in problems.items():
            title = problem_data.get("title", "No title")
            difficulty = problem_data.get("difficulty", "Unknown")
            category = problem_data.get("category", "Unknown")

            print(f"ID: {problem_id}")
            print(f"  Title: {title}")
            print(f"  Difficulty: {difficulty}")
            print(f"  Category: {category}")
            print()

    except ImportError as e:
        print(f"Error importing CLI runner: {e}")
        sys.exit(1)


@app.command()
def validate_setup():
    """Validate that the DS evaluation system is properly configured."""
    print("Validating Data Science Evaluation Setup...")
    print("=" * 50)

    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version < (3, 11):
        print("❌ Python 3.11+ required")
        return
    else:
        print("✅ Python version OK")

    # Check required imports
    required_modules = ["pandas", "duckdb", "faker", "anthropic", "docker", "yaml", "sklearn", "numpy"]

    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} available")
        except ImportError:
            print(f"❌ {module} missing")

    # Check environment variables
    env_vars = ["ANTHROPIC_API_KEY"]
    for var in env_vars:
        if os.getenv(var):
            print(f"✅ {var} set")
        else:
            print(f"⚠️  {var} not set (required for agent execution)")

    # Check Docker
    try:
        import docker

        client = docker.from_env()
        client.ping()
        print("✅ Docker available")
    except Exception:
        print("❌ Docker not available")

    # Check file structure
    expected_dirs = ["src", "problems", "examples"]
    for dir_name in expected_dirs:
        if Path(dir_name).exists():
            print(f"✅ {dir_name} directory exists")
        else:
            print(f"❌ {dir_name} directory missing")

    print("\nSetup validation complete!")


if __name__ == "__main__":
    app()
