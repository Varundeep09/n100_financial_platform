"""Schema and Data Quality (DQ) validator for N100 Financial Intelligence Platform."""

import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
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

REPORTS_DIR: Path = PROJECT_ROOT / os.getenv("REPORTS_DIR", "reports")

DQ04_BS_TOLERANCE: float = float(os.getenv("DQ04_BS_BALANCE_TOLERANCE", "0.01"))
DQ05_OPM_TOLERANCE: float = float(os.getenv("DQ05_OPM_TOLERANCE_PCT", "1.0"))
DQ09_NET_CASH_TOLERANCE: float = float(os.getenv("DQ09_NET_CASH_TOLERANCE_CR", "10.0"))
DQ11_TAX_MAX_PCT: float = float(os.getenv("DQ11_TAX_RATE_MAX_PCT", "60.0"))
DQ12_PAYOUT_MAX_PCT: float = float(os.getenv("DQ12_DIVIDEND_PAYOUT_MAX_PCT", "200.0"))
DQ16_MIN_YEARS: int = int(os.getenv("DQ16_MIN_COVERAGE_YEARS", "5"))

NORMALIZED_YEAR_REGEX: re.Pattern[str] = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
TICKER_VALID_REGEX: re.Pattern[str] = re.compile(r"^[A-Z0-9\-&]{2,12}$")


@dataclass
class ValidationFailure:
    """Represents a single data quality rule violation."""

    company_id: str
    year: str
    field: str
    issue: str
    severity: str


def validate_dq01_company_pk_uniqueness(
    companies_df: pd.DataFrame,
) -> list[ValidationFailure]:
    """Verify primary key uniqueness on companies dataset (DQ-01)."""
    failures: list[ValidationFailure] = []
    if companies_df is None or companies_df.empty:
        return failures
    id_col = "id" if "id" in companies_df.columns else "company_id"
    dups = companies_df[companies_df.duplicated(subset=[id_col], keep=False)]
    for _, row in dups.iterrows():
        raw_id = str(row[id_col])
        failures.append(
            ValidationFailure(
                company_id=raw_id,
                year="N/A",
                field=id_col,
                issue=f"Duplicate company PK detected: {raw_id}",
                severity="CRITICAL",
            )
        )
    return failures


def validate_dq02_annual_pk_uniqueness(
    df: pd.DataFrame, table_name: str
) -> list[ValidationFailure]:
    """Verify compound PK uniqueness (company_id, year) in annual financial tables (DQ-02)."""
    failures: list[ValidationFailure] = []
    if df is None or df.empty:
        return failures
    yr_col = "year" if "year" in df.columns else "Year"
    df_eval = df.copy()
    df_eval["_norm_ticker"] = df_eval["company_id"].apply(normalize_ticker)
    df_eval["_norm_year"] = df_eval[yr_col].apply(normalize_year)
    dups = df_eval[
        df_eval.duplicated(subset=["_norm_ticker", "_norm_year"], keep="last")
    ]
    for _, row in dups.iterrows():
        failures.append(
            ValidationFailure(
                company_id=str(row.get("_norm_ticker") or row["company_id"]),
                year=str(row.get("_norm_year") or row[yr_col]),
                field=f"{table_name}.(company_id, {yr_col})",
                issue=f"Duplicate annual record in {table_name}: company={row['company_id']}, year={row[yr_col]}",
                severity="CRITICAL",
            )
        )
    return failures


def validate_dq03_fk_integrity(
    df: pd.DataFrame, valid_company_ids: set[str], table_name: str
) -> list[ValidationFailure]:
    """Verify that all company identifiers exist in the companies master universe (DQ-03)."""
    failures: list[ValidationFailure] = []
    if df is None or df.empty:
        return failures
    col_name = (
        "company_id"
        if "company_id" in df.columns
        else ("id" if "id" in df.columns else None)
    )
    if col_name is None:
        return failures
    yr_col = (
        "year" if "year" in df.columns else ("Year" if "Year" in df.columns else "N/A")
    )

    for _, row in df.iterrows():
        raw_val = row[col_name]
        norm_val = normalize_ticker(raw_val)
        if norm_val is None or norm_val not in valid_company_ids:
            row_yr = str(row[yr_col]) if yr_col != "N/A" else "N/A"
            failures.append(
                ValidationFailure(
                    company_id=str(raw_val),
                    year=row_yr,
                    field=f"{table_name}.{col_name}",
                    issue=f"Foreign key violation: '{raw_val}' not present in companies master",
                    severity="CRITICAL",
                )
            )
    return failures


