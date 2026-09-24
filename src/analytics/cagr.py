"""CAGR (Compound Annual Growth Rate) engine for Revenue, PAT, and EPS.

Implements:
- Standard CAGR formula: ((end_value / start_value) ** (1 / n) - 1) * 100
- 3-year, 5-year, and 10-year rolling windows with exact year-gap matching
- Gap-aware windowing: matches base row with exact (year - w, same month),
  returning 'INSUFFICIENT' if a sequence gap exists instead of misaligning rows.
- 6 edge cases per project spec Section 23.1:
  * Positive base, Positive end -> Computed normally (flag: None)
  * Positive base, Negative end -> None, flag = 'DECLINE_TO_LOSS'
  * Negative base, Positive end -> None, flag = 'TURNAROUND'
  * Negative base, Negative end -> None, flag = 'BOTH_NEGATIVE'
  * Zero base                  -> None, flag = 'ZERO_BASE'
  * Less than n years of data  -> None, flag = 'INSUFFICIENT'
- Exact (company_id, year) matching without hardcoded month filters, supporting non-March companies.
- Clean separation of revenue/PAT/EPS CAGR from banking-template P&L column corruption.
"""

import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "nifty100.db"


def calculate_cagr(
    start_value: float | None,
    end_value: float | None,
    periods: int,
) -> tuple[float | None, str | None]:
    """Calculate CAGR over n periods, returning (cagr_pct, edge_case_flag) per Section 23.1."""
    if periods is None or periods <= 0:
        return None, "INSUFFICIENT"
    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"

    try:
        s = float(start_value)
        e = float(end_value)
    except (ValueError, TypeError):
        return None, "INSUFFICIENT"

    if np.isnan(s) or np.isnan(e):
        return None, "INSUFFICIENT"

    if abs(s) < 1e-9:
        return None, "ZERO_BASE"

    if s > 0 and e < 0:
        return None, "DECLINE_TO_LOSS"

    if s < 0 and e > 0:
        return None, "TURNAROUND"

    if s < 0 and e < 0:
        return None, "BOTH_NEGATIVE"

    if s > 0 and abs(e) < 1e-9:
        return None, "DECLINE_TO_LOSS"

    if s < 0 and abs(e) < 1e-9:
        return None, "TURNAROUND"

    cagr_pct = round(((e / s) ** (1.0 / periods) - 1.0) * 100.0, 4)
    return cagr_pct, None


def get_pl_cagr_data(
    company_id: str | None = None,
    db_path: Path = DB_PATH,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Extract annual P&L figures (sales, net_profit, eps) for CAGR computation."""
    should_close = False
    if conn is None:
        conn = sqlite3.connect(str(db_path))
        should_close = True

    try:
        where_clause = f"WHERE pl.company_id = '{company_id}'" if company_id else ""
        query = f"""
            SELECT pl.company_id, pl.year, pl.sales, pl.net_profit, pl.eps, s.broad_sector
            FROM profitandloss pl
            LEFT JOIN sectors s ON pl.company_id = s.company_id
            {where_clause}
            ORDER BY pl.company_id, pl.year;
        """
        return pd.read_sql_query(query, conn)
    except (sqlite3.Error, OSError) as exc:
        logger.error(f"Failed to query P&L data for CAGR: {exc}")
        return pd.DataFrame()
    finally:
        if should_close and conn is not None:
            conn.close()


def calculate_cagr_metrics(
    df: pd.DataFrame,
    windows: tuple[int, ...] = (3, 5, 10),
) -> pd.DataFrame:
    """Compute 3yr, 5yr, and 10yr CAGR and edge-case flags using exact year-gap matching."""
    if df.empty:
        return pd.DataFrame()

    results: list[pd.DataFrame] = []

    for _, group in df.groupby("company_id", sort=False):
        g = group.sort_values("year").reset_index(drop=True)
        g_res = g.copy()

        # Map each year string to its row Series for exact target lookups
        year_row_map: dict[str, pd.Series] = {
            str(row["year"]): row for _, row in g.iterrows()
        }

        for w in windows:
            rev_cagr: list[float | None] = []
            rev_flag: list[str | None] = []
            pat_cagr: list[float | None] = []
            pat_flag: list[str | None] = []
            eps_cagr: list[float | None] = []
            eps_flag: list[str | None] = []

            for _, curr_row in g.iterrows():
                curr_year_str = str(curr_row["year"])
                try:
                    curr_y = int(curr_year_str[:4])
                    curr_m = curr_year_str[5:7]
                    target_year_str = f"{curr_y - w:04d}-{curr_m}"
                except (ValueError, IndexError):
                    target_year_str = ""

                if target_year_str in year_row_map:
                    base_row = year_row_map[target_year_str]

                    # Revenue (sales)
                    rc, rf = calculate_cagr(base_row["sales"], curr_row["sales"], w)
                    rev_cagr.append(rc)
                    rev_flag.append(rf)

                    # PAT (net_profit)
                    pc, pf = calculate_cagr(
                        base_row["net_profit"], curr_row["net_profit"], w
                    )
                    pat_cagr.append(pc)
                    pat_flag.append(pf)

                    # EPS
                    ec, ef = calculate_cagr(base_row["eps"], curr_row["eps"], w)
                    eps_cagr.append(ec)
                    eps_flag.append(ef)
                else:
                    # Gap in sequence or insufficient history for exact w-year window
                    rev_cagr.append(None)
                    rev_flag.append("INSUFFICIENT")
                    pat_cagr.append(None)
                    pat_flag.append("INSUFFICIENT")
                    eps_cagr.append(None)
                    eps_flag.append("INSUFFICIENT")

            g_res[f"revenue_cagr_{w}yr"] = rev_cagr
            g_res[f"revenue_cagr_{w}yr_flag"] = rev_flag
            g_res[f"pat_cagr_{w}yr"] = pat_cagr
            g_res[f"pat_cagr_{w}yr_flag"] = pat_flag
            g_res[f"eps_cagr_{w}yr"] = eps_cagr
            g_res[f"eps_cagr_{w}yr_flag"] = eps_flag

        results.append(g_res)

    return pd.concat(results, ignore_index=True)


def get_cagr_summary(
    company_id: str | None = None,
    db_path: Path = DB_PATH,
    latest_only: bool = True,
) -> pd.DataFrame:
    """Retrieve CAGR analytics table, optionally filtering to each company's latest fiscal year."""
    raw_df = get_pl_cagr_data(company_id=company_id, db_path=db_path)
    if raw_df.empty:
        return pd.DataFrame()

    cagr_df = calculate_cagr_metrics(raw_df)
    if not latest_only:
        return cagr_df

    # Extract latest year per company
    idx_latest = cagr_df.groupby("company_id")["year"].idxmax()
    return cagr_df.loc[idx_latest].sort_values("company_id").reset_index(drop=True)
