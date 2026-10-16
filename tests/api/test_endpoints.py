"""Unit tests for Sprint 6 FastAPI Core Endpoints (Day 36).

Verifies Groups 1-3 REST endpoints:
- /health returns 200 with all 10 table row counts
- /companies returns exactly 92 companies
- /companies/TCS returns correct name and sector
- /companies/INVALID returns 404
- /screener?min_roe=15&max_de=1 returns 10-50 companies (AC-13)
- /screener/presets returns 6 presets
- /sectors returns 11 sectors
- /market/overview returns expected keys
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Fixture providing a FastAPI TestClient."""
    return TestClient(app)


def test_health_returns_200_with_all_tables(client: TestClient) -> None:
    """Verify /health returns HTTP 200 with status=healthy and all 10 table row counts."""
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data.get("status") == "healthy"
    counts = data.get("db_row_counts", {})

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
        assert tbl in counts, f"Table {tbl} missing from db_row_counts"
        assert counts[tbl] > 0, f"Table {tbl} row count is {counts[tbl]}, expected > 0"


def test_companies_returns_exactly_92(client: TestClient) -> None:
    """Verify /companies returns a list of exactly 92 companies."""
    response = client.get("/companies")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    companies = response.json()
    assert isinstance(companies, list), "Expected list response"
    assert len(companies) == 92, f"Expected 92 companies, got {len(companies)}"

    # Also verify /api/v1/companies alias
    v1_resp = client.get("/api/v1/companies")
    assert v1_resp.status_code == 200
    assert len(v1_resp.json()) == 92


def test_companies_tcs_returns_correct_name_and_sector(client: TestClient) -> None:
    """Verify /companies/TCS returns correct company name and sector."""
    response = client.get("/companies/TCS")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["id"] == "TCS"
    assert "Tata Consultancy Services" in data["company_name"]
    assert data["sector"] == "Information Technology"
    assert "latest_ratios" in data
    assert isinstance(data["latest_ratios"], dict)


def test_companies_invalid_returns_404(client: TestClient) -> None:
    """Verify requesting an invalid/non-existent ticker returns HTTP 404."""
    response = client.get("/companies/INVALID")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_screener_ac13_roe15_de1_returns_10_to_50_companies(client: TestClient) -> None:
    """AC-13: Verify /screener?min_roe=15&max_de=1 returns between 10 and 50 companies."""
    response = client.get("/screener?min_roe=15&max_de=1")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    results = response.json()
    assert isinstance(results, list), "Expected list of matching companies"
    count = len(results)
    assert 10 <= count <= 50, f"AC-13 violation: Expected 10-50 companies, got {count}"

    # Verify every returned company satisfies the criteria
    for co in results:
        assert co["roe"] >= 15.0, f"{co['company_id']} has ROE {co['roe']} < 15.0"
        assert co["de"] <= 1.0, f"{co['company_id']} has D/E {co['de']} > 1.0"


def test_screener_presets_returns_six_presets(client: TestClient) -> None:
    """Verify /screener/presets returns all 6 predefined institutional presets."""
    response = client.get("/screener/presets")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    presets = response.json()
    assert isinstance(presets, list), "Expected list of presets"
    assert len(presets) == 6, f"Expected exactly 6 presets, got {len(presets)}"

    preset_keys = {p["preset_key"] for p in presets}
    expected_keys = {
        "quality_compounder",
        "value_pick",
        "dividend_aristocrat",
        "growth_rocket",
        "asset_light_champion",
        "financial_health",
    }
    assert expected_keys.issubset(preset_keys), f"Missing presets: {expected_keys - preset_keys}"


def test_sectors_returns_eleven_sectors(client: TestClient) -> None:
    """Verify /sectors returns aggregate statistics across all 11 macro sectors."""
    response = client.get("/sectors")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    sectors = response.json()
    assert isinstance(sectors, list), "Expected list of sectors"
    assert len(sectors) == 11, f"Expected exactly 11 sectors, got {len(sectors)}"

    total_cos = sum(s["company_count"] for s in sectors)
    assert total_cos == 92, f"Expected sum of companies across 11 sectors == 92, got {total_cos}"


def test_market_overview_returns_expected_keys(client: TestClient) -> None:
    """Verify /market/overview returns expected universe KPI benchmarks."""
    response = client.get("/market/overview")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    required_keys = [
        "total_companies",
        "avg_roe",
        "median_pe",
        "count_positive_fcf",
        "count_low_leverage",
        "top_companies",
    ]
    for key in required_keys:
        assert key in data, f"Key '{key}' missing from /market/overview payload"

    assert data["total_companies"] == 92
    assert len(data["top_companies"]) == 3, f"Expected top 3 companies, got {len(data['top_companies'])}"