def validate_dq04_bs_balance(
    bs_df: pd.DataFrame, tolerance: float = DQ04_BS_TOLERANCE
) -> list[ValidationFailure]:
    """Validate that balance sheet total assets match total liabilities within tolerance (DQ-04)."""
    failures: list[ValidationFailure] = []
    if bs_df is None or bs_df.empty:
        return failures
    for _, row in bs_df.iterrows():
        assets = float(row.get("total_assets", 0.0) or 0.0)
        liabs = float(row.get("total_liabilities", 0.0) or 0.0)
        diff = abs(assets - liabs)
        denom = assets if assets > 0 else (liabs if liabs > 0 else 1.0)
        imbalance_ratio = diff / denom
        if imbalance_ratio >= tolerance:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="balancesheet.(total_assets, total_liabilities)",
                    issue=f"Balance sheet imbalance: assets={assets}, liabilities={liabs}, ratio={imbalance_ratio:.4f} >= {tolerance}",
                    severity="WARNING",
                )
            )
    return failures


def validate_dq05_opm_cross_check(
    pl_df: pd.DataFrame, tolerance: float = DQ05_OPM_TOLERANCE
) -> list[ValidationFailure]:
    """Verify consistency between reported and calculated operating profit margins (DQ-05)."""
    failures: list[ValidationFailure] = []
    if pl_df is None or pl_df.empty:
        return failures
    for _, row in pl_df.iterrows():
        sales = float(row.get("sales", 0.0) or 0.0)
        op = float(row.get("operating_profit", 0.0) or 0.0)
        opm = float(row.get("opm_percentage", 0.0) or 0.0)
        if sales > 0:
            calc_opm = (op / sales) * 100.0
            if abs(opm - calc_opm) >= tolerance:
                failures.append(
                    ValidationFailure(
                        company_id=str(row.get("company_id", "UNKNOWN")),
                        year=str(row.get("year", "UNKNOWN")),
                        field="profitandloss.opm_percentage",
                        issue=f"OPM mismatch: reported={opm:.2f}%, calculated={calc_opm:.2f}%, diff={abs(opm - calc_opm):.2f}% >= {tolerance}%",
                        severity="WARNING",
                    )
                )
    return failures


def validate_dq06_positive_sales(
    pl_df: pd.DataFrame, bank_company_ids: set[str]
) -> list[ValidationFailure]:
    """Verify that non-financial companies report positive sales figures (DQ-06)."""
    failures: list[ValidationFailure] = []
    if pl_df is None or pl_df.empty:
        return failures
    for _, row in pl_df.iterrows():
        ticker = normalize_ticker(row.get("company_id"))
        if ticker and ticker in bank_company_ids:
            continue
        sales = float(row.get("sales", 0.0) or 0.0)
        if sales <= 0:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="profitandloss.sales",
                    issue=f"Non-positive sales for non-bank company: sales={sales}",
                    severity="WARNING",
                )
            )
    return failures


def validate_dq07_year_format(
    df: pd.DataFrame, table_name: str
) -> list[ValidationFailure]:
    """Ensure all date and year fields normalise to standard 'YYYY-MM' format (DQ-07)."""
    failures: list[ValidationFailure] = []
    if df is None or df.empty:
        return failures
    yr_col = (
        "year" if "year" in df.columns else ("Year" if "Year" in df.columns else None)
    )
    if yr_col is None:
        return failures
    for _, row in df.iterrows():
        raw_yr = row[yr_col]
        norm_yr = normalize_year(raw_yr)
        if norm_yr == PARSE_ERROR or not NORMALIZED_YEAR_REGEX.match(norm_yr):
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(raw_yr),
                    field=f"{table_name}.{yr_col}",
                    issue=f"Unparseable year format in {table_name}: '{raw_yr}' -> {norm_yr}",
                    severity="CRITICAL",
                )
            )
    return failures


def validate_dq08_ticker_format(
    df: pd.DataFrame, table_name: str, col_name: str = "company_id"
) -> list[ValidationFailure]:
    """Validate ticker formatting and character constraints (DQ-08)."""
    failures: list[ValidationFailure] = []
    if df is None or df.empty or col_name not in df.columns:
        return failures
    yr_col = (
        "year" if "year" in df.columns else ("Year" if "Year" in df.columns else "N/A")
    )
    for _, row in df.iterrows():
        raw_ticker = row[col_name]
        norm_ticker = normalize_ticker(raw_ticker)
        if norm_ticker is None:
            row_yr = str(row[yr_col]) if yr_col != "N/A" else "N/A"
            failures.append(
                ValidationFailure(
                    company_id=str(raw_ticker),
                    year=row_yr,
                    field=f"{table_name}.{col_name}",
                    issue=f"Invalid ticker format in {table_name}: '{raw_ticker}'",
                    severity="CRITICAL",
                )
            )
    return failures


