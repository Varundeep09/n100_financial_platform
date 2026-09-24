"""Cash Flow KPIs and Capital Allocation Classification Engine.

Sprint 2, Day 11 Deliverables:
1. Free Cash Flow (FCF):
   - Formula: operating_activity + investing_activity.
   - Negative values are allowed and meaningful (preserved, not nulled).
2. CFO Quality Score:
   - Formula: Trailing 5-year average of CFO / PAT (operating_activity / net_profit).
   - Exact calendar year-gap matching (no silent averaging across fiscal gaps).
   - Quality classifications:
     * > 1.0     -> 'High Quality'
     * 0.5 - 1.0 -> 'Moderate'
     * < 0.5     -> 'Accrual Risk'
   - Returns None if PAT = 0 for any year in the window, or if fewer than 5 consecutive years exist.
3. CapEx Intensity:
   - Formula: abs(investing_activity) / sales * 100.
   - Intensity classifications:
     * < 3%      -> 'Asset Light'
     * 3% - 8%   -> 'Moderate'
     * > 8%      -> 'Capital Intensive'
4. FCF Conversion Rate:
   - Formula: FCF / operating_profit * 100.
   - Banking-template handling: returns None with label 'Not Applicable (Banking Template)' for
     the 16 confirmed banking/financing template companies.
   - Returns None if operating_profit is None or 0.
   - Preserves negative conversion rates when FCF is negative.
5. Capital Allocation 8-Pattern Classifier:
   - Based on the signs of (CFO, CFI, CFF):
     * (+, -, -) with CFO Quality > 1.0 -> 'Shareholder Returns'
     * (+, -, -) otherwise              -> 'Reinvestor'
     * (+, +, -)                        -> 'Liquidating Assets'
     * (-, +, +) or (-, +, -)           -> 'Distress Signal'
     * (-, -, +)                        -> 'Growth Funded by Debt'
     * (+, +, +)                        -> 'Cash Accumulator'
     * (-, -, -)                        -> 'Pre-Revenue'
     * (+, -, +)                        -> 'Mixed'
6. Pipeline and Exporters:
   - get_cashflow_data(company_id=None, db_path=DB_PATH) -> pd.DataFrame
   - calculate_cashflow_kpis(df: pd.DataFrame) -> pd.DataFrame
   - generate_capital_allocation_csv(output_path=None, db_path=DB_PATH) -> Path
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.analytics.ratios import (
    BANKING_TEMPLATE_COMPANIES,
    FINANCIALS_SECTOR_COMPANIES,
    normalize_pl_statement,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "nifty100.db"


class MetricResult(dict):
    """Versatile metric container supporting dict key, attribute, and tuple unpacking access."""

    def __init__(self, value: Any, label: Any, **kwargs: Any) -> None:
        super().__init__(value=value, label=label, **kwargs)
        self.__dict__ = self

    def __iter__(self):
        return iter((self["value"], self["label"]))


class CapitalAllocationResult(dict):
    """Result container for capital allocation 8-pattern classification."""

    def __init__(
        self,
        cfo_sign: str,
        cfi_sign: str,
        cff_sign: str,
        pattern_label: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            cfo_sign=cfo_sign,
            cfi_sign=cfi_sign,
            cff_sign=cff_sign,
            pattern_label=pattern_label,
            **kwargs,
        )
        self.__dict__ = self

    def __iter__(self):
        return iter(
            (
                self["cfo_sign"],
                self["cfi_sign"],
                self["cff_sign"],
                self["pattern_label"],
            )
        )


def _extract_sign(val: Any) -> str | None:
    """Extract + or - sign safely from numeric or string input."""
    if val is None:
        return None
    if isinstance(val, str):
        val_str = val.strip()
        if val_str in ("+", "-", "?"):
            return val_str
        try:
            f = float(val_str)
            return "+" if f >= 0 else "-"
        except ValueError:
            return None
    try:
        f = float(val)
        if np.isnan(f):
            return None
        return "+" if f >= 0 else "-"
    except (ValueError, TypeError):
        return None


def compute_fcf(
    operating_activity: float | None,
    investing_activity: float | None,
) -> float | None:
    """Calculate Free Cash Flow (FCF) as operating_activity + investing_activity.

    Negative values are allowed and meaningful (preserved, not nulled).
    Returns None if either input is None or NaN.
    """
    if operating_activity is None or investing_activity is None:
        return None
    try:
        cfo = float(operating_activity)
        cfi = float(investing_activity)
    except (ValueError, TypeError):
        return None
    if np.isnan(cfo) or np.isnan(cfi):
        return None
    return round(cfo + cfi, 4)


def compute_cfo_quality_score(
    cfo_or_history: Any,
    pat_history: Any = None,
    company_id: str | None = None,
    broad_sector: str | None = None,
    is_financial: bool = False,
) -> MetricResult:
    """Calculate CFO Quality Score as trailing 5-year average of CFO / PAT.

    Thresholds:
      - > 1.0     -> 'High Quality'
      - 0.5 - 1.0 -> 'Moderate'
      - < 0.5     -> 'Accrual Risk'

    Financials Sector Carve-Out:
      - For lending institutions (IRFC, RECLTD, PFC, and commercial banks), operating
        cash flows structurally include loan disbursements/advances as cash outflows.
        Evaluating CFO / PAT as 'Accrual Risk' is economically misleading.
      - Financials companies return value=None, label='Not Applicable (Financials Sector)'.

    Returns (None, None) if:
      - Fewer than 5 periods exist
      - PAT == 0 for any period in the 5-year window
      - Any period has missing/NaN data
    """
    if (
        is_financial
        or broad_sector == "Financials"
        or (company_id and company_id in FINANCIALS_SECTOR_COMPANIES)
    ):
        return MetricResult(value=None, label="Not Applicable (Financials Sector)")
    if pat_history is not None:
        cfo_list = list(cfo_or_history)
        pat_list = list(pat_history)
        if len(cfo_list) < 5 or len(pat_list) < 5:
            return MetricResult(value=None, label=None)
        ratios: list[float] = []
        for c, p in zip(cfo_list[-5:], pat_list[-5:]):
            if c is None or p is None:
                return MetricResult(value=None, label=None)
            try:
                c_val = float(c)
                p_val = float(p)
            except (ValueError, TypeError):
                return MetricResult(value=None, label=None)
            if np.isnan(c_val) or np.isnan(p_val) or abs(p_val) < 1e-9:
                return MetricResult(value=None, label=None)
            ratios.append(c_val / p_val)
    else:
        items = list(cfo_or_history)
        if len(items) < 5:
            return MetricResult(value=None, label=None)
        ratios = []
        for item in items[-5:]:
            if isinstance(item, (tuple, list)):
                c, p = item
                if c is None or p is None:
                    return MetricResult(value=None, label=None)
                try:
                    c_val = float(c)
                    p_val = float(p)
                except (ValueError, TypeError):
                    return MetricResult(value=None, label=None)
                if np.isnan(c_val) or np.isnan(p_val) or abs(p_val) < 1e-9:
                    return MetricResult(value=None, label=None)
                ratios.append(c_val / p_val)
            else:
                if item is None:
                    return MetricResult(value=None, label=None)
                try:
                    r_val = float(item)
                except (ValueError, TypeError):
                    return MetricResult(value=None, label=None)
                if np.isnan(r_val):
                    return MetricResult(value=None, label=None)
                ratios.append(r_val)

    if len(ratios) != 5:
        return MetricResult(value=None, label=None)

    avg_score = round(float(np.mean(ratios)), 4)
    if avg_score > 1.0:
        label = "High Quality"
    elif avg_score >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return MetricResult(value=avg_score, label=label)


def compute_capex_intensity(
    investing_activity: float | None,
    sales: float | None,
) -> MetricResult:
    """Calculate CapEx Intensity as abs(investing_activity) / sales * 100.

    Thresholds:
      - < 3%      -> 'Asset Light'
      - 3% - 8%   -> 'Moderate'
      - > 8%      -> 'Capital Intensive'
    """
    if investing_activity is None or sales is None:
        return MetricResult(value=None, label=None)
    try:
        cfi = float(investing_activity)
        s = float(sales)
    except (ValueError, TypeError):
        return MetricResult(value=None, label=None)
    if np.isnan(cfi) or np.isnan(s) or s <= 0:
        return MetricResult(value=None, label=None)

    intensity = round((abs(cfi) / s) * 100.0, 4)
    if intensity < 3.0:
        label = "Asset Light"
    elif intensity <= 8.0:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return MetricResult(value=intensity, label=label)


def compute_fcf_conversion(
    fcf: float | None,
    operating_profit: float | None,
    company_id: str | None = None,
    is_banking_template: bool = False,
) -> MetricResult:
    """Calculate FCF Conversion Rate as FCF / operating_profit * 100.

    Returns None with 'Not Applicable (Banking Template)' for banking-template companies.
    Returns None if operating_profit is None or 0.
    Preserves negative conversion rates when FCF is negative.
    """
    if is_banking_template or (company_id and company_id in BANKING_TEMPLATE_COMPANIES):
        return MetricResult(value=None, label="Not Applicable (Banking Template)")

    if operating_profit is None:
        return MetricResult(value=None, label="Operating Profit Missing")
    try:
        op = float(operating_profit)
    except (ValueError, TypeError):
        return MetricResult(value=None, label="Operating Profit Missing")
    if np.isnan(op) or abs(op) < 1e-9:
        return MetricResult(value=None, label="Operating Profit Zero")

    if fcf is None:
        return MetricResult(value=None, label="FCF Missing")
    try:
        f = float(fcf)
    except (ValueError, TypeError):
        return MetricResult(value=None, label="FCF Missing")
    if np.isnan(f):
        return MetricResult(value=None, label="FCF Missing")

    conv_rate = round((f / op) * 100.0, 4)
    return MetricResult(value=conv_rate, label="Normal")


def classify_capital_allocation(
    cfo: Any,
    cfi: Any,
    cff: Any,
    cfo_quality_label: str | None = None,
    cfo_quality_score: float | None = None,
) -> CapitalAllocationResult:
    """Classify company-year into one of 8 capital allocation patterns based on signs of (CFO, CFI, CFF).

    Patterns:
      - (+, -, -) & High Quality CFO -> 'Shareholder Returns'
      - (+, -, -) otherwise          -> 'Reinvestor'
      - (+, +, -)                    -> 'Liquidating Assets'
      - (-, +, +) or (-, +, -)       -> 'Distress Signal'
      - (-, -, +)                    -> 'Growth Funded by Debt'
      - (+, +, +)                    -> 'Cash Accumulator'
      - (-, -, -)                    -> 'Pre-Revenue'
      - (+, -, +)                    -> 'Mixed'
    """
    s_cfo = _extract_sign(cfo)
    s_cfi = _extract_sign(cfi)
    s_cff = _extract_sign(cff)

    if (
        s_cfo is None
        or s_cfi is None
        or s_cff is None
        or s_cfo == "?"
        or s_cfi == "?"
        or s_cff == "?"
    ):
        return CapitalAllocationResult("?", "?", "?", "Insufficient Data")

    is_high_quality = cfo_quality_label == "High Quality" or (
        cfo_quality_score is not None and cfo_quality_score > 1.0
    )

    if s_cfo == "+" and s_cfi == "-" and s_cff == "-":
        pattern = "Shareholder Returns" if is_high_quality else "Reinvestor"
    elif s_cfo == "+" and s_cfi == "+" and s_cff == "-":
        pattern = "Liquidating Assets"
    elif (
        s_cfo == "-"
        and s_cfi == "+"
        and s_cff == "+"
        or s_cfo == "-"
        and s_cfi == "+"
        and s_cff == "-"
    ):
        pattern = "Distress Signal"
    elif s_cfo == "-" and s_cfi == "-" and s_cff == "+":
        pattern = "Growth Funded by Debt"
    elif s_cfo == "+" and s_cfi == "+" and s_cff == "+":
        pattern = "Cash Accumulator"
    elif s_cfo == "-" and s_cfi == "-" and s_cff == "-":
        pattern = "Pre-Revenue"
    elif s_cfo == "+" and s_cfi == "-" and s_cff == "+":
        pattern = "Mixed"
    else:
        pattern = "Mixed"

    return CapitalAllocationResult(s_cfo, s_cfi, s_cff, pattern)


def get_cashflow_data(
    company_id: str | None = None,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """Load joined cashflow and profitandloss data from database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    query = """
        SELECT 
            cf.company_id,
            cf.year,
            cf.operating_activity,
            cf.investing_activity,
            cf.financing_activity,
            cf.net_cash_flow,
            pl.sales,
            pl.expenses,
            pl.operating_profit,
            pl.opm_percentage,
            pl.other_income,
            pl.depreciation,
            pl.profit_before_tax,
            pl.net_profit,
            s.broad_sector
        FROM cashflow cf
        LEFT JOIN profitandloss pl ON cf.company_id = pl.company_id AND cf.year = pl.year
        LEFT JOIN sectors s ON cf.company_id = s.company_id
    """
    params: list[Any] = []
    if company_id:
        query += " WHERE cf.company_id = ?"
        params.append(company_id)

    query += " ORDER BY cf.company_id, cf.year;"

    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


