"""Unit tests for the multi-criteria fundamental screener engine and 6 preset templates."""

import pandas as pd
import pytest

from src.screener.engine import (
    apply_trend_filter,
    filter_universe,
    load_screener_config,
    load_screener_universe,
    run_all_presets,
    run_preset,
)


@pytest.fixture(scope="module")
def screener_data() -> tuple[pd.DataFrame, dict]:
    """Fixture providing cached universe DataFrame and YAML configuration."""
    df = load_screener_universe()
    config = load_screener_config()
    return df, config


def test_quality_compounder_preset(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify Quality Compounder preset returns 1-30 companies and excludes SBIN."""
    df, config = screener_data
    results = run_preset("quality_compounder", df=df, config=config)

    assert 1 <= len(results) <= 30
    assert "SBIN" not in results["company_id"].values
    assert (results["return_on_equity_pct"] > 15.0).all()
    assert (results["debt_to_equity"] < 1.0).all()
    assert (results["free_cash_flow_cr"] > 0.0).all()
    assert (results["revenue_cagr_3yr"] > 10.0).all()
    assert (results["operating_profit_margin_pct"] > 10.0).all()


def test_value_pick_preset(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify Value Pick preset returns 1-30 companies and excludes SBIN."""
    df, config = screener_data
    results = run_preset("value_pick", df=df, config=config)

    assert 1 <= len(results) <= 30
    assert "SBIN" not in results["company_id"].values
    assert (results["pe_ratio"] < 20.0).all()
    assert (results["pb_ratio"] < 3.0).all()
    assert (results["return_on_equity_pct"] > 11.0).all()
    assert (results["debt_to_equity"] < 2.0).all()


def test_dividend_aristocrat_preset(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify Dividend Aristocrat preset returns 1-30 companies and excludes SBIN."""
    df, config = screener_data
    results = run_preset("dividend_aristocrat", df=df, config=config)

    assert 1 <= len(results) <= 30
    assert "SBIN" not in results["company_id"].values
    assert (results["dividend_payout_ratio_pct"] > 30.0).all()
    assert (results["free_cash_flow_cr"] > 0.0).all()
    assert (results["debt_to_equity"] < 1.0).all()
    assert (results["return_on_equity_pct"] > 12.0).all()


def test_growth_rocket_preset(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify Growth Rocket preset returns 1-30 companies and excludes SBIN."""
    df, config = screener_data
    results = run_preset("growth_rocket", df=df, config=config)

    assert 1 <= len(results) <= 30
    assert "SBIN" not in results["company_id"].values
    assert (results["revenue_cagr_3yr"] > 20.0).all()
    assert (results["pat_cagr_3yr"] > 20.0).all()
    assert (results["operating_profit_margin_pct"] > 15.0).all()


def test_asset_light_champion_preset(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify Asset Light Champion preset returns 1-30 companies and excludes SBIN."""
    df, config = screener_data
    results = run_preset("asset_light_champion", df=df, config=config)

    assert 1 <= len(results) <= 30
    assert "SBIN" not in results["company_id"].values
    assert (results["capex_intensity_pct"] < 3.0).all()
    assert (results["return_on_equity_pct"] > 20.0).all()
    assert (results["operating_profit_margin_pct"] > 20.0).all()


def test_financial_health_preset(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify Financial Health preset returns 1-30 companies and excludes SBIN."""
    df, config = screener_data
    results = run_preset("financial_health", df=df, config=config)

    assert 1 <= len(results) <= 30
    assert "SBIN" not in results["company_id"].values
    assert (results["interest_coverage"] > 3.0).all()
    assert (results["debt_to_equity"] < 0.5).all()
    assert (results["cfo_quality_score"] > 0.85).all()
    assert (results["free_cash_flow_cr"] > 0.0).all()


def test_null_handling_rule(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify rows with None in filtered fields are excluded, while preserving un-filtered nulls."""
    df, _ = screener_data
    # Filter on ROCE (banks have ROCE = None)
    filtered = filter_universe(
        df, filters={"return_on_capital_employed_pct": {"min": 10.0}}
    )
    assert filtered["return_on_capital_employed_pct"].notna().all()
    # Banks must be excluded because their ROCE is None
    assert "HDFCBANK" not in filtered["company_id"].values

    # Confirm that a company with null in an unfiltered column still appears if it passes active filters
    # TCS has net_debt_cr = None (or ICR not null, etc.)
    tcs_row = filtered[filtered["company_id"] == "TCS"]
    assert len(tcs_row) == 1


def test_trend_filter_accelerating_growth(
    screener_data: tuple[pd.DataFrame, dict]
) -> None:
    """Verify trend filter confirms 3yr CAGR > 5yr CAGR."""
    df, _ = screener_data
    mask = apply_trend_filter(df, "accelerating_revenue")
    passing = df[mask]

    assert len(passing) > 0
    assert (passing["revenue_cagr_3yr"] > passing["revenue_cagr_5yr"]).all()
    assert passing["revenue_cagr_3yr"].notna().all()
    assert passing["revenue_cagr_5yr"].notna().all()


def test_boolean_logic_and_vs_or(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify AND logic is more restrictive than OR logic."""
    df, _ = screener_data
    filters = {
        "return_on_equity_pct": {"min": 25.0},
        "operating_profit_margin_pct": {"min": 25.0},
    }
    and_results = filter_universe(df, filters=filters, logic="AND")
    or_results = filter_universe(df, filters=filters, logic="OR")

    assert len(or_results) >= len(and_results)
    assert set(and_results["company_id"]).issubset(set(or_results["company_id"]))


def test_run_all_presets_completeness(screener_data: tuple[pd.DataFrame, dict]) -> None:
    """Verify run_all_presets returns results for all 6 presets."""
    df, config = screener_data
    all_res = run_all_presets(df=df, config=config)

    assert len(all_res) == 6
    expected_presets = {
        "quality_compounder",
        "value_pick",
        "dividend_aristocrat",
        "growth_rocket",
        "asset_light_champion",
        "financial_health",
    }
    assert set(all_res.keys()) == expected_presets
