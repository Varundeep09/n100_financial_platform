"""Profitability ratio engine and financial metrics for N100 Financial Intelligence Platform."""

import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

DB_PATH: Path = PROJECT_ROOT / os.getenv("DB_PATH", "db/nifty100.db")

OPM_DISCREPANCIES: list[dict[str, Any]] = []


def compute_npm(net_profit: float | None, sales: float | None) -> float | None:
    """Calculate Net Profit Margin as (net_profit / sales) * 100, returning None if sales is 0 or invalid."""
    if net_profit is None or sales is None:
        return None
    if isinstance(net_profit, (float, np.floating)) and np.isnan(net_profit):
        return None
    if isinstance(sales, (float, np.floating)) and np.isnan(sales):
        return None
    if abs(float(sales)) < 1e-9:
        return None
    return round((float(net_profit) / float(sales)) * 100.0, 4)


def compute_opm(
    operating_profit: float | None,
    sales: float | None,
    source_opm: float | None = None,
    company_id: str | None = None,
    year: str | None = None,
) -> float | None:
    """Calculate Operating Profit Margin as (operating_profit / sales) * 100 and log discrepancies > 1%."""
    if operating_profit is None or sales is None:
        return None
    if isinstance(operating_profit, (float, np.floating)) and np.isnan(
        operating_profit
    ):
        return None
    if isinstance(sales, (float, np.floating)) and np.isnan(sales):
        return None
    if abs(float(sales)) < 1e-9:
        return None

    computed_opm = round((float(operating_profit) / float(sales)) * 100.0, 4)

    if source_opm is not None and not (
        isinstance(source_opm, (float, np.floating)) and np.isnan(source_opm)
    ):
        diff = abs(computed_opm - float(source_opm))
        if diff > 1.0:
            discrepancy = {
                "company_id": company_id or "UNKNOWN",
                "year": year or "UNKNOWN",
                "sales": float(sales),
                "operating_profit": float(operating_profit),
                "computed_opm": computed_opm,
                "source_opm": float(source_opm),
                "diff": round(diff, 4),
            }
            OPM_DISCREPANCIES.append(discrepancy)
            logger.debug(
                f"OPM mismatch for {company_id} ({year}): computed={computed_opm}%, source={source_opm}% (diff={diff:.2f}%)"
            )

    return computed_opm


def compute_roe(
    net_profit: float | None,
    equity_capital: float | None,
    reserves: float | None,
) -> float | None:
    """Calculate Return on Equity as (net_profit / (equity_capital + reserves)) * 100, returning None if equity <= 0."""
    if net_profit is None or equity_capital is None or reserves is None:
        return None
    for val in [net_profit, equity_capital, reserves]:
        if isinstance(val, (float, np.floating)) and np.isnan(val):
            return None
    total_equity = float(equity_capital) + float(reserves)
    if total_equity <= 0.0:
        return None
    return round((float(net_profit) / total_equity) * 100.0, 4)


def compute_roce(
    operating_profit: float | None,
    depreciation: float | None,
    equity_capital: float | None,
    reserves: float | None,
    borrowings: float | None,
    broad_sector: str | None = None,
) -> dict[str, Any]:
    """Calculate ROCE as EBIT / (equity + reserves + borrowings) * 100 with sector_relative flag for Financials."""
    is_financials = broad_sector == "Financials"
    if operating_profit is None or equity_capital is None or reserves is None:
        return {"value": None, "sector_relative": is_financials}
    for val in [operating_profit, equity_capital, reserves]:
        if isinstance(val, (float, np.floating)) and np.isnan(val):
            return {"value": None, "sector_relative": is_financials}

    depr_val = (
        float(depreciation)
        if depreciation is not None and not np.isnan(depreciation)
        else 0.0
    )
    bor_val = (
        float(borrowings)
        if borrowings is not None and not np.isnan(borrowings)
        else 0.0
    )

    ebit = float(operating_profit) - depr_val
    capital_employed = float(equity_capital) + float(reserves) + bor_val

    if capital_employed <= 0.0:
        return {"value": None, "sector_relative": is_financials}

    roce_val = round((ebit / capital_employed) * 100.0, 4)
    return {"value": roce_val, "sector_relative": is_financials}


