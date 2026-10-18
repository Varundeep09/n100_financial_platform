"""Unit tests for CAGR calculation engine (Revenue, PAT, EPS - 3yr/5yr/10yr).

Includes tests for:
- Standard CAGR formula
- All 6 edge case flags per Section 23.1:
  1. Positive base, Positive end -> Normal computation
  2. Positive base, Negative end -> None, 'DECLINE_TO_LOSS'
  3. Negative base, Positive end -> None, 'TURNAROUND'
  4. Negative base, Negative end -> None, 'BOTH_NEGATIVE'
  5. Zero base                  -> None, 'ZERO_BASE'
  6. Less than n years of data  -> None, 'INSUFFICIENT'
- JIOFIN: limited history (< 3 years) -> all return None with flag='INSUFFICIENT'
- Banking-template companies (AXISBANK/HDFCBANK): revenue/PAT/EPS CAGR works normally despite OPM=None
- Real loss-making company (TATASTEEL): 'DECLINE_TO_LOSS'
- Real turnaround company (TATAMOTORS): 'TURNAROUND'
- Pipeline column structure verification
"""

from pathlib import Path

import pandas as pd
import pytest

from src.analytics.cagr import (
    calculate_cagr,
    calculate_cagr_metrics,
    get_pl_cagr_data,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "nifty100.db"


# =============================================================================
# UNIT TESTS: FORMULA & EDGE CASES
# =============================================================================


def test_cagr_formula_normal() -> None:
    """Verify standard CAGR calculation with positive start and end values."""
    # 100 to 200 over 3 years: (200/100)^(1/3) - 1 = 25.9921%
    val, flag = calculate_cagr(100.0, 200.0, 3)
    assert val == pytest.approx(25.9921, abs=0.0001)
    assert flag is None

    # 50,000 to 100,000 over 5 years: (100000/50000)^(1/5) - 1 = 14.8698%
    val, flag = calculate_cagr(50000.0, 100000.0, 5)
    assert val == pytest.approx(14.8698, abs=0.0001)
    assert flag is None


def test_cagr_edge_case_decline_to_loss() -> None:
    """Verify positive base to negative/zero end triggers DECLINE_TO_LOSS."""
    val, flag = calculate_cagr(100.0, -20.0, 3)
    assert val is None
    assert flag == "DECLINE_TO_LOSS"

    # End value drops to exactly 0
    val_zero_end, flag_zero_end = calculate_cagr(100.0, 0.0, 3)
    assert val_zero_end is None
    assert flag_zero_end == "DECLINE_TO_LOSS"


def test_cagr_edge_case_turnaround() -> None:
    """Verify negative base to positive/zero end triggers TURNAROUND."""
    val, flag = calculate_cagr(-50.0, 100.0, 3)
    assert val is None
    assert flag == "TURNAROUND"

    # From negative to breakeven (0)
    val_be, flag_be = calculate_cagr(-50.0, 0.0, 3)
    assert val_be is None
    assert flag_be == "TURNAROUND"


def test_cagr_edge_case_both_negative() -> None:
    """Verify negative base to negative end triggers BOTH_NEGATIVE."""
    val, flag = calculate_cagr(-50.0, -100.0, 3)
    assert val is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_edge_case_zero_base() -> None:
    """Verify zero base triggers ZERO_BASE flag."""
    val, flag = calculate_cagr(0.0, 100.0, 3)
    assert val is None
    assert flag == "ZERO_BASE"

    val_zero, flag_zero = calculate_cagr(0.0, 0.0, 5)
    assert val_zero is None
    assert flag_zero == "ZERO_BASE"


def test_cagr_edge_case_insufficient_periods() -> None:
    """Verify missing values or invalid period triggers INSUFFICIENT flag."""
    # Missing base
    val, flag = calculate_cagr(None, 100.0, 3)
    assert val is None
    assert flag == "INSUFFICIENT"

    # Missing end
    val, flag = calculate_cagr(100.0, None, 3)
    assert val is None
    assert flag == "INSUFFICIENT"

    # Invalid period (<= 0)
    val, flag = calculate_cagr(100.0, 200.0, 0)
    assert val is None
    assert flag == "INSUFFICIENT"


# =============================================================================
# INTEGRATION TESTS ON REAL DATA
# =============================================================================


def test_cagr_jiofin_insufficient_real_data() -> None:
    """Verify JIOFIN (< 3 years of history) returns None with INSUFFICIENT for all windows."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_jiofin = get_pl_cagr_data(company_id="JIOFIN", db_path=DB_PATH)
    assert not df_jiofin.empty
    assert len(df_jiofin) < 3  # Confirmed only 2 years (FY23 and FY24)

    cagr_df = calculate_cagr_metrics(df_jiofin)
    assert not cagr_df.empty

    latest_row = cagr_df.iloc[-1]
    for w in [3, 5, 10]:
        assert pd.isna(latest_row[f"revenue_cagr_{w}yr"])
        assert latest_row[f"revenue_cagr_{w}yr_flag"] == "INSUFFICIENT"
        assert pd.isna(latest_row[f"pat_cagr_{w}yr"])
        assert latest_row[f"pat_cagr_{w}yr_flag"] == "INSUFFICIENT"
        assert pd.isna(latest_row[f"eps_cagr_{w}yr"])
        assert latest_row[f"eps_cagr_{w}yr_flag"] == "INSUFFICIENT"


def test_cagr_banking_template_normal_real_data() -> None:
    """Verify banking-template company (AXISBANK) computes normal CAGR despite OPM=None."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_axis = get_pl_cagr_data(company_id="AXISBANK", db_path=DB_PATH)
    assert not df_axis.empty

    cagr_df = calculate_cagr_metrics(df_axis)
    latest_row = cagr_df[cagr_df["year"] == "2024-03"].iloc[0]

    # Revenue CAGR 3yr should be valid positive number (~19.97%)
    assert not pd.isna(latest_row["revenue_cagr_3yr"])
    assert latest_row["revenue_cagr_3yr"] == pytest.approx(19.966, abs=0.01)
    assert pd.isna(latest_row["revenue_cagr_3yr_flag"])

    # PAT CAGR 3yr should be valid positive number (~55.69%)
    assert not pd.isna(latest_row["pat_cagr_3yr"])
    assert latest_row["pat_cagr_3yr"] == pytest.approx(55.688, abs=0.01)
    assert pd.isna(latest_row["pat_cagr_3yr_flag"])

    # EPS CAGR 3yr should be valid positive number (~54.41%)
    assert not pd.isna(latest_row["eps_cagr_3yr"])
    assert latest_row["eps_cagr_3yr"] == pytest.approx(54.414, abs=0.01)
    assert pd.isna(latest_row["eps_cagr_3yr_flag"])


def test_cagr_loss_making_company_real_data() -> None:
    """Verify TATASTEEL (net loss in FY24) triggers DECLINE_TO_LOSS for PAT CAGR."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_tata = get_pl_cagr_data(company_id="TATASTEEL", db_path=DB_PATH)
    assert not df_tata.empty

    cagr_df = calculate_cagr_metrics(df_tata)
    latest_row = cagr_df[cagr_df["year"] == "2024-03"].iloc[0]

    # Revenue was positive and grew normally
    assert not pd.isna(latest_row["revenue_cagr_3yr"])
    assert pd.isna(latest_row["revenue_cagr_3yr_flag"])

    # PAT fell from +8,190 Cr in FY21 to -4,910 Cr in FY24
    assert pd.isna(latest_row["pat_cagr_3yr"])
    assert latest_row["pat_cagr_3yr_flag"] == "DECLINE_TO_LOSS"
    assert pd.isna(latest_row["pat_cagr_5yr"])
    assert latest_row["pat_cagr_5yr_flag"] == "DECLINE_TO_LOSS"


def test_cagr_turnaround_company_real_data() -> None:
    """Verify TATAMOTORS (loss in FY21, profit in FY24) triggers TURNAROUND for PAT CAGR."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_tm = get_pl_cagr_data(company_id="TATAMOTORS", db_path=DB_PATH)
    assert not df_tm.empty

    cagr_df = calculate_cagr_metrics(df_tm)
    latest_row = cagr_df[cagr_df["year"] == "2024-03"].iloc[0]

    # PAT rose from -13,395 Cr in FY21 to +31,807 Cr in FY24
    assert pd.isna(latest_row["pat_cagr_3yr"])
    assert latest_row["pat_cagr_3yr_flag"] == "TURNAROUND"
    assert pd.isna(latest_row["pat_cagr_5yr"])
    assert latest_row["pat_cagr_5yr_flag"] == "TURNAROUND"


def test_cagr_dataframe_pipeline_column_structure() -> None:
    """Verify calculate_cagr_metrics generates all 18 required CAGR value and flag columns."""
    sample_data = {
        "company_id": ["TESTCO"] * 12,
        "year": [f"{2013 + i}-03" for i in range(12)],
        "sales": [100.0 * (1.1**i) for i in range(12)],
        "net_profit": [10.0 * (1.15**i) for i in range(12)],
        "eps": [1.0 * (1.12**i) for i in range(12)],
    }
    df = pd.DataFrame(sample_data)
    res_df = calculate_cagr_metrics(df)

    expected_columns = [
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
    ]
    for col in expected_columns:
        assert col in res_df.columns

    # Verify latest year (index 11) has computed values for 3, 5, 10
    latest = res_df.iloc[-1]
    assert latest["revenue_cagr_3yr"] == pytest.approx(10.0, abs=0.01)
    assert latest["pat_cagr_3yr"] == pytest.approx(15.0, abs=0.01)
    assert latest["eps_cagr_3yr"] == pytest.approx(12.0, abs=0.01)
    assert latest["revenue_cagr_10yr"] == pytest.approx(10.0, abs=0.01)


def test_cagr_year_gap_handling_ambujacem_regression() -> None:
    """Verify gap in AMBUJACEM's sequence returns INSUFFICIENT instead of misaligned row-offset calculation."""
    if not DB_PATH.exists():
        pytest.skip("Database db/nifty100.db not present")

    df_ambuja = get_pl_cagr_data(company_id="AMBUJACEM", db_path=DB_PATH)
    assert not df_ambuja.empty

    cagr_df = calculate_cagr_metrics(df_ambuja)

    # 1. Row 2021-12 had 2018-12 (exact 3 years prior) -> computes normally (~3.61%)
    row_2021 = cagr_df[cagr_df["year"] == "2021-12"].iloc[0]
    assert not pd.isna(row_2021["revenue_cagr_3yr"])
    assert row_2021["revenue_cagr_3yr"] == pytest.approx(3.6109, abs=0.01)
    assert pd.isna(row_2021["revenue_cagr_3yr_flag"])

    # 2. Row 2023-03: candidate 2020-03 does not exist (2022 skipped) -> INSUFFICIENT (not misaligned against 2019-12)
    row_2023 = cagr_df[cagr_df["year"] == "2023-03"].iloc[0]
    assert pd.isna(row_2023["revenue_cagr_3yr"])
    assert row_2023["revenue_cagr_3yr_flag"] == "INSUFFICIENT"

    # 3. Row 2024-03: candidate 2021-03 does not exist -> INSUFFICIENT
    row_2024 = cagr_df[cagr_df["year"] == "2024-03"].iloc[0]
    assert pd.isna(row_2024["revenue_cagr_3yr"])
    assert row_2024["revenue_cagr_3yr_flag"] == "INSUFFICIENT"
