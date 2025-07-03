# Data Science Agent Evaluation System

A comprehensive evaluation framework for data science agents, featuring a restricted action space for analytical tasks, mock data generation, and automated scoring.

## Overview

This system evaluates data science agents on their ability to:
- Explore and understand datasets
- Perform SQL-based data analysis
- Generate insights and visualizations
- Create well-documented code and reports
- Solve real-world analytical problems

## System Architecture

### Core Components

1. **DSAgent** - Main agent interface with restricted action space:
   - `write_file(path, content)` - Write code/analysis files
   - `list_tables()` - Discover available datasets
   - `describe_table(table_name)` - Get schema and basic stats
   - `read_table(table_name, limit=None)` - Sample or read full table
   - `execute_sql(query)` - Run SQL queries on datasets

2. **DSAgentEvaluator** - Orchestrates evaluation and scoring:
   - Problem environment setup
   - Agent execution monitoring
   - Automated scoring with rubrics
   - Result validation and cleanup

3. **Mock Data Generator** - Creates realistic synthetic datasets:
   - Customer/user data with demographics
   - Sales/transaction data for e-commerce analysis
   - Time series data with patterns
   - Text data (reviews, comments)
   - Geospatial location data

4. **Docker Environment** - Containerized execution for security and consistency

## Quick Start

### Prerequisites

- Python 3.11+
- Docker
- Anthropic API key for Claude

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd data-science-eval-runner

# Install dependencies
pip install -e .

# Validate setup
python -m taiga validate-setup
```

### Set Environment Variables

```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

### Basic Usage

1. **Setup mock data:**
```bash
python -m taiga setup-data
```

2. **List available problems:**
```bash
python -m taiga list-problems
```

3. **Run a sample agent:**
```bash
python -m taiga run-agent "sales_analysis_001" "Analyze customer sales data to identify top customers and trends"
```

4. **Evaluate an agent:**
```bash
python -m taiga eval-agent examples.sample_ds_agent --problem sales_analysis_001 --output results.json
```

## Evaluation Problems

### Available Problem Types

1. **sales_analysis_001** (Easy)
   - Exploratory data analysis
   - Customer transaction analysis
   - Sales trend identification

2. **customer_segmentation_002** (Medium)
   - RFM analysis
   - Clustering algorithms
   - Customer behavior segmentation

3. **time_series_forecast_003** (Hard)
   - Time series modeling
   - Sales forecasting
   - Trend and seasonality analysis

### Problem Definition Format

Problems are defined in YAML files in the `problems/` directory:

```yaml
id: sales_analysis_001
title: "Customer Sales Analysis"
description: "Analyze customer transaction data to identify top customers and sales trends"
difficulty: "easy"
category: "exploratory_data_analysis"

problem_statement: |
  Your task is to:
  1. Explore the available datasets
  2. Identify the top 10 customers by total purchase amount
  3. Analyze monthly sales trends
  4. Create a summary report

expected_files:
  - "analysis.py"
  - "top_customers.csv" 
  - "monthly_sales.csv"
  - "report.md"

scoring:
  correctness: 0.4
  methodology: 0.3
  code_quality: 0.15
  completeness: 0.15
```

## Command Line Interface

### Main Commands

```bash
# Setup and validation
python -m taiga validate-setup          # Validate system setup
python -m taiga setup-data              # Generate mock data
python -m taiga list-problems            # List available problems

# Agent execution
python -m taiga run-agent PROBLEM_ID "PROBLEM_STATEMENT"    # Run agent directly
python -m taiga eval-agent AGENT --problem PROBLEM_ID       # Evaluate agent
python -m taiga eval-agent AGENT --suite SUITE_NAME         # Run problem suite

# MCP server
python -m taiga ds-mcp                   # Start DS agent MCP server
```

### Evaluation Options

```bash
# Single problem evaluation
python -m taiga eval-agent my_agent --problem sales_analysis_001

# Problem suite evaluation  
python -m taiga eval-agent my_agent --suite standard

# Custom configuration
python -m taiga eval-agent my_agent --config custom_config.yaml

# Save results
python -m taiga eval-agent my_agent --suite all --output results.json

# Verbose output
python -m taiga eval-agent my_agent --problem sales_analysis_001 --verbose
```

## Building Custom Agents

### Basic Agent Structure

```python
import asyncio
from src.ds_agent import DSAgent, RunAgentParams

class MyDSAgent:
    def __init__(self, db_path="/workdir/data.db"):
        self.agent = DSAgent(db_path)
    
    async def solve_problem(self, problem_statement: str):
        # 1. Explore data
        tables = await self.agent.list_tables()
        
        # 2. Analyze specific tables
        customers = await self.agent.describe_table("customers")
        
        # 3. Run SQL queries
        query = "SELECT COUNT(*) FROM customers"
        result = await self.agent.execute_sql(query)
        
        # 4. Write analysis files
        code = "# Analysis code here"
        await self.agent.write_file("analysis.py", code)
        
        return {"success": True}
```

