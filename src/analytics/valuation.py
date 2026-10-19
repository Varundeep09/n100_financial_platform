"""Valuation & Market Multiples Analytics Module.

Sprint 4: Valuation & Market Data Engine (Module 6)
Computes 5-year historical median multiples (P/E, P/B, EV/EBITDA),
sector median multiples for relative benchmarking, FCF yields,
and automated overvaluation/undervaluation flags.
Generates reports/valuation_summary.xlsx and reports/valuation_flags.csv.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("db/nifty100.db")
DEFAULT_EXCEL_PATH = Path("reports/valuation_summary.xlsx")
DEFAULT_CSV_PATH = Path("reports/valuation_flags.csv")


def calculate_valuation_metrics(
    db_path: Path | str = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Ingest market_cap, sectors, and financial_ratios to compute valuation multiples.

    Calculates:
    - Current valuation multiples (P/E, P/B, EV/EBITDA, Dividend Yield)
    - 5-year historical median multiples per company (2019-2024)
    - Sector median multiples for relative valuation benchmarking
    - Free Cash Flow Yield (%)
    - Valuation badges: 'Caution (Overvalued)', 'Discount (Undervalued)', 'Fair Value'

    Args:
        db_path: Path to nifty100.db SQLite database.

    Returns:
        DataFrame with 92 constituent rows and all valuation metrics.
    """
    resolved_db = Path(db_path).resolve()
    if not resolved_db.exists():
        fallback = Path(__file__).resolve().parents[2] / "db" / "nifty100.db"
        if fallback.exists():
            resolved_db = fallback
        else:
            raise FileNotFoundError(f"Database not found at: {resolved_db}")

    with sqlite3.connect(resolved_db) as conn:
        cos_df = pd.read_sql(
            "SELECT id as company_id, company_name FROM companies ORDER BY id ASC;",
            conn,
        )
        sec_df = pd.read_sql(
            "SELECT company_id, broad_sector, sub_sector FROM sectors;", conn
        )
        mc_all = pd.read_sql(
            """
            SELECT company_id, year, market_cap_crore, enterprise_value_crore, 
                   pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct 
            FROM market_cap 
            WHERE year LIKE '%-03'
            ORDER BY company_id ASC, year ASC;
            """,
            conn,
        )
        fr_latest = pd.read_sql(
            """
            SELECT company_id, free_cash_flow_cr, return_on_equity_pct, 
                   return_on_capital_employed_pct, operating_profit_margin_pct, 
                   revenue_cagr_3yr, composite_quality_score, extreme_magnitude_flag
            FROM financial_ratios
            WHERE year LIKE '%-03'
            GROUP BY company_id
            HAVING year = MAX(year);
            """,
            conn,
        )

    # Latest market cap snapshot per company (2024-03)
    mc_latest = mc_all.sort_values("year").groupby("company_id").last().reset_index()

    # 5-year historical median multiples (2019-2024)
    medians_5yr = (
        mc_all.groupby("company_id")
        .agg(
            median_pe_5yr=("pe_ratio", "median"),
            median_pb_5yr=("pb_ratio", "median"),
            median_ev_ebitda_5yr=("ev_ebitda", "median"),
        )
        .reset_index()
    )

    # Merge dataset
    df = cos_df.merge(sec_df, on="company_id", how="left")
    df = df.merge(
        mc_latest.drop(columns=["id", "year"], errors="ignore"),
        on="company_id",
        how="left",
    )
    df = df.merge(medians_5yr, on="company_id", how="left")
    df = df.merge(fr_latest, on="company_id", how="left")

    # Clean extreme magnitude flags for ROE/ROCE
    df.loc[
        df["extreme_magnitude_flag"] == 1,
        ["return_on_equity_pct", "return_on_capital_employed_pct"],
    ] = None

    # Sector median multiples
    sec_medians = (
        df.groupby("broad_sector")
        .agg(
            sector_median_pe=("pe_ratio", "median"),
            sector_median_pb=("pb_ratio", "median"),
            sector_median_ev_ebitda=("ev_ebitda", "median"),
        )
        .reset_index()
    )

    df = df.merge(sec_medians, on="broad_sector", how="left")

    # FCF Yield = FCF / Market Cap * 100
    df["fcf_yield_pct"] = np.where(
        df["market_cap_crore"].notna()
        & (df["market_cap_crore"] > 0)
        & df["free_cash_flow_cr"].notna(),
        (df["free_cash_flow_cr"] / df["market_cap_crore"]) * 100,
        np.nan,
    )

    # Automated Relative Valuation Flag (vs Sector Median P/E)
    def assign_valuation_flag(row: pd.Series) -> str:
        """Classify current P/E multiple relative to sector median benchmark.

        Args:
            row (pd.Series): DataFrame row containing pe_ratio and sector_median_pe.

        Returns:
            str: Valuation category ('Caution (Overvalued)', 'Discount (Undervalued)', 'Fair', or 'Not Applicable').
        """
        pe = row["pe_ratio"]
        sec_pe = row["sector_median_pe"]
        if pd.isna(pe) or pd.isna(sec_pe) or sec_pe <= 0:
            return "Not Applicable"
        if pe > 1.5 * sec_pe:
            return "Caution (Overvalued)"
        elif pe < 0.7 * sec_pe:
            return "Discount (Undervalued)"
        return "Fair Value"

    df["valuation_flag"] = df.apply(assign_valuation_flag, axis=1)

    # Historical Valuation Flag (vs Company 5-Yr Median P/E)
    def assign_historical_flag(row: pd.Series) -> str:
        """Classify current P/E multiple relative to 5-year historical average.

        Args:
            row (pd.Series): DataFrame row containing pe_ratio and pe_5yr_avg.

        Returns:
            str: Historical valuation category ('Historical Premium', 'Historical Discount', 'In Line', or 'Not Applicable').
        """
        pe = row["pe_ratio"]
        med_pe = row["median_pe_5yr"]
        if pd.isna(pe) or pd.isna(med_pe) or med_pe <= 0:
            return "Not Applicable"
        if pe > 1.25 * med_pe:
            return "Premium to History"
        elif pe < 0.85 * med_pe:
            return "Discount to History"
        return "In Line with History"

    df["historical_valuation_flag"] = df.apply(assign_historical_flag, axis=1)

    return df


