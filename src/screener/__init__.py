"""Screener and investment filtering package for Nifty 100 Financial Intelligence Platform."""

from src.screener.engine import (
    apply_single_filter,
    apply_trend_filter,
    filter_universe,
    load_screener_config,
    load_screener_universe,
    run_all_presets,
    run_preset,
)
from src.screener.ranking import (
    add_composite_scores,
    calculate_composite_ranking,
    calculate_percentile_ranks,
    export_screener_reports,
    winsorize_series,
)

__all__ = [
    "add_composite_scores",
    "apply_single_filter",
    "apply_trend_filter",
    "calculate_composite_ranking",
    "calculate_percentile_ranks",
    "export_screener_reports",
    "filter_universe",
    "load_screener_config",
    "load_screener_universe",
    "run_all_presets",
    "run_preset",
    "winsorize_series",
]
