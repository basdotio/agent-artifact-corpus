---
name: testing-patterns
description: pytest fixtures and integration testing patterns for Spark applications, including DataFrame assertions and mock data generation.
triggers:
  - pytest
  - unit testing
  - integration testing
  - spark testing
  - test fixtures
category: testing
---

# Testing Patterns Skill

## Overview

Comprehensive testing patterns for Databricks and Spark applications using pytest, fixtures, and assertion utilities. This skill provides reusable patterns for unit testing transformations, integration testing pipelines, and mocking Spark components.

**Key Benefits:**
- Reusable test fixtures for Spark
- DataFrame assertion utilities
- Mock data generation patterns
- Integration test strategies
- CI/CD test automation
- Coverage tracking

## When to Use This Skill

Use testing patterns when you need to:
- Unit test data transformations
- Validate pipeline logic before deployment
- Set up regression testing
- Create test data for development
- Implement CI/CD quality gates
- Debug transformation logic
- Document expected behavior

## Core Concepts

### 1. Pytest Configuration

**conftest.py Setup:**
```python
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Create shared Spark session for all tests."""
    return (
        SparkSession.builder
        .master("local[2]")
        .appName("pytest-spark")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )


@pytest.fixture
def sample_customers(spark):
    """Generate sample customer data."""
    return spark.createDataFrame([
        ("C1", "Alice", "alice@example.com", 100.0),
        ("C2", "Bob", "bob@example.com", 200.0),
        ("C3", "Charlie", "charlie@example.com", 300.0)
    ], ["customer_id", "name", "email", "lifetime_value"])
```

### 2. DataFrame Assertions

**Custom Assertion Helpers:**
```python
from pyspark.sql import DataFrame
from typing import List, Set


def assert_schema_match(df: DataFrame, expected_columns: List[str]):
    """Assert DataFrame has expected schema."""
    actual_columns = df.columns
    assert set(actual_columns) == set(expected_columns), \\
        f"Schema mismatch: got {actual_columns}, expected {expected_columns}"


def assert_no_nulls(df: DataFrame, columns: List[str]):
    """Assert specified columns have no null values."""
    for col in columns:
        null_count = df.filter(df[col].isNull()).count()
        assert null_count == 0, f"Column '{col}' has {null_count} null values"


def assert_unique(df: DataFrame, key_columns: List[str]):
    """Assert key columns form unique keys."""
    total_count = df.count()
    unique_count = df.select(key_columns).distinct().count()
    assert total_count == unique_count, \\
        f"Duplicate keys found: {total_count - unique_count} duplicates"
```

### 3. Mock Data Generation

**Test Data Builders:**
```python
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from datetime import datetime, timedelta
import random


class TestDataBuilder:
    """Build realistic test data."""

    def __init__(self, spark: SparkSession):
        self.spark = spark

    def generate_orders(self, count: int = 100):
        """Generate sample order data."""
        schema = StructType([
            StructField("order_id", StringType(), False),
            StructField("customer_id", StringType(), False),
            StructField("order_date", TimestampType(), False),
            StructField("amount", DoubleType(), False),
            StructField("status", StringType(), False)
        ])

        data = [
            (
                f"O{i:05d}",
                f"C{random.randint(1, 50):03d}",
                datetime.now() - timedelta(days=random.randint(0, 365)),
                round(random.uniform(10.0, 1000.0), 2),
                random.choice(["pending", "completed", "cancelled"])
            )
            for i in range(count)
        ]

        return self.spark.createDataFrame(data, schema)
```

### 4. Integration Testing

**End-to-End Pipeline Tests:**
```python
import pytest
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import RunResultState


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for complete pipeline."""

    @pytest.fixture
    def workspace_client(self):
        """Create Databricks workspace client."""
        return WorkspaceClient()

    def test_bronze_to_silver_pipeline(
        self,
        spark,
        workspace_client,
        tmp_path
    ):
        """Test bronze to silver transformation."""
        # Arrange: Create test data
        bronze_data = spark.createDataFrame([
            ("1", "test@example.com", "100"),
            ("2", "invalid_email", "200"),
            ("3", None, "300")
        ], ["id", "email", "amount"])

        bronze_path = str(tmp_path / "bronze")
        bronze_data.write.format("delta").save(bronze_path)

        # Act: Run transformation
        silver_df = transform_bronze_to_silver(
            spark.read.format("delta").load(bronze_path)
        )

        # Assert: Verify results
        assert silver_df.count() == 2  # Invalid record dropped
        assert_no_nulls(silver_df, ["id", "email"])
        assert_schema_match(
            silver_df,
            ["id", "email", "amount", "validated_at"]
        )
```

## Implementation Patterns

### Pattern 1: Unit Testing Transformations

