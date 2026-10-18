"""Unit tests for Sprint 6 FastAPI Service Scaffold & Health Check.

Verifies that the FastAPI application initializes correctly, /health returns
HTTP 200 with valid schema, and non-zero row counts are verified for all core tables.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "db" / "nifty100.db"


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Fixture providing a FastAPI TestClient instance."""
    return TestClient(app)


def test_health_endpoint_status_code_and_schema(client: TestClient) -> None:
    """Verify /health returns HTTP 200 with status=healthy and expected payload fields."""
    response = client.get("/health")
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert (
        data.get("status") == "healthy"
    ), f"Expected status 'healthy', got: {data.get('status')}"
    assert data.get("db_status") == "connected"
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert "db_row_counts" in data
    assert isinstance(data["db_row_counts"], dict)

    # Also verify /api/v1/health alias
    v1_response = client.get("/api/v1/health")
    assert v1_response.status_code == 200
    assert v1_response.json().get("status") == "healthy"


def test_health_endpoint_table_counts(client: TestClient) -> None:
    """Verify that all core tables exist in db_row_counts with positive counts."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    table_counts = data["db_row_counts"]

    # 10 core tables required in specification
    core_tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "sectors",
        "stock_prices",
        "market_cap",
        "financial_ratios",
        "documents",
        "prosandcons",
    ]

    for tbl in core_tables:
        assert (
            tbl in table_counts
        ), f"Table {tbl} missing from db_row_counts: {table_counts.keys()}"
        assert (
            table_counts[tbl] > 0
        ), f"Table {tbl} row count must be positive, got {table_counts[tbl]}"

    # Specific company count check
    assert (
        table_counts["companies"] == 92
    ), f"Expected 92 companies, got {table_counts['companies']}"