def generate_valuation_summary_report(
    db_path: Path | str = DEFAULT_DB_PATH,
    output_excel: Path | str = DEFAULT_EXCEL_PATH,
    output_csv: Path | str = DEFAULT_CSV_PATH,
) -> pd.DataFrame:
    """Generate reports/valuation_summary.xlsx (92 rows) and reports/valuation_flags.csv.

    Args:
        db_path: Path to SQLite database.
        output_excel: Destination path for Excel workbook.
        output_csv: Destination path for CSV flags.

    Returns:
        Processed DataFrame containing 92 constituent rows.
    """
    df = calculate_valuation_metrics(db_path=db_path)

    excel_path = Path(output_excel)
    csv_path = Path(output_csv)
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    summary_cols = [
        "company_id",
        "company_name",
        "broad_sector",
        "sub_sector",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "median_pe_5yr",
        "sector_median_pe",
        "valuation_flag",
        "historical_valuation_flag",
        "pb_ratio",
        "median_pb_5yr",
        "ev_ebitda",
        "median_ev_ebitda_5yr",
        "dividend_yield_pct",
        "free_cash_flow_cr",
        "fcf_yield_pct",
        "return_on_equity_pct",
    ]

    summary_df = df[summary_cols].copy()

    sector_summary = (
        df.groupby("broad_sector")
        .agg(
            company_count=("company_id", "count"),
            sector_median_pe=("pe_ratio", "median"),
            sector_median_pb=("pb_ratio", "median"),
            sector_median_ev_ebitda=("ev_ebitda", "median"),
            sector_median_fcf_yield=("fcf_yield_pct", "median"),
            total_market_cap_cr=("market_cap_crore", "sum"),
        )
        .reset_index()
    )

    flags_df = df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "pe_ratio",
            "sector_median_pe",
            "median_pe_5yr",
            "valuation_flag",
            "historical_valuation_flag",
            "fcf_yield_pct",
        ]
    ].sort_values(by=["valuation_flag", "pe_ratio"], ascending=[True, False])

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Valuation Summary", index=False)
        sector_summary.to_excel(writer, sheet_name="Sector Multiples", index=False)
        flags_df.to_excel(writer, sheet_name="Valuation Flags", index=False)

    logger.info(
        "Exported valuation summary workbook: %s (%d rows)", excel_path, len(summary_df)
    )

    flags_df.to_csv(csv_path, index=False)
    logger.info("Exported valuation flags CSV: %s", csv_path)

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    val_df = generate_valuation_summary_report()
    print(f"Generated valuation_summary.xlsx with {len(val_df)} rows.")