def validate_dq09_net_cash_check(
    cf_df: pd.DataFrame, tolerance: float = DQ09_NET_CASH_TOLERANCE
) -> list[ValidationFailure]:
    """Verify that net cash flow matches component cash flow sums within tolerance (DQ-09)."""
    failures: list[ValidationFailure] = []
    if cf_df is None or cf_df.empty:
        return failures
    for _, row in cf_df.iterrows():
        cfo = float(row.get("operating_activity", 0.0) or 0.0)
        cfi = float(row.get("investing_activity", 0.0) or 0.0)
        cff = float(row.get("financing_activity", 0.0) or 0.0)
        reported_net = float(row.get("net_cash_flow", 0.0) or 0.0)
        calculated_net = cfo + cfi + cff
        if abs(reported_net - calculated_net) > tolerance:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="cashflow.net_cash_flow",
                    issue=f"Net cash mismatch: reported={reported_net}, calculated={calculated_net}, diff={abs(reported_net - calculated_net):.2f} > {tolerance}",
                    severity="WARNING",
                )
            )
    return failures


def validate_dq10_non_negative_fixed_assets(
    bs_df: pd.DataFrame,
) -> list[ValidationFailure]:
    """Verify that reported fixed assets are non-negative (DQ-10)."""
    failures: list[ValidationFailure] = []
    if bs_df is None or bs_df.empty:
        return failures
    for _, row in bs_df.iterrows():
        fa = float(row.get("fixed_assets", 0.0) or 0.0)
        if fa < 0:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="balancesheet.fixed_assets",
                    issue=f"Negative fixed assets detected: fixed_assets={fa}",
                    severity="WARNING",
                )
            )
    return failures


def validate_dq11_tax_rate_range(
    pl_df: pd.DataFrame, max_tax_pct: float = DQ11_TAX_MAX_PCT
) -> list[ValidationFailure]:
    """Verify that effective tax rates fall within realistic bounds (DQ-11)."""
    failures: list[ValidationFailure] = []
    if pl_df is None or pl_df.empty:
        return failures
    for _, row in pl_df.iterrows():
        tax = float(row.get("tax_percentage", 0.0) or 0.0)
        if tax < 0.0 or tax > max_tax_pct:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="profitandloss.tax_percentage",
                    issue=f"Tax rate out of bounds [0, {max_tax_pct}]: tax={tax:.2f}%",
                    severity="WARNING",
                )
            )
    return failures


def validate_dq12_dividend_payout_cap(
    pl_df: pd.DataFrame, max_payout: float = DQ12_PAYOUT_MAX_PCT
) -> list[ValidationFailure]:
    """Flag dividend payout ratios exceeding reasonable maximum thresholds (DQ-12)."""
    failures: list[ValidationFailure] = []
    if pl_df is None or pl_df.empty:
        return failures
    for _, row in pl_df.iterrows():
        payout = float(row.get("dividend_payout", 0.0) or 0.0)
        if payout > max_payout or payout < 0.0:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="profitandloss.dividend_payout",
                    issue=f"Dividend payout ratio flagged: payout={payout:.2f}% > {max_payout}%",
                    severity="WARNING",
                )
            )
    return failures


def validate_dq13_url_validity(
    docs_df: pd.DataFrame,
    sample_size: int | None = 20,
    check_live: bool = True,
) -> list[ValidationFailure]:
    """Verify reachability and HTTP status of annual report document URLs (DQ-13)."""
    failures: list[ValidationFailure] = []
    if docs_df is None or docs_df.empty:
        return failures

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    eval_df = docs_df if sample_size is None else docs_df.head(sample_size)
    for _, row in eval_df.iterrows():
        url = str(row.get("Annual_Report", "")).strip()
        if not url or not url.startswith("http"):
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("Year", "UNKNOWN")),
                    field="documents.Annual_Report",
                    issue=f"Invalid URL structure: '{url}'",
                    severity="WARNING",
                )
            )
            continue

        if check_live:
            try:
                resp = requests.head(
                    url, headers=headers, timeout=5.0, allow_redirects=True
                )
                if resp.status_code != 200:
                    failures.append(
                        ValidationFailure(
                            company_id=str(row.get("company_id", "UNKNOWN")),
                            year=str(row.get("Year", "UNKNOWN")),
                            field="documents.Annual_Report",
                            issue=f"URL returned non-200 status ({resp.status_code}): {url}",
                            severity="WARNING",
                        )
                    )
            except requests.RequestException as exc:
                failures.append(
                    ValidationFailure(
                        company_id=str(row.get("company_id", "UNKNOWN")),
                        year=str(row.get("Year", "UNKNOWN")),
                        field="documents.Annual_Report",
                        issue=f"URL unreachable ({exc.__class__.__name__}): {url}",
                        severity="WARNING",
                    )
                )
    return failures


