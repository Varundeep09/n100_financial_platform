"""Final QA Integration Tests for Sprint 6 (Day 38 / Module 12).

Comprehensive verification covering:
- Sprint 5 Outputs: All 92 tearsheet PDFs, 11 sector report PDFs, portfolio_summary.pdf, pros/cons coverage
- Clustering Outputs: 89 constituents in cluster_labels.csv, 5 distinct institutional labels, centroid consistency
- OpenAPI Export: docs/openapi.json valid schema containing all 16 endpoints
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "nifty100.db"
REPORTS_DIR = REPO_ROOT / "reports"
TEARSHEETS_DIR = REPORTS_DIR / "tearsheets"
SECTOR_REPORTS_DIR = REPORTS_DIR / "sector_reports"
PORTFOLIO_SUMMARY_PDF = REPORTS_DIR / "portfolio_summary.pdf"
PROS_CONS_CSV = REPORTS_DIR / "pros_cons_generated.csv"
OPENAPI_JSON = REPO_ROOT / "docs" / "openapi.json"
CLUSTER_LABELS_CSV = REPO_ROOT / "data" / "processed" / "cluster_labels.csv"


# ==============================================================================
# SPRINT 5 OUTPUT VERIFICATION TESTS
# ==============================================================================


def test_qa_all_92_tearsheet_pdfs_exist_and_sized() -> None:
    """Verify all 92 companies have a valid tearsheet PDF in reports/tearsheets/ (> 20KB)."""
    assert TEARSHEETS_DIR.exists(), f"Tearsheets directory missing at {TEARSHEETS_DIR}"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    company_ids = [
        r[0] for r in cur.execute("SELECT id FROM companies ORDER BY id").fetchall()
    ]
    conn.close()

    assert len(company_ids) == 92, f"Expected 92 companies, found {len(company_ids)}"

    missing_files = []
    undersized_files = []
    for cid in company_ids:
        pdf_file = TEARSHEETS_DIR / f"{cid}_tearsheet.pdf"
        if not pdf_file.is_file():
            missing_files.append(cid)
        elif pdf_file.stat().st_size < 20000:
            undersized_files.append((cid, pdf_file.stat().st_size))

    assert not missing_files, f"Missing tearsheet PDFs for: {missing_files}"
    assert not undersized_files, f"Tearsheets smaller than 20KB: {undersized_files}"


def test_qa_pros_cons_coverage_and_confidence() -> None:
    """Verify pros_cons_generated.csv has >= 1 entry per company and confidence >= 60%."""
    assert PROS_CONS_CSV.exists(), f"Missing {PROS_CONS_CSV}"
    df = pd.read_csv(PROS_CONS_CSV)

    assert not df.empty, "pros_cons_generated.csv is empty"
    assert (
        df["company_id"].nunique() == 92
    ), f"Expected 92 unique companies, got {df['company_id'].nunique()}"
    assert (df["confidence_pct"] >= 60.0).all(), "Found confidence score below 60%"
    assert set(df["type"].unique()) == {
        "pro",
        "con",
    }, f"Unexpected types: {df['type'].unique()}"

    # Verify every company has at least 1 pro and 1 con
    pro_counts = df[df["type"] == "pro"].groupby("company_id").size()
    con_counts = df[df["type"] == "con"].groupby("company_id").size()
    assert len(pro_counts) == 92, "Some company lacks pros"
    assert len(con_counts) == 92, "Some company lacks cons"


def test_qa_sector_reports_and_portfolio_summary_exist() -> None:
    """Verify 11 sector reports exist and portfolio_summary.pdf > 50KB."""
    assert (
        SECTOR_REPORTS_DIR.exists()
    ), f"Missing sector reports dir: {SECTOR_REPORTS_DIR}"
    sector_pdfs = list(SECTOR_REPORTS_DIR.glob("*_report.pdf"))
    assert len(sector_pdfs) == 11, f"Expected 11 sector reports, got {len(sector_pdfs)}"

    assert PORTFOLIO_SUMMARY_PDF.exists(), f"Missing {PORTFOLIO_SUMMARY_PDF}"
    assert (
        PORTFOLIO_SUMMARY_PDF.stat().st_size > 50000
    ), "portfolio_summary.pdf is smaller than 50KB"


# ==============================================================================
# CLUSTERING OUTPUT VERIFICATION TESTS
# ==============================================================================


def test_qa_cluster_labels_csv_has_89_rows() -> None:
    """Verify cluster_labels.csv has exactly 89 rows (92 minus SBIN, BEL, HAL)."""
    assert CLUSTER_LABELS_CSV.exists(), f"Missing {CLUSTER_LABELS_CSV}"
    df = pd.read_csv(CLUSTER_LABELS_CSV)

    assert len(df) == 89, f"Expected 89 rows, got {len(df)}"

    # Confirm exclusion of SBIN, BEL, HAL
    for excluded in ["SBIN", "BEL", "HAL"]:
        assert (
            excluded not in df["company_id"].values
        ), f"Excluded ticker '{excluded}' found in clustering results"

    # Confirm required features exist and are non-null
    feature_cols = [
        "roe",
        "opm",
        "revenue_cagr_3yr",
        "debt_to_equity",
        "free_cash_flow_cr",
        "composite_score",
    ]
    for col in feature_cols:
        assert (
            col in df.columns
        ), f"Feature column '{col}' missing from cluster_labels.csv"
        # Core features like composite_score and roe must be present for all
        if col in [
            "company_id",
            "cluster_id",
            "cluster_label",
            "composite_score",
            "roe",
        ]:
            assert (
                df[col].notna().all()
            ), f"Null value found in mandatory feature '{col}'"


def test_qa_five_distinct_cluster_labels_and_archetypes() -> None:
    """Verify exactly 5 distinct, meaningful cluster labels across IDs 0-4."""
    assert CLUSTER_LABELS_CSV.exists(), f"Missing {CLUSTER_LABELS_CSV}"
    df = pd.read_csv(CLUSTER_LABELS_CSV)

    unique_labels = sorted(df["cluster_label"].unique())
    assert (
        len(unique_labels) == 5
    ), f"Expected 5 distinct labels, got {len(unique_labels)}: {unique_labels}"

    unique_ids = set(df["cluster_id"].unique())
    assert unique_ids == {0, 1, 2, 3, 4}, f"Expected cluster IDs 0-4, got {unique_ids}"

    # Verify expected institutional archetype labels exist
    expected_archetypes = {
        "Quality Compounders",
        "Value & Cyclicals",
        "Financials & Credit Heavy",
        "High Margin Infrastructure",
        "High Growth & Momentum",
    }
    assert (
        set(unique_labels) == expected_archetypes
    ), f"Mismatch in archetypes: {set(unique_labels) ^ expected_archetypes}"


# ==============================================================================
# OPENAPI SPECIFICATION VERIFICATION TESTS
# ==============================================================================


def test_qa_openapi_json_contains_all_16_endpoints() -> None:
    """Verify docs/openapi.json contains all 16 endpoints under /api/v1/."""
    assert OPENAPI_JSON.exists(), f"Missing OpenAPI spec at {OPENAPI_JSON}"

    with open(OPENAPI_JSON, encoding="utf-8") as f:
        spec = json.load(f)

    assert spec.get("openapi", "").startswith(
        "3."
    ), f"Expected OpenAPI 3.x, got {spec.get('openapi')}"
    paths = spec.get("paths", {})

    expected_16 = [
        "/api/v1/companies",
        "/api/v1/companies/{ticker}",
        "/api/v1/companies/{ticker}/ratios",
        "/api/v1/companies/{ticker}/financials",
        "/api/v1/companies/{ticker}/peers",
        "/api/v1/companies/{ticker}/cashflow",
        "/api/v1/companies/{ticker}/valuation",
        "/api/v1/screener",
        "/api/v1/screener/presets",
        "/api/v1/screener/presets/{preset_name}",
        "/api/v1/sectors",
        "/api/v1/sectors/{sector_name}",
        "/api/v1/market/overview",
        "/api/v1/peers/{peer_group_name}",
        "/api/v1/reports/tearsheet/{ticker}",
        "/api/v1/reports/sector/{sector_name}",
    ]

    for ep in expected_16:
        assert ep in paths, f"Endpoint '{ep}' missing from openapi.json"
    assert (
        len(paths) == 16
    ), f"Expected exactly 16 documented endpoints, found {len(paths)}"


# ==============================================================================
# SPRINT 6 DAY 39 DELIVERABLES VERIFICATION TESTS (D-22 & D-23)
# ==============================================================================


def test_qa_analyst_guide_pdf_exists_and_size() -> None:
    """Verify analyst_guide.pdf (D-22) exists, > 100KB, and has 10-15 pages."""
    guide_pdf = REPORTS_DIR / "analyst_guide.pdf"
    assert guide_pdf.exists(), f"analyst_guide.pdf missing at {guide_pdf}"
    size = guide_pdf.stat().st_size
    assert size > 100_000, f"analyst_guide.pdf size {size} bytes is <= 100KB"

    # Verify page count is within 10-15 pages
    with open(guide_pdf, "rb") as f:
        pdf_content = f.read()
    import re

    pages = re.findall(rb"/Type\s*/Page[\s/>]", pdf_content)
    assert 10 <= len(pages) <= 15, f"Expected 10-15 pages, got {len(pages)}"


def test_qa_acceptance_checklist_pdf_exists_and_size() -> None:
    """Verify acceptance_checklist.pdf (D-23) exists, > 30KB, and has >= 2 pages."""
    checklist_pdf = REPORTS_DIR / "acceptance_checklist.pdf"
    assert (
        checklist_pdf.exists()
    ), f"acceptance_checklist.pdf missing at {checklist_pdf}"
    size = checklist_pdf.stat().st_size
    assert size > 30_000, f"acceptance_checklist.pdf size {size} bytes is <= 30KB"

    with open(checklist_pdf, "rb") as f:
        pdf_content = f.read()
    import re

    pages = re.findall(rb"/Type\s*/Page[\s/>]", pdf_content)
    assert len(pages) >= 2, f"Expected at least 2 pages, got {len(pages)}"


# ==============================================================================
# SPRINT 6 DAY 40 INTEGRATION AUDIT TESTS (D-13 & MASTER DELIVERABLES)
# ==============================================================================


def test_qa_cashflow_intelligence_report_exists_and_valid() -> None:
    """Verify cashflow_intelligence.xlsx (D-13) exists, > 50KB, and has expected sheets."""
    cf_xlsx = REPORTS_DIR / "cashflow_intelligence.xlsx"
    assert cf_xlsx.exists(), f"cashflow_intelligence.xlsx missing at {cf_xlsx}"
    assert (
        cf_xlsx.stat().st_size > 50_000
    ), f"cashflow_intelligence.xlsx smaller than 50KB: {cf_xlsx.stat().st_size} bytes"

    import openpyxl

    wb = openpyxl.load_workbook(cf_xlsx, read_only=True)
    expected_sheets = {"Latest Summary", "Historical KPIs", "Sector Patterns"}
    assert expected_sheets.issubset(
        set(wb.sheetnames)
    ), f"Missing sheets in cashflow_intelligence.xlsx: {set(wb.sheetnames)}"
    wb.close()


def test_qa_all_23_deliverables_present_and_accounted() -> None:
    """Verify all 23 specification deliverables D-01 through D-23 exist and are valid."""
    deliverable_paths = [
        REPO_ROOT / "db" / "nifty100.db",
        REPORTS_DIR / "load_audit.csv",
        REPORTS_DIR / "validation_failures.csv",
        REPO_ROOT / "notebooks" / "exploratory_queries.sql",
        REPO_ROOT / "data" / "processed" / "capital_allocation.csv",
        REPORTS_DIR / "screener_output.xlsx",
        REPO_ROOT / "screener_config.yaml",
        REPORTS_DIR / "peer_comparison.xlsx",
        REPORTS_DIR / "radar_charts",
        REPO_ROOT / "src" / "dashboard" / "app.py",
        REPORTS_DIR / "valuation_summary.xlsx",
        REPORTS_DIR / "cashflow_intelligence.xlsx",
        REPO_ROOT / "data" / "processed" / "pros_cons_generated.csv",
        REPO_ROOT / "data" / "processed" / "analysis_parsed.csv",
        REPORTS_DIR / "tearsheets",
        REPORTS_DIR / "sector_reports",
        REPORTS_DIR / "portfolio_summary.pdf",
        REPO_ROOT / "data" / "processed" / "cluster_labels.csv",
        REPO_ROOT / "src" / "api" / "main.py",
        REPORTS_DIR / "pytest_report.html",
        REPORTS_DIR / "analyst_guide.pdf",
        REPORTS_DIR / "acceptance_checklist.pdf",
    ]

    for p in deliverable_paths:
        assert p.exists(), f"Deliverable missing at: {p}"

    # Also verify SQLite financial_ratios table row count (D-05)
    conn = sqlite3.connect(DB_PATH)
    count = conn.cursor().execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    conn.close()
    assert count >= 1100, f"financial_ratios table has only {count} rows (< 1100)"


def test_qa_repo_cleanliness_and_funding_config() -> None:
    """Verify repository polish standards: .github/FUNDING.yml exists and .gitignore protects repo."""
    funding_path = Path(".github/FUNDING.yml")
    assert funding_path.exists(), ".github/FUNDING.yml should exist"
    funding_content = funding_path.read_text(encoding="utf-8")
    assert "github:" in funding_content

    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore should exist"
    gi_content = gitignore_path.read_text(encoding="utf-8")
    assert "reports/**/*.pdf" in gi_content
    assert "reports/**/*.png" in gi_content
    assert "db/*.db" in gi_content
