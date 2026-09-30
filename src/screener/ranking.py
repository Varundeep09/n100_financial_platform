"""Multi-Factor Composite Ranking Engine for Nifty 100 Companies.

Module 3: Company Screener & Filter Engine
Sprint 3, Day 16: Composite Ranking Engine & Screener Output Export
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.screener.engine import (
    DEFAULT_DB_PATH,
    load_screener_config,
    load_screener_universe,
    run_all_presets,
)

logger = logging.getLogger(__name__)

# Default excluded tickers due to corrupted source data (BEL, HAL) or missing base ratios (SBIN)
DEFAULT_EXCLUDED_TICKERS = {"SBIN", "BEL", "HAL"}

# Pillar Weights
WEIGHT_PROFITABILITY = 0.35
WEIGHT_CASH_QUALITY = 0.30
WEIGHT_GROWTH = 0.20
WEIGHT_SOLVENCY = 0.15

# Pillar Component Columns
PROFITABILITY_COLS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
]
CASH_QUALITY_COLS = [
    "cfo_quality_score",
    "free_cash_flow_cr",
]
GROWTH_COLS = [
    "revenue_cagr_3yr",
    "pat_cagr_3yr",
]
SOLVENCY_COLS = [
    "debt_to_equity",
    "interest_coverage",
]


def winsorize_series(
    series: pd.Series,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
) -> pd.Series:
    """Winsorize numeric series at specified lower and upper quantiles.

    Values below lower_quantile are clipped to the lower quantile value.
    Values above upper_quantile are clipped to the upper quantile value.
    Null/NaN values are preserved without modification.

    Args:
        series: Pandas Series with numeric values.
        lower_quantile: Lower cutoff quantile (default 0.05).
        upper_quantile: Upper cutoff quantile (default 0.95).

    Returns:
        Clipped / Winsorized Pandas Series.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if len(valid) == 0:
        return numeric.copy()

    q_low = float(valid.quantile(lower_quantile))
    q_high = float(valid.quantile(upper_quantile))

    return numeric.clip(lower=q_low, upper=q_high)


