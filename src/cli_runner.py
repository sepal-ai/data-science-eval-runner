#!/usr/bin/env python3
"""
Command Line Interface for Data Science Agent Evaluation System.
"""

import asyncio
import json
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from .ds_evaluator import DSAgentEvaluator, EvaluationConfig, EvaluationResult
from .data_generator import setup_database_with_mock_data


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        if config_path.endswith(".yaml") or config_path.endswith(".yml"):
            return yaml.safe_load(f)
        elif config_path.endswith(".json"):
            return json.load(f)
        else:
            raise ValueError("Configuration file must be .yaml, .yml, or .json")


def load_problem_definitions(problems_dir: str = "problems") -> Dict[str, Dict[str, Any]]:
    """Load problem definitions from problems directory."""
    problems = {}
    problems_path = Path(problems_dir)

    if not problems_path.exists():
        print(f"Problems directory not found: {problems_dir}")
        return problems

    for problem_file in problems_path.glob("*.yaml"):
        try:
            with open(problem_file, "r") as f:
                problem_data = yaml.safe_load(f)
                problem_id = problem_data.get("id", problem_file.stem)
                problems[problem_id] = problem_data
        except Exception as e:
            print(f"Error loading problem {problem_file}: {e}")

    return problems


def print_evaluation_result(result: EvaluationResult) -> None:
    """Print evaluation result in a formatted way."""
    print(f"\n{'=' * 50}")
    print(f"Problem: {result.problem_id}")
    print(f"Success: {result.success}")
    print(f"Score: {result.score:.2f}")
    print(f"Execution Time: {result.execution_time:.2f}s")

    if result.subscores:
        print(f"\nSubscores:")
        for category, score in result.subscores.items():
            print(f"  {category.capitalize()}: {score:.2f}")

    if result.created_files:
        print(f"\nCreated Files:")
        for file in result.created_files:
            print(f"  - {file}")

    if result.error_message:
        print(f"\nError: {result.error_message}")

    print(f"{'=' * 50}")


def print_summary(results: List[EvaluationResult], evaluator: DSAgentEvaluator) -> None:
    """Print evaluation summary."""
    summary = evaluator.get_evaluation_summary(results)

    print(f"\n{'=' * 60}")
    print(f"EVALUATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total Evaluations: {summary.get('total_evaluations', 0)}")
    print(f"Successful: {summary.get('successful_evaluations', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1%}")
    print(f"Average Score: {summary.get('average_score', 0):.2f}")
    print(f"Average Execution Time: {summary.get('average_execution_time', 0):.2f}s")

    distribution = summary.get("score_distribution", {})
    if distribution:
        print(f"\nScore Distribution:")
        print(f"  Excellent (90-100%): {distribution.get('excellent', 0)}")
        print(f"  Good (70-89%): {distribution.get('good', 0)}")
        print(f"  Satisfactory (50-69%): {distribution.get('satisfactory', 0)}")
        print(f"  Poor (0-49%): {distribution.get('poor', 0)}")

    print(f"{'=' * 60}")


async def run_single_evaluation(
    agent_module: str, problem_id: str, problems: Dict[str, Dict[str, Any]], config: Dict[str, Any]
) -> EvaluationResult:
    """Run evaluation on a single problem."""
    evaluator = DSAgentEvaluator()

    # Setup problem configuration
    problem_config = EvaluationConfig(
        problem_id=problem_id,
        timeout_seconds=config.get("timeout_seconds", 300),
        max_memory_mb=config.get("max_memory_mb", 1024),
        max_cpu_cores=config.get("max_cpu_cores", 1.0),
        workdir=config.get("workdir", "/workdir"),
        database_path=config.get("database_path", "/workdir/data.db"),
    )

    # Setup problem
    if not evaluator.setup_problem(problem_config):
        return EvaluationResult(
            problem_id=problem_id,
            success=False,
            score=0.0,
            subscores={},
            execution_time=0.0,
            error_message="Failed to setup problem",
        )

    try:
        # Run evaluation
        result = await evaluator.evaluate_agent(agent_module, problem_id)
        return result
    finally:
        # Cleanup
        evaluator.cleanup_problem(problem_id)


