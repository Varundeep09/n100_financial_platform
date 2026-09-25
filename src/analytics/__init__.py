"""Analytics engines for N100 Financial Intelligence Platform."""

from src.analytics.cagr import calculate_cagr_metrics
from src.analytics.cashflow_kpis import calculate_cashflow_kpis
from src.analytics.populate_financial_ratios import populate_financial_ratios
from src.analytics.ratios import (
    BANKING_TEMPLATE_COMPANIES,
    FINANCIALS_SECTOR_COMPANIES,
    calculate_profitability_metrics,
)

__all__ = [
    "BANKING_TEMPLATE_COMPANIES",
    "FINANCIALS_SECTOR_COMPANIES",
    "calculate_cagr_metrics",
    "calculate_cashflow_kpis",
    "calculate_profitability_metrics",
    "populate_financial_ratios",
]
