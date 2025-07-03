"""
Mock data generation using Faker for realistic synthetic datasets.
"""

import pandas as pd
import numpy as np
from faker import Faker
from typing import Dict, List, Optional, Any
import random
from datetime import datetime, timedelta
import duckdb
from pathlib import Path


class DataGenerator:
    """Generate realistic synthetic datasets using Faker."""

    def __init__(self, seed: int = 42):
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)
        np.random.seed(seed)

    def generate_customers(self, n: int = 1000) -> pd.DataFrame:
        """Generate customer/user data with demographics and behavior."""
        customers = []

        for _ in range(n):
            customer = {
                "customer_id": self.fake.uuid4(),
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "email": self.fake.email(),
                "phone": self.fake.phone_number(),
                "date_of_birth": self.fake.date_of_birth(minimum_age=18, maximum_age=80),
                "gender": random.choice(["M", "F", "Other"]),
                "address": self.fake.street_address(),
                "city": self.fake.city(),
                "state": self.fake.state(),
                "country": self.fake.country(),
                "postal_code": self.fake.postcode(),
                "registration_date": self.fake.date_between(start_date="-2y", end_date="today"),
                "is_premium": random.choice([True, False]),
                "lifetime_value": round(random.uniform(50, 5000), 2),
                "last_login": self.fake.date_time_between(start_date="-30d", end_date="now"),
                "account_status": random.choice(["active", "inactive", "suspended"]),
            }
            customers.append(customer)

        return pd.DataFrame(customers)

    def generate_sales_transactions(self, n: int = 5000, customer_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """Generate sales/transaction data for e-commerce or financial analysis."""
        transactions = []

        if customer_ids is None:
            customer_ids = [self.fake.uuid4() for _ in range(200)]

        categories = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports", "Food", "Health", "Automotive"]
        payment_methods = ["credit_card", "debit_card", "paypal", "bank_transfer", "cash"]

        for _ in range(n):
            transaction = {
                "transaction_id": self.fake.uuid4(),
                "customer_id": random.choice(customer_ids),
                "transaction_date": self.fake.date_time_between(start_date="-1y", end_date="now"),
                "product_name": self.fake.catch_phrase(),
                "category": random.choice(categories),
                "quantity": random.randint(1, 10),
                "unit_price": round(random.uniform(5, 500), 2),
                "total_amount": 0,  # Will calculate
                "currency": random.choice(["USD", "EUR", "GBP", "CAD"]),
                "payment_method": random.choice(payment_methods),
                "discount_percent": round(random.uniform(0, 20), 2) if random.random() < 0.3 else 0,
                "tax_amount": 0,  # Will calculate
                "shipping_cost": round(random.uniform(0, 25), 2),
                "order_status": random.choice(["completed", "pending", "cancelled", "refunded"]),
            }

            # Calculate derived fields
            subtotal = transaction["quantity"] * transaction["unit_price"]
            discount = subtotal * (transaction["discount_percent"] / 100)
            transaction["tax_amount"] = round((subtotal - discount) * 0.08, 2)  # 8% tax
            transaction["total_amount"] = round(
                subtotal - discount + transaction["tax_amount"] + transaction["shipping_cost"], 2
            )

            transactions.append(transaction)

        return pd.DataFrame(transactions)

    def generate_time_series(self, n: int = 1000, start_date: str = "2023-01-01") -> pd.DataFrame:
        """Generate time series data for metrics or IoT sensors."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        dates = [start + timedelta(hours=i) for i in range(n)]

        # Generate multiple metrics with realistic patterns
        base_temp = 20  # Base temperature
        data = []

        for i, date in enumerate(dates):
            # Simulate daily and seasonal patterns
            daily_cycle = 5 * np.sin(2 * np.pi * i / 24)  # Daily temperature cycle
            seasonal_cycle = 10 * np.sin(2 * np.pi * i / (24 * 365))  # Seasonal cycle
            noise = np.random.normal(0, 2)

            row = {
                "timestamp": date,
                "temperature": round(base_temp + daily_cycle + seasonal_cycle + noise, 2),
                "humidity": round(random.uniform(30, 90), 2),
                "pressure": round(random.uniform(990, 1030), 2),
                "wind_speed": round(random.uniform(0, 25), 2),
                "solar_radiation": max(0, round(1000 * np.sin(2 * np.pi * i / 24) + np.random.normal(0, 100), 2)),
                "energy_consumption": round(random.uniform(50, 200), 2),
                "cpu_usage": round(random.uniform(10, 95), 2),
                "memory_usage": round(random.uniform(20, 85), 2),
                "network_traffic": round(random.uniform(100, 10000), 2),
            }
            data.append(row)

        return pd.DataFrame(data)

    def generate_reviews(self, n: int = 2000, product_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """Generate text data including reviews and comments."""
        reviews = []

        if product_ids is None:
            product_ids = [self.fake.uuid4() for _ in range(50)]

        sentiments = ["positive", "negative", "neutral"]

        for _ in range(n):
            sentiment = random.choice(sentiments)

            # Generate review text based on sentiment
            if sentiment == "positive":
                review_text = " ".join([self.fake.sentence(), "Great product!", self.fake.sentence()])
                rating = random.randint(4, 5)
            elif sentiment == "negative":
                review_text = " ".join([self.fake.sentence(), "Not satisfied with the quality.", self.fake.sentence()])
                rating = random.randint(1, 2)
            else:
                review_text = " ".join([self.fake.sentence(), "It's okay.", self.fake.sentence()])
                rating = 3

            review = {
                "review_id": self.fake.uuid4(),
                "product_id": random.choice(product_ids),
                "customer_id": self.fake.uuid4(),
                "rating": rating,
                "review_title": self.fake.catch_phrase(),
                "review_text": review_text,
                "review_date": self.fake.date_between(start_date="-2y", end_date="today"),
                "helpful_votes": random.randint(0, 100),
                "verified_purchase": random.choice([True, False]),
                "sentiment": sentiment,
                "word_count": len(review_text.split()),
            }
            reviews.append(review)

        return pd.DataFrame(reviews)

    def generate_geospatial_data(self, n: int = 500) -> pd.DataFrame:
        """Generate geospatial data for locations and routes."""
        locations = []

        location_types = ["store", "warehouse", "customer", "supplier", "distribution_center"]

        for _ in range(n):
            location = {
                "location_id": self.fake.uuid4(),
                "name": self.fake.company(),
                "location_type": random.choice(location_types),
                "latitude": float(self.fake.latitude()),
                "longitude": float(self.fake.longitude()),
                "address": self.fake.street_address(),
                "city": self.fake.city(),
                "state": self.fake.state(),
                "country": self.fake.country(),
                "postal_code": self.fake.postcode(),
                "is_active": random.choice([True, False]),
                "capacity": random.randint(100, 10000),
                "operating_hours": f"{random.randint(6, 10)}:00 - {random.randint(18, 22)}:00",
                "established_date": self.fake.date_between(start_date="-10y", end_date="today"),
            }
            locations.append(location)

        return pd.DataFrame(locations)


def setup_database_with_mock_data(db_path: str = "/workdir/data.db") -> None:
    """Set up DuckDB database with generated mock data."""
    generator = DataGenerator()

    # Generate datasets
    print("Generating mock data...")
    customers_df = generator.generate_customers(1000)

    # Extract customer IDs for transactions
    customer_ids = customers_df["customer_id"].tolist()
    transactions_df = generator.generate_sales_transactions(5000, customer_ids[:200])

    time_series_df = generator.generate_time_series(2000)
    reviews_df = generator.generate_reviews(1500)
    locations_df = generator.generate_geospatial_data(300)

    # Create database directory if it doesn't exist
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Connect to DuckDB and create tables
    print(f"Setting up database at {db_path}...")
    conn = duckdb.connect(db_path)

    try:
        # Create tables
        conn.execute("CREATE TABLE IF NOT EXISTS customers AS SELECT * FROM customers_df")
        conn.execute("CREATE TABLE IF NOT EXISTS transactions AS SELECT * FROM transactions_df")
        conn.execute("CREATE TABLE IF NOT EXISTS time_series AS SELECT * FROM time_series_df")
        conn.execute("CREATE TABLE IF NOT EXISTS reviews AS SELECT * FROM reviews_df")
        conn.execute("CREATE TABLE IF NOT EXISTS locations AS SELECT * FROM locations_df")

        # Verify data was loaded
        tables = ["customers", "transactions", "time_series", "reviews", "locations"]
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"Table '{table}': {count} rows")

        print("Database setup complete!")

    finally:
        conn.close()


if __name__ == "__main__":
    # Generate and setup database when run directly
    setup_database_with_mock_data()
