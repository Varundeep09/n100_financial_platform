"""Unit tests for financial ratio engine (Profitability, Leverage, and Efficiency).

Includes tests for:
- Profitability: NPM, OPM, ROE, ROCE, ROA.
- Leverage & Solvency: Debt-to-Equity, High Leverage Flag, Interest Coverage Ratio (ICR), Net Debt.
- Efficiency: Asset Turnover.
- Standard non-financial companies.
- Automatic recovery of shifted non-financial companies (HINDUNILVR, CIPLA, COALINDIA, etc.).
- Evidence-based Financials sector handling:
  * Banking template Financials (AXISBANK, HDFCBANK, etc.) -> OPM=None, ROCE=None, ICR=None ('Not Applicable (Banking Template)').
  * Clean Financials (JIOFIN, IRFC, RECLTD, etc.) -> OPM, ROCE, ICR computed normally with sector_relative=True.
- Sector-based high leverage exemption: all 23 Financials sector companies are exempt from high_leverage_flag.
- Extreme value sanity flagging (|ROE| > 200%, |ROA| > 100%) for near-zero equity/asset bases (INDIGO).
- Missing balance sheet graceful handling (SBIN).
- Edge cases (zero sales, negative equity, zero assets, zero borrowings, zero interest).
"""

from pathlib import Path

import pytest

