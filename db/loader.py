"""Database initialisation and ETL table loader for N100 Financial Intelligence Platform."""

import logging
import os
import sqlite3
import sys
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
    db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH
) -> dict[str, int]:
    """Execute end-to-end extraction, transformation, and SQLite insertion across 10 tables."""
    conn = init_database(db_path, schema_path)
    counts: dict[str, int] = {}

    try:
        # 1. Master Companies
        raw_companies = load_core_file("companies.xlsx")
        clean_companies = transform_companies(raw_companies)
        clean_companies.to_sql("companies", conn, if_exists="append", index=False)
        counts["companies"] = len(clean_companies)
        valid_tickers = set(clean_companies["id"])
        logger.info(f"Loaded 'companies' table: {len(clean_companies)} rows")

        # 2. Profit and Loss
        raw_pl = load_core_file("profitandloss.xlsx")
        clean_pl = transform_profitandloss(raw_pl, valid_tickers)
        clean_pl.to_sql("profitandloss", conn, if_exists="append", index=False)
        counts["profitandloss"] = len(clean_pl)
        logger.info(f"Loaded 'profitandloss' table: {len(clean_pl)} rows")

        # 3. Balance Sheet
        raw_bs = load_core_file("balancesheet.xlsx")
        clean_bs = transform_balancesheet(raw_bs, valid_tickers)
        clean_bs.to_sql("balancesheet", conn, if_exists="append", index=False)
        counts["balancesheet"] = len(clean_bs)
        logger.info(f"Loaded 'balancesheet' table: {len(clean_bs)} rows")

        # 4. Cash Flow
        raw_cf = load_core_file("cashflow.xlsx")
        clean_cf = transform_cashflow(raw_cf, valid_tickers)
        clean_cf.to_sql("cashflow", conn, if_exists="append", index=False)
        counts["cashflow"] = len(clean_cf)
        logger.info(f"Loaded 'cashflow' table: {len(clean_cf)} rows")

        # 5. Analysis
        raw_analysis = load_core_file("analysis.xlsx")
        clean_analysis = transform_analysis(raw_analysis, valid_tickers)
        clean_analysis.to_sql("analysis", conn, if_exists="append", index=False)
        counts["analysis"] = len(clean_analysis)
        logger.info(f"Loaded 'analysis' table: {len(clean_analysis)} rows")

        # 6. Documents
        raw_docs = load_core_file("documents.xlsx")
        clean_docs = transform_documents(raw_docs, valid_tickers)
        clean_docs.to_sql("documents", conn, if_exists="append", index=False)
        counts["documents"] = len(clean_docs)
        logger.info(f"Loaded 'documents' table: {len(clean_docs)} rows")

        # 7. Pros and Cons
        raw_pc = load_core_file("prosandcons.xlsx")
        clean_pc = transform_prosandcons(raw_pc, valid_tickers)
        clean_pc.to_sql("prosandcons", conn, if_exists="append", index=False)
        counts["prosandcons"] = len(clean_pc)
        logger.info(f"Loaded 'prosandcons' table: {len(clean_pc)} rows")

        # 8. Sectors
        raw_sectors = load_supporting_file("sectors.xlsx")
        clean_sectors = transform_sectors(raw_sectors, valid_tickers)
        clean_sectors.to_sql("sectors", conn, if_exists="append", index=False)
        counts["sectors"] = len(clean_sectors)
        logger.info(f"Loaded 'sectors' table: {len(clean_sectors)} rows")

        # 9. Stock Prices
        raw_prices = load_supporting_file("stock_prices.xlsx")
        clean_prices = transform_stock_prices(raw_prices, valid_tickers)
        clean_prices.to_sql("stock_prices", conn, if_exists="append", index=False)
        counts["stock_prices"] = len(clean_prices)
        logger.info(f"Loaded 'stock_prices' table: {len(clean_prices)} rows")

        # 10. Market Cap
        raw_mcap = load_supporting_file("market_cap.xlsx")
        clean_mcap = transform_market_cap(raw_mcap, valid_tickers)
        clean_mcap.to_sql("market_cap", conn, if_exists="append", index=False)
        counts["market_cap"] = len(clean_mcap)
        logger.info(f"Loaded 'market_cap' table: {len(clean_mcap)} rows")

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