def validate_dq14_eps_sign_consistency(
    pl_df: pd.DataFrame,
) -> list[ValidationFailure]:
    """Verify mathematical sign consistency between reported net profit and EPS (DQ-14)."""
    failures: list[ValidationFailure] = []
    if pl_df is None or pl_df.empty:
        return failures
    for _, row in pl_df.iterrows():
        np_val = float(row.get("net_profit", 0.0) or 0.0)
        eps_val = float(row.get("eps", 0.0) or 0.0)
        if np_val > 0 and eps_val <= 0:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="profitandloss.(net_profit, eps)",
                    issue=f"EPS sign mismatch: net_profit={np_val} > 0 but eps={eps_val} <= 0",
                    severity="WARNING",
                )
            )
        elif np_val < 0 and eps_val >= 0:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="profitandloss.(net_profit, eps)",
                    issue=f"EPS sign mismatch: net_profit={np_val} < 0 but eps={eps_val} >= 0",
                    severity="WARNING",
                )
            )
    return failures


def validate_dq15_strict_bs_balance(
    bs_df: pd.DataFrame,
) -> list[ValidationFailure]:
    """Perform exact integer equality check on balance sheet assets and liabilities (DQ-15)."""
    failures: list[ValidationFailure] = []
    if bs_df is None or bs_df.empty:
        return failures
    for _, row in bs_df.iterrows():
        assets = float(row.get("total_assets", 0.0) or 0.0)
        liabs = float(row.get("total_liabilities", 0.0) or 0.0)
        if assets != liabs:
            failures.append(
                ValidationFailure(
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row.get("year", "UNKNOWN")),
                    field="balancesheet.(total_assets, total_liabilities)",
                    issue=f"Strict balance sheet imbalance (INFO): assets={assets}, liabilities={liabs}",
                    severity="INFO",
                )
            )
    return failures


def validate_dq16_coverage_check(
    pl_df: pd.DataFrame,
    bs_df: pd.DataFrame,
    cf_df: pd.DataFrame,
    valid_company_ids: set[str],
    min_years: int = DQ16_MIN_YEARS,
) -> list[ValidationFailure]:
    """Flag companies with fewer than minimum required reporting annual periods (DQ-16)."""
    failures: list[ValidationFailure] = []
    for table_name, df in [("P&L", pl_df), ("BS", bs_df), ("CF", cf_df)]:
        if df is None or df.empty:
            continue
        eval_df = df.copy()
        eval_df["_clean_ticker"] = eval_df["company_id"].apply(normalize_ticker)
        eval_df["_clean_year"] = eval_df["year"].apply(normalize_year)
        filtered = eval_df[
            eval_df["_clean_ticker"].isin(valid_company_ids)
            & (eval_df["_clean_year"] != PARSE_ERROR)
        ].drop_duplicates(subset=["_clean_ticker", "_clean_year"])

        yr_counts = filtered.groupby("_clean_ticker")["_clean_year"].nunique()
        for cid in valid_company_ids:
            cnt = yr_counts.get(cid, 0)
            if cnt < min_years:
                failures.append(
                    ValidationFailure(
                        company_id=str(cid),
                        year="ALL",
                        field=f"{table_name}.coverage",
                        issue=f"Insufficient history in {table_name}: {cnt} years < {min_years} years required",
                        severity="WARNING",
                    )
                )
    return failures


def save_validation_failures(
    failures: list[ValidationFailure], output_path: Path | None = None
) -> pd.DataFrame:
    """Persist all collected validation failure records to validation_failures.csv."""
    target_path = output_path or (REPORTS_DIR / "validation_failures.csv")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    records = [asdict(f) for f in failures]
    df = pd.DataFrame(
        records,
        columns=["company_id", "year", "field", "issue", "severity"],
    )
    df.to_csv(target_path, index=False, encoding="utf-8")
    logger.info(f"Saved {len(df)} validation failure records to {target_path}")
    return df


