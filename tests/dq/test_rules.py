"""Unit tests for all 16 Data Quality (DQ) validation rules (Sprint 1, Day 3)."""

import pandas as pd

from src.etl.validator import (
    validate_dq01_company_pk_uniqueness,
    validate_dq02_annual_pk_uniqueness,
    validate_dq03_fk_integrity,
    validate_dq04_bs_balance,
    validate_dq05_opm_cross_check,
    validate_dq06_positive_sales,
    validate_dq07_year_format,
    validate_dq08_ticker_format,
    validate_dq09_net_cash_check,
    validate_dq10_non_negative_fixed_assets,
    validate_dq11_tax_rate_range,
    validate_dq12_dividend_payout_cap,
    validate_dq13_url_validity,
    validate_dq14_eps_sign_consistency,
    validate_dq15_strict_bs_balance,
    validate_dq16_coverage_check,
)

# ---------------------------------------------------------------------------
# DQ-01: Company PK Uniqueness
# ---------------------------------------------------------------------------


def test_dq01_company_pk_unique_pass() -> None:
    """Verify unique company IDs pass DQ-01 validation."""
    df = pd.DataFrame({"id": ["TCS", "INFY", "HDFCBANK"]})
    failures = validate_dq01_company_pk_uniqueness(df)
    assert len(failures) == 0


def test_dq01_company_pk_unique_fail() -> None:
    """Verify duplicate company ID triggers DQ-01 CRITICAL failure."""
    df = pd.DataFrame({"id": ["TCS", "INFY", "TCS"]})
    failures = validate_dq01_company_pk_uniqueness(df)
    assert len(failures) == 2
    assert failures[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# DQ-02: Annual PK Uniqueness
# ---------------------------------------------------------------------------


def test_dq02_annual_pk_unique_pass() -> None:
    """Verify unique (company_id, year) tuples pass DQ-02 validation."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS", "INFY"],
            "year": ["2023-03", "2024-03", "2023-03"],
        }
    )
    failures = validate_dq02_annual_pk_uniqueness(df, "profitandloss")
    assert len(failures) == 0


def test_dq02_annual_pk_unique_fail() -> None:
    """Verify duplicate (company_id, year) triggers DQ-02 CRITICAL failure."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS"],
            "year": ["2023-03", "Mar 2023"],
        }
    )
    failures = validate_dq02_annual_pk_uniqueness(df, "profitandloss")
    assert len(failures) == 1
    assert failures[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# DQ-03: FK Integrity
# ---------------------------------------------------------------------------


def test_dq03_fk_integrity_pass() -> None:
    """Verify child rows with valid parent company IDs pass DQ-03."""
    df = pd.DataFrame({"company_id": ["TCS", "INFY"], "year": ["2023", "2023"]})
    valid_ids = {"TCS", "INFY", "HDFCBANK"}
    failures = validate_dq03_fk_integrity(df, valid_ids, "profitandloss")
    assert len(failures) == 0


def test_dq03_fk_integrity_fail() -> None:
    """Verify orphan child rows trigger DQ-03 CRITICAL failure."""
    df = pd.DataFrame({"company_id": ["TCS", "UNKNOWN_CO"], "year": ["2023", "2023"]})
    valid_ids = {"TCS", "INFY"}
    failures = validate_dq03_fk_integrity(df, valid_ids, "profitandloss")
    assert len(failures) == 1
    assert failures[0].severity == "CRITICAL"
    assert "UNKNOWN_CO" in failures[0].issue


# ---------------------------------------------------------------------------
# DQ-04: Balance Sheet Balance (Spec Test Case)
# ---------------------------------------------------------------------------


def test_dq04_bs_balance_pass() -> None:
    """Verify balanced balance sheet passes DQ-04 validation."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "total_assets": [1000.0],
            "total_liabilities": [1000.0],
        }
    )
    failures = validate_dq04_bs_balance(df, tolerance=0.01)
    assert len(failures) == 0


def test_dq04_bs_balance() -> None:
    """Verify spec example: assets=1000, liab=1020 triggers DQ-04 WARNING."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "total_assets": [1000.0],
            "total_liabilities": [1020.0],
        }
    )
    failures = validate_dq04_bs_balance(df, tolerance=0.01)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-05: OPM Cross-Check
# ---------------------------------------------------------------------------


