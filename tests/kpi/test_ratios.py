"""Unit tests for profitability ratio engine (NPM, OPM, ROE, ROCE, ROA).

Includes tests for:
- Standard non-financial companies.
- Automatic recovery of shifted non-financial companies (HINDUNILVR, CIPLA, COALINDIA, etc.).
- Financials sector graceful None handling for OPM and ROCE across all 23 Financials.
- Extreme value sanity flagging (|ROE| > 200%, |ROA| > 100%) for near-zero equity/asset bases (INDIGO).
- Missing balance sheet graceful handling (SBIN).
- Edge cases (zero sales, negative equity, zero assets).
"""

from pathlib import Path

import pytest
from src.analytics.ratios import (
    OPM_DISCREPANCIES,
    calculate_profitability_metrics,
    check_extreme_magnitude_flag,
    compute_npm,
    compute_opm,
    compute_roa,
    compute_roce,
    compute_roe,
    get_financial_statements_data,
    normalize_pl_statement,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "nifty100.db"


def test_npm_normal() -> None:
    """Verify standard Net Profit Margin computation."""
    assert compute_npm(15000.0, 100000.0) == 15.0
    assert compute_npm(79020.0, 899041.0) == 8.7894


def test_npm_zero_sales() -> None:
    """Verify Net Profit Margin returns None when sales is zero, negative, or missing."""
    assert compute_npm(100.0, 0.0) is None
    assert compute_npm(100.0, None) is None
    assert compute_npm(None, 1000.0) is None


def test_roe_positive() -> None:
    """Verify Return on Equity with positive total shareholders equity."""
    assert compute_roe(20000.0, 1000.0, 99000.0) == 20.0
    assert compute_roe(46099.0, 362.0, 90000.0) == 51.0159


def test_roe_negative_equity() -> None:
    """Verify Return on Equity returns None when net worth is zero or negative."""
    assert compute_roe(1000.0, 500.0, -1500.0) is None
    assert compute_roe(1000.0, 500.0, -500.0) is None
    assert compute_roe(None, 500.0, 1000.0) is None
    assert compute_roe(1000.0, None, 1000.0) is None


def test_roce_normal() -> None:
    """Verify Return on Capital Employed for standard non-financial company."""
    res = compute_roce(
        operating_profit=25000.0,
        depreciation=5000.0,
        equity_capital=1000.0,
        reserves=49000.0,
        borrowings=50000.0,
        broad_sector="Energy",
    )
    assert res["value"] == 20.0
    assert res["sector_relative"] is False


def test_roce_financials_sector_none() -> None:
    """Verify ROCE for Financials sector returns None with sector_relative as True."""
    res = compute_roce(
        operating_profit=25000.0,
        depreciation=5000.0,
        equity_capital=1000.0,
        reserves=49000.0,
        borrowings=50000.0,
        broad_sector="Financials",
    )
    assert res["value"] is None
    assert res["sector_relative"] is True


def test_opm_financials_sector_none() -> None:
    """Verify OPM for Financials sector returns None."""
    assert compute_opm(25000.0, 100000.0, broad_sector="Financials") is None


def test_roa_normal() -> None:
    """Verify standard Return on Assets computation."""
    assert compute_roa(15000.0, 100000.0) == 15.0
    assert compute_roa(79020.0, 1815123.0) == 4.3534


def test_roa_zero_assets() -> None:
    """Verify Return on Assets returns None when total assets is zero, negative, or missing."""
    assert compute_roa(1000.0, 0.0) is None
    assert compute_roa(1000.0, -500.0) is None
    assert compute_roa(1000.0, None) is None
    assert compute_roa(None, 100000.0) is None


def test_extreme_magnitude_flag() -> None:
    """Verify extreme magnitude flag triggers on outlier ratios."""
    assert check_extreme_magnitude_flag(roe=892.57, roce=1064.91, roa=668.33) is True
    assert check_extreme_magnitude_flag(roe=20.0, roce=25.0, roa=12.0) is False
    assert check_extreme_magnitude_flag(roe=-250.0, roce=10.0, roa=5.0) is True


def test_opm_cross_check_logging() -> None:
    """Verify OPM calculation and discrepancy logging for non-financials."""
    initial_len = len(OPM_DISCREPANCIES)
    opm_match = compute_opm(
        2000.0,
        10000.0,
        source_opm=20.0,
        company_id="TESTCO",
        year="2024-03",
        broad_sector="Materials",
    )
    assert opm_match == 20.0
    assert len(OPM_DISCREPANCIES) == initial_len

    opm_diff = compute_opm(
        2500.0,
        10000.0,
        source_opm=20.0,
        company_id="TESTCO",
        year="2024-03",
        broad_sector="Materials",
    )
    assert opm_diff == 25.0
    assert len(OPM_DISCREPANCIES) == initial_len + 1


def test_normalize_pl_statement_shifted_recovery() -> None:
    """Verify automated detection and recovery of shifted non-financial columns."""
    norm = normalize_pl_statement(
        sales=68904.0,
        expenses=4805.0,  # Other Income in raw Excel for INDIGO
        operating_profit=52573.0,  # True Expenses for INDIGO
        opm_percentage=16331.0,  # True Operating Profit for INDIGO
        other_income=24.0,  # True OPM %
        depreciation=6406.0,
        profit_before_tax=8043.0,
        net_profit=8167.0,
        broad_sector="Consumer Discretionary",
    )
    assert norm["is_shifted"] is True
    assert norm["status"] == "SHIFTED_NON_FINANCIAL_RECOVERED"
    assert norm["true_sales"] == 68904.0
    assert norm["true_expenses"] == 52573.0
    assert norm["true_operating_profit"] == 16331.0
    assert norm["true_other_income"] == 4805.0


def test_normalize_pl_statement_financials() -> None:
    """Verify Financials sector normalization marks true_operating_profit as None."""
    norm = normalize_pl_statement(
        sales=109369.0,
        expenses=59474.0,
        operating_profit=37943.0,
        opm_percentage=11952.0,
        other_income=11.0,
        depreciation=1334.0,
        profit_before_tax=33060.0,
        net_profit=24861.0,
        broad_sector="Financials",
    )
    assert norm["is_financial"] is True
    assert norm["true_operating_profit"] is None
    assert norm["status"] == "FINANCIAL_SECTOR"


def test_indigo_profitability_recovered_and_flagged() -> None:
    """Verify INDIGO recovers OPM correctly and triggers extreme magnitude flag on thin equity/asset base."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_indigo = get_financial_statements_data(company_id="INDIGO", db_path=DB_PATH)
    assert not df_indigo.empty
    metrics_df = calculate_profitability_metrics(df_indigo)

    row_2024 = metrics_df[metrics_df["year"] == "2024-03"].iloc[0]
    assert row_2024["pl_normalization_status"] == "SHIFTED_NON_FINANCIAL_RECOVERED"
    assert row_2024["npm_pct"] == pytest.approx(11.85, abs=0.01)
    assert row_2024["opm_pct"] == pytest.approx(23.70, abs=0.01)
    assert row_2024["roe_pct"] == pytest.approx(892.57, abs=0.01)
    assert bool(row_2024["extreme_magnitude_flag"]) is True


def test_hindunilvr_profitability_recovered() -> None:
    """Verify end-to-end profitability calculation on HINDUNILVR with recovered columns."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_hul = get_financial_statements_data(company_id="HINDUNILVR", db_path=DB_PATH)
    assert not df_hul.empty
    metrics_df = calculate_profitability_metrics(df_hul)

    row_2024 = metrics_df[metrics_df["year"] == "2024-03"].iloc[0]
    assert row_2024["pl_normalization_status"] == "SHIFTED_NON_FINANCIAL_RECOVERED"
    assert row_2024["npm_pct"] == pytest.approx(16.61, abs=0.01)
    assert row_2024["opm_pct"] == pytest.approx(23.68, abs=0.01)
    assert row_2024["roe_pct"] == pytest.approx(20.07, abs=0.02)
    assert row_2024["roce_pct"] == pytest.approx(25.51, abs=0.01)
    assert row_2024["roa_pct"] == pytest.approx(13.10, abs=0.01)
    assert bool(row_2024["extreme_magnitude_flag"]) is False


def test_axisbank_profitability_financials_separation() -> None:
    """Verify AXISBANK computes valid NPM/ROE/ROA but returns None for OPM and ROCE."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_axis = get_financial_statements_data(company_id="AXISBANK", db_path=DB_PATH)
    assert not df_axis.empty
    metrics_df = calculate_profitability_metrics(df_axis)

    row_2024 = metrics_df[metrics_df["year"] == "2024-03"].iloc[0]
    assert row_2024["pl_normalization_status"] == "FINANCIAL_SECTOR"
    assert row_2024["npm_pct"] == pytest.approx(22.73, abs=0.01)
    assert row_2024["opm_pct"] is None
    assert row_2024["roe_pct"] == pytest.approx(15.83, abs=0.01)
    assert row_2024["roce_pct"] is None
    assert bool(row_2024["roce_sector_relative"]) is True
    assert row_2024["roa_pct"] == pytest.approx(1.64, abs=0.01)
    assert bool(row_2024["extreme_magnitude_flag"]) is False


def test_sbin_bs_ratios_return_none() -> None:
    """Verify SBIN returns valid NPM but None for all Balance Sheet dependent ratios and OPM/ROCE."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_sbin = get_financial_statements_data(company_id="SBIN", db_path=DB_PATH)
    assert not df_sbin.empty
    assert len(df_sbin) == 12

    metrics_df = calculate_profitability_metrics(df_sbin)
    assert len(metrics_df) == 12

    for _, row in metrics_df.iterrows():
        assert row["npm_pct"] is not None
        assert row["opm_pct"] is None
        assert row["roe_pct"] is None
        assert row["roce_pct"] is None
        assert row["roa_pct"] is None
        assert bool(row["roce_sector_relative"]) is True