def calculate_cashflow_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all cash flow KPIs and capital allocation classification across joined DataFrame."""
    if df.empty:
        return pd.DataFrame()

    out_df = df.copy()

    # Process per company to maintain exact calendar year lookups for trailing 5-year CFO Quality Score
    grouped = out_df.groupby("company_id", sort=False)
    processed_dfs: list[pd.DataFrame] = []

    for comp_id, group in grouped:
        g = group.sort_values("year").reset_index(drop=True)
        year_row_map: dict[str, pd.Series] = {
            str(row["year"]): row for _, row in g.iterrows()
        }

        g_fcf: list[float | None] = []
        g_cfo_q_score: list[float | None] = []
        g_cfo_q_label: list[str | None] = []
        g_capex_int: list[float | None] = []
        g_capex_lbl: list[str | None] = []
        g_fcf_conv_rate: list[float | None] = []
        g_fcf_conv_lbl: list[str] = []
        g_cfo_sign: list[str] = []
        g_cfi_sign: list[str] = []
        g_cff_sign: list[str] = []
        g_pattern_label: list[str] = []

        for _, curr_row in g.iterrows():
            curr_year_str = str(curr_row["year"])
            broad_sector = curr_row.get("broad_sector")

            # 1. FCF
            cfo_raw = curr_row.get("operating_activity")
            cfi_raw = curr_row.get("investing_activity")
            cff_raw = curr_row.get("financing_activity")
            fcf_val = compute_fcf(cfo_raw, cfi_raw)
            g_fcf.append(fcf_val)

            is_financial = (broad_sector == "Financials") or (
                str(comp_id) in FINANCIALS_SECTOR_COMPANIES if comp_id else False
            )

            # 2. CFO Quality Score (trailing 5 consecutive calendar years matching exact month)
            if is_financial:
                q_res = MetricResult(
                    value=None, label="Not Applicable (Financials Sector)"
                )
            else:
                try:
                    curr_y = int(curr_year_str[:4])
                    curr_m = curr_year_str[5:7]
                except (ValueError, IndexError):
                    curr_y = None
                    curr_m = ""

                valid_window = True
                trailing_cfos: list[float] = []
                trailing_pats: list[float] = []

                if curr_y is None or not curr_m:
                    valid_window = False
                else:
                    for offset in range(5):
                        target_year_str = f"{curr_y - offset:04d}-{curr_m}"
                        if target_year_str not in year_row_map:
                            valid_window = False
                            break
                        row_t = year_row_map[target_year_str]
                        pat = row_t.get("net_profit")
                        cfo = row_t.get("operating_activity")

                        if pat is None or (
                            isinstance(pat, (float, np.floating)) and np.isnan(pat)
                        ):
                            valid_window = False
                            break
                        if cfo is None or (
                            isinstance(cfo, (float, np.floating)) and np.isnan(cfo)
                        ):
                            valid_window = False
                            break

                        pat_val = float(pat)
                        cfo_val = float(cfo)

                        if abs(pat_val) < 1e-9:
                            valid_window = False
                            break

                        trailing_cfos.append(cfo_val)
                        trailing_pats.append(pat_val)

                if valid_window and len(trailing_cfos) == 5:
                    # Reverse so trailing order is chronological
                    q_res = compute_cfo_quality_score(
                        trailing_cfos[::-1], trailing_pats[::-1]
                    )
                else:
                    q_res = MetricResult(value=None, label=None)

            g_cfo_q_score.append(q_res.value)
            g_cfo_q_label.append(q_res.label)

            # 3. CapEx Intensity
            sales_val = curr_row.get("sales")
            capex_res = compute_capex_intensity(cfi_raw, sales_val)
            g_capex_int.append(capex_res.value)
            g_capex_lbl.append(capex_res.label)

            # 4. FCF Conversion Rate (with banking template & shifted column awareness)
            norm = normalize_pl_statement(
                sales=sales_val,
                expenses=curr_row.get("expenses"),
                operating_profit=curr_row.get("operating_profit"),
                opm_percentage=curr_row.get("opm_percentage"),
                other_income=curr_row.get("other_income"),
                depreciation=curr_row.get("depreciation"),
                profit_before_tax=curr_row.get("profit_before_tax"),
                net_profit=curr_row.get("net_profit"),
                company_id=str(comp_id) if comp_id else None,
                broad_sector=broad_sector,
            )
            true_op = norm["true_operating_profit"]
            is_bank_template = norm["is_banking_template"]

            fcf_conv_res = compute_fcf_conversion(
                fcf=fcf_val,
                operating_profit=true_op,
                company_id=str(comp_id) if comp_id else None,
                is_banking_template=is_bank_template,
            )
            g_fcf_conv_rate.append(fcf_conv_res.value)
            g_fcf_conv_lbl.append(fcf_conv_res.label)

            # 5. Capital Allocation Classification
            alloc_res = classify_capital_allocation(
                cfo=cfo_raw,
                cfi=cfi_raw,
                cff=cff_raw,
                cfo_quality_label=q_res.label,
                cfo_quality_score=q_res.value,
            )
            g_cfo_sign.append(alloc_res.cfo_sign)
            g_cfi_sign.append(alloc_res.cfi_sign)
            g_cff_sign.append(alloc_res.cff_sign)
            g_pattern_label.append(alloc_res.pattern_label)

        g["fcf"] = g_fcf
        g["cfo_quality_score"] = g_cfo_q_score
        g["cfo_quality_label"] = g_cfo_q_label
        g["capex_intensity"] = g_capex_int
        g["capex_intensity_label"] = g_capex_lbl
        g["fcf_conversion_rate"] = g_fcf_conv_rate
        g["fcf_conversion_label"] = g_fcf_conv_lbl
        g["cfo_sign"] = g_cfo_sign
        g["cfi_sign"] = g_cfi_sign
        g["cff_sign"] = g_cff_sign
        g["pattern_label"] = g_pattern_label
        g["capital_allocation_pattern"] = g_pattern_label
        processed_dfs.append(g)

    result_df = pd.concat(processed_dfs, ignore_index=True)
    return result_df


def generate_capital_allocation_csv(
    output_path: Path | None = None,
    db_path: Path = DB_PATH,
) -> Path:
    """Generate capital_allocation.csv with columns: company_id, year, cfo_sign, cfi_sign, cff_sign, pattern_label."""
    if output_path is None:
        output_path = REPO_ROOT / "data" / "processed" / "capital_allocation.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df_raw = get_cashflow_data(db_path=db_path)
    df_kpi = calculate_cashflow_kpis(df_raw)

    export_df = df_kpi[
        [
            "company_id",
            "year",
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "pattern_label",
        ]
    ].copy()

    export_df.to_csv(output_path, index=False)
    logger.info(
        "Exported %d capital allocation records to %s", len(export_df), output_path
    )
    return output_path
