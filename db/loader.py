"""Database initialisation and ETL table loader for N100 Financial Intelligence Platform."""

import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.etl.loader import (
    PARSE_ERROR,
    load_core_file,
    load_supporting_file,
    normalize_ticker,
    normalize_year,
)

load_dotenv()

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

DB_PATH: Path = PROJECT_ROOT / os.getenv("DB_PATH", "db/nifty100.db")
SCHEMA_PATH: Path = PROJECT_ROOT / "db" / "schema.sql"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
AUDIT_PATH: Path = REPORTS_DIR / "load_audit.csv"


def init_database(
    db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH
) -> sqlite3.Connection:
    """Initialise SQLite database schema from DDL file with foreign keys enabled."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        with open(schema_path, encoding="utf-8") as f:
            ddl = f.read()
        conn.executescript(ddl)
        conn.commit()
        logger.info(f"Database schema initialised successfully at {db_path}")
    except (OSError, sqlite3.Error) as exc:
        logger.error(f"Error initialising schema from '{schema_path}': {exc}")
    return conn


def transform_companies(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalise master companies dataset."""
    clean_df = df.copy()
    clean_df["id"] = clean_df["id"].apply(normalize_ticker)
    clean_df = clean_df.dropna(subset=["id"])
    clean_df = clean_df.drop_duplicates(subset=["id"], keep="last")
    if "company_name" in clean_df.columns:
        clean_df["company_name"] = (
            clean_df["company_name"]
            .astype(str)
            .str.replace("\n", " ", regex=False)
            .str.strip()
        )
    return clean_df


