"""Unit tests for Sprint 6 FastAPI Core Endpoints & Analytics (Days 36 & 37).

Verifies:
- /health returns 200 with all 10 table row counts
- /companies returns exactly 92 companies
- /companies/TCS returns correct name and sector
- /companies/INVALID returns 404
- /screener?min_roe=15&max_de=1 returns 10-50 companies (AC-13)
- /screener/presets returns 6 presets
- /sectors returns 11 sectors
- /market/overview returns expected keys
- All 16 endpoints in openapi.json
- Tearsheet FileResponse returns PDF content-type
- Cluster_labels.csv has 89 rows (92 - 3 excluded)
- 5 distinct cluster_labels
- Company cashflow 5Y trend & capital allocation pattern
- Company valuation multiples & DCF implied value
- Peer group full analysis across 20 metrics
"""

from __future__ import annotations

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import REPO_ROOT, app


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
    assert expected_keys.issubset(
        preset_keys
    ), f"Missing presets: {expected_keys - preset_keys}"


def test_sectors_returns_eleven_sectors(client: TestClient) -> None:
    """Verify /sectors returns aggregate statistics across all 11 macro sectors."""
    response = client.get("/sectors")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    sectors = response.json()
    assert isinstance(sectors, list), "Expected list of sectors"
    assert len(sectors) == 11, f"Expected exactly 11 sectors, got {len(sectors)}"

    total_cos = sum(s["company_count"] for s in sectors)
    assert (
        total_cos == 92
    ), f"Expected sum of companies across 11 sectors == 92, got {total_cos}"


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
    assert (
        len(data["top_companies"]) == 3
    ), f"Expected top 3 companies, got {len(data['top_companies'])}"


# ==============================================================================
# SPRINT 6 DAY 37 TESTS: OPENAPI, CLUSTERING & REMAINING ENDPOINTS
# ==============================================================================


def test_all_16_endpoints_in_openapi() -> None:
    """Verify docs/openapi.json contains all 16 core REST API endpoints."""
    openapi_file = REPO_ROOT / "docs" / "openapi.json"
    assert openapi_file.exists(), f"OpenAPI specification not found at {openapi_file}"

    with open(openapi_file, encoding="utf-8") as f:
        spec = json.load(f)

    paths = spec.get("paths", {})
    expected_endpoints = [
        # Group 1: Company Intelligence (5)
        "/api/v1/companies",
        "/api/v1/companies/{ticker}",
        "/api/v1/companies/{ticker}/ratios",
        "/api/v1/companies/{ticker}/financials",
        "/api/v1/companies/{ticker}/peers",
        # Group 2: Screener Engine (3)
        "/api/v1/screener",
        "/api/v1/screener/presets",
        "/api/v1/screener/presets/{preset_name}",
        # Group 3: Market Data & Sectors (3)
        "/api/v1/sectors",
        "/api/v1/sectors/{sector_name}",
        "/api/v1/market/overview",
        # Group 4: Cash Flow & Valuation (2)
        "/api/v1/companies/{ticker}/cashflow",
        "/api/v1/companies/{ticker}/valuation",
        # Group 5: Peers & Reporting (3)
        "/api/v1/peers/{peer_group_name}",
        "/api/v1/reports/tearsheet/{ticker}",
        "/api/v1/reports/sector/{sector_name}",
    ]

    for ep in expected_endpoints:
        assert ep in paths, f"Expected endpoint '{ep}' missing from docs/openapi.json"
    assert (
        len(paths) == 16
    ), f"Expected exactly 16 documented endpoints, got {len(paths)}"


def test_tearsheet_fileresponse_returns_pdf_content_type(client: TestClient) -> None:
    """Verify /api/v1/reports/tearsheet/{ticker} streams PDF file with application/pdf media type."""
    response = client.get("/api/v1/reports/tearsheet/TCS")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    content_type = response.headers.get("content-type", "")
    assert (
        "application/pdf" in content_type
    ), f"Expected application/pdf, got {content_type}"
    assert (
        len(response.content) > 10000
    ), "PDF content is too small to be a valid tearsheet"

    # Also test invalid ticker returns 404
    inv_resp = client.get("/api/v1/reports/tearsheet/INVALID_TICKER")
    assert inv_resp.status_code == 404


