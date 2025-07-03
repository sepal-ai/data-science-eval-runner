Data Science Agent Evaluation System Design
Overview
This document outlines the design for a comprehensive evaluation system for data science agents, focusing on their ability to perform analytical tasks in a controlled environment.
System Architecture
Core Components
1. DSAgent Class
The main agent interface with restricted action space for data science tasks.
Action Space:

write_file(path, content) - Write code/analysis files - use existing function in codebase
list_tables() - Discover available datasets
describe_table(table_name) - Get schema and basic stats
read_table(table_name, limit=None) - Sample or read full table
execute_sql(query) - Run SQL queries on datasets

2. DSAgentEvaluator Class
Orchestrates the evaluation process and scoring.
Key Methods:

setup_problem(problem_config) - Initialize evaluation environment
evaluate_agent(agent, problem_id) - Run agent on problem and score results
score_results(agent_output, ground_truth, rubric) - Apply scoring rubric

Responsibilities:

Problem environment setup
Agent execution monitoring
Result validation and scoring
Cleanup and teardown

3. Docker Environment
Containerized execution environment for consistent and secure evaluation.
Configuration:

Base image with Python, DuckDB, and common data science libraries
Restricted filesystem access (only /workdir writable)
Network isolation for security
Resource limits (CPU, memory, time)

Data Infrastructure
Mock Data Generation
Use Faker library for realistic synthetic datasets.
Dataset Types:

Customer/user data (demographics, behavior)
Sales/transaction data (e-commerce, financial)
Time series data (metrics, IoT sensors)
Text data (reviews, comments, documents)
Geospatial data (locations, routes)

Database Environment
DuckDB as the primary database engine for evaluation.
Benefits:

Lightweight and fast
SQL-compatible
Supports various data formats (CSV, Parquet, JSON)
Databricks Delta Lake compatibility
Easy to embed and reset

Setup:
sql-- Example table creation
CREATE TABLE customers AS SELECT * FROM 'customers.parquet';
CREATE TABLE orders AS SELECT * FROM 'orders.csv';
CREATE TABLE products AS SELECT * FROM 'products.json';
Evaluation Framework
Problem Types
1. One-off Tasks (V1 Focus)
Single-turn problems with clear objectives and measurable outcomes.
Examples:

Exploratory data analysis
Statistical hypothesis testing
Data cleaning and preprocessing
Feature engineering
Basic machine learning model training
Report generation

2. Multi-turn Tasks (Future)
Complex, interactive problems requiring multiple steps and iterations.
Examples:

Full ML pipeline development
A/B test design and analysis
Business intelligence dashboard creation
Data pipeline optimization

Scoring System
Rubric Categories

Correctness (40%) - Accuracy of analysis and results
Methodology (30%) - Appropriateness of approach and techniques
Code Quality (15%) - Readability, efficiency, best practices
Completeness (15%) - Thoroughness of analysis and documentation

Scoring Levels

Excellent (90-100%) - Exceeds expectations, production-ready
Good (70-89%) - Meets requirements with minor issues
Satisfactory (50-69%) - Adequate but needs improvement
Poor (0-49%) - Significant issues or incomplete

Command Line Interface
Basic Usage
bash# Run evaluation on specific problem
python eval_runner.py --agent my_agent.py --problem sales_analysis_001

# Run full evaluation suite
python eval_runner.py --agent my_agent.py --suite standard_suite

# Custom configuration
python eval_runner.py --agent my_agent.py --config custom_config.yaml
Configuration Options

Agent implementation file/class
Problem set selection
Timeout settings
Resource limits
Output format (JSON, CSV, HTML report)
Logging verbosity

Implementation Plan
Phase 1: Core Infrastructure

Set up Docker environment with DuckDB and Python
Implement DSAgent base class and action space
Create DSAgentEvaluator with basic scoring
Build CLI interface for single evaluations

Phase 2: Data Generation

Implement Faker-based mock data generators
Create diverse dataset templates
Build database seeding functionality
Add data validation and quality checks

Phase 3: Evaluation Problems

Define standard problem set (10-15 problems)
Create rubrics and ground truth solutions
Implement automated scoring for common metrics
Add manual review capability for subjective elements

Phase 4: Advanced Features

Multi-turn conversation support
Subjective query evaluation with LLM judges
Performance benchmarking and comparison
Results visualization and reporting

Technical Specifications
Dependencies

Python 3.9+
Docker 20.10+
DuckDB 0.8+
Faker 18.0+
Pandas, NumPy, SciPy
Matplotlib
Scikit-learn
Jupyter (for result inspection)

File Structure
ds_eval_system/
├── src/
│   ├── agent/
│   │   ├── base.py          # DSAgent base class
│   │   └── actions.py       # Action implementations
│   ├── evaluator/
│   │   ├── core.py          # DSAgentEvaluator
│   │   ├── scoring.py       # Scoring logic
│   │   └── rubrics.py       # Evaluation rubrics
│   ├── data/
│   │   ├── generators.py    # Mock data generation
│   │   └── seeding.py       # Database setup
│   └── cli/
│       └── runner.py        # Command line interface
├── problems/
│   ├── problem_001.yaml     # Problem definitions
│   └── ...
├── docker/
│   └── Dockerfile           # Evaluation environment
├── tests/
└── examples/