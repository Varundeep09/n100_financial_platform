"""Unit tests for Sprint 5 NLP Module and qualitative artifacts.

Verifies analysis_parsed.csv parsing from analysis.xlsx and
pros_cons_generated.csv generation covering all 92 companies.
"""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
ANALYSIS_CSV = REPORTS_DIR / "analysis_parsed.csv"
PROS_CONS_CSV = REPORTS_DIR / "pros_cons_generated.csv"


def test_analysis_parsed_csv_exists_and_non_empty() -> None:
    """Verify analysis_parsed.csv exists in reports/ and has parsed records."""
    assert ANALYSIS_CSV.exists(), f"Missing {ANALYSIS_CSV}"
    df = pd.read_csv(ANALYSIS_CSV)
    assert not df.empty, "analysis_parsed.csv is empty"
    expected_cols = {"company_id", "metric_type", "period_years", "value_pct"}
    assert expected_cols.issubset(df.columns), f"Missing columns in analysis_parsed.csv: {df.columns}"


def test_analysis_parsed_numeric_values_valid() -> None:
    """Verify parsed CAGR and growth values are non-null floats."""
    df = pd.read_csv(ANALYSIS_CSV)
    assert df["value_pct"].notna().all(), "Found null values in value_pct"
    assert df["period_years"].between(1, 15).all(), "Invalid period_years in analysis_parsed"


def test_pros_cons_generated_csv_exists_and_schema() -> None:
    """Verify pros_cons_generated.csv exists with expected schema."""
    assert PROS_CONS_CSV.exists(), f"Missing {PROS_CONS_CSV}"
    df = pd.read_csv(PROS_CONS_CSV)
    expected_cols = {"company_id", "type", "rule_triggered", "text", "confidence_pct"}
    assert expected_cols.issubset(df.columns), f"Missing columns: {df.columns}"


def test_ac16_nlp_coverage_all_92_companies_have_pro_and_con() -> None:
    """AC-16: Verify all 92 companies have at least 1 pro and at least 1 con."""
    df = pd.read_csv(PROS_CONS_CSV)
    assert df["company_id"].nunique() == 92, f"Expected 92 distinct companies, got {df['company_id'].nunique()}"

    pros_by_company = df[df["type"] == "pro"].groupby("company_id").size()
    cons_by_company = df[df["type"] == "con"].groupby("company_id").size()

    assert len(pros_by_company) == 92, "Not all 92 companies have at least 1 pro"
    assert len(cons_by_company) == 92, "Not all 92 companies have at least 1 con"
    assert (pros_by_company >= 1).all(), "Some company has 0 pros"
    assert (cons_by_company >= 1).all(), "Some company has 0 cons"


def test_pros_cons_confidence_bounds() -> None:
    """Verify confidence_pct is bounded between 60.0% and 100.0%."""
    df = pd.read_csv(PROS_CONS_CSV)
    assert df["confidence_pct"].between(60.0, 100.0).all(), "Confidence scores outside 60-100% range"


def test_pros_cons_no_null_text() -> None:
    """Verify no empty or null bullet points exist in pros_cons_generated.csv."""
    df = pd.read_csv(PROS_CONS_CSV)
    assert df["text"].notna().all(), "Found null text in pros/cons"
    assert (df["text"].str.strip().str.len() > 5).all(), "Found trivial/empty text entries"


def test_pros_cons_types_are_strictly_pro_or_con() -> None:
    """Verify type column is strictly 'pro' or 'con'."""
    df = pd.read_csv(PROS_CONS_CSV)
    assert set(df["type"].unique()).issubset({"pro", "con"}), f"Invalid types found: {df['type'].unique()}"