### Agent with Claude Integration

```python
from src.ds_agent import DSAgent, RunAgentParams

# Create agent with conversation loop
agent = DSAgent()

# Run with Claude integration
params = RunAgentParams(
    problem_id="sales_analysis_001",
    problem_statement="Analyze sales data...",
    model="claude-3-5-sonnet-20241022",
    max_iterations=10
)

result = await agent.run_agent(params)
```

## Scoring System

### Rubric Categories

- **Correctness (40%)** - Accuracy of analysis and results
- **Methodology (30%)** - Appropriateness of approach and techniques  
- **Code Quality (15%)** - Readability, efficiency, best practices
- **Completeness (15%)** - Thoroughness of analysis and documentation

### Scoring Levels

- **Excellent (90-100%)** - Exceeds expectations, production-ready
- **Good (70-89%)** - Meets requirements with minor issues
- **Satisfactory (50-69%)** - Adequate but needs improvement  
- **Poor (0-49%)** - Significant issues or incomplete

## Configuration

### config.yaml

```yaml
# Evaluation settings
timeout_seconds: 600
max_memory_mb: 2048
max_cpu_cores: 2.0

# Agent settings  
model: "claude-3-5-sonnet-20241022"
max_iterations: 15
max_tokens: 8192

# Problem suites
suites:
  basic: ["sales_analysis_001"]
  standard: ["sales_analysis_001", "customer_segmentation_002"]
  advanced: ["sales_analysis_001", "customer_segmentation_002", "time_series_forecast_003"]

# Scoring rubric
scoring:
  correctness_weight: 0.4
  methodology_weight: 0.3  
  code_quality_weight: 0.15
  completeness_weight: 0.15
```

## Docker Usage

### Build and Run

```bash
# Build the evaluation environment
docker build -t ds-eval .

# Run with data volume
docker run -v $(pwd)/data:/workdir/data ds-eval

# Interactive mode
docker run -it ds-eval /bin/bash

# Run specific evaluation
docker run -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY ds-eval \
  python -m taiga eval-agent examples.sample_ds_agent --problem sales_analysis_001
```

## Mock Data

The system generates realistic synthetic datasets including:

- **Customers** (1,000 records) - Demographics, registration info, account status
- **Transactions** (5,000 records) - Purchase history, amounts, payment methods
- **Time Series** (2,000 points) - Metrics with daily/seasonal patterns
- **Reviews** (1,500 records) - Product reviews with sentiment
- **Locations** (300 records) - Geospatial data for stores/warehouses

### Database Schema

```sql
-- Customers table
CREATE TABLE customers (
    customer_id VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR,
    registration_date DATE,
    lifetime_value DECIMAL,
    -- ... more columns
);

-- Transactions table  
CREATE TABLE transactions (
    transaction_id VARCHAR,
    customer_id VARCHAR,
    transaction_date TIMESTAMP,
    total_amount DECIMAL,
    order_status VARCHAR,
    -- ... more columns
);
```

## Development

### Project Structure

```
├── src/
│   ├── ds_agent.py          # Core agent with conversation loop
│   ├── data_generator.py    # Mock data generation
│   ├── ds_evaluator.py      # Evaluation orchestration
│   └── cli_runner.py        # Command line interface
├── problems/                # Problem definitions
├── examples/                # Sample agents
├── taiga/                   # Original MCP functionality
├── config.yaml             # Default configuration
├── Dockerfile              # Evaluation environment
└── README.md               # This file
```

### Adding New Problems

1. Create a YAML file in `problems/`:

```yaml
id: my_new_problem
title: "My Analysis Problem"
description: "Solve this analytical challenge"
difficulty: "medium"
category: "data_analysis"

problem_statement: |
  Your analytical task here...

expected_files:
  - "solution.py"
  - "results.csv"
```

2. Add to a problem suite in `config.yaml`

3. Test with an agent:

```bash
python -m taiga eval-agent examples.sample_ds_agent --problem my_new_problem
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Examples

See the `examples/` directory for:
- `sample_ds_agent.py` - Basic agent demonstrating the tool usage
- Advanced agent patterns and techniques
- Problem-specific solution approaches

## Support

For issues and questions:
1. Check the GitHub issues
2. Review the example agents
3. Validate your setup with `python -m taiga validate-setup`

## License

[Your license here]