from src.analytics.ratios import (
    FINANCIALS_SECTOR_COMPANIES,
    OPM_DISCREPANCIES,
    UNRELIABLE_BALANCESHEET_COMPANIES,
    calculate_profitability_metrics,
    check_extreme_magnitude_flag,
    check_high_leverage_flag,
    compute_asset_turnover,
    compute_debt_to_equity,
    compute_interest_coverage,
    compute_net_debt,
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


# =============================================================================
# PROFITABILITY TESTS
# =============================================================================


def test_npm_normal() -> None:
    """Verify standard Net Profit Margin computation."""
    assert compute_npm(15000.0, 100000.0) == 15.0
    assert compute_npm(79020.0, 899041.0) == 8.7894


def test_npm_zero_sales() -> None:
    """Verify Net Profit Margin returns None when sales is zero, negative, or missing."""
    assert compute_npm(100.0, 0.0) is None
    assert compute_npm(100.0, None) is None


def test_roe_positive() -> None:
    """Verify standard Return on Equity computation."""
    assert compute_roe(1000.0, 2000.0, 3000.0) == 20.0


def test_roe_negative_equity() -> None:
    """Verify Return on Equity returns None when net worth is negative or zero."""
    assert compute_roe(100.0, 100.0, -150.0) is None
    assert compute_roe(100.0, 50.0, -50.0) is None
    assert compute_roe(None, 100.0, 200.0) is None


def test_roce_normal() -> None:
    """Verify standard Return on Capital Employed computation."""
    res = compute_roce(
        operating_profit=250.0,
        depreciation=50.0,
        equity_capital=200.0,
        reserves=300.0,
        borrowings=500.0,
        broad_sector="Consumer Goods",
    )
    assert res["value"] == 20.0
    assert res["sector_relative"] is False


def test_roce_banking_financials_none() -> None:
    """Verify ROCE returns None with sector_relative=True for banking-template Financials."""
    res = compute_roce(
        operating_profit=5000.0,
        depreciation=200.0,
        equity_capital=1000.0,
        reserves=10000.0,
        borrowings=50000.0,
        broad_sector="Financials",
        is_banking_template=True,
    )
    assert res["value"] is None
    assert res["sector_relative"] is True


def test_opm_banking_financials_none() -> None:
    """Verify OPM returns None for banking-template Financials."""
    assert (
        compute_opm(
            15000.0,
            25000.0,
            company_id="AXISBANK",
            is_banking_template=True,
        )
        is None
    )


def test_roa_normal() -> None:
    """Verify Return on Assets computation."""
    assert compute_roa(200.0, 2000.0) == 10.0


def test_roa_zero_assets() -> None:
    """Verify Return on Assets returns None when total assets <= 0 or None."""
    assert compute_roa(100.0, 0.0) is None
    assert compute_roa(100.0, -500.0) is None
    assert compute_roa(100.0, None) is None


def test_extreme_magnitude_flag() -> None:
    """Verify extreme magnitude flag triggers on near-zero equity/asset ratios."""
    assert check_extreme_magnitude_flag(roe=892.57, roce=1064.91, roa=668.33) is True
    assert check_extreme_magnitude_flag(roe=20.5, roce=18.2, roa=8.4) is False
    assert check_extreme_magnitude_flag(roe=None, roce=None, roa=150.0) is True


def test_opm_cross_check_logging() -> None:
    """Verify OPM cross-check logging catches discrepancies > 1%."""
    initial_len = len(OPM_DISCREPANCIES)
    compute_opm(
        operating_profit=2000.0,
        sales=10000.0,
        source_opm=25.0,
        company_id="TESTCO",
        year="2024-03",
    )
    assert len(OPM_DISCREPANCIES) == initial_len + 1
    last_log = OPM_DISCREPANCIES[-1]
    assert last_log["company_id"] == "TESTCO"
    assert last_log["diff"] == 5.0


def test_normalize_pl_statement_shifted_recovery() -> None:
    """Verify P&L column shifts in non-financials are automatically corrected."""
    norm = normalize_pl_statement(
        sales=61896.0,
        expenses=46786.0,
        operating_profit=46786.0,
        opm_percentage=15110.0,
        other_income=24.0,
        depreciation=1156.0,
        profit_before_tax=14674.0,
        net_profit=10282.0,
        company_id="HINDUNILVR",
        broad_sector="Consumer Goods",
    )
    assert norm["is_shifted"] is True
    assert norm["status"] == "SHIFTED_NON_FINANCIAL_RECOVERED"
    assert norm["true_operating_profit"] == 15110.0
    assert norm["true_expenses"] == 46786.0
    assert norm["true_other_income"] == 46786.0


def test_normalize_pl_statement_banking_financials() -> None:
    """Verify banking-template Financials nullify true_operating_profit and true_other_income."""
    norm = normalize_pl_statement(
        sales=109438.0,
        expenses=76974.0,
        operating_profit=76974.0,
        opm_percentage=32464.0,
        other_income=30.0,
        depreciation=1200.0,
        profit_before_tax=34000.0,
        net_profit=26000.0,
        company_id="AXISBANK",
        broad_sector="Financials",
    )
    assert norm["is_banking_template"] is True
    assert norm["status"] == "BANKING_TEMPLATE_FINANCIAL"
    assert norm["true_operating_profit"] is None
    assert norm["true_other_income"] is None


def test_normalize_pl_statement_clean_financials() -> None:
    """Verify clean Financials maintain valid P&L structure without nullification."""
    norm = normalize_pl_statement(
        sales=374.0,
        expenses=59.0,
        operating_profit=315.0,
        opm_percentage=84.22,
        other_income=4.0,
        depreciation=1.0,
        profit_before_tax=318.0,
        net_profit=238.0,
        company_id="JIOFIN",
        broad_sector="Financials",
    )
    assert norm["is_banking_template"] is False
    assert norm["status"] == "CLEAN_FINANCIAL"
    assert norm["true_operating_profit"] == 315.0
    assert norm["true_other_income"] == 4.0


# =============================================================================
# LEVERAGE & EFFICIENCY TESTS (DAY 9)
# =============================================================================


def test_debt_to_equity_normal() -> None:
    """Verify standard Debt-to-Equity calculation: borrowings / (equity + reserves)."""
    assert compute_debt_to_equity(500.0, 100.0, 400.0) == 1.0
    assert compute_debt_to_equity(1500.0, 200.0, 800.0) == 1.5


def test_debt_to_equity_zero_borrowings_returns_zero() -> None:
    """Verify Debt-to-Equity returns 0.0 (NOT None) if borrowings == 0."""
    assert compute_debt_to_equity(0.0, 100.0, 500.0) == 0.0
    assert compute_debt_to_equity(0.0, 50.0, 250.0) == 0.0


def test_debt_to_equity_negative_or_zero_equity_returns_none() -> None:
    """Verify Debt-to-Equity returns None when net worth is zero, negative, or missing."""
    assert compute_debt_to_equity(500.0, 100.0, -100.0) is None
    assert compute_debt_to_equity(500.0, 100.0, -200.0) is None
    assert compute_debt_to_equity(500.0, None, 500.0) is None
    assert compute_debt_to_equity(None, 100.0, 500.0) is None


def test_high_leverage_flag_normal_and_financials_exemption() -> None:
    """Verify high leverage flag triggers for non-financials, but exempts all Financials."""
    # Non-financial company with D/E > 5 -> True
    assert check_high_leverage_flag(5.5, company_id="TATAMOTORS") is True
    assert (
        check_high_leverage_flag(
            5.5, broad_sector="Consumer Discretionary", company_id="TATAMOTORS"
        )
        is True
    )

    # Non-financial company with D/E <= 5 -> False
    assert check_high_leverage_flag(2.1, company_id="RELIANCE") is False
    assert (
        check_high_leverage_flag(2.1, broad_sector="Energy", company_id="RELIANCE")
        is False
    )

    # Financials broad_sector with D/E > 5 -> False (structurally normal for financial lenders)
    assert check_high_leverage_flag(8.38, broad_sector="Financials") is False
    assert (
        check_high_leverage_flag(8.38, broad_sector="Financials", company_id="IRFC")
        is False
    )
    assert (
        check_high_leverage_flag(6.42, broad_sector="Financials", company_id="RECLTD")
        is False
    )

    # Clean Financials with D/E <= 5 -> False
    assert (
        check_high_leverage_flag(0.0, broad_sector="Financials", company_id="JIOFIN")
        is False
    )

    # None D/E -> False
    assert check_high_leverage_flag(None, broad_sector="Financials") is False
    assert check_high_leverage_flag(None, company_id="SBIN") is False


def test_high_leverage_flag_financials_sector_excluded() -> None:
    """Verify high leverage flag is False for all Financials companies (banks, NBFCs, lenders)."""
    # 1. Broad sector check directly
    assert check_high_leverage_flag(8.5, broad_sector="Financials") is False
    assert check_high_leverage_flag(15.0, broad_sector="Financials") is False

    # 2. Check representative companies across banks, NBFCs, and specialty lenders
    sample_financials = [
        "AXISBANK",
        "HDFCBANK",
        "SBIN",
        "BAJFINANCE",
        "PFC",
        "IRFC",
        "RECLTD",
    ]
    for fin_ticker in sample_financials:
        assert fin_ticker in FINANCIALS_SECTOR_COMPANIES
        # Company ID lookup
        assert check_high_leverage_flag(8.5, company_id=fin_ticker) is False
        # Full parameters
        assert (
            check_high_leverage_flag(
                8.5, broad_sector="Financials", company_id=fin_ticker
            )
            is False
        )


def test_icr_banking_template_returns_none_with_correct_label() -> None:
    """Verify ICR returns None with 'Not Applicable (Banking Template)' for banking templates."""
    # Direct function test with is_banking_template=True
    res_direct = compute_interest_coverage(
        operating_profit=50000.0,
        other_income=2000.0,
        interest=10000.0,
        is_banking_template=True,
    )
    assert res_direct["value"] is None
    assert res_direct["label"] == "Not Applicable (Banking Template)"
    assert res_direct["risk_flag"] is False

    # Direct function test with banking company_id
    for bank_id in ["AXISBANK", "HDFCBANK", "SBIN", "BAJFINANCE"]:
        res_bank = compute_interest_coverage(
            operating_profit=45000.0,
            other_income=1500.0,
            interest=8000.0,
            company_id=bank_id,
        )
        assert res_bank["value"] is None
        assert res_bank["label"] == "Not Applicable (Banking Template)"
        assert res_bank["risk_flag"] is False


def test_icr_interest_zero_returns_none_with_debtfree_label() -> None:
    """Verify ICR returns None with 'Debt Free' label when interest is zero or None."""
    # Zero interest
    res_zero = compute_interest_coverage(
        operating_profit=1000.0,
        other_income=200.0,
        interest=0.0,
        company_id="INFY",
    )
    assert res_zero["value"] is None
    assert res_zero["label"] == "Debt Free"
    assert res_zero["risk_flag"] is False

    # None interest
    res_none = compute_interest_coverage(
        operating_profit=1000.0,
        other_income=200.0,
        interest=None,
        company_id="TCS",
    )
    assert res_none["value"] is None
    assert res_none["label"] == "Debt Free"
    assert res_none["risk_flag"] is False


def test_icr_normal_and_risk_flag() -> None:
    """Verify standard ICR computation and warning risk flag when ICR < 1.5."""
    # Normal safe ICR: (1000 + 200) / 300 = 4.0 -> safe
    res_safe = compute_interest_coverage(
        operating_profit=1000.0,
        other_income=200.0,
        interest=300.0,
        company_id="RELIANCE",
    )
    assert res_safe["value"] == 4.0
    assert res_safe["label"] == "Normal"
    assert res_safe["risk_flag"] is False

    # High risk ICR: (100 + 20) / 100 = 1.2 (< 1.5) -> risk_flag = True
    res_risky = compute_interest_coverage(
        operating_profit=100.0,
        other_income=20.0,
        interest=100.0,
        company_id="RISKCO",
    )
    assert res_risky["value"] == 1.2
    assert res_risky["label"] == "Normal"
    assert res_risky["risk_flag"] is True


def test_net_debt_normal_and_cash_rich() -> None:
    """Verify Net Debt as borrowings - investments, handling cash-rich companies and missing data."""
    # Indebted company: borrowings > investments
    assert compute_net_debt(borrowings=1000.0, investments=300.0) == 700.0
    # Cash-rich / Net-cash company: investments > borrowings
    assert compute_net_debt(borrowings=200.0, investments=500.0) == -300.0
    # Zero debt with investments
    assert compute_net_debt(borrowings=0.0, investments=450.0) == -450.0
    # Borrowings with zero investments
    assert compute_net_debt(borrowings=800.0, investments=0.0) == 800.0
    assert compute_net_debt(borrowings=800.0, investments=None) == 800.0
    # Missing borrowings (e.g. SBIN) -> returns None
    assert compute_net_debt(borrowings=None, investments=500.0) is None


def test_asset_turnover_normal_and_zero_assets() -> None:
    """Verify Asset Turnover as sales / total_assets, returning None if total_assets <= 0."""
    # Normal computation: 5000 / 10000 = 0.5
    assert compute_asset_turnover(5000.0, 10000.0) == 0.5
    # Zero or negative assets -> None
    assert compute_asset_turnover(5000.0, 0.0) is None
    assert compute_asset_turnover(5000.0, -100.0) is None
    # Missing sales or assets -> None
    assert compute_asset_turnover(None, 10000.0) is None
    assert compute_asset_turnover(5000.0, None) is None


# =============================================================================
# INTEGRATION TESTS ON REAL DATA
# =============================================================================


def test_jiofin_profitability_clean_metrics() -> None:
    """Verify JIOFIN computes real OPM=84.04% and ROCE=1.10% with sector_relative=True."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_jiofin = get_financial_statements_data(company_id="JIOFIN", db_path=DB_PATH)
    assert not df_jiofin.empty

    metrics_df = calculate_profitability_metrics(df_jiofin)
    assert not metrics_df.empty

    row_2024 = metrics_df[metrics_df["year"] == "2024-03"].iloc[0]
    assert row_2024["pl_normalization_status"] == "CLEAN_FINANCIAL"
    assert row_2024["npm_pct"] == pytest.approx(86.52, abs=0.01)
    assert row_2024["opm_pct"] == pytest.approx(84.04, abs=0.01)
    assert row_2024["roe_pct"] == pytest.approx(1.15, abs=0.01)
    assert row_2024["roce_pct"] == pytest.approx(1.10, abs=0.01)
    assert bool(row_2024["roce_sector_relative"]) is True
    # Day 9 leverage metrics
    assert row_2024["debt_to_equity"] == 0.0  # Zero borrowings -> 0.0
    assert bool(row_2024["high_leverage_flag"]) is False
    assert row_2024["icr"] is not None
    assert row_2024["icr_label"] == "Normal"
    assert bool(row_2024["icr_risk_flag"]) is False
    assert row_2024["net_debt"] < 0  # Investments > Borrowings


def test_irfc_clean_financials_leverage_and_icr() -> None:
    """Verify IRFC computes valid high D/E with high_leverage_flag=False (Financials exemption), while ICR risk flag triggers."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_irfc = get_financial_statements_data(company_id="IRFC", db_path=DB_PATH)
    assert not df_irfc.empty

    metrics_df = calculate_profitability_metrics(df_irfc)
    row_2024 = metrics_df[metrics_df["year"] == "2024-03"].iloc[0]

    assert row_2024["pl_normalization_status"] == "CLEAN_FINANCIAL"
    assert row_2024["debt_to_equity"] > 5.0
    # Sector-based exemption: lenders/NBFCs do not trigger misleading high leverage risk
    assert bool(row_2024["high_leverage_flag"]) is False
    # ICR < 1.5 risk flag remains active and unaffected
    assert row_2024["icr"] is not None
    assert row_2024["icr"] == pytest.approx(1.32, abs=0.01)
    assert row_2024["icr_label"] == "Normal"
    assert bool(row_2024["icr_risk_flag"]) is True


def test_recltd_clean_financials_leverage_and_icr() -> None:
    """Verify RECLTD computes high D/E with high_leverage_flag=False (Financials exemption) and valid ICR."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_rec = get_financial_statements_data(company_id="RECLTD", db_path=DB_PATH)
    assert not df_rec.empty

    metrics_df = calculate_profitability_metrics(df_rec)
    row_2024 = metrics_df[metrics_df["year"] == "2024-03"].iloc[0]

    assert row_2024["pl_normalization_status"] == "CLEAN_FINANCIAL"
    assert row_2024["debt_to_equity"] > 5.0
    # Sector-based exemption
    assert bool(row_2024["high_leverage_flag"]) is False
    assert row_2024["icr"] is not None
    assert row_2024["icr"] == pytest.approx(1.60, abs=0.01)
    assert row_2024["icr_label"] == "Normal"
    assert bool(row_2024["icr_risk_flag"]) is False


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
    assert row_2024["asset_turnover"] is not None
    assert row_2024["debt_to_equity"] == pytest.approx(0.02, abs=0.01)
    assert bool(row_2024["high_leverage_flag"]) is False


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
    assert row_2024["debt_to_equity"] == pytest.approx(0.02, abs=0.01)
    assert bool(row_2024["high_leverage_flag"]) is False
    assert row_2024["icr"] is not None
    assert row_2024["icr_label"] == "Normal"


def test_axisbank_profitability_banking_separation() -> None:
    """Verify AXISBANK computes valid NPM/ROE/ROA but returns None for OPM and ROCE."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_axis = get_financial_statements_data(company_id="AXISBANK", db_path=DB_PATH)
    assert not df_axis.empty

    metrics_df = calculate_profitability_metrics(df_axis)
    row_2024 = metrics_df[metrics_df["year"] == "2024-03"].iloc[0]

    assert row_2024["pl_normalization_status"] == "BANKING_TEMPLATE_FINANCIAL"
    assert row_2024["npm_pct"] == pytest.approx(22.73, abs=0.01)
    assert row_2024["opm_pct"] is None
    assert row_2024["roe_pct"] == pytest.approx(15.83, abs=0.01)
    assert row_2024["roce_pct"] is None
    assert bool(row_2024["roce_sector_relative"]) is True
    assert row_2024["roa_pct"] == pytest.approx(1.64, abs=0.01)
    assert bool(row_2024["extreme_magnitude_flag"]) is False
    # Day 9 leverage metrics
    assert (
        bool(row_2024["high_leverage_flag"]) is False
    )  # Exempt from Financials broad sector
    assert row_2024["icr"] is None
    assert row_2024["icr_label"] == "Not Applicable (Banking Template)"
    assert bool(row_2024["icr_risk_flag"]) is False


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
        # Day 9 BS-dependent & ICR metrics
        assert row["debt_to_equity"] is None
        assert bool(row["high_leverage_flag"]) is False
        assert row["icr"] is None
        assert row["icr_label"] == "Not Applicable (Banking Template)"
        assert bool(row["icr_risk_flag"]) is False
        assert row["net_debt"] is None
        assert row["asset_turnover"] is None

def test_bel_hal_unreliable_balancesheet_neutralized() -> None:
    """Verify BEL and HAL balance sheet ratios are neutralized to None with data_quality_flag=True."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    for cid in ["BEL", "HAL"]:
        df_co = get_financial_statements_data(company_id=cid, db_path=DB_PATH)
        assert not df_co.empty
        metrics_df = calculate_profitability_metrics(df_co)
        assert not metrics_df.empty

        for _, row in metrics_df.iterrows():
            assert row["roe_pct"] is None
            assert row["roce_pct"] is None
            assert row["roa_pct"] is None
            assert row["debt_to_equity"] is None
            assert bool(row["high_leverage_flag"]) is False
            assert row["asset_turnover"] is None
            assert bool(row["extreme_magnitude_flag"]) is True
            assert bool(row["data_quality_flag"]) is True
            assert row["data_quality_label"] == "Unreliable Balance Sheet Data"
