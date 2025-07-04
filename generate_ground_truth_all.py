#!/usr/bin/env python3
"""
Generate ground truth solutions for all evaluation problems.
"""

import json
import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import duckdb

from data_generator import setup_database_with_mock_data


def generate_customer_segmentation_ground_truth(conn):
    """Generate ground truth solutions for customer_segmentation_002."""

    print("Generating Customer Segmentation ground truth...")

    # Calculate RFM metrics
    rfm_query = """
    WITH customer_metrics AS (
        SELECT 
            c.customer_id,
            c.first_name,
            c.last_name,
            DATE_DIFF('year', c.date_of_birth::DATE, CURRENT_DATE) as age,
            c.gender,
            c.is_premium,
            c.lifetime_value,
            -- Recency: Days since last purchase
            DATE_DIFF('day', MAX(t.transaction_date::DATE), CURRENT_DATE) as recency_days,
            -- Frequency: Number of completed transactions
            COUNT(t.transaction_id) as frequency,
            -- Monetary: Total amount spent
            ROUND(SUM(t.total_amount), 2) as monetary
        FROM customers c
        LEFT JOIN transactions t ON c.customer_id = t.customer_id
        WHERE t.order_status = 'completed'
        GROUP BY c.customer_id, c.first_name, c.last_name, c.date_of_birth, c.gender, c.is_premium, c.lifetime_value
    ),
    rfm_scores AS (
        SELECT *,
            -- RFM Scoring (1-5 scale)
            CASE 
                WHEN recency_days <= 30 THEN 5
                WHEN recency_days <= 60 THEN 4
                WHEN recency_days <= 90 THEN 3
                WHEN recency_days <= 180 THEN 2
                ELSE 1
            END as recency_score,
            CASE 
                WHEN frequency >= 10 THEN 5
                WHEN frequency >= 7 THEN 4
                WHEN frequency >= 5 THEN 3
                WHEN frequency >= 3 THEN 2
                ELSE 1
            END as frequency_score,
            CASE 
                WHEN monetary >= 15000 THEN 5
                WHEN monetary >= 10000 THEN 4
                WHEN monetary >= 5000 THEN 3
                WHEN monetary >= 2000 THEN 2
                ELSE 1
            END as monetary_score
        FROM customer_metrics
    ),
    customer_segments AS (
        SELECT *,
            -- Simple segment classification based on RFM scores
            CASE 
                WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'Champions'
                WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'Loyal Customers'
                WHEN recency_score >= 4 AND frequency_score <= 2 THEN 'New Customers'
                WHEN recency_score <= 2 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'At Risk'
                WHEN recency_score <= 2 AND frequency_score <= 2 THEN 'Lost Customers'
                ELSE 'Potential Loyalists'
            END as segment
        FROM rfm_scores
    )
    SELECT * FROM customer_segments
    ORDER BY monetary DESC
    """

    segments_df = conn.execute(rfm_query).fetchdf()

    # Calculate segment statistics
    segment_stats = (
        segments_df.groupby("segment")
        .agg({"customer_id": "count", "monetary": ["mean", "sum"], "frequency": "mean", "recency_days": "mean"})
        .round(2)
    )

    # Flatten column names
    segment_stats.columns = ["customer_count", "avg_monetary", "total_monetary", "avg_frequency", "avg_recency"]
    segment_stats = segment_stats.reset_index()

    # Key metrics
    total_customers = len(segments_df)
    avg_rfm_score = (
        segments_df["recency_score"] + segments_df["frequency_score"] + segments_df["monetary_score"]
    ).mean() / 3

    ground_truth = {
        "total_customers_analyzed": int(total_customers),
        "number_of_segments": int(segments_df["segment"].nunique()),
        "largest_segment": str(segment_stats.loc[segment_stats["customer_count"].idxmax(), "segment"]),
        "largest_segment_size": int(segment_stats["customer_count"].max()),
        "highest_value_segment": str(segment_stats.loc[segment_stats["avg_monetary"].idxmax(), "segment"]),
        "highest_value_segment_avg": float(segment_stats["avg_monetary"].max()),
        "champions_count": int(segments_df[segments_df["segment"] == "Champions"].shape[0]),
        "lost_customers_count": int(segments_df[segments_df["segment"] == "Lost Customers"].shape[0]),
        "avg_rfm_score": float(round(avg_rfm_score, 2)),
        "segments_summary": [
            {
                "segment": str(row["segment"]),
                "customer_count": int(row["customer_count"]),
                "avg_monetary": float(row["avg_monetary"]),
                "total_monetary": float(row["total_monetary"]),
                "avg_frequency": float(row["avg_frequency"]),
                "avg_recency": float(row["avg_recency"]),
            }
            for _, row in segment_stats.iterrows()
        ],
    }

    return ground_truth


