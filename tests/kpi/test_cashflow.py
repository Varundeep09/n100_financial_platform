"""Unit tests for Cash Flow KPIs and Capital Allocation Classifier (Sprint 2, Day 11).

Covers:
1. Free Cash Flow (FCF) calculation and negative FCF preservation.
2. CFO Quality Score trailing 5-year average, threshold labels, and exact year-gap handling.
3. CapEx Intensity ratio and classifications (Asset Light, Moderate, Capital Intensive).
4. FCF Conversion Rate calculation, zero/missing operating profit handling, and banking-template exclusion.
5. Capital allocation 8-pattern classification logic across all sign combinations.
6. Real company database tests (SBIN, AXISBANK, TCS, RELIANCE, IRFC, AMBUJACEM).
7. Processed CSV export integrity (1063 rows, valid column schema).
"""

import pandas as pd

from src.analytics.cashflow_kpis import (
    calculate_cashflow_kpis,
    classify_capital_allocation,
    compute_capex_intensity,
    compute_cfo_quality_score,
    compute_fcf,
    compute_fcf_conversion,
    generate_capital_allocation_csv,
    get_cashflow_data,
)


def test_fcf_normal_and_negative_preserved():
    """Verify FCF computation and confirm negative FCF is strictly preserved, not nulled."""
    # Normal positive FCF
    assert compute_fcf(500.0, -200.0) == 300.0

    # Negative FCF (e.g. heavy CapEx or negative operating cash)
    neg_fcf = compute_fcf(100.0, -600.0)
    assert neg_fcf == -500.0
    assert neg_fcf is not None
    assert neg_fcf < 0

    # Large negative FCF (e.g. RELIANCE FY21 scale)
    large_neg = compute_fcf(-20000.0, -95000.0)
    assert large_neg == -115000.0

    # Null/missing handling
    assert compute_fcf(None, -100.0) is None
    assert compute_fcf(100.0, None) is None
    assert compute_fcf(float("nan"), -100.0) is None


def test_cfo_quality_score_thresholds():
    """Test CFO Quality Score (trailing 5yr CFO/PAT) classification thresholds."""
    # High Quality: > 1.0
    res_high = compute_cfo_quality_score([120.0] * 5, [100.0] * 5)
    assert res_high.value == 1.2
    assert res_high.label == "High Quality"

    # Moderate: 0.5 - 1.0 (boundary check at exactly 0.5 and 1.0)
    res_mod = compute_cfo_quality_score([75.0] * 5, [100.0] * 5)
    assert res_mod.value == 0.75
    assert res_mod.label == "Moderate"

    res_mod_b1 = compute_cfo_quality_score([50.0] * 5, [100.0] * 5)
    assert res_mod_b1.value == 0.5
    assert res_mod_b1.label == "Moderate"

    res_mod_b2 = compute_cfo_quality_score([100.0] * 5, [100.0] * 5)
    assert res_mod_b2.value == 1.0
    assert res_mod_b2.label == "Moderate"

    # Accrual Risk: < 0.5
    res_risk = compute_cfo_quality_score([30.0] * 5, [100.0] * 5)
    assert res_risk.value == 0.3
    assert res_risk.label == "Accrual Risk"

    res_neg = compute_cfo_quality_score([-10.0] * 5, [100.0] * 5)
    assert res_neg.value == -0.1
    assert res_neg.label == "Accrual Risk"


def test_cfo_quality_score_edge_cases_and_gap_windowing():
    """Verify CFO Quality Score returns None if PAT = 0 in any year, or if < 5 years of history exist."""
    # PAT = 0 in one of the 5 years -> must return None, not divide by zero
    res_zero = compute_cfo_quality_score(
        [100.0, 110.0, 120.0, 130.0, 140.0], [80.0, 90.0, 0.0, 100.0, 110.0]
    )
    assert res_zero.value is None
    assert res_zero.label is None

    # Fewer than 5 years of history -> None
    res_short = compute_cfo_quality_score([100.0, 110.0, 120.0], [80.0, 90.0, 100.0])
    assert res_short.value is None
    assert res_short.label is None

    # None in inputs
    res_none = compute_cfo_quality_score(
        [100.0, 110.0, None, 130.0, 140.0], [80.0, 90.0, 100.0, 100.0, 110.0]
    )
    assert res_none.value is None
    assert res_none.label is None


