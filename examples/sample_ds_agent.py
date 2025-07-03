#!/usr/bin/env python3
"""
Sample Data Science Agent

This is an example agent that demonstrates how to use the data science tools
to solve analytical problems. It can be used as a template for building
more sophisticated agents.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ds_agent import DSAgent, RunAgentParams


class SampleDSAgent:
    """Sample data science agent that follows a systematic approach."""

    def __init__(self, db_path: str = "./workdir/data.db"):
        self.agent = DSAgent(db_path)

    async def solve_problem(self, problem_statement: str) -> dict:
        """
        Solve a data science problem using a structured approach.

        This demonstrates a typical workflow:
        1. Explore the data
        2. Understand the problem
        3. Perform analysis
        4. Generate outputs
        5. Document findings
        """

        print("Starting data science problem solving...")
        print(f"Problem: {problem_statement}")

        results = {"steps": [], "files_created": []}

        try:
            # Step 1: Explore available data
            print("\n=== Step 1: Data Exploration ===")
            tables_result = await self.agent.list_tables()
            if tables_result.error:
                return {"error": f"Failed to list tables: {tables_result.error}"}

            print("Available tables:")
            print(tables_result.output)
            results["steps"].append("Listed available tables")

            # Step 2: Examine each table
            print("\n=== Step 2: Table Examination ===")
            # Get table names from the output
            if "customers" in tables_result.output:
                customers_desc = await self.agent.describe_table("customers")
                print("Customers table:")
                print(customers_desc.output)
                results["steps"].append("Examined customers table")

            if "transactions" in tables_result.output:
                transactions_desc = await self.agent.describe_table("transactions")
                print("Transactions table:")
                print(transactions_desc.output)
                results["steps"].append("Examined transactions table")

            # Step 3: Perform basic analysis
            print("\n=== Step 3: Basic Analysis ===")

            # Example: Top customers by total amount
            top_customers_query = """
            SELECT 
                c.customer_id,
                c.first_name,
                c.last_name,
                c.email,
                SUM(t.total_amount) as total_spent,
                COUNT(t.transaction_id) as transaction_count
            FROM customers c
            JOIN transactions t ON c.customer_id = t.customer_id
            WHERE t.order_status = 'completed'
            GROUP BY c.customer_id, c.first_name, c.last_name, c.email
            ORDER BY total_spent DESC
            LIMIT 10
            """

            top_customers_result = await self.agent.execute_sql(top_customers_query)
            if not top_customers_result.error:
                print("Top 10 customers by spending:")
                print(top_customers_result.output)
                results["steps"].append("Identified top customers")

            # Step 4: Create analysis script
            print("\n=== Step 4: Creating Analysis Script ===")
            analysis_script = """
import pandas as pd
import duckdb

# Connect to database
conn = duckdb.connect('./workdir/data.db')

# Get top customers
top_customers_query = '''
SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    SUM(t.total_amount) as total_spent,
    COUNT(t.transaction_id) as transaction_count
FROM customers c
JOIN transactions t ON c.customer_id = t.customer_id
WHERE t.order_status = 'completed'
GROUP BY c.customer_id, c.first_name, c.last_name, c.email
ORDER BY total_spent DESC
LIMIT 10
'''

top_customers = conn.execute(top_customers_query).fetchdf()
print("Top 10 Customers by Spending:")
print(top_customers)

# Save to CSV
top_customers.to_csv('./workdir/top_customers.csv', index=False)
print("Results saved to top_customers.csv")

# Monthly sales analysis
monthly_sales_query = '''
SELECT 
    DATE_TRUNC('month', transaction_date) as month,
    SUM(total_amount) as total_sales,
    COUNT(transaction_id) as transaction_count,
    AVG(total_amount) as avg_transaction_value
FROM transactions
WHERE order_status = 'completed'
GROUP BY DATE_TRUNC('month', transaction_date)
ORDER BY month
'''

monthly_sales = conn.execute(monthly_sales_query).fetchdf()
print("\\nMonthly Sales Summary:")
print(monthly_sales)

# Save monthly sales
monthly_sales.to_csv('./workdir/monthly_sales.csv', index=False)
print("Monthly sales saved to monthly_sales.csv")

conn.close()
"""

            script_result = await self.agent.write_file("./workdir/analysis.py", analysis_script)
            if not script_result.error:
                print("Created analysis.py")
                results["files_created"].append("analysis.py")
                results["steps"].append("Created analysis script")

            # Step 5: Create a summary report
            print("\n=== Step 5: Creating Summary Report ===")
            report_content = """
# Data Science Analysis Report

## Problem Statement
Analyze customer transaction data to identify top customers and sales trends.

## Data Overview
- Customers: Demographic and account information
- Transactions: Purchase history with amounts, dates, and status

## Key Findings

### Top Customers Analysis
- Identified top 10 customers by total spending
- Results saved in `top_customers.csv`

### Sales Trends
- Monthly sales aggregation shows trends over time
- Results saved in `monthly_sales.csv`

## Methodology
1. Explored available datasets using SQL queries
2. Performed data aggregation to identify patterns
3. Created reproducible analysis scripts
4. Documented findings and methodology

## Files Generated
- `analysis.py`: Main analysis script
- `top_customers.csv`: Top 10 customers by spending
- `monthly_sales.csv`: Monthly sales summary
- `report.md`: This summary report

## Recommendations
1. Focus retention efforts on top spending customers
2. Analyze monthly trends for seasonal patterns
3. Investigate factors driving customer spending differences
"""

            report_result = await self.agent.write_file("./workdir/report.md", report_content)
            if not report_result.error:
                print("Created report.md")
                results["files_created"].append("report.md")
                results["steps"].append("Created summary report")

            print("\n=== Analysis Complete ===")
            print(f"Steps completed: {len(results['steps'])}")
            print(f"Files created: {results['files_created']}")

            results["success"] = True
            return results

        except Exception as e:
            print(f"Error during analysis: {e}")
            return {"error": str(e), "steps": results["steps"]}

    async def run_with_params(self, params: RunAgentParams) -> dict:
        """Run the agent with specified parameters."""
        return await self.solve_problem(params.problem_statement)


async def main():
    """Main entry point for testing the sample agent."""
    if len(sys.argv) < 2:
        print("Usage: python sample_ds_agent.py 'problem statement'")
        sys.exit(1)

    problem_statement = sys.argv[1]

    # Setup data first
    from data_generator import setup_database_with_mock_data

    print("Setting up mock data...")
    setup_database_with_mock_data()

    # Run the agent
    agent = SampleDSAgent()
    result = await agent.solve_problem(problem_statement)

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Success: {result.get('success', False)}")
    if result.get("error"):
        print(f"Error: {result['error']}")
    if result.get("steps"):
        print(f"Steps completed: {len(result['steps'])}")
        for i, step in enumerate(result["steps"], 1):
            print(f"  {i}. {step}")
    if result.get("files_created"):
        print(f"Files created: {result['files_created']}")


if __name__ == "__main__":
    asyncio.run(main())