def run_full_validation(check_live_urls: bool = False) -> pd.DataFrame:
    """Execute all 16 Data Quality rules across the core and supporting datasets."""
    logger.info("Starting complete 16-rule Data Quality validation run...")
    companies_df = load_core_file("companies.xlsx")
    pl_df = load_core_file("profitandloss.xlsx")
    bs_df = load_core_file("balancesheet.xlsx")
    cf_df = load_core_file("cashflow.xlsx")
    analysis_df = load_core_file("analysis.xlsx")
    docs_df = load_core_file("documents.xlsx")
    prosandcons_df = load_core_file("prosandcons.xlsx")
    sectors_df = load_supporting_file("sectors.xlsx")

    valid_company_ids: set[str] = set()
    if companies_df is not None:
        valid_company_ids = set(companies_df["id"].apply(normalize_ticker).dropna())

    bank_company_ids: set[str] = set()
    if sectors_df is not None:
        bank_mask = sectors_df["broad_sector"].isin(
            ["Financial Services", "Financials"]
        ) | sectors_df["sub_sector"].str.contains("Bank", case=False, na=False)
        bank_company_ids = set(
            sectors_df[bank_mask]["company_id"].apply(normalize_ticker).dropna()
        )

    all_failures: list[ValidationFailure] = []

    # DQ-01: Company PK Uniqueness
    all_failures.extend(validate_dq01_company_pk_uniqueness(companies_df))

    # DQ-02: Annual PK Uniqueness
    for name, df in [
        ("profitandloss", pl_df),
        ("balancesheet", bs_df),
        ("cashflow", cf_df),
    ]:
        all_failures.extend(validate_dq02_annual_pk_uniqueness(df, name))

    # DQ-03: FK Integrity
    for name, df in [
        ("profitandloss", pl_df),
        ("balancesheet", bs_df),
        ("cashflow", cf_df),
        ("analysis", analysis_df),
        ("documents", docs_df),
        ("prosandcons", prosandcons_df),
    ]:
        all_failures.extend(validate_dq03_fk_integrity(df, valid_company_ids, name))

    # DQ-04: BS Balance
    all_failures.extend(validate_dq04_bs_balance(bs_df))

    # DQ-05: OPM Cross-Check
    all_failures.extend(validate_dq05_opm_cross_check(pl_df))

    # DQ-06: Positive Sales
    all_failures.extend(validate_dq06_positive_sales(pl_df, bank_company_ids))

    # DQ-07: Year Format
    for name, df in [
        ("profitandloss", pl_df),
        ("balancesheet", bs_df),
        ("cashflow", cf_df),
        ("documents", docs_df),
    ]:
        all_failures.extend(validate_dq07_year_format(df, name))

    # DQ-08: Ticker Format
    all_failures.extend(
        validate_dq08_ticker_format(companies_df, "companies", col_name="id")
    )
    for name, df in [
        ("profitandloss", pl_df),
        ("balancesheet", bs_df),
        ("cashflow", cf_df),
    ]:
        all_failures.extend(validate_dq08_ticker_format(df, name))

    # DQ-09: Net Cash Check
    all_failures.extend(validate_dq09_net_cash_check(cf_df))

    # DQ-10: Non-Negative Fixed Assets
    all_failures.extend(validate_dq10_non_negative_fixed_assets(bs_df))

    # DQ-11: Tax Rate Range
    all_failures.extend(validate_dq11_tax_rate_range(pl_df))

    # DQ-12: Dividend Payout Cap
    all_failures.extend(validate_dq12_dividend_payout_cap(pl_df))

    # DQ-13: URL Validity
    all_failures.extend(
        validate_dq13_url_validity(docs_df, sample_size=20, check_live=check_live_urls)
    )

    # DQ-14: EPS Sign Consistency
    all_failures.extend(validate_dq14_eps_sign_consistency(pl_df))

    # DQ-15: Strict BS Balance
    all_failures.extend(validate_dq15_strict_bs_balance(bs_df))

    # DQ-16: Coverage Check
    all_failures.extend(
        validate_dq16_coverage_check(pl_df, bs_df, cf_df, valid_company_ids)
    )

    result_df = save_validation_failures(all_failures)
    return result_df


if __name__ == "__main__":
    run_full_validation(check_live_urls=False)