def transform_profitandloss(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean, normalise, and deduplicate annual profit and loss statements."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df["year"] = clean_df["year"].apply(normalize_year)
    clean_df = clean_df[
        clean_df["company_id"].isin(valid_tickers) & (clean_df["year"] != PARSE_ERROR)
    ]
    clean_df = clean_df.drop_duplicates(subset=["company_id", "year"], keep="last")
    cols = [
        "company_id",
        "year",
        "sales",
        "expenses",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout",
    ]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_balancesheet(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean, normalise, and coerce fixed assets for annual balance sheet statements."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df["year"] = clean_df["year"].apply(normalize_year)
    clean_df = clean_df[
        clean_df["company_id"].isin(valid_tickers) & (clean_df["year"] != PARSE_ERROR)
    ]
    clean_df = clean_df.drop_duplicates(subset=["company_id", "year"], keep="last")
    if "fixed_assets" in clean_df.columns:
        clean_df["fixed_assets"] = clean_df["fixed_assets"].apply(
            lambda x: max(0.0, float(x)) if pd.notna(x) else np.nan
        )
    cols = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_asset",
        "total_assets",
    ]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_cashflow(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean, normalise, and deduplicate annual cash flow statements."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df["year"] = clean_df["year"].apply(normalize_year)
    clean_df = clean_df[
        clean_df["company_id"].isin(valid_tickers) & (clean_df["year"] != PARSE_ERROR)
    ]
    clean_df = clean_df.drop_duplicates(subset=["company_id", "year"], keep="last")
    cols = [
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_analysis(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean and filter multi-period growth analysis records."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df = clean_df[clean_df["company_id"].isin(valid_tickers)]
    cols = [
        "company_id",
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    ]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_documents(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean, normalise, and filter annual report document links."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    yr_col = "Year" if "Year" in clean_df.columns else "year"
    clean_df["year"] = clean_df[yr_col].apply(normalize_year)
    clean_df = clean_df[
        clean_df["company_id"].isin(valid_tickers) & (clean_df["year"] != PARSE_ERROR)
    ]
    clean_df["annual_report"] = clean_df["Annual_Report"]
    cols = ["company_id", "year", "annual_report"]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_prosandcons(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean and filter pros and cons text summaries."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df = clean_df[clean_df["company_id"].isin(valid_tickers)]
    cols = ["company_id", "pros", "cons"]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_sectors(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean and filter sector classifications."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df = clean_df[clean_df["company_id"].isin(valid_tickers)]
    clean_df = clean_df.drop_duplicates(subset=["company_id"], keep="last")
    cols = [
        "company_id",
        "broad_sector",
        "sub_sector",
        "index_weight_pct",
        "market_cap_category",
    ]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_stock_prices(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean and filter monthly stock price historical series."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df = clean_df[clean_df["company_id"].isin(valid_tickers)]
    clean_df = clean_df.drop_duplicates(subset=["company_id", "date"], keep="last")
    cols = [
        "company_id",
        "date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "adjusted_close",
    ]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def transform_market_cap(df: pd.DataFrame, valid_tickers: set[str]) -> pd.DataFrame:
    """Clean, normalise, and filter annual market capitalisation records."""
    clean_df = df.copy()
    clean_df["company_id"] = clean_df["company_id"].apply(normalize_ticker)
    clean_df["year"] = clean_df["year"].apply(normalize_year)
    clean_df = clean_df[
        clean_df["company_id"].isin(valid_tickers) & (clean_df["year"] != PARSE_ERROR)
    ]
    clean_df = clean_df.drop_duplicates(subset=["company_id", "year"], keep="last")
    cols = [
        "company_id",
        "year",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]
    return clean_df[[c for c in cols if c in clean_df.columns]]


def load_all_tables(
    db_path: Path = DB_PATH,
    schema_path: Path = SCHEMA_PATH,
    audit_path: Path = AUDIT_PATH,
) -> dict[str, int]:
    """Execute end-to-end production load for all 12 files and write load_audit.csv."""
    conn = init_database(db_path, schema_path)
    counts: dict[str, int] = {}
    audit_rows: list[dict[str, object]] = []

    try:
        # 1. Master Companies
        t0 = time.perf_counter()
        raw_companies = load_core_file("companies.xlsx")
        clean_companies = transform_companies(raw_companies)
        clean_companies.to_sql("companies", conn, if_exists="append", index=False)
        counts["companies"] = len(clean_companies)
        valid_tickers = set(clean_companies["id"])
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "companies",
                "rows_in": len(raw_companies),
                "rows_out": len(clean_companies),
                "rejected": len(raw_companies) - len(clean_companies),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'companies': {len(clean_companies)} rows in {dt:.3f}s")

        # 2. Profit and Loss
        t0 = time.perf_counter()
        raw_pl = load_core_file("profitandloss.xlsx")
        clean_pl = transform_profitandloss(raw_pl, valid_tickers)
        clean_pl.to_sql("profitandloss", conn, if_exists="append", index=False)
        counts["profitandloss"] = len(clean_pl)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "profitandloss",
                "rows_in": len(raw_pl),
                "rows_out": len(clean_pl),
                "rejected": len(raw_pl) - len(clean_pl),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'profitandloss': {len(clean_pl)} rows in {dt:.3f}s")

        # 3. Balance Sheet
        t0 = time.perf_counter()
        raw_bs = load_core_file("balancesheet.xlsx")
        clean_bs = transform_balancesheet(raw_bs, valid_tickers)
        clean_bs.to_sql("balancesheet", conn, if_exists="append", index=False)
        counts["balancesheet"] = len(clean_bs)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "balancesheet",
                "rows_in": len(raw_bs),
                "rows_out": len(clean_bs),
                "rejected": len(raw_bs) - len(clean_bs),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'balancesheet': {len(clean_bs)} rows in {dt:.3f}s")

        # 4. Cash Flow
        t0 = time.perf_counter()
        raw_cf = load_core_file("cashflow.xlsx")
        clean_cf = transform_cashflow(raw_cf, valid_tickers)
        clean_cf.to_sql("cashflow", conn, if_exists="append", index=False)
        counts["cashflow"] = len(clean_cf)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "cashflow",
                "rows_in": len(raw_cf),
                "rows_out": len(clean_cf),
                "rejected": len(raw_cf) - len(clean_cf),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'cashflow': {len(clean_cf)} rows in {dt:.3f}s")

        # 5. Analysis
        t0 = time.perf_counter()
        raw_analysis = load_core_file("analysis.xlsx")
        clean_analysis = transform_analysis(raw_analysis, valid_tickers)
        clean_analysis.to_sql("analysis", conn, if_exists="append", index=False)
        counts["analysis"] = len(clean_analysis)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "analysis",
                "rows_in": len(raw_analysis),
                "rows_out": len(clean_analysis),
                "rejected": len(raw_analysis) - len(clean_analysis),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'analysis': {len(clean_analysis)} rows in {dt:.3f}s")

        # 6. Documents
        t0 = time.perf_counter()
        raw_docs = load_core_file("documents.xlsx")
        clean_docs = transform_documents(raw_docs, valid_tickers)
        clean_docs.to_sql("documents", conn, if_exists="append", index=False)
        counts["documents"] = len(clean_docs)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "documents",
                "rows_in": len(raw_docs),
                "rows_out": len(clean_docs),
                "rejected": len(raw_docs) - len(clean_docs),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'documents': {len(clean_docs)} rows in {dt:.3f}s")

        # 7. Pros and Cons
        t0 = time.perf_counter()
        raw_pc = load_core_file("prosandcons.xlsx")
        clean_pc = transform_prosandcons(raw_pc, valid_tickers)
        clean_pc.to_sql("prosandcons", conn, if_exists="append", index=False)
        counts["prosandcons"] = len(clean_pc)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "prosandcons",
                "rows_in": len(raw_pc),
                "rows_out": len(clean_pc),
                "rejected": len(raw_pc) - len(clean_pc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'prosandcons': {len(clean_pc)} rows in {dt:.3f}s")

        # 8. Sectors
        t0 = time.perf_counter()
        raw_sectors = load_supporting_file("sectors.xlsx")
        clean_sectors = transform_sectors(raw_sectors, valid_tickers)
        clean_sectors.to_sql("sectors", conn, if_exists="append", index=False)
        counts["sectors"] = len(clean_sectors)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "sectors",
                "rows_in": len(raw_sectors),
                "rows_out": len(clean_sectors),
                "rejected": len(raw_sectors) - len(clean_sectors),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'sectors': {len(clean_sectors)} rows in {dt:.3f}s")

        # 9. Stock Prices
        t0 = time.perf_counter()
        raw_prices = load_supporting_file("stock_prices.xlsx")
        clean_prices = transform_stock_prices(raw_prices, valid_tickers)
        clean_prices.to_sql("stock_prices", conn, if_exists="append", index=False)
        counts["stock_prices"] = len(clean_prices)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "stock_prices",
                "rows_in": len(raw_prices),
                "rows_out": len(clean_prices),
                "rejected": len(raw_prices) - len(clean_prices),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'stock_prices': {len(clean_prices)} rows in {dt:.3f}s")

        # 10. Market Cap
        t0 = time.perf_counter()
        raw_mcap = load_supporting_file("market_cap.xlsx")
        clean_mcap = transform_market_cap(raw_mcap, valid_tickers)
        clean_mcap.to_sql("market_cap", conn, if_exists="append", index=False)
        counts["market_cap"] = len(clean_mcap)
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "market_cap",
                "rows_in": len(raw_mcap),
                "rows_out": len(clean_mcap),
                "rejected": len(raw_mcap) - len(clean_mcap),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(f"Loaded 'market_cap': {len(clean_mcap)} rows in {dt:.3f}s")

        # 11. Supplementary File: Financial Ratios (Profiled, held for Sprint 2)
        t0 = time.perf_counter()
        raw_ratios = load_supporting_file("financial_ratios.xlsx")
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "financial_ratios",
                "rows_in": len(raw_ratios),
                "rows_out": 0,
                "rejected": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(
            f"Profiled 'financial_ratios' (Sprint 2 computed): {len(raw_ratios)} raw rows"
        )

        # 12. Supplementary File: Peer Groups (Profiled, held for Sprint 3)
        t0 = time.perf_counter()
        raw_peers = load_supporting_file("peer_groups.xlsx")
        dt = time.perf_counter() - t0
        audit_rows.append(
            {
                "table": "peer_groups",
                "rows_in": len(raw_peers),
                "rows_out": 0,
                "rejected": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runtime_s": round(dt, 4),
            }
        )
        logger.info(
            f"Profiled 'peer_groups' (Sprint 3 screener): {len(raw_peers)} raw rows"
        )

        # Write load_audit.csv
        audit_df = pd.DataFrame(audit_rows)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_df.to_csv(audit_path, index=False)
        logger.info(f"Load audit log successfully generated at {audit_path}")

        # Integrity Check
        cursor = conn.cursor()
        fk_check = cursor.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_check:
            logger.error(
                f"PRAGMA foreign_key_check failed with {len(fk_check)} violations: {fk_check}"
            )
        else:
            logger.info("PRAGMA foreign_key_check passed with 0 violations.")

        conn.commit()
    except (OSError, sqlite3.Error, ValueError, KeyError) as exc:
        logger.error(f"Failed during database table load: {exc}")
        conn.rollback()
    finally:
        conn.close()

    return counts


if __name__ == "__main__":
    load_all_tables()