def generate_time_series_ground_truth(conn):
    """Generate ground truth solutions for time_series_forecast_003."""

    print("Generating Time Series Forecasting ground truth...")

    # Generate daily sales data
    daily_sales_query = """
    SELECT 
        transaction_date::DATE as date,
        ROUND(SUM(total_amount), 2) as daily_sales,
        COUNT(transaction_id) as transaction_count
    FROM transactions
    WHERE order_status = 'completed'
    GROUP BY transaction_date::DATE
    ORDER BY date
    """

    daily_sales_df = conn.execute(daily_sales_query).fetchdf()

    # Convert to pandas datetime
    daily_sales_df["date"] = pd.to_datetime(daily_sales_df["date"])
    daily_sales_df = daily_sales_df.set_index("date").sort_index()

    # Fill missing dates with 0 sales
    date_range = pd.date_range(start=daily_sales_df.index.min(), end=daily_sales_df.index.max(), freq="D")
    daily_sales_df = daily_sales_df.reindex(date_range, fill_value=0)

    # Calculate key time series metrics
    total_sales = daily_sales_df["daily_sales"].sum()
    avg_daily_sales = daily_sales_df["daily_sales"].mean()
    max_daily_sales = daily_sales_df["daily_sales"].max()
    min_daily_sales = daily_sales_df["daily_sales"].min()
    days_with_sales = (daily_sales_df["daily_sales"] > 0).sum()
    total_days = len(daily_sales_df)

    # Find best and worst sales days
    best_sales_date = daily_sales_df["daily_sales"].idxmax()
    worst_sales_date = daily_sales_df["daily_sales"].idxmin()

    # Calculate trend (simple linear trend)
    daily_sales_df["day_number"] = range(len(daily_sales_df))
    correlation = daily_sales_df["daily_sales"].corr(daily_sales_df["day_number"])
    trend_direction = "increasing" if correlation > 0.1 else "decreasing" if correlation < -0.1 else "stable"

    # Day of week analysis
    daily_sales_df["day_of_week"] = daily_sales_df.index.day_name()
    dow_avg = daily_sales_df.groupby("day_of_week")["daily_sales"].mean().sort_values(ascending=False)
    best_day_of_week = dow_avg.index[0]
    worst_day_of_week = dow_avg.index[-1]

    # Monthly analysis
    daily_sales_df["month"] = daily_sales_df.index.to_period("M")
    monthly_avg = daily_sales_df.groupby("month")["daily_sales"].mean()
    best_month = str(monthly_avg.idxmax())
    worst_month = str(monthly_avg.idxmin())

    # Simple forecast metrics (using last 7 days average as baseline)
    last_7_days_avg = daily_sales_df["daily_sales"].tail(7).mean()
    last_30_days_avg = daily_sales_df["daily_sales"].tail(30).mean()

    # Volatility (coefficient of variation)
    volatility = daily_sales_df["daily_sales"].std() / daily_sales_df["daily_sales"].mean()

    ground_truth = {
        "total_days_analyzed": int(total_days),
        "days_with_sales": int(days_with_sales),
        "total_sales": float(round(total_sales, 2)),
        "avg_daily_sales": float(round(avg_daily_sales, 2)),
        "max_daily_sales": float(round(max_daily_sales, 2)),
        "min_daily_sales": float(round(min_daily_sales, 2)),
        "best_sales_date": str(best_sales_date.strftime("%Y-%m-%d")),
        "best_sales_amount": float(round(daily_sales_df.loc[best_sales_date, "daily_sales"], 2)),
        "worst_sales_date": str(worst_sales_date.strftime("%Y-%m-%d")),
        "worst_sales_amount": float(round(daily_sales_df.loc[worst_sales_date, "daily_sales"], 2)),
        "trend_direction": str(trend_direction),
        "trend_correlation": float(round(correlation, 3)),
        "best_day_of_week": str(best_day_of_week),
        "best_day_avg_sales": float(round(dow_avg.iloc[0], 2)),
        "worst_day_of_week": str(worst_day_of_week),
        "worst_day_avg_sales": float(round(dow_avg.iloc[-1], 2)),
        "best_month": str(best_month),
        "worst_month": str(worst_month),
        "volatility_coefficient": float(round(volatility, 3)),
        "last_7_days_avg": float(round(last_7_days_avg, 2)),
        "last_30_days_avg": float(round(last_30_days_avg, 2)),
        "forecast_baseline": float(round(last_7_days_avg, 2)),  # Simple forecast baseline
    }

    return ground_truth