async def run_suite_evaluation(
    agent_module: str, suite_name: str, problems: Dict[str, Dict[str, Any]], config: Dict[str, Any]
) -> List[EvaluationResult]:
    """Run evaluation on a suite of problems."""
    suite_problems = []

    # Get problems for the suite
    if suite_name == "all":
        suite_problems = list(problems.keys())
    elif suite_name in config.get("suites", {}):
        suite_problems = config["suites"][suite_name]
    else:
        # Try to find problems with the suite name as prefix
        suite_problems = [pid for pid in problems.keys() if pid.startswith(suite_name)]

    if not suite_problems:
        print(f"No problems found for suite: {suite_name}")
        return []

    print(f"Running evaluation suite '{suite_name}' with {len(suite_problems)} problems...")

    results = []
    for problem_id in suite_problems:
        if problem_id not in problems:
            print(f"Problem not found: {problem_id}")
            continue

        print(f"\nRunning problem: {problem_id}")
        result = await run_single_evaluation(agent_module, problem_id, problems, config)
        results.append(result)
        print_evaluation_result(result)

    return results


def save_results(results: List[EvaluationResult], output_file: str) -> None:
    """Save evaluation results to file."""
    output_path = Path(output_file)

    # Convert results to serializable format
    results_data = []
    for result in results:
        result_dict = {
            "problem_id": result.problem_id,
            "success": result.success,
            "score": result.score,
            "subscores": result.subscores,
            "execution_time": result.execution_time,
            "error_message": result.error_message,
            "created_files": result.created_files or [],
            "metadata": result.metadata or {},
        }
        results_data.append(result_dict)

    # Save based on file extension
    if output_file.endswith(".json"):
        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2)
    elif output_file.endswith(".csv"):
        import pandas as pd

        # Flatten results for CSV
        flattened = []
        for result in results_data:
            row = {
                "problem_id": result["problem_id"],
                "success": result["success"],
                "score": result["score"],
                "execution_time": result["execution_time"],
                "error_message": result["error_message"],
            }
            # Add subscores as separate columns
            for category, score in result["subscores"].items():
                row[f"subscore_{category}"] = score
            flattened.append(row)

        df = pd.DataFrame(flattened)
        df.to_csv(output_path, index=False)
    else:
        # Default to JSON
        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2)

    print(f"Results saved to: {output_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Data Science Agent Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single problem
  python eval_runner.py --agent my_agent.py --problem sales_analysis_001

  # Run full suite
  python eval_runner.py --agent my_agent.py --suite standard_suite

  # Custom configuration
  python eval_runner.py --agent my_agent.py --config custom_config.yaml

  # Save results
  python eval_runner.py --agent my_agent.py --suite all --output results.json
        """,
    )

    parser.add_argument("--agent", required=True, help="Agent implementation module (e.g., my_agent.py)")

    parser.add_argument("--problem", help="Specific problem ID to evaluate")

    parser.add_argument("--suite", help="Problem suite to evaluate (e.g., standard_suite, all)")

    parser.add_argument("--config", default="config.yaml", help="Configuration file (YAML or JSON)")

    parser.add_argument("--problems-dir", default="problems", help="Directory containing problem definitions")

    parser.add_argument("--output", help="Output file for results (JSON or CSV)")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument("--setup-only", action="store_true", help="Only setup database and exit")

    args = parser.parse_args()

    # Validate arguments
    if not args.problem and not args.suite:
        parser.error("Must specify either --problem or --suite")

    if args.problem and args.suite:
        parser.error("Cannot specify both --problem and --suite")

    # Load configuration
    try:
        if os.path.exists(args.config):
            config = load_config(args.config)
        else:
            print(f"Configuration file not found: {args.config}, using defaults")
            config = {}
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Setup database only mode
    if args.setup_only:
        print("Setting up database...")
        setup_database_with_mock_data()
        print("Database setup complete!")
        return

    # Load problem definitions
    problems = load_problem_definitions(args.problems_dir)

    if not problems:
        print("No problems found. Use --setup-only to generate sample data.")
        sys.exit(1)

    # Run evaluation
    try:
        if args.problem:
            # Single problem evaluation
            if args.problem not in problems:
                print(f"Problem not found: {args.problem}")
                sys.exit(1)

            result = asyncio.run(run_single_evaluation(args.agent, args.problem, problems, config))
            results = [result]
            print_evaluation_result(result)

        else:
            # Suite evaluation
            results = asyncio.run(run_suite_evaluation(args.agent, args.suite, problems, config))

        # Print summary
        if len(results) > 1:
            evaluator = DSAgentEvaluator()
            print_summary(results, evaluator)

        # Save results if requested
        if args.output:
            save_results(results, args.output)

    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Evaluation failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