def test_capex_intensity_thresholds():
    """Verify CapEx intensity calculation and classification thresholds."""
    # Asset Light: < 3%
    res_light = compute_capex_intensity(-200.0, 10000.0)
    assert res_light.value == 2.0
    assert res_light.label == "Asset Light"

    # Moderate: 3% - 8% (inclusive)
    res_mod = compute_capex_intensity(-500.0, 10000.0)
    assert res_mod.value == 5.0
    assert res_mod.label == "Moderate"

    res_mod_b1 = compute_capex_intensity(-300.0, 10000.0)
    assert res_mod_b1.value == 3.0
    assert res_mod_b1.label == "Moderate"

    res_mod_b2 = compute_capex_intensity(-800.0, 10000.0)
    assert res_mod_b2.value == 8.0
    assert res_mod_b2.label == "Moderate"

    # Capital Intensive: > 8%
    res_heavy = compute_capex_intensity(-1200.0, 10000.0)
    assert res_heavy.value == 12.0
    assert res_heavy.label == "Capital Intensive"

    # Edge cases: zero or negative sales
    assert compute_capex_intensity(-500.0, 0.0).value is None
    assert compute_capex_intensity(-500.0, -100.0).value is None
    assert compute_capex_intensity(None, 10000.0).value is None


def test_fcf_conversion_banking_template_returns_none():
    """Explicitly verify SBIN and other banking-template companies return None with correct label."""
    # SBIN explicitly flagged
    sbin_res = compute_fcf_conversion(
        fcf=18156.0, operating_profit=194547.0, company_id="SBIN"
    )
    assert sbin_res.value is None
    assert sbin_res.label == "Not Applicable (Banking Template)"

    # AXISBANK with is_banking_template=True
    axis_res = compute_fcf_conversion(
        fcf=-14556.0,
        operating_profit=42000.0,
        company_id="AXISBANK",
        is_banking_template=True,
    )
    assert axis_res.value is None
    assert axis_res.label == "Not Applicable (Banking Template)"

    # HDFCBANK
    hdfc_res = compute_fcf_conversion(
        fcf=35669.0, operating_profit=60000.0, company_id="HDFCBANK"
    )
    assert hdfc_res.value is None
    assert hdfc_res.label == "Not Applicable (Banking Template)"


def test_fcf_conversion_clean_companies():
    """Verify FCF Conversion Rate for clean non-financials, negative FCF, and zero operating profit."""
    # Normal healthy conversion (TCS)
    tcs_res = compute_fcf_conversion(
        fcf=50429.0, operating_profit=64296.0, company_id="TCS"
    )
    assert tcs_res.value == 78.4326
    assert tcs_res.label == "Normal"

    # Negative FCF conversion preserved (RELIANCE FY21)
    rel_res = compute_fcf_conversion(
        fcf=-115427.0, operating_profit=80790.0, company_id="RELIANCE"
    )
    assert rel_res.value == -142.8729
    assert rel_res.label == "Normal"

    # Zero operating profit
    zero_op = compute_fcf_conversion(fcf=100.0, operating_profit=0.0, company_id="INFY")
    assert zero_op.value is None
    assert zero_op.label == "Operating Profit Zero"

    # Missing operating profit
    missing_op = compute_fcf_conversion(
        fcf=100.0, operating_profit=None, company_id="INFY"
    )
    assert missing_op.value is None
    assert missing_op.label == "Operating Profit Missing"


