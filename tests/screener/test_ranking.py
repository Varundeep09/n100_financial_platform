"""Unit tests for the multi-factor composite ranking engine and screener exports.

Sprint 3, Day 16: Composite Ranking Engine & Screener Output
"""

from __future__ import annotations

import openpyxl
import pandas as pd
import pytest

from src.screener.engine import load_screener_universe, run_all_presets
from src.screener.ranking import (
    calculate_composite_ranking,
    export_screener_reports,
    winsorize_series,
)


@pytest.fixture(scope="module")
def ranked_universe() -> tuple[pd.DataFrame, pd.Series, dict[str, pd.DataFrame]]:
    """Fixture providing universe DataFrame, composite scores, and all preset results."""
    df = load_screener_universe()
    scores = calculate_composite_ranking(df)
    df["composite_ranking_score"] = scores
    presets = run_all_presets(df=df)
    return df, scores, presets


def test_composite_score_bounds_for_non_none_companies(
    ranked_universe: tuple[pd.DataFrame, pd.Series, dict[str, pd.DataFrame]],
) -> None:
    """Verify that composite ranking scores are between 0 and 100 for all non-None companies."""
    _, scores, _ = ranked_universe
    valid_scores = scores.dropna()

    assert (
        len(valid_scores) > 80
    ), "Expected at least 80 companies to have valid composite scores"
    assert (valid_scores >= 0.0).all(), "Composite scores must not be negative"
    assert (valid_scores <= 100.0).all(), "Composite scores must not exceed 100.0"


def test_sbin_bel_hal_have_none_composite_score(
    ranked_universe: tuple[pd.DataFrame, pd.Series, dict[str, pd.DataFrame]],
) -> None:
    """Verify SBIN, BEL, and HAL receive None/NaN composite scores.

    Design Rationale:
      BEL and HAL have documented ~100x scale errors in source balance sheets (extreme_magnitude_flag=1).
      SBIN has missing balance sheet ratios in source.
      Excluding them avoids ungrounded institutional rankings.
    """
    df, scores, _ = ranked_universe
    score_map = dict(zip(df["company_id"], scores, strict=False))

    for ticker in ["SBIN", "BEL", "HAL"]:
        assert ticker in score_map, f"Ticker {ticker} missing from universe"
        assert pd.isna(
            score_map[ticker]
        ), f"Expected {ticker} to have None composite score, got {score_map[ticker]}"


def test_winsorisation_applied_before_ranking() -> None:
    """Verify Winsorisation caps extreme values at 5th/95th percentiles without exceeding them."""
    # Test on synthetic series with extreme positive and negative outliers
    data = pd.Series(
        [10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 25.0, 28.0, 30.0, 5000.0, -1000.0]
    )
    p05 = float(data.quantile(0.05))
    p95 = float(data.quantile(0.95))

    clipped = winsorize_series(data, lower_quantile=0.05, upper_quantile=0.95)

    assert (
        clipped.max() <= p95 + 1e-6
    ), "No winsorized value should exceed 95th percentile"
    assert (
        clipped.min() >= p05 - 1e-6
    ), "No winsorized value should fall below 5th percentile"
    assert float(clipped.max()) < 5000.0, "Outlier 5000.0 must be clipped"
    assert float(clipped.min()) > -1000.0, "Outlier -1000.0 must be clipped"

    # Test on actual universe series
    df = load_screener_universe()
    roe_series = pd.to_numeric(df["return_on_equity_pct"], errors="coerce").dropna()
    p95_roe = float(roe_series.quantile(0.95))
    clipped_roe = winsorize_series(roe_series, lower_quantile=0.05, upper_quantile=0.95)

    assert clipped_roe.max() <= p95_roe + 1e-6


def test_top_5_companies_by_composite_score_are_in_at_least_one_preset(
    ranked_universe: tuple[pd.DataFrame, pd.Series, dict[str, pd.DataFrame]],
) -> None:
    """Verify that all Top 5 companies by composite ranking score match at least one preset screener."""
    df, _, presets = ranked_universe

    # Collect all unique companies matching at least one preset
    preset_membership: set[str] = set()
    for p_df in presets.values():
        preset_membership.update(p_df["company_id"].tolist())

    ranked = df.sort_values(by="composite_ranking_score", ascending=False)
    top_5_tickers = ranked["company_id"].head(5).tolist()

    assert len(top_5_tickers) == 5
    for ticker in top_5_tickers:
        assert (
            ticker in preset_membership
        ), f"Top 5 company '{ticker}' did not match any of the 6 preset screeners"


def test_master_screener_output_workbook_structure() -> None:
    """Verify that screener_output.xlsx contains 7 sheets and 92 companies on Summary sheet."""
    # Ensure reports are generated
    export_screener_reports()

    wb = openpyxl.load_workbook("screener_output.xlsx")
    expected_sheets = [
        "Summary",
        "Quality Compounder",
        "Value Pick",
        "Dividend Aristocrat",
        "Growth Rocket",
        "Asset Light Champion",
        "Financial Health",
    ]
    assert wb.sheetnames == expected_sheets

    summary_df = pd.read_excel("screener_output.xlsx", sheet_name="Summary")
    assert (
        len(summary_df) == 92
    ), f"Expected 92 companies in Summary sheet, got {len(summary_df)}"
    assert "composite_ranking_score" in summary_df.columns
    assert "total_presets_matched" in summary_df.columns