**Test Data Transformations:**
```python
"""
Unit tests for order transformations.
"""
import pytest
from pyspark.sql.functions import col, when, lit
from datetime import datetime


def enrich_orders(df):
    """Add calculated fields to orders."""
    return df.withColumn(
        "discount_amount",
        when(col("amount") > 100, col("amount") * 0.1).otherwise(lit(0.0))
    ).withColumn(
        "enriched_at",
        lit(datetime.now())
    )


class TestOrderTransformations:
    """Test order transformation logic."""

    def test_enrich_orders_adds_discount(self, spark):
        """Test discount calculation logic."""
        # Arrange
        input_df = spark.createDataFrame([
            ("O1", 150.0),
            ("O2", 50.0)
        ], ["order_id", "amount"])

        # Act
        result = enrich_orders(input_df)

        # Assert
        assert "discount_amount" in result.columns
        high_order = result.filter(col("order_id") == "O1").first()
        low_order = result.filter(col("order_id") == "O2").first()

        assert high_order["discount_amount"] == 15.0
        assert low_order["discount_amount"] == 0.0

    def test_enrich_orders_adds_timestamp(self, spark):
        """Test timestamp addition."""
        input_df = spark.createDataFrame([
            ("O1", 100.0)
        ], ["order_id", "amount"])

        result = enrich_orders(input_df)

        assert "enriched_at" in result.columns
        assert result.first()["enriched_at"] is not None

    def test_enrich_orders_preserves_original_columns(self, spark):
        """Test original columns are preserved."""
        input_df = spark.createDataFrame([
            ("O1", 100.0)
        ], ["order_id", "amount"])

        result = enrich_orders(input_df)

        assert set(input_df.columns).issubset(set(result.columns))
```

### Pattern 2: Parameterized Testing

**Test Multiple Scenarios:**
```python
import pytest


@pytest.mark.parametrize("amount,expected_discount", [
    (50.0, 0.0),    # Below threshold
    (100.0, 0.0),   # At threshold
    (150.0, 15.0),  # Above threshold
    (1000.0, 100.0) # High value
])
def test_discount_calculation(spark, amount, expected_discount):
    """Test discount calculation with various amounts."""
    df = spark.createDataFrame([
        ("O1", amount)
    ], ["order_id", "amount"])

    result = enrich_orders(df)

    actual_discount = result.first()["discount_amount"]
    assert actual_discount == expected_discount


@pytest.mark.parametrize("email,expected_valid", [
    ("user@example.com", True),
    ("invalid_email", False),
    ("", False),
    (None, False)
])
def test_email_validation(spark, email, expected_valid):
    """Test email validation logic."""
    df = spark.createDataFrame([
        ("C1", email)
    ], ["customer_id", "email"])

    result = validate_customer_data(df)

    is_valid = result.filter(col("customer_id") == "C1").count() > 0
    assert is_valid == expected_valid
```

### Pattern 3: Fixture Factories

**Reusable Test Data Factories:**
```python
"""
Test data factories for common entities.
"""
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any


@pytest.fixture
def customer_factory(spark):
    """Factory for generating customer test data."""
    def _create_customers(
        count: int = 10,
        status: str = "active",
        **overrides
    ):
        base_data = [
            {
                "customer_id": f"C{i:05d}",
                "name": f"Customer {i}",
                "email": f"customer{i}@example.com",
                "status": status,
                "created_at": datetime.now() - timedelta(days=i),
                **overrides
            }
            for i in range(count)
        ]
        return spark.createDataFrame(base_data)

    return _create_customers


@pytest.fixture
def order_factory(spark):
    """Factory for generating order test data."""
    def _create_orders(
        customer_ids: List[str],
        orders_per_customer: int = 5
    ):
        data = []
        order_num = 0
        for customer_id in customer_ids:
            for i in range(orders_per_customer):
                data.append({
                    "order_id": f"O{order_num:06d}",
                    "customer_id": customer_id,
                    "amount": 100.0 * (i + 1),
                    "order_date": datetime.now() - timedelta(days=i)
                })
                order_num += 1
        return spark.createDataFrame(data)

    return _create_orders


# Usage in tests
def test_customer_aggregation(customer_factory, order_factory):
    """Test customer order aggregation."""
    customers = customer_factory(count=3)
    customer_ids = [row["customer_id"] for row in customers.collect()]
    orders = order_factory(customer_ids, orders_per_customer=5)

    result = aggregate_customer_orders(customers, orders)

    assert result.count() == 3
    assert "total_orders" in result.columns
    assert "total_amount" in result.columns
```

### Pattern 4: DLT Pipeline Testing