def test_capital_allocation_8_pattern_classifier():
    """Verify all 8 capital allocation patterns based on sign of (CFO, CFI, CFF)."""
    # 1. (+,-,-) with High Quality CFO -> Shareholder Returns
    p1 = classify_capital_allocation(
        500.0, -200.0, -150.0, cfo_quality_label="High Quality"
    )
    assert p1.pattern_label == "Shareholder Returns"
    assert (p1.cfo_sign, p1.cfi_sign, p1.cff_sign) == ("+", "-", "-")

    # 2. (+,-,-) without High Quality CFO -> Reinvestor
    p2 = classify_capital_allocation(
        500.0, -200.0, -150.0, cfo_quality_label="Moderate"
    )
    assert p2.pattern_label == "Reinvestor"

    # 3. (+,+,-) -> Liquidating Assets
    p3 = classify_capital_allocation(300.0, 100.0, -200.0)
    assert p3.pattern_label == "Liquidating Assets"
    assert (p3.cfo_sign, p3.cfi_sign, p3.cff_sign) == ("+", "+", "-")

    # 4. (-,+,+) -> Distress Signal
    p4 = classify_capital_allocation(-100.0, 50.0, 80.0)
    assert p4.pattern_label == "Distress Signal"
    assert (p4.cfo_sign, p4.cfi_sign, p4.cff_sign) == ("-", "+", "+")

    # (-,+,-) -> Also Distress Signal (burning cash and liquidating assets to service debt)
    p4b = classify_capital_allocation(-100.0, 50.0, -80.0)
    assert p4b.pattern_label == "Distress Signal"

    # 5. (-,-,+) -> Growth Funded by Debt
    p5 = classify_capital_allocation(-150.0, -300.0, 500.0)
    assert p5.pattern_label == "Growth Funded by Debt"
    assert (p5.cfo_sign, p5.cfi_sign, p5.cff_sign) == ("-", "-", "+")

    # 6. (+,+,+) -> Cash Accumulator
    p6 = classify_capital_allocation(200.0, 50.0, 100.0)
    assert p6.pattern_label == "Cash Accumulator"
    assert (p6.cfo_sign, p6.cfi_sign, p6.cff_sign) == ("+", "+", "+")

    # 7. (-,-,-) -> Pre-Revenue
    p7 = classify_capital_allocation(-50.0, -100.0, -20.0)
    assert p7.pattern_label == "Pre-Revenue"
    assert (p7.cfo_sign, p7.cfi_sign, p7.cff_sign) == ("-", "-", "-")

    # 8. (+,-,+) -> Mixed
    p8 = classify_capital_allocation(400.0, -250.0, 100.0)
    assert p8.pattern_label == "Mixed"
    assert (p8.cfo_sign, p8.cfi_sign, p8.cff_sign) == ("+", "-", "+")

    # Insufficient / NaN data
    p_null = classify_capital_allocation(None, -100.0, 50.0)
    assert p_null.pattern_label == "Insufficient Data"


def test_real_database_ambujacem_exact_gap_windowing():
    """Verify AMBUJACEM fiscal gap (2022 skip) returns None for 5yr CFO Quality Score in 2024-03."""
    df_raw = get_cashflow_data(company_id="AMBUJACEM")
    assert not df_raw.empty

    df_kpi = calculate_cashflow_kpis(df_raw)

    # 2024-03 should have None/NaN for 5yr CFO Quality Score because 2022 was skipped
    row_2024 = df_kpi[df_kpi["year"] == "2024-03"].iloc[0]
    assert pd.isna(row_2024["cfo_quality_score"])
    assert (
        pd.isna(row_2024["cfo_quality_label"]) or row_2024["cfo_quality_label"] is None
    )

    # Pre-gap December years (e.g. 2021-12) with 5 consecutive December years should have valid score
    row_2021 = df_kpi[df_kpi["year"] == "2021-12"].iloc[0]
    assert not pd.isna(row_2021["cfo_quality_score"])
    assert row_2021["cfo_quality_label"] == "High Quality"


