"""Unit tests for profitability ratio engine (NPM, OPM, ROE, ROCE, ROA)."""

from pathlib import Path

import pytest

from src.analytics.ratios import (
    OPM_DISCREPANCIES,
    calculate_profitability_metrics,
    compute_npm,
    compute_opm,
    compute_roa,
    compute_roce,
    compute_roe,
    get_financial_statements_data,
)

DB_PATH = Path("db/nifty100.db")


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


def test_roce_financials_sector_flag() -> None:
    """Verify ROCE for Financials sector flags sector_relative as True."""
    res = compute_roce(
        operating_profit=25000.0,
        depreciation=5000.0,
        equity_capital=1000.0,
        reserves=49000.0,
        borrowings=50000.0,
        broad_sector="Financials",
    )
    assert res["value"] == 20.0
    assert res["sector_relative"] is True


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


def test_opm_cross_check_logging() -> None:
    """Verify OPM calculation and discrepancy logging for variances exceeding 1%."""
    initial_len = len(OPM_DISCREPANCIES)
    opm_match = compute_opm(
        2000.0, 10000.0, source_opm=20.0, company_id="TESTCO", year="2024-03"
    )
    assert opm_match == 20.0
    assert len(OPM_DISCREPANCIES) == initial_len

    opm_diff = compute_opm(
        2500.0, 10000.0, source_opm=20.0, company_id="TESTCO", year="2024-03"
    )
    assert opm_diff == 25.0
    assert len(OPM_DISCREPANCIES) == initial_len + 1


def test_sbin_bs_ratios_return_none() -> None:
    """Verify SBIN returns valid P&L ratios but None for all Balance Sheet dependent ratios."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_sbin = get_financial_statements_data(company_id="SBIN", db_path=DB_PATH)
    assert not df_sbin.empty
    assert len(df_sbin) == 12

    metrics_df = calculate_profitability_metrics(df_sbin)
    assert len(metrics_df) == 12

    for _, row in metrics_df.iterrows():
        assert row["npm_pct"] is not None
        assert row["opm_pct"] is not None
        assert row["roe_pct"] is None
        assert row["roce_pct"] is None
        assert row["roa_pct"] is None
        assert row["roce_sector_relative"] is True