def compute_roa(net_profit: float | None, total_assets: float | None) -> float | None:
    """Calculate Return on Assets as (net_profit / total_assets) * 100, returning None if assets <= 0."""
    if net_profit is None or total_assets is None:
        return None
    if isinstance(net_profit, (float, np.floating)) and np.isnan(net_profit):
        return None
    if isinstance(total_assets, (float, np.floating)) and np.isnan(total_assets):
        return None
    if float(total_assets) <= 0.0:
        return None
    return round((float(net_profit) / float(total_assets)) * 100.0, 4)


def get_financial_statements_data(
    company_id: str | None = None,
    db_path: Path = DB_PATH,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Extract joined annual financial statement records using exact (company_id, year) matching."""
    should_close = False
    if conn is None:
        conn = sqlite3.connect(str(db_path))
        should_close = True

    try:
        where_clause = f"WHERE pl.company_id = '{company_id}'" if company_id else ""
        query = f"""
            SELECT pl.company_id, pl.year, 
                   pl.sales, pl.expenses, pl.operating_profit, pl.opm_percentage, 
                   pl.other_income, pl.interest, pl.depreciation, pl.profit_before_tax, 
                   pl.tax_percentage, pl.net_profit, pl.eps,
                   bs.equity_capital, bs.reserves, bs.borrowings, bs.other_liabilities, 
                   bs.total_liabilities, bs.fixed_assets, bs.cwip, bs.investments, 
                   bs.other_asset, bs.total_assets,
                   s.broad_sector
            FROM profitandloss pl
            LEFT JOIN balancesheet bs ON pl.company_id = bs.company_id AND pl.year = bs.year
            LEFT JOIN sectors s ON pl.company_id = s.company_id
            {where_clause}
            ORDER BY pl.company_id, pl.year;
        """
        return pd.read_sql_query(query, conn)
    except (sqlite3.Error, OSError) as exc:
        logger.error(f"Failed to query financial statements data: {exc}")
        return pd.DataFrame()
    finally:
        if should_close and conn is not None:
            conn.close()


def calculate_profitability_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all profitability ratios across a joined financial statements DataFrame."""
    if df.empty:
        return pd.DataFrame()

    out_df = df.copy()

    npm_list: list[float | None] = []
    opm_list: list[float | None] = []
    roe_list: list[float | None] = []
    roce_list: list[float | None] = []
    roce_sec_list: list[bool] = []
    roa_list: list[float | None] = []

    for _, row in out_df.iterrows():
        npm_list.append(compute_npm(row.get("net_profit"), row.get("sales")))
        opm_list.append(
            compute_opm(
                row.get("operating_profit"),
                row.get("sales"),
                source_opm=row.get("opm_percentage"),
                company_id=row.get("company_id"),
                year=row.get("year"),
            )
        )
        roe_list.append(
            compute_roe(
                row.get("net_profit"),
                row.get("equity_capital"),
                row.get("reserves"),
            )
        )
        roce_dict = compute_roce(
            row.get("operating_profit"),
            row.get("depreciation"),
            row.get("equity_capital"),
            row.get("reserves"),
            row.get("borrowings"),
            broad_sector=row.get("broad_sector"),
        )
        roce_list.append(roce_dict["value"])
        roce_sec_list.append(roce_dict["sector_relative"])
        roa_list.append(compute_roa(row.get("net_profit"), row.get("total_assets")))

    out_df["npm_pct"] = npm_list
    out_df["opm_pct"] = opm_list
    out_df["roe_pct"] = roe_list
    out_df["roce_pct"] = roce_list
    out_df["roce_sector_relative"] = roce_sec_list
    out_df["roa_pct"] = roa_list

    return out_df