def test_dq05_opm_cross_check_pass() -> None:
    """Verify consistent OPM percentage passes DQ-05 validation."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "sales": [1000.0],
            "operating_profit": [250.0],
            "opm_percentage": [25.0],
        }
    )
    failures = validate_dq05_opm_cross_check(df, tolerance=1.0)
    assert len(failures) == 0


def test_dq05_opm_cross_check_fail() -> None:
    """Verify inconsistent reported OPM triggers DQ-05 WARNING."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "sales": [1000.0],
            "operating_profit": [250.0],
            "opm_percentage": [30.0],
        }
    )
    failures = validate_dq05_opm_cross_check(df, tolerance=1.0)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-06: Positive Sales (Spec Test Case)
# ---------------------------------------------------------------------------


def test_dq06_positive_sales_pass() -> None:
    """Verify positive sales for non-bank company passes DQ-06."""
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["2023-03"], "sales": [100.0]})
    failures = validate_dq06_positive_sales(df, bank_company_ids={"HDFCBANK"})
    assert len(failures) == 0


def test_dq06_zero_sales() -> None:
    """Verify spec example: sales=0 for non-bank company triggers DQ-06 WARNING."""
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["2023-03"], "sales": [0.0]})
    failures = validate_dq06_positive_sales(df, bank_company_ids={"HDFCBANK"})
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


def test_dq06_bank_zero_sales_carveout() -> None:
    """Verify bank company with zero/negative sales is carved out from DQ-06."""
    df = pd.DataFrame({"company_id": ["HDFCBANK"], "year": ["2023-03"], "sales": [0.0]})
    failures = validate_dq06_positive_sales(df, bank_company_ids={"HDFCBANK"})
    assert len(failures) == 0


# ---------------------------------------------------------------------------
# DQ-07: Year Format
# ---------------------------------------------------------------------------


def test_dq07_year_format_pass() -> None:
    """Verify valid year strings pass DQ-07 validation."""
    df = pd.DataFrame({"company_id": ["TCS", "INFY"], "year": ["Mar-23", "2023-03"]})
    failures = validate_dq07_year_format(df, "profitandloss")
    assert len(failures) == 0


def test_dq07_year_format_fail() -> None:
    """Verify unparseable year string triggers DQ-07 CRITICAL failure."""
    df = pd.DataFrame({"company_id": ["TCS"], "year": ["xyz"]})
    failures = validate_dq07_year_format(df, "profitandloss")
    assert len(failures) == 1
    assert failures[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# DQ-08: Ticker Format
# ---------------------------------------------------------------------------


def test_dq08_ticker_format_pass() -> None:
    """Verify valid ticker symbols pass DQ-08 validation."""
    df = pd.DataFrame({"company_id": ["TCS", "BAJAJ-AUTO", "M&M"]})
    failures = validate_dq08_ticker_format(df, "companies")
    assert len(failures) == 0


def test_dq08_ticker_format_fail() -> None:
    """Verify invalid ticker symbol triggers DQ-08 CRITICAL failure."""
    df = pd.DataFrame({"company_id": ["TCS$INC"]})
    failures = validate_dq08_ticker_format(df, "companies")
    assert len(failures) == 1
    assert failures[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# DQ-09: Net Cash Check
# ---------------------------------------------------------------------------


def test_dq09_net_cash_check_pass() -> None:
    """Verify matching net cash components pass DQ-09 validation."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "operating_activity": [100.0],
            "investing_activity": [-50.0],
            "financing_activity": [-40.0],
            "net_cash_flow": [10.0],
        }
    )
    failures = validate_dq09_net_cash_check(df, tolerance=10.0)
    assert len(failures) == 0


def test_dq09_net_cash_check_fail() -> None:
    """Verify cash flow mismatch exceeding tolerance triggers DQ-09 WARNING."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "operating_activity": [100.0],
            "investing_activity": [-50.0],
            "financing_activity": [-40.0],
            "net_cash_flow": [50.0],
        }
    )
    failures = validate_dq09_net_cash_check(df, tolerance=10.0)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-10: Non-Negative Fixed Assets
# ---------------------------------------------------------------------------


def test_dq10_non_negative_fixed_assets_pass() -> None:
    """Verify non-negative fixed assets pass DQ-10 validation."""
    df = pd.DataFrame(
        {"company_id": ["TCS"], "year": ["2023-03"], "fixed_assets": [500.0]}
    )
    failures = validate_dq10_non_negative_fixed_assets(df)
    assert len(failures) == 0


def test_dq10_non_negative_fixed_assets_fail() -> None:
    """Verify negative fixed assets trigger DQ-10 WARNING."""
    df = pd.DataFrame(
        {"company_id": ["TCS"], "year": ["2023-03"], "fixed_assets": [-10.0]}
    )
    failures = validate_dq10_non_negative_fixed_assets(df)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-11: Tax Rate Range
