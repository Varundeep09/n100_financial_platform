"""Excel loader and field normaliser module for N100 Financial Intelligence Platform."""

import logging
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
RAW_DIR: Path = PROJECT_ROOT / os.getenv("RAW_DATA_DIR", "data/raw")
SUPPORTING_DIR: Path = PROJECT_ROOT / os.getenv(
    "SUPPORTING_DATA_DIR", "data/supporting"
)
PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
DB_PATH: Path = PROJECT_ROOT / os.getenv("DB_PATH", "db/nifty100.db")

PARSE_ERROR: str = "PARSE_ERROR"

CORE_FILES: list[str] = [
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "analysis.xlsx",
    "documents.xlsx",
    "prosandcons.xlsx",
]

SUPPORTING_FILES: list[str] = [
    "sectors.xlsx",
    "stock_prices.xlsx",
    "market_cap.xlsx",
    "financial_ratios.xlsx",
    "peer_groups.xlsx",
]

MONTH_MAP: dict[str, str] = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}

NORMALIZED_YEAR_REGEX: re.Pattern[str] = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
FY_PREFIX_REGEX: re.Pattern[str] = re.compile(r"^fy[- ]?(\d{2,4})$", re.IGNORECASE)
BARE_YEAR_REGEX: re.Pattern[str] = re.compile(r"^\d{4}$")
MONTH_YEAR_REGEX: re.Pattern[str] = re.compile(
    r"^([a-z]+)[-\s/]+(\d{2,4})(?:\s+.*)?$", re.IGNORECASE
)
YEAR_MONTH_REGEX: re.Pattern[str] = re.compile(
    r"^(\d{2,4})[-\s/]+([a-z]+)$", re.IGNORECASE
)
TICKER_VALID_REGEX: re.Pattern[str] = re.compile(r"^[A-Z0-9\-&]{2,12}$")


def log_parse_failure(raw_value: Any, field_name: str = "year") -> None:
    """Log an unparseable raw value to data/processed/parse_failures.csv."""
    try:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        failure_file = PROCESSED_DIR / "parse_failures.csv"
        file_exists = failure_file.exists()
        with open(failure_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("timestamp,field,raw_value\n")
            ts = datetime.now(timezone.utc).isoformat()
            f.write(f"{ts},{field_name},{raw_value}\n")
    except OSError as exc:
        logger.error(f"Failed to record parse failure for value '{raw_value}': {exc}")


def normalize_year(value: Any) -> str:
    """Standardise any valid fiscal year or date representation to 'YYYY-MM' format."""
    if value is None:
        log_parse_failure(value, field_name="year")
        return PARSE_ERROR

    if isinstance(value, float) and np.isnan(value):
        log_parse_failure(value, field_name="year")
        return PARSE_ERROR

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return f"{value.year:04d}-{value.month:02d}"

    if isinstance(value, (int, np.integer)):
        int_val = int(value)
        if 1900 <= int_val <= 2099:
            return f"{int_val:04d}-03"
        if 0 <= int_val < 50:
            return f"20{int_val:02d}-03"
        if 50 <= int_val <= 99:
            return f"19{int_val:02d}-03"
        log_parse_failure(value, field_name="year")
        return PARSE_ERROR

    if isinstance(value, (float, np.floating)):
        if value.is_integer():
            return normalize_year(int(value))
        log_parse_failure(value, field_name="year")
        return PARSE_ERROR

    val_str = str(value).strip()
    if not val_str:
        log_parse_failure(value, field_name="year")
        return PARSE_ERROR

    if NORMALIZED_YEAR_REGEX.match(val_str):
        return val_str

    fy_match = FY_PREFIX_REGEX.match(val_str)
    if fy_match:
        digits = fy_match.group(1)
        if len(digits) == 2:
            yr_int = int(digits)
            yyyy = f"20{digits}" if yr_int < 50 else f"19{digits}"
        else:
            yyyy = digits
        return f"{yyyy}-03"

    if BARE_YEAR_REGEX.match(val_str):
        return f"{val_str}-03"

    my_match = MONTH_YEAR_REGEX.match(val_str)
    if my_match:
        month_part = my_match.group(1).lower()
        year_part = my_match.group(2)
        if month_part in MONTH_MAP:
            mm = MONTH_MAP[month_part]
            if len(year_part) == 2:
                yr_int = int(year_part)
                yyyy = f"20{year_part}" if yr_int < 50 else f"19{year_part}"
            else:
                yyyy = year_part
            return f"{yyyy}-{mm}"

    ym_match = YEAR_MONTH_REGEX.match(val_str)
    if ym_match:
        year_part = ym_match.group(1)
        month_part = ym_match.group(2).lower()
        if month_part in MONTH_MAP:
            mm = MONTH_MAP[month_part]
            if len(year_part) == 2:
                yr_int = int(year_part)
                yyyy = f"20{year_part}" if yr_int < 50 else f"19{year_part}"
            else:
                yyyy = year_part
            return f"{yyyy}-{mm}"

    log_parse_failure(value, field_name="year")
    return PARSE_ERROR


def normalize_ticker(value: Any) -> str | None:
    """Clean and validate NSE ticker symbol according to DQ-08 specifications."""
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    ticker_str = str(value).strip().upper()
    if not ticker_str:
        return None
    if TICKER_VALID_REGEX.match(ticker_str):
        return ticker_str
    return None


def load_core_file(filename: str) -> pd.DataFrame | None:
    """Read a core dataset Excel file with title row skipped (header=1)."""
    try:
        file_path = RAW_DIR / filename
        logger.debug(f"Reading core file from {file_path}")
        return pd.read_excel(file_path, header=1)
    except (OSError, ValueError) as exc:
        logger.error(f"Failed to load core Excel file '{filename}': {exc}")
        return None


def load_supporting_file(filename: str) -> pd.DataFrame | None:
    """Read a supplementary dataset Excel file with standard header (header=0)."""
    try:
        file_path = SUPPORTING_DIR / filename
        logger.debug(f"Reading supporting file from {file_path}")
        return pd.read_excel(file_path, header=0)
    except (OSError, ValueError) as exc:
        logger.error(f"Failed to load supporting Excel file '{filename}': {exc}")
        return None


def main() -> None:
    """Execute Day 2 loader verification on all core and supporting source files."""
    logger.info("Starting Excel loader verification...")
    all_ok = True
    for label, folder, files in [
        ("Core", RAW_DIR, CORE_FILES),
        ("Supporting", SUPPORTING_DIR, SUPPORTING_FILES),
    ]:
        logger.info(f"Checking {label} files in: {folder}")
        for fname in files:
            fpath = folder / fname
            if fpath.exists():
                logger.info(f"  [OK] {fname}")
            else:
                logger.error(f"  [MISSING] {fname}")
                all_ok = False
    if all_ok:
        logger.info("All 12 source files verified present.")


if __name__ == "__main__":
    main()
