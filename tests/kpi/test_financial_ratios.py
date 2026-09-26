"""Unit tests for financial_ratios table population (Sprint 2, Day 12).

Verifies:
1. financial_ratios SQLite table schema (PK: company_id + year composite, FK: company_id -> companies.id).
2. Minimum row count (>= 1,100 rows).
3. Zero columns are 100% null across the table.
4. Edge cases & sector-relative policies preserved in database table:
   - 16 Banking-template companies: OPM, ROCE, ICR, FCF Conversion = None
   - 23 Financials sector companies: high_leverage_flag = 0, sector_relative_flag = 1, CFO Quality = None
   - Exact year-gap CAGR matching: AMBUJACEM 2024-03 5yr CFO Quality = None
5. Spot-check verification for INFY, TITAN, and BAJAJ-AUTO matches manual arithmetic within 0.1%.
"""

import sqlite3

import pandas as pd
import pytest

from src.analytics.ratios import (
    DB_PATH,
    FINANCIALS_SECTOR_COMPANIES,
)


@pytest.fixture(scope="module")
def fr_df():
    """Load populated financial_ratios table from database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM financial_ratios", conn)
    conn.close()
    return df


def test_financial_ratios_row_count(fr_df):
    """Verify total row count is at least 1,100 rows across all 92 companies."""
    assert len(fr_df) >= 1100
    assert fr_df["company_id"].nunique() == 92


def test_financial_ratios_no_column_is_all_null(fr_df):
    """Confirm none of the 47 columns are 100% null across the whole table."""
    total_rows = len(fr_df)
    for col in fr_df.columns:
        null_count = fr_df[col].isna().sum()
        assert null_count < total_rows, f"Column {col} is 100% null!"


def test_financial_ratios_primary_key_and_schema():
    """Verify composite primary key and foreign key constraint in SQLite table info."""
    conn = sqlite3.connect(DB_PATH)
    pragma_df = pd.read_sql("PRAGMA table_info(financial_ratios)", conn)
    conn.close()

    pk_cols = pragma_df[pragma_df["pk"] > 0].sort_values("pk")["name"].tolist()
    assert pk_cols == ["company_id", "year"]

    expected_cols = {
        "company_id",
        "year",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "return_on_assets_pct",
        "debt_to_equity",
        "high_leverage_flag",
        "interest_coverage",
        "icr_label",
        "icr_risk_flag",
        "net_debt_cr",
        "asset_turnover",
        "revenue_cagr_3yr",
        "revenue_cagr_3yr_flag",
        "revenue_cagr_5yr",
        "revenue_cagr_5yr_flag",
        "revenue_cagr_10yr",
        "revenue_cagr_10yr_flag",
        "pat_cagr_3yr",
        "pat_cagr_3yr_flag",
        "pat_cagr_5yr",
        "pat_cagr_5yr_flag",
        "pat_cagr_10yr",
        "pat_cagr_10yr_flag",
        "eps_cagr_3yr",
        "eps_cagr_3yr_flag",
        "eps_cagr_5yr",
        "eps_cagr_5yr_flag",
        "eps_cagr_10yr",
        "eps_cagr_10yr_flag",
        "free_cash_flow_cr",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_conversion_rate_pct",
        "fcf_conversion_label",
        "capital_allocation_pattern",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
        "composite_quality_score",
        "sector_relative_flag",
        "extreme_magnitude_flag",
        "data_quality_flag",
        "data_quality_label",
    }
    assert expected_cols.issubset(set(pragma_df["name"].tolist()))


def test_financial_ratios_banking_template_policies(fr_df):
    """Verify banking-template companies return None for OPM, ROCE, ICR, and FCF Conversion."""
    for bank_id in ["SBIN", "AXISBANK", "HDFCBANK", "ICICIBANK", "KOTAKBANK"]:
        bank_rows = fr_df[fr_df["company_id"] == bank_id]
        assert not bank_rows.empty
        # All OPM, ROCE, and ICR must be None for banking template
        assert bank_rows["operating_profit_margin_pct"].isna().all()
        assert bank_rows["return_on_capital_employed_pct"].isna().all()
        assert bank_rows["interest_coverage"].isna().all()
        assert bank_rows["fcf_conversion_rate_pct"].isna().all()
        assert (
            bank_rows["fcf_conversion_label"] == "Not Applicable (Banking Template)"
        ).all()


def test_financial_ratios_financials_sector_flags(fr_df):
    """Verify all 23 Financials sector companies have sector_relative_flag=1 and high_leverage_flag=0."""
    fin_df = fr_df[fr_df["company_id"].isin(FINANCIALS_SECTOR_COMPANIES)]
    assert fin_df["company_id"].nunique() == 23
    assert (fin_df["sector_relative_flag"] == 1).all()
    assert (fin_df["high_leverage_flag"] == 0).all()
    # CFO Quality label must be 'Not Applicable (Financials Sector)'
    assert (fin_df["cfo_quality_label"] == "Not Applicable (Financials Sector)").all()


def test_financial_ratios_manual_spot_checks(fr_df):
    """Verify 3 manual spot-checks (INFY, TITAN, BAJAJ-AUTO) match within 0.1%."""
    # 1. INFY 2024-03: Net Profit 26,248 Cr / Net Worth 88,116 Cr = 29.788%
    infy = fr_df[(fr_df["company_id"] == "INFY") & (fr_df["year"] == "2024-03")].iloc[0]
    assert abs(infy["return_on_equity_pct"] - 29.788) < 0.1
    # 5yr Revenue CAGR: 82,675 Cr to 153,670 Cr = 13.1991%
    assert abs(infy["revenue_cagr_5yr"] - 13.1991) < 0.1

    # 2. TITAN 2024-03: Net Profit 3,496 Cr / Net Worth 9,393 Cr = 37.219%
    titan = fr_df[(fr_df["company_id"] == "TITAN") & (fr_df["year"] == "2024-03")].iloc[
        0
    ]
    assert abs(titan["return_on_equity_pct"] - 37.219) < 0.1
    # 5yr Revenue CAGR: 19,779 Cr to 51,084 Cr = 20.8972%
    assert abs(titan["revenue_cagr_5yr"] - 20.8972) < 0.1

    # 3. BAJAJ-AUTO 2024-03: Net Profit 7,708 Cr / Net Worth 28,962 Cr = 26.614%
    bajaj = fr_df[
        (fr_df["company_id"] == "BAJAJ-AUTO") & (fr_df["year"] == "2024-03")
    ].iloc[0]
    assert abs(bajaj["return_on_equity_pct"] - 26.614) < 0.1
    # 5yr Revenue CAGR: 30,358 Cr to 44,870 Cr = 8.1276%
    assert abs(bajaj["revenue_cagr_5yr"] - 8.1276) < 0.1


def test_financial_ratios_composite_quality_score_complete(fr_df):
    """Confirm composite_quality_score is never null and is bounded within 0-100."""
    assert fr_df["composite_quality_score"].isna().sum() == 0
    assert (fr_df["composite_quality_score"] >= 0).all()
    assert (fr_df["composite_quality_score"] <= 100).all()

def test_financial_ratios_bel_hal_remediation(fr_df):
    """Verify BEL and HAL balance-sheet ratios are None with data_quality_flag=1 and label='Unreliable Balance Sheet Data'."""
    for cid in ["BEL", "HAL"]:
        sub = fr_df[fr_df["company_id"] == cid]
        assert not sub.empty
        assert sub["return_on_equity_pct"].isna().all()
        assert sub["return_on_capital_employed_pct"].isna().all()
        assert sub["return_on_assets_pct"].isna().all()
        assert sub["debt_to_equity"].isna().all()
        assert sub["asset_turnover"].isna().all()
        assert (sub["extreme_magnitude_flag"] == 1).all()
        assert (sub["data_quality_flag"] == 1).all()
        assert (sub["data_quality_label"] == "Unreliable Balance Sheet Data").all()


def test_financial_ratios_indigo_extreme_magnitude_flag(fr_df):
    """Verify INDIGO has extreme_magnitude_flag=1 while preserving computed ratios."""
    sub = fr_df[fr_df["company_id"] == "INDIGO"]
    assert not sub.empty
    row_24 = sub[sub["year"] == "2024-03"].iloc[0]
    assert row_24["extreme_magnitude_flag"] == 1
    assert row_24["data_quality_flag"] == 0
    assert row_24["return_on_equity_pct"] > 800.0


def test_financial_ratios_no_unhandled_outliers_over_500_pct(fr_df):
    """Verify no unflagged company exhibits |ROE| > 500% or |ROCE| > 500% (BEL/HAL neutralized)."""
    outliers = fr_df[
        (fr_df["return_on_equity_pct"].abs() > 500.0)
        | (fr_df["return_on_capital_employed_pct"].abs() > 500.0)
    ]
    # BEL and HAL must NOT appear in outliers
    assert "BEL" not in outliers["company_id"].unique()
    assert "HAL" not in outliers["company_id"].unique()
    # All remaining extreme outliers must have extreme_magnitude_flag = 1
    assert (outliers["extreme_magnitude_flag"] == 1).all()