# ---------------------------------------------------------------------------


def test_dq11_tax_rate_range_pass() -> None:
    """Verify tax rate within [0, 60]% passes DQ-11 validation."""
    df = pd.DataFrame(
        {"company_id": ["TCS"], "year": ["2023-03"], "tax_percentage": [25.0]}
    )
    failures = validate_dq11_tax_rate_range(df, max_tax_pct=60.0)
    assert len(failures) == 0


def test_dq11_tax_rate_range_fail() -> None:
    """Verify tax rate outside [0, 60]% triggers DQ-11 WARNING."""
    df = pd.DataFrame(
        {"company_id": ["TCS"], "year": ["2023-03"], "tax_percentage": [75.0]}
    )
    failures = validate_dq11_tax_rate_range(df, max_tax_pct=60.0)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-12: Dividend Payout Cap
# ---------------------------------------------------------------------------


def test_dq12_dividend_payout_cap_pass() -> None:
    """Verify dividend payout <= 200% passes DQ-12 validation."""
    df = pd.DataFrame(
        {"company_id": ["TCS"], "year": ["2023-03"], "dividend_payout": [45.0]}
    )
    failures = validate_dq12_dividend_payout_cap(df, max_payout=200.0)
    assert len(failures) == 0


def test_dq12_dividend_payout_cap_fail() -> None:
    """Verify dividend payout > 200% triggers DQ-12 WARNING."""
    df = pd.DataFrame(
        {"company_id": ["TCS"], "year": ["2023-03"], "dividend_payout": [250.0]}
    )
    failures = validate_dq12_dividend_payout_cap(df, max_payout=200.0)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-13: URL Validity
# ---------------------------------------------------------------------------


def test_dq13_url_validity_structure() -> None:
    """Verify malformed URL structure triggers DQ-13 WARNING."""
    df = pd.DataFrame(
        {"company_id": ["TCS"], "Year": ["2023"], "Annual_Report": ["not_a_url"]}
    )
    failures = validate_dq13_url_validity(df, check_live=False)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-14: EPS Sign Consistency
# ---------------------------------------------------------------------------


def test_dq14_eps_sign_consistency_pass() -> None:
    """Verify matching signs for net profit and EPS pass DQ-14 validation."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "net_profit": [100.0],
            "eps": [15.0],
        }
    )
    failures = validate_dq14_eps_sign_consistency(df)
    assert len(failures) == 0


def test_dq14_eps_sign_consistency_fail() -> None:
    """Verify conflicting signs between net profit and EPS trigger DQ-14 WARNING."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "net_profit": [100.0],
            "eps": [-5.0],
        }
    )
    failures = validate_dq14_eps_sign_consistency(df)
    assert len(failures) == 1
    assert failures[0].severity == "WARNING"


# ---------------------------------------------------------------------------
# DQ-15: Strict Balance Sheet Balance
# ---------------------------------------------------------------------------


def test_dq15_strict_bs_balance() -> None:
    """Verify strict inequality between assets and liabilities generates INFO flag."""
    df = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2023-03"],
            "total_assets": [1000.0],
            "total_liabilities": [999.0],
        }
    )
    failures = validate_dq15_strict_bs_balance(df)
    assert len(failures) == 1
    assert failures[0].severity == "INFO"


# ---------------------------------------------------------------------------
# DQ-16: Coverage Check
# ---------------------------------------------------------------------------


def test_dq16_coverage_check_pass() -> None:
    """Verify company with >= 5 years of records passes DQ-16."""
    years = ["2019-03", "2020-03", "2021-03", "2022-03", "2023-03"]
    df = pd.DataFrame({"company_id": ["TCS"] * 5, "year": years})
    failures = validate_dq16_coverage_check(
        pl_df=df,
        bs_df=df,
        cf_df=df,
        valid_company_ids={"TCS"},
        min_years=5,
    )
    assert len(failures) == 0


def test_dq16_coverage_check_fail() -> None:
    """Verify company with < 5 years of records triggers DQ-16 WARNING."""
    df = pd.DataFrame(
        {"company_id": ["NEWCO", "NEWCO"], "year": ["2022-03", "2023-03"]}
    )
    failures = validate_dq16_coverage_check(
        pl_df=df,
        bs_df=df,
        cf_df=df,
        valid_company_ids={"NEWCO"},
        min_years=5,
    )
    assert len(failures) == 3
    assert all(f.severity == "WARNING" for f in failures)
