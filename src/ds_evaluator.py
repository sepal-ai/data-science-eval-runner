"""
DSAgentEvaluator for orchestrating the evaluation process and scoring.
"""

import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import docker
import pandas as pd

from data_generator import setup_database_with_mock_data


@dataclass
class Grade:
    """Grade for evaluation results."""

    subscores: Dict[str, float]
    weights: Dict[str, float]
    metadata: Dict[str, Any] = None


@dataclass
class EvaluationConfig:
    """Configuration for evaluation setup."""

    problem_id: str
    timeout_seconds: int = 300
    max_memory_mb: int = 1024
    max_cpu_cores: float = 1.0
    workdir: str = "./workdir"
    database_path: str = "./workdir/data.db"


@dataclass
class EvaluationResult:
    """Result of an agent evaluation."""

    problem_id: str
    success: bool
    score: float
    subscores: Dict[str, float]
    execution_time: float
    error_message: Optional[str] = None
    agent_output: Optional[str] = None
    created_files: List[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class ScoringRubric:
    """Scoring rubric for evaluation."""

    correctness_weight: float = 0.4
    methodology_weight: float = 0.3
    code_quality_weight: float = 0.15
    completeness_weight: float = 0.15

    def __post_init__(self):
        # Ensure weights sum to 1.0
        total = self.correctness_weight + self.methodology_weight + self.code_quality_weight + self.completeness_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Rubric weights must sum to 1.0, got {total}")


class DSAgentEvaluator:
    """
    Orchestrates the evaluation process and scoring for data science agents.

    Key Methods:
    - setup_problem(problem_config) - Initialize evaluation environment
    - evaluate_agent(agent, problem_id) - Run agent on problem and score results
    - score_results(agent_output, ground_truth, rubric) - Apply scoring rubric
    """

    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        self.docker_client = docker_client or docker.from_env()
        self.evaluation_configs: Dict[str, EvaluationConfig] = {}
        self.scoring_rubrics: Dict[str, ScoringRubric] = {}

    def setup_problem(self, problem_config: EvaluationConfig) -> bool:
        """Initialize evaluation environment for a specific problem."""
        try:
            print(f"Setting up problem: {problem_config.problem_id}")

            # Store configuration
            self.evaluation_configs[problem_config.problem_id] = problem_config

            # Create default scoring rubric if not exists
            if problem_config.problem_id not in self.scoring_rubrics:
                self.scoring_rubrics[problem_config.problem_id] = ScoringRubric()

            # Setup mock data for the problem
            setup_database_with_mock_data(problem_config.database_path)

            print(f"Problem {problem_config.problem_id} setup complete")
            return True

        except Exception as e:
            print(f"Failed to setup problem {problem_config.problem_id}: {e}")
            return False

    async def evaluate_agent(self, agent_module: str, problem_id: str) -> EvaluationResult:
        """Run agent on problem and score results."""
        start_time = datetime.now()

        if problem_id not in self.evaluation_configs:
            return EvaluationResult(
                problem_id=problem_id,
                success=False,
                score=0.0,
                subscores={},
                execution_time=0.0,
                error_message=f"Problem {problem_id} not configured",
            )

        config = self.evaluation_configs[problem_id]

        try:
            # Create temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                workdir = Path(temp_dir) / "workdir"
                workdir.mkdir(exist_ok=True)

                # Setup database in working directory
                db_path = workdir / "data.db"
                setup_database_with_mock_data(str(db_path))

                # Run agent locally (Docker support coming later)
                result = await self._run_agent_locally(agent_module, problem_id, workdir, config)

                execution_time = (datetime.now() - start_time).total_seconds()

                if result["success"]:
                    # Score the results
                    score_result = await self._score_agent_results(problem_id, workdir, result["output"])

                    return EvaluationResult(
                        problem_id=problem_id,
                        success=True,
                        score=score_result["total_score"],
                        subscores=score_result["subscores"],
                        execution_time=execution_time,
                        agent_output=result["output"],
                        created_files=self._list_created_files(workdir),
                        metadata=score_result.get("metadata", {}),
                    )
                else:
                    return EvaluationResult(
                        problem_id=problem_id,
                        success=False,
                        score=0.0,
                        subscores={},
                        execution_time=execution_time,
                        error_message=result["error"],
                        agent_output=result.get("output"),
                    )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return EvaluationResult(
                problem_id=problem_id,
                success=False,
                score=0.0,
                subscores={},
                execution_time=execution_time,
                error_message=str(e),
            )

    async def _run_agent_locally(
        self, agent_module: str, problem_id: str, workdir: Path, config: EvaluationConfig
    ) -> Dict[str, Any]:
        """Run agent locally without Docker for testing."""
        try:
            import os
            import subprocess
            import sys
            from pathlib import Path

            # Change to workdir for execution
            original_cwd = os.getcwd()
            os.chdir(workdir)

            # Set up environment
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(original_cwd) / "src")

            try:
                # Run the agent module
                agent_path = Path(original_cwd) / agent_module

                # Import and run the agent
                sys.path.insert(0, str(Path(original_cwd) / "src"))
                sys.path.insert(0, str(Path(original_cwd)))

                # Use the generic DSAgent class for all evaluations
                from ds_agent import DSAgent, RunAgentParams

                # Get problem statement from problem definition
                problem_statement = self._get_problem_statement(problem_id)

                # Create agent with workdir database
                agent = DSAgent(str(workdir / "data.db"))

                # Create params for the agent
                params = RunAgentParams(
                    problem_id=problem_id,
                    problem_statement=problem_statement,
                    database_path=str(workdir / "data.db"),
                    workdir=str(workdir),
                )

                # Run the AI-powered agent
                result = await agent.run_agent(params)

                return {
                    "success": result.get("success", True),
                    "output": result.get("final_response", "Agent completed successfully"),
                    "error": result.get("error"),
                }

            finally:
                # Restore original working directory
                os.chdir(original_cwd)

        except Exception as e:
            return {"success": False, "output": None, "error": f"Local execution failed: {str(e)}"}

    async def _run_agent_in_container(
        self, agent_module: str, problem_id: str, workdir: Path, config: EvaluationConfig
    ) -> Dict[str, Any]:
        """Run agent in Docker container with resource limits."""
        try:
            # Create container with resource limits
            container = self.docker_client.containers.run(
                image="python:3.11-slim",
                command=f"python -m {agent_module}",
                working_dir="/workdir",
                volumes={str(workdir): {"bind": "/workdir", "mode": "rw"}},
                mem_limit=f"{config.max_memory_mb}m",
                cpu_quota=int(config.max_cpu_cores * 100000),
                cpu_period=100000,
                network_mode="none",  # No network access for security
                detach=True,
                remove=True,
            )

            # Wait for completion with timeout
            try:
                exit_code = container.wait(timeout=config.timeout_seconds)
                logs = container.logs().decode("utf-8")

                return {
                    "success": exit_code["StatusCode"] == 0,
                    "output": logs,
                    "error": None if exit_code["StatusCode"] == 0 else f"Exit code: {exit_code['StatusCode']}",
                }

            except Exception as e:
                # Container timed out or failed
                try:
                    container.kill()
                except:
                    pass
                return {"success": False, "output": None, "error": f"Container execution failed: {str(e)}"}

        except Exception as e:
            return {"success": False, "output": None, "error": f"Failed to start container: {str(e)}"}

    async def _score_agent_results(self, problem_id: str, workdir: Path, agent_output: Any) -> Dict[str, Any]:
        """Score agent results using the rubric."""
        rubric = self.scoring_rubrics[problem_id]

        # Initialize subscores
        subscores = {"correctness": 0.0, "methodology": 0.0, "code_quality": 0.0, "completeness": 0.0}

        try:
            # Check for created files and analysis
            created_files = self._list_created_files(workdir)

            # Score correctness (40%)
            subscores["correctness"] = await self._score_correctness(problem_id, workdir, created_files)

            # Score methodology (30%)
            subscores["methodology"] = await self._score_methodology(problem_id, agent_output, created_files)

            # Score code quality (15%)
            subscores["code_quality"] = await self._score_code_quality(workdir, created_files)

            # Score completeness (15%)
            subscores["completeness"] = await self._score_completeness(problem_id, workdir, created_files)

            # Calculate total score
            total_score = (
                subscores["correctness"] * rubric.correctness_weight
                + subscores["methodology"] * rubric.methodology_weight
                + subscores["code_quality"] * rubric.code_quality_weight
                + subscores["completeness"] * rubric.completeness_weight
            )

            return {
                "total_score": total_score,
                "subscores": subscores,
                "metadata": {"created_files": created_files, "rubric_weights": asdict(rubric)},
            }

        except Exception as e:
            print(f"Scoring error: {e}", exc_info=True)
            return {"total_score": 0.0, "subscores": subscores, "metadata": {"error": str(e)}}

    async def _score_correctness(self, problem_id: str, workdir: Path, created_files: List[str]) -> float:
        """Score the correctness of the analysis and results."""
        score = 0.0

        # Load ground truth for comparison
        ground_truth = self._load_ground_truth(problem_id)

        # Check if structured analysis results exist
        analysis_results_file = workdir / "analysis_results.json"
        if analysis_results_file.exists():
            try:
                import json

                with open(analysis_results_file, "r") as f:
                    agent_results = json.load(f)

                # Compare against ground truth
                if ground_truth:
                    accuracy_score = self._compare_results_to_ground_truth(agent_results, ground_truth)
                    score += accuracy_score * 0.7  # 70% weight for accuracy
                else:
                    score += 0.5  # Partial credit if no ground truth available

                # Check if key metrics are present
                required_keys = [
                    "top_customer_total_spent",
                    "top_customer_name",
                    "total_revenue",
                    "total_transactions",
                    "unique_customers",
                    "avg_transaction_value",
                ]
                present_keys = sum(1 for key in required_keys if key in agent_results)
                score += (present_keys / len(required_keys)) * 0.3  # 30% weight for completeness

            except Exception as e:
                print(f"Error loading analysis results: {e}")
                score += 0.2  # Partial credit for file existence
        else:
            # Fallback to old scoring method
            expected_files = self._get_expected_files(problem_id)
            for expected_file in expected_files:
                if expected_file in created_files:
                    score += 0.1

            # Check if analysis file contains expected elements
            analysis_files = [f for f in created_files if f.endswith((".py", ".sql", ".md", ".txt"))]
            if analysis_files:
                score += 0.2

        return min(1.0, score)

    async def _score_methodology(self, problem_id: str, agent_output: Any, created_files: List[str]) -> float:
        """Score the appropriateness of approach and techniques."""
        score = 0.0

        # Convert agent_output to string if it's a list or other type
        if isinstance(agent_output, list):
            agent_output_str = " ".join(str(item) for item in agent_output)
        elif agent_output is None:
            agent_output_str = ""
        else:
            agent_output_str = str(agent_output)

        # Check for appropriate SQL queries
        if "SELECT" in agent_output_str.upper() and "FROM" in agent_output_str.upper():
            score += 0.3

        # Check for data exploration
        if any(keyword in agent_output_str.upper() for keyword in ["DESCRIBE", "COUNT", "GROUP BY", "DISTINCT"]):
            score += 0.3

        # Check for analytical thinking
        if any(keyword in agent_output_str.lower() for keyword in ["analysis", "insight", "pattern", "trend"]):
            score += 0.2

        # Check for appropriate file outputs
        if any(f.endswith(".py") for f in created_files):
            score += 0.2

        return min(1.0, score)

    async def _score_code_quality(self, workdir: Path, created_files: List[str]) -> float:
        """Score readability, efficiency, and best practices."""
        score = 0.0

        python_files = [f for f in created_files if f.endswith(".py")]

        for py_file in python_files:
            try:
                file_path = workdir / py_file
                with open(file_path, "r") as f:
                    content = f.read()

                # Check for comments
                if "#" in content:
                    score += 0.2

                # Check for proper imports
                if "import" in content:
                    score += 0.2

                # Check for reasonable structure
                if "def " in content or "class " in content:
                    score += 0.3

                # Check for basic error handling
                if "try:" in content or "except" in content:
                    score += 0.3

            except Exception:
                continue

        return min(1.0, score)

    async def _score_completeness(self, problem_id: str, workdir: Path, created_files: List[str]) -> float:
        """Score thoroughness of analysis and documentation."""
        score = 0.0

        # Check for multiple file types (code, results, documentation)
        file_types = set()
        for file in created_files:
            if file.endswith(".py"):
                file_types.add("code")
            elif file.endswith((".csv", ".json", ".txt")):
                file_types.add("results")
            elif file.endswith(".md"):
                file_types.add("documentation")

        score += len(file_types) * 0.3

        # Check for comprehensive analysis
        if len(created_files) >= 3:
            score += 0.1

        return min(1.0, score)

    def _get_problem_statement(self, problem_id: str) -> str:
        """Get problem statement from problem definition."""
        try:
            # Load problem definition from YAML file
            import yaml

            problem_file = Path("problems") / f"{problem_id}.yaml"
            if problem_file.exists():
                with open(problem_file, "r") as f:
                    problem_data = yaml.safe_load(f)
                    return problem_data.get("problem_statement", f"Solve the data science problem: {problem_id}")
            else:
                return f"Analyze the data and provide insights for problem: {problem_id}"
        except Exception as e:
            print(f"Error loading problem statement: {e}")
            return f"Analyze the data and provide insights for problem: {problem_id}"

    def _load_ground_truth(self, problem_id: str) -> Optional[Dict[str, Any]]:
        """Load ground truth solutions for a problem."""
        try:
            import yaml

            problem_file = Path("problems") / f"{problem_id}.yaml"
            if problem_file.exists():
                with open(problem_file, "r") as f:
                    problem_data = yaml.safe_load(f)
                    return problem_data.get("ground_truth")
            return None
        except Exception as e:
            print(f"Error loading ground truth: {e}")
            return None

    def _compare_results_to_ground_truth(self, agent_results: Dict[str, Any], ground_truth: Dict[str, Any]) -> float:
        """Compare agent results to ground truth and return accuracy score (0-1)."""
        score = 0.0
        total_checks = 0

        # Define tolerance for numerical comparisons
        tolerance = 0.05  # 5% tolerance

        # Check numerical values
        numerical_keys = [
            ("top_customer_total_spent", "top_customer_total_spent"),
            ("total_revenue", "total_revenue"),
            ("total_transactions", "total_transactions"),
            ("unique_customers", "unique_customers"),
            ("avg_transaction_value", "avg_transaction_value"),
            ("highest_month_sales", "highest_month_sales"),
            ("lowest_month_sales", "lowest_month_sales"),
            ("months_with_data", "months_with_data"),
        ]

        for agent_key, gt_key in numerical_keys:
            if agent_key in agent_results and gt_key in ground_truth:
                total_checks += 1
                agent_val = float(agent_results[agent_key])
                gt_val = float(ground_truth[gt_key])

                # Check if within tolerance
                if abs(agent_val - gt_val) / gt_val <= tolerance:
                    score += 1.0
                elif abs(agent_val - gt_val) / gt_val <= tolerance * 2:
                    score += 0.5  # Partial credit for close values

        # Check string values
        string_keys = [
            ("top_customer_name", "top_customer_name"),
        ]

        for agent_key, gt_key in string_keys:
            if agent_key in agent_results and gt_key in ground_truth:
                total_checks += 1
                if agent_results[agent_key].strip().lower() == ground_truth[gt_key].strip().lower():
                    score += 1.0
                elif (
                    agent_results[agent_key].strip().lower() in ground_truth[gt_key].strip().lower()
                    or ground_truth[gt_key].strip().lower() in agent_results[agent_key].strip().lower()
                ):
                    score += 0.5  # Partial credit for partial matches

        return score / total_checks if total_checks > 0 else 0.0

    def _get_expected_files(self, problem_id: str) -> List[str]:
        """Get list of expected output files for a problem."""
        # This would be configured per problem type
        return ["analysis.py", "results.csv", "report.md"]

    def _validate_results(self, workdir: Path, created_files: List[str]) -> bool:
        """Perform basic validation of results."""
        try:
            # Check if CSV files have reasonable structure
            csv_files = [f for f in created_files if f.endswith(".csv")]
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(workdir / csv_file)
                    if df.empty:
                        return False
                except:
                    return False

            return True
        except:
            return False

    def _list_created_files(self, workdir: Path) -> List[str]:
        """List all files created in the working directory."""
        files = []
        try:
            for item in workdir.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    rel_path = item.relative_to(workdir)
                    files.append(str(rel_path))
        except Exception as e:
            print(f"Error listing files: {e}")

        return files

    def cleanup_problem(self, problem_id: str) -> None:
        """Clean up resources for a problem."""
        if problem_id in self.evaluation_configs:
            config = self.evaluation_configs[problem_id]

            # Clean up database file if it exists
            if os.path.exists(config.database_path):
                try:
                    os.remove(config.database_path)
                except:
                    pass

            # Remove from configurations
            del self.evaluation_configs[problem_id]
            if problem_id in self.scoring_rubrics:
                del self.scoring_rubrics[problem_id]

    def get_evaluation_summary(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate summary statistics from evaluation results."""
        if not results:
            return {}

        successful_results = [r for r in results if r.success]

        summary = {
            "total_evaluations": len(results),
            "successful_evaluations": len(successful_results),
            "success_rate": len(successful_results) / len(results),
            "average_score": sum(r.score for r in successful_results) / len(successful_results)
            if successful_results
            else 0.0,
            "average_execution_time": sum(r.execution_time for r in results) / len(results),
            "score_distribution": {
                "excellent": len([r for r in successful_results if r.score >= 0.9]),
                "good": len([r for r in successful_results if 0.7 <= r.score < 0.9]),
                "satisfactory": len([r for r in successful_results if 0.5 <= r.score < 0.7]),
                "poor": len([r for r in successful_results if r.score < 0.5]),
            },
        }

        return summary