def main():
    """Generate ground truth solutions for all problems."""

    # Setup database with consistent data
    db_path = "./ground_truth.db"
    setup_database_with_mock_data(db_path)

    # Connect to database
    conn = duckdb.connect(db_path)

    print("=== GENERATING GROUND TRUTH FOR ALL PROBLEMS ===")

    # Generate Customer Segmentation ground truth
    segmentation_gt = generate_customer_segmentation_ground_truth(conn)

    print(f"\n📊 CUSTOMER SEGMENTATION RESULTS:")
    print(f"   - Total Customers: {segmentation_gt['total_customers_analyzed']}")
    print(f"   - Number of Segments: {segmentation_gt['number_of_segments']}")
    print(
        f"   - Largest Segment: {segmentation_gt['largest_segment']} ({segmentation_gt['largest_segment_size']} customers)"
    )
    print(
        f"   - Highest Value Segment: {segmentation_gt['highest_value_segment']} (${segmentation_gt['highest_value_segment_avg']:.2f} avg)"
    )
    print(f"   - Champions: {segmentation_gt['champions_count']} customers")
    print(f"   - Lost Customers: {segmentation_gt['lost_customers_count']} customers")

    # Generate Time Series ground truth
    ts_gt = generate_time_series_ground_truth(conn)

    print(f"\n📈 TIME SERIES RESULTS:")
    print(f"   - Total Days Analyzed: {ts_gt['total_days_analyzed']}")
    print(f"   - Average Daily Sales: ${ts_gt['avg_daily_sales']:.2f}")
    print(f"   - Max Daily Sales: ${ts_gt['max_daily_sales']:.2f} on {ts_gt['best_sales_date']}")
    print(f"   - Trend: {ts_gt['trend_direction']} (correlation: {ts_gt['trend_correlation']})")
    print(f"   - Best Day of Week: {ts_gt['best_day_of_week']} (${ts_gt['best_day_avg_sales']:.2f})")
    print(f"   - Volatility: {ts_gt['volatility_coefficient']:.3f}")

    conn.close()

    # Save ground truth to problem files
    problems_dir = Path("problems")

    # Update customer segmentation problem
    segmentation_file = problems_dir / "customer_segmentation_002.yaml"
    if segmentation_file.exists():
        import yaml

        with open(segmentation_file, "r") as f:
            segmentation_problem = yaml.safe_load(f)

        segmentation_problem["ground_truth"] = segmentation_gt

        with open(segmentation_file, "w") as f:
            yaml.dump(segmentation_problem, f, default_flow_style=False, sort_keys=False)

        print(f"\n✅ Updated {segmentation_file} with ground truth")

    # Update time series problem
    ts_file = problems_dir / "time_series_forecast_003.yaml"
    if ts_file.exists():
        import yaml

        with open(ts_file, "r") as f:
            ts_problem = yaml.safe_load(f)

        ts_problem["ground_truth"] = ts_gt

        with open(ts_file, "w") as f:
            yaml.dump(ts_problem, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Updated {ts_file} with ground truth")

    # Also save individual JSON files for reference
    with open(problems_dir / "customer_segmentation_002_ground_truth.json", "w") as f:
        json.dump(segmentation_gt, f, indent=2)

    with open(problems_dir / "time_series_forecast_003_ground_truth.json", "w") as f:
        json.dump(ts_gt, f, indent=2)

    print(f"\n🎯 Ground truth generated for all problems!")
    print(f"   - Customer Segmentation: {len(segmentation_gt)} metrics")
    print(f"   - Time Series Forecasting: {len(ts_gt)} metrics")


if __name__ == "__main__":
    main()