**Test DLT Functions:**
```python
"""
Test DLT pipeline functions.
"""
import pytest
from unittest.mock import Mock, patch


def test_dlt_bronze_ingestion(spark, tmp_path):
    """Test bronze layer ingestion logic."""
    # Mock DLT read_stream
    with patch('dlt.read_stream') as mock_read:
        # Create test data
        test_data = spark.createDataFrame([
            ("1", "data1"),
            ("2", "data2")
        ], ["id", "value"])

        mock_read.return_value = test_data

        # Import and test the transformation function
        from pipelines.bronze import transform_raw_data

        result = transform_raw_data()

        assert "ingested_at" in result.columns
        assert result.count() == 2


def test_dlt_expectations_logic(spark):
    """Test data quality logic without DLT decorators."""
    # Extract core transformation logic
    def apply_quality_rules(df):
        """Core quality logic from DLT pipeline."""
        return df.filter(
            (col("customer_id").isNotNull()) &
            (col("amount") > 0)
        )

    # Test data with violations
    test_data = spark.createDataFrame([
        ("C1", 100.0),   # Valid
        (None, 200.0),   # Null customer_id
        ("C2", -50.0),   # Negative amount
        ("C3", 150.0)    # Valid
    ], ["customer_id", "amount"])

    result = apply_quality_rules(test_data)

    assert result.count() == 2  # Only valid records
```

### Pattern 5: Performance Testing

**Test Performance Characteristics:**
```python
"""
Performance tests for transformations.
"""
import pytest
import time


@pytest.mark.performance
def test_large_dataset_performance(spark):
    """Test transformation performance with large dataset."""
    # Generate large test dataset
    large_df = spark.range(0, 1000000).toDF("id")
    large_df = large_df.withColumn("value", col("id") * 2)

    # Measure transformation time
    start_time = time.time()

    result = complex_transformation(large_df)
    result.write.format("noop").mode("overwrite").save()

    duration = time.time() - start_time

    # Assert performance requirements
    assert duration < 60, f"Transformation took {duration}s, expected < 60s"
    assert result.count() == 1000000


@pytest.mark.performance
def test_join_performance(spark, customer_factory, order_factory):
    """Test join performance with realistic data volumes."""
    customers = customer_factory(count=10000)
    customer_ids = [row["customer_id"] for row in customers.limit(1000).collect()]
    orders = order_factory(customer_ids, orders_per_customer=100)

    start_time = time.time()

    result = customers.join(orders, "customer_id", "inner")
    result.write.format("noop").mode("overwrite").save()

    duration = time.time() - start_time

    assert duration < 30, f"Join took {duration}s, expected < 30s"
```

## Best Practices

### 1. Test Organization

```
tests/
├── unit/
│   ├── conftest.py
│   ├── test_transformations.py
│   ├── test_validators.py
│   └── test_aggregations.py
├── integration/
│   ├── conftest.py
│   ├── test_pipeline_end_to_end.py
│   └── test_dlt_integration.py
├── fixtures/
│   ├── sample_data.py
│   └── mock_services.py
└── performance/
    └── test_performance.py
```

### 2. Naming Conventions

- Test files: `test_*.py`
- Test functions: `test_<what_is_tested>`
- Fixtures: descriptive nouns (e.g., `customer_data`, `spark_session`)
- Test classes: `Test<Component>` (e.g., `TestOrderTransformations`)

### 3. Test Independence

```python
# Good: Each test is independent
def test_transformation_a(spark):
    df = spark.createDataFrame([...])
    result = transform_a(df)
    assert result.count() == expected

def test_transformation_b(spark):
    df = spark.createDataFrame([...])  # Fresh data
    result = transform_b(df)
    assert result.count() == expected


# Bad: Tests depend on shared state
shared_df = None

def test_transformation_a(spark):
    global shared_df
    shared_df = transform_a(spark.createDataFrame([...]))

def test_transformation_b():
    result = transform_b(shared_df)  # Depends on test_a
```

### 4. Assertion Quality

```python
# Good: Specific assertions
def test_discount_calculation(spark):
    result = calculate_discount(order_df)
    assert result.filter(col("amount") > 100).select("discount").first()[0] == 10.0

# Bad: Weak assertions
def test_discount_calculation(spark):
    result = calculate_discount(order_df)
    assert result is not None  # Too generic
    assert result.count() > 0  # Doesn't test logic
```

### 5. Mock External Dependencies

```python
from unittest.mock import patch, Mock


def test_external_api_call(spark):
    """Test transformation that calls external API."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {"rate": 1.2}
        mock_get.return_value = mock_response

        result = enrich_with_exchange_rate(order_df)

        mock_get.assert_called_once()
        assert "exchange_rate" in result.columns
```

## Common Pitfalls to Avoid

Don't:
- Test framework code (e.g., testing that Spark works)
- Write tests that depend on execution order
- Use production data in tests
- Skip cleanup of test resources
- Mix unit and integration tests

Do:
- Test business logic and transformations
- Make tests independent and idempotent
- Generate synthetic test data
- Clean up temporary resources
- Separate test types (unit, integration, performance)

## Complete Examples

See `/examples/` directory for:
- `test_transformation_pipeline.py`: Complete unit test suite
- `test_integration_workflow.py`: End-to-end integration tests

## Related Skills

- `delta-live-tables`: Testing DLT pipelines
- `data-quality`: Quality validation testing
- `cicd-workflows`: Automated test execution
- `medallion-architecture`: Layer-specific testing

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [PySpark Testing Best Practices](https://docs.databricks.com/dev-tools/pytest.html)
- [Databricks Testing Guide](https://docs.databricks.com/dev-tools/testing.html)
