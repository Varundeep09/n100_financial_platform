"""Analytics engines for N100 Financial Intelligence Platform."""

from src.analytics.cagr import calculate_cagr_metrics
from src.analytics.cashflow_kpis import calculate_cashflow_kpis
from src.analytics.peer import (
    PEER_METRICS,
    calculate_benchmark_gap,
    calculate_peer_percentiles,
    classify_percentile,
    get_peer_percentiles,
    populate_peer_percentiles,
)
from src.analytics.peer_comparison import (
    PEER_WORKBOOK_METRICS,
    generate_peer_comparison_workbook,
)
from src.analytics.populate_financial_ratios import populate_financial_ratios
from src.analytics.radar import (
    RADAR_AXIS_CONFIG,
    generate_all_radar_charts,
    generate_single_radar_chart,
)
from src.analytics.ratios import (
    BANKING_TEMPLATE_COMPANIES,
    FINANCIALS_SECTOR_COMPANIES,
    UNRELIABLE_BALANCESHEET_COMPANIES,
    calculate_profitability_metrics,
)

__all__ = [
    "BANKING_TEMPLATE_COMPANIES",
    "FINANCIALS_SECTOR_COMPANIES",
    "PEER_METRICS",
    "PEER_WORKBOOK_METRICS",
    "RADAR_AXIS_CONFIG",
    "UNRELIABLE_BALANCESHEET_COMPANIES",
    "calculate_benchmark_gap",
    "calculate_cagr_metrics",
    "calculate_cashflow_kpis",
    "calculate_peer_percentiles",
    "calculate_profitability_metrics",
    "classify_percentile",
    "generate_all_radar_charts",
    "generate_peer_comparison_workbook",
    "generate_single_radar_chart",
    "get_peer_percentiles",
    "populate_financial_ratios",
    "populate_peer_percentiles",
]
