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
from src.analytics.populate_financial_ratios import populate_financial_ratios
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
    "UNRELIABLE_BALANCESHEET_COMPANIES",
    "calculate_benchmark_gap",
    "calculate_cagr_metrics",
    "calculate_cashflow_kpis",
    "calculate_peer_percentiles",
    "calculate_profitability_metrics",
    "classify_percentile",
    "get_peer_percentiles",
    "populate_financial_ratios",
    "populate_peer_percentiles",
]