def test_cluster_labels_csv_has_89_rows() -> None:
    """Verify cluster_labels.csv has exactly 89 rows (92 constituents minus SBIN, BEL, HAL)."""
    csv_candidates = [
        REPO_ROOT / "data" / "processed" / "cluster_labels.csv",
        REPO_ROOT / "reports" / "cluster_labels.csv",
    ]
    existing_csv = next((p for p in csv_candidates if p.exists()), None)
    assert (
        existing_csv is not None
    ), "cluster_labels.csv not found in data/processed/ or reports/"

    df = pd.read_csv(existing_csv)
    assert len(df) == 89, f"Expected 89 rows in cluster_labels.csv, got {len(df)}"

    # Excluded tickers must not appear
    for ticker in ["SBIN", "BEL", "HAL"]:
        assert (
            ticker not in df["company_id"].values
        ), f"Excluded ticker {ticker} found in cluster_labels.csv"

    # Confirm required columns
    expected_cols = [
        "company_id",
        "cluster_id",
        "cluster_label",
        "roe",
        "opm",
        "revenue_cagr_3yr",
        "debt_to_equity",
        "free_cash_flow_cr",
        "composite_score",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Column '{col}' missing from cluster_labels.csv"


def test_five_distinct_cluster_labels() -> None:
    """Verify KMeans clustering produces exactly 5 distinct, meaningful cluster labels."""
    csv_file = REPO_ROOT / "data" / "processed" / "cluster_labels.csv"
    if not csv_file.exists():
        csv_file = REPO_ROOT / "reports" / "cluster_labels.csv"
    assert csv_file.exists(), f"cluster_labels.csv not found at {csv_file}"

    df = pd.read_csv(csv_file)
    unique_labels = df["cluster_label"].unique()
    assert (
        len(unique_labels) == 5
    ), f"Expected 5 distinct cluster labels, got {len(unique_labels)}: {unique_labels}"

    # Cluster IDs must span 0 to 4
    unique_ids = set(df["cluster_id"].unique())
    assert unique_ids == {
        0,
        1,
        2,
        3,
        4,
    }, f"Expected cluster IDs {0,1,2,3,4}, got {unique_ids}"


def test_company_cashflow_and_valuation_endpoints(client: TestClient) -> None:
    """Verify /cashflow and /valuation analytical endpoints return valid payloads."""
    # Test Cashflow
    cf_resp = client.get("/api/v1/companies/INFY/cashflow")
    assert cf_resp.status_code == 200
    cf_data = cf_resp.json()
    assert cf_data["ticker"] == "INFY"
    assert "capital_allocation_pattern" in cf_data
    assert "cfo_quality_label" in cf_data
    assert len(cf_data["fcf_trend_5yr"]) == 5

    # Test Valuation
    val_resp = client.get("/api/v1/companies/INFY/valuation")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["ticker"] == "INFY"
    assert val_data["pe_ratio"] is not None
    assert (
        val_data["valuation_flag"] is not None and len(val_data["valuation_flag"]) > 0
    )


def test_peers_and_sector_report_endpoints(client: TestClient) -> None:
    """Verify /peers/{peer_group_name} and /reports/sector/{sector_name} endpoints."""
    # Test Peers
    peer_resp = client.get("/api/v1/peers/IT Services")
    assert peer_resp.status_code == 200
    peer_data = peer_resp.json()
    assert peer_data["peer_group_name"] == "IT Services"
    assert peer_data["metrics_count"] == 20
    assert len(peer_data["members"]) > 0

    # Test Sector Report
    sec_resp = client.get("/api/v1/reports/sector/Information_Technology")
    assert sec_resp.status_code == 200
    assert "application/pdf" in sec_resp.headers.get("content-type", "")