def calculate_percentile_ranks(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Winsorized percentile ranks (0-100) across all 10 sub-component metrics.

    D/E is inverted so that lower leverage receives a higher percentile rank.
    Companies with None for a metric are excluded from that metric's ranking pool.

    Args:
        df: Screener universe DataFrame.

    Returns:
        DataFrame with percentile rank columns for each constituent ratio.
    """
    percentiles = pd.DataFrame(index=df.index)
    all_metrics = PROFITABILITY_COLS + CASH_QUALITY_COLS + GROWTH_COLS + SOLVENCY_COLS

    for metric in all_metrics:
        if metric not in df.columns:
            percentiles[metric] = np.nan
            continue

        raw = pd.to_numeric(df[metric], errors="coerce")
        valid = raw.dropna()
        if len(valid) == 0:
            percentiles[metric] = np.nan
            continue

        # Winsorise at 5th and 95th percentiles
        clipped = winsorize_series(valid, lower_quantile=0.05, upper_quantile=0.95)

        # Invert D/E: lower debt is better
        if metric == "debt_to_equity":
            ranks = clipped.rank(pct=True, ascending=False) * 100.0
        else:
            ranks = clipped.rank(pct=True, ascending=True) * 100.0

        percentiles[metric] = ranks

    return percentiles


def calculate_composite_ranking(
    df: pd.DataFrame,
    exclude_tickers: set[str] | list[str] | None = None,
) -> pd.Series:
    """Calculate the 0-100 composite ranking score for all companies in the universe.

    Weighting structure:
      - 35% Profitability: average of ROE, ROCE, OPM, NPM percentiles
      - 30% Cash Quality: average of CFO Quality Score, FCF percentiles
      - 20% Growth: average of Revenue CAGR 3yr, PAT CAGR 3yr percentiles
      - 15% Solvency: average of D/E (inverted), ICR percentiles

    Design Decision on SBIN / BEL / HAL:
      SBIN, BEL, and HAL receive None (NaN) composite ranking scores because their
      source data contains documented balance sheet scale corruptions (~100x scale error,
      extreme_magnitude_flag=1) or severe banking reporting gaps. Assigning partial scores
      would create ungrounded institutional rankings.

    Args:
        df: Screener universe DataFrame.
        exclude_tickers: Collection of tickers forced to None. Defaults to {'SBIN', 'BEL', 'HAL'}.

    Returns:
        Series of composite scores (0-100), rounded to 2 decimal places.
    """
    if exclude_tickers is None:
        excluded = DEFAULT_EXCLUDED_TICKERS
    else:
        excluded = set(exclude_tickers)

    pct_df = calculate_percentile_ranks(df)

    # Compute pillar scores (averaging available non-null metrics)
    prof_score = pct_df[PROFITABILITY_COLS].mean(axis=1, skipna=True)
    cash_score = pct_df[CASH_QUALITY_COLS].mean(axis=1, skipna=True)
    growth_score = pct_df[GROWTH_COLS].mean(axis=1, skipna=True)
    solv_score = pct_df[SOLVENCY_COLS].mean(axis=1, skipna=True)

    pillar_df = pd.DataFrame(
        {
            "prof": prof_score,
            "cash": cash_score,
            "growth": growth_score,
            "solv": solv_score,
        },
        index=df.index,
    )

    weights = {
        "prof": WEIGHT_PROFITABILITY,
        "cash": WEIGHT_CASH_QUALITY,
        "growth": WEIGHT_GROWTH,
        "solv": WEIGHT_SOLVENCY,
    }

    composite_scores = pd.Series(index=df.index, dtype=float)

    for idx in df.index:
        cid = str(df.loc[idx, "company_id"])
        if cid in excluded:
            composite_scores.loc[idx] = np.nan
            continue

        row = pillar_df.loc[idx]
        avail = row.dropna()
        if len(avail) == 0:
            composite_scores.loc[idx] = np.nan
            continue

        # Reweight proportionally across available non-null pillars
        w_avail = pd.Series({k: weights[k] for k in avail.index})
        norm_weights = w_avail / w_avail.sum()
        weighted_score = (avail * norm_weights).sum()

        composite_scores.loc[idx] = round(float(weighted_score), 2)

    return composite_scores


def add_composite_scores(
    df: pd.DataFrame,
    exclude_tickers: set[str] | list[str] | None = None,
) -> pd.DataFrame:
    """Append composite_ranking_score column to a DataFrame.

    Args:
        df: Screener universe or preset results DataFrame.
        exclude_tickers: Optional custom list of excluded tickers.

    Returns:
        DataFrame with composite_ranking_score appended.
    """
    df_copy = df.copy()
    scores = calculate_composite_ranking(df_copy, exclude_tickers=exclude_tickers)
    df_copy["composite_ranking_score"] = scores
    return df_copy


def export_screener_reports(
    output_dir: Path | str = "reports/screener_output",
    master_file: Path | str = "screener_output.xlsx",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Path]:
    """Generate and export individual preset reports and master multi-sheet workbook.

    Args:
        output_dir: Directory to save individual preset Excel files.
        master_file: Path to master multi-sheet Excel file.
        db_path: Database path to load universe.

    Returns:
        Dict mapping report names to generated Path objects.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    master_path = Path(master_file)
    master_path.parent.mkdir(parents=True, exist_ok=True)

    config = load_screener_config()
    universe = load_screener_universe(db_path=db_path)
    universe = add_composite_scores(universe)

    # Dictionary of presets definitions
    preset_definitions = config.get("presets", {})
    all_presets = run_all_presets(df=universe, config=config, db_path=db_path)

    generated_files: dict[str, Path] = {}

    # 1. Export Individual Preset Workbooks
    for preset_key, p_df in all_presets.items():
        p_def = preset_definitions.get(preset_key, {})
        filter_metrics = list(p_def.get("filters", {}).keys())

        # Desired columns
        base_cols = ["company_id", "company_name", "broad_sector"]
        metric_cols = [
            c for c in filter_metrics if c in p_df.columns and c not in base_cols
        ]
        final_cols = base_cols + metric_cols + ["composite_ranking_score"]

        # Ensure unique columns while preserving order
        final_cols = list(dict.fromkeys(final_cols))

        preset_export_df = p_df[[c for c in final_cols if c in p_df.columns]].copy()
        preset_export_df = preset_export_df.sort_values(
            by="composite_ranking_score", ascending=False
        )

        preset_file = out_dir / f"{preset_key}.xlsx"
        with pd.ExcelWriter(preset_file, engine="openpyxl") as writer:
            preset_export_df.to_excel(
                writer, sheet_name=p_def.get("name", preset_key)[:31], index=False
            )

        logger.info("Exported preset '%s' to %s", preset_key, preset_file)
        generated_files[preset_key] = preset_file

    # 2. Build Master Multi-Sheet Workbook (7 Sheets)
    # Sheet 1: Summary Sheet with all 92 companies & membership flags
    summary_df = universe[
        ["company_id", "company_name", "broad_sector", "composite_ranking_score"]
    ].copy()

    for preset_key, p_df in all_presets.items():
        flag_col = f"in_{preset_key}"
        passing_ids = set(p_df["company_id"])
        summary_df[flag_col] = summary_df["company_id"].isin(passing_ids)

    # Total presets matched column
    flag_cols = [f"in_{k}" for k in all_presets]
    summary_df["total_presets_matched"] = summary_df[flag_cols].sum(axis=1)

    # Sort summary: highest composite score first, NaNs at end
    summary_df = summary_df.sort_values(
        by=["composite_ranking_score", "total_presets_matched"],
        ascending=[False, False],
        na_position="last",
    )

    with pd.ExcelWriter(master_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Sheets 2-7: Preset sheets
        for preset_key, p_df in all_presets.items():
            p_def = preset_definitions.get(preset_key, {})
            filter_metrics = list(p_def.get("filters", {}).keys())
            base_cols = ["company_id", "company_name", "broad_sector"]
            metric_cols = [
                c for c in filter_metrics if c in p_df.columns and c not in base_cols
            ]
            final_cols = list(
                dict.fromkeys(base_cols + metric_cols + ["composite_ranking_score"])
            )

            p_export = p_df[[c for c in final_cols if c in p_df.columns]].copy()
            p_export = p_export.sort_values(
                by="composite_ranking_score", ascending=False
            )

            sheet_name = p_def.get("name", preset_key)[:31]
            p_export.to_excel(writer, sheet_name=sheet_name, index=False)

    logger.info("Exported master multi-sheet workbook to %s", master_path)
    generated_files["master"] = master_path

    # Also mirror master in reports/ if master_file is root
    if master_path.name == "screener_output.xlsx" and master_path.parent != out_dir:
        report_mirror = Path("reports") / "screener_output.xlsx"
        report_mirror.parent.mkdir(parents=True, exist_ok=True)
        summary_df.to_excel(report_mirror, sheet_name="Summary", index=False)
        with pd.ExcelWriter(report_mirror, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            for preset_key, p_df in all_presets.items():
                p_def = preset_definitions.get(preset_key, {})
                filter_metrics = list(p_def.get("filters", {}).keys())
                base_cols = ["company_id", "company_name", "broad_sector"]
                metric_cols = [
                    c
                    for c in filter_metrics
                    if c in p_df.columns and c not in base_cols
                ]
                final_cols = list(
                    dict.fromkeys(base_cols + metric_cols + ["composite_ranking_score"])
                )
                p_export = p_df[[c for c in final_cols if c in p_df.columns]].copy()
                p_export = p_export.sort_values(
                    by="composite_ranking_score", ascending=False
                )
                writer_sheet = p_def.get("name", preset_key)[:31]
                p_export.to_excel(writer, sheet_name=writer_sheet, index=False)
        generated_files["reports_master"] = report_mirror

    return generated_files