def test_real_database_banking_template_exclusion_and_clean_financials():
    """Verify real database computation: banks return None for FCF conversion, while clean financials compute normally."""
    # 1. SBIN (banking template)
    sbin_raw = get_cashflow_data(company_id="SBIN")
    sbin_kpi = calculate_cashflow_kpis(sbin_raw)
    sbin_2024 = sbin_kpi[sbin_kpi["year"] == "2024-03"].iloc[0]
    assert pd.isna(sbin_2024["fcf_conversion_rate"])
    assert sbin_2024["fcf_conversion_label"] == "Not Applicable (Banking Template)"

    # 2. IRFC (clean financials)
    irfc_raw = get_cashflow_data(company_id="IRFC")
    irfc_kpi = calculate_cashflow_kpis(irfc_raw)
    irfc_2024 = irfc_kpi[irfc_kpi["year"] == "2024-03"].iloc[0]
    assert not pd.isna(irfc_2024["fcf_conversion_rate"])
    assert irfc_2024["fcf_conversion_label"] == "Normal"

    # 3. TCS (standard non-financial: FY24 liquidated liquid mutual funds giving (+,+,-))
    tcs_raw = get_cashflow_data(company_id="TCS")
    tcs_kpi = calculate_cashflow_kpis(tcs_raw)
    tcs_2024 = tcs_kpi[tcs_kpi["year"] == "2024-03"].iloc[0]
    assert not pd.isna(tcs_2024["fcf_conversion_rate"])
    assert tcs_2024["capex_intensity_label"] == "Asset Light"
    assert tcs_2024["pattern_label"] == "Liquidating Assets"

    # TCS FY22 (+,-,-) with high quality score -> Shareholder Returns
    tcs_2022 = tcs_kpi[tcs_kpi["year"] == "2022-03"].iloc[0]
    assert tcs_2022["pattern_label"] == "Shareholder Returns"

    # 4. CIPLA FY24 (+,-,-) -> Shareholder Returns
    cipla_raw = get_cashflow_data(company_id="CIPLA")
    cipla_kpi = calculate_cashflow_kpis(cipla_raw)
    cipla_2024 = cipla_kpi[cipla_kpi["year"] == "2024-03"].iloc[0]
    assert cipla_2024["pattern_label"] == "Shareholder Returns"


def test_financials_sector_cfo_quality_exemption():
    """Verify lending NBFCs and banks are exempted from CFO Quality Score to prevent false Accrual Risk flags."""
    # Direct function call with is_financial / company_id
    res_irfc = compute_cfo_quality_score(
        [100.0] * 5, [100.0] * 5, company_id="IRFC", broad_sector="Financials"
    )
    assert res_irfc.value is None
    assert res_irfc.label == "Not Applicable (Financials Sector)"

    # Database integration check across lending NBFCs and banks
    for cid in ["IRFC", "RECLTD", "PFC", "SBIN", "HDFCBANK"]:
        raw = get_cashflow_data(company_id=cid)
        kpi = calculate_cashflow_kpis(raw)
        row_2024 = kpi[kpi["year"] == "2024-03"].iloc[0]
        assert pd.isna(row_2024["cfo_quality_score"])
        assert row_2024["cfo_quality_label"] == "Not Applicable (Financials Sector)"


def test_capital_allocation_csv_export_integrity(tmp_path):
    """Verify generate_capital_allocation_csv creates a complete 1,063 row table with required columns."""
    csv_file = tmp_path / "test_capital_allocation.csv"
    out_path = generate_capital_allocation_csv(output_path=csv_file)
    assert out_path.exists()

    df = pd.read_csv(out_path)
    assert len(df) == 1063
    expected_cols = [
        "company_id",
        "year",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    ]
    assert df.columns.tolist() == expected_cols

    # Ensure all 8 patterns exist in the output dataset
    patterns = set(df["pattern_label"].unique())
    for expected in [
        "Reinvestor",
        "Shareholder Returns",
        "Liquidating Assets",
        "Distress Signal",
        "Growth Funded by Debt",
        "Cash Accumulator",
        "Pre-Revenue",
        "Mixed",
    ]:
        assert expected in patterns
