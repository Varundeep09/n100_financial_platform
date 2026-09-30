"""Multi-criteria Fundamental Screener and Filter Engine for Nifty 100 universe.

Module 3: Company Screener & Filter Engine
Sprint 3, Day 15: Custom Filter Engine
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("screener_config.yaml")
DEFAULT_DB_PATH = Path("db/nifty100.db")


def load_screener_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and parse screener configuration from YAML file.

    Args:
        config_path: Optional path to screener_config.yaml.

    Returns:
        Dictionary containing thresholds and preset configurations.

    Raises:
        FileNotFoundError: If the specified configuration file does not exist.
    """
    if config_path is None:
        if DEFAULT_CONFIG_PATH.exists():
            resolved_path = DEFAULT_CONFIG_PATH
        else:
            resolved_path = Path(__file__).resolve().parents[2] / "screener_config.yaml"
    else:
        resolved_path = Path(config_path)

    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Screener configuration file not found at: {resolved_path}"
        )

    with open(resolved_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.debug("Loaded screener configuration from %s", resolved_path)
    return config or {}


def load_screener_universe(db_path: Path | str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Load latest annual snapshot per company, joined with sectors and market_cap.

    Filters for latest fiscal year ending in March (MAX(year) LIKE '%-03').

    Args:
        db_path: Path to nifty100.db SQLite database.

    Returns:
        DataFrame containing 91 companies with ratios, sector, and valuation metrics.
    """
    resolved_db = Path(db_path)
    if not resolved_db.exists():
        raise FileNotFoundError(f"Database not found at: {resolved_db}")

    query = """
    WITH latest_fr AS (
        SELECT company_id, MAX(year) AS max_year
        FROM financial_ratios
        WHERE year LIKE '%-03'
        GROUP BY company_id
    ),
    latest_mc AS (
        SELECT company_id, MAX(year) AS max_year
        FROM market_cap
        WHERE year LIKE '%-03'
        GROUP BY company_id
    )
    SELECT 
        fr.*,
        c.company_name,
        s.broad_sector,
        s.sub_sector,
        s.index_weight_pct,
        mc.pe_ratio,
        mc.pb_ratio,
        mc.market_cap_crore,
        mc.dividend_yield_pct
    FROM financial_ratios fr
    JOIN latest_fr lfr 
      ON fr.company_id = lfr.company_id AND fr.year = lfr.max_year
    LEFT JOIN companies c 
      ON fr.company_id = c.id
    LEFT JOIN sectors s 
      ON fr.company_id = s.company_id
    LEFT JOIN market_cap mc 
      ON fr.company_id = mc.company_id AND fr.year = mc.year
    ORDER BY fr.company_id ASC;
    """

    conn = sqlite3.connect(f"file:{resolved_db.as_posix()}?mode=ro", uri=True)
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    logger.debug("Loaded screener universe with %d companies", len(df))
    return df


def apply_single_filter(
    df: pd.DataFrame, metric: str, rule: dict[str, Any] | float
) -> pd.Series:
    """Evaluate a single metric threshold condition against the universe.

    Strict null handling: any row with None/NaN for the filtered metric evaluates to False.

    Args:
        df: Screener universe DataFrame.
        metric: Column name to filter on.
        rule: Threshold condition dict (e.g. {'min': 15.0}, {'max': 1.0}, {'eq': 0.0}) or scalar.

    Returns:
        Boolean Series of rows passing the condition.
    """
    if metric not in df.columns:
        logger.warning(
            "Metric '%s' not found in universe columns. Excluding all.", metric
        )
        return pd.Series(False, index=df.index)

    series = pd.to_numeric(df[metric], errors="coerce")
    valid_mask = series.notna()

    if isinstance(rule, (int, float)):
        return valid_mask & (series >= rule)

    if not isinstance(rule, dict):
        return pd.Series(False, index=df.index)

    mask = valid_mask.copy()

    if "min" in rule:
        mask = mask & (series > rule["min"])
    if "min_inc" in rule or "gte" in rule:
        val = rule.get("min_inc", rule.get("gte"))
        mask = mask & (series >= val)
    if "max" in rule:
        mask = mask & (series < rule["max"])
    if "max_inc" in rule or "lte" in rule:
        val = rule.get("max_inc", rule.get("lte"))
        mask = mask & (series <= val)
    if "eq" in rule:
        mask = mask & (series == rule["eq"])

    return mask


def apply_trend_filter(
    df: pd.DataFrame, trend_type: str = "accelerating_revenue"
) -> pd.Series:
    """Evaluate multi-year trend direction beyond single-row thresholds.

    Supports:
        'accelerating_revenue': verifies 3-year Revenue CAGR > 5-year Revenue CAGR.
        Both metrics must be non-null and numeric.

    Args:
        df: Screener universe DataFrame.
        trend_type: Trend identifier.

    Returns:
        Boolean Series of passing companies.
    """
    if trend_type == "accelerating_revenue":
        r3 = pd.to_numeric(df.get("revenue_cagr_3yr"), errors="coerce")
        r5 = pd.to_numeric(df.get("revenue_cagr_5yr"), errors="coerce")
        return r3.notna() & r5.notna() & (r3 > r5)

    logger.warning("Unknown trend filter type: %s", trend_type)
    return pd.Series(True, index=df.index)


def filter_universe(
    df: pd.DataFrame,
    filters: dict[str, Any] | None = None,
    logic: str = "AND",
    accelerating_revenue: bool = False,
) -> pd.DataFrame:
    """Apply arbitrary fundamental criteria and trend direction filters to universe.

    Args:
        df: Screener universe DataFrame.
        filters: Mapping of metric names to threshold rule dicts.
        logic: Combination boolean logic ('AND' or 'OR'). Defaults to 'AND'.
        accelerating_revenue: If True, requires Revenue CAGR 3yr > Revenue CAGR 5yr.

    Returns:
        Filtered DataFrame of passing companies with all original ratio columns.
    """
    if df.empty:
        return df.copy()

    masks: list[pd.Series] = []

    if filters:
        for metric, rule in filters.items():
            masks.append(apply_single_filter(df, metric, rule))

    if accelerating_revenue:
        masks.append(apply_trend_filter(df, "accelerating_revenue"))

    if not masks:
        return df.copy()

    norm_logic = logic.strip().upper()
    if norm_logic == "AND":
        combined_mask = np.logical_and.reduce(masks)
    elif norm_logic == "OR":
        combined_mask = np.logical_or.reduce(masks)
    else:
        raise ValueError(f"Unsupported boolean logic '{logic}'. Must be 'AND' or 'OR'.")

    return df[combined_mask].copy()


def run_preset(
    preset_key: str,
    df: pd.DataFrame | None = None,
    config: dict[str, Any] | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Execute one of the 6 production screening presets by name.

    Args:
        preset_key: Identifier (e.g. 'quality_compounder', 'value_pick', etc.).
        df: Optional pre-loaded universe DataFrame.
        config: Optional pre-loaded configuration dict.
        db_path: Path to database if universe needs loading.

    Returns:
        DataFrame of companies passing the preset screener.
    """
    if config is None:
        config = load_screener_config()

    presets = config.get("presets", {})
    if preset_key not in presets:
        raise KeyError(
            f"Preset '{preset_key}' not found in configuration. Available: {list(presets.keys())}"
        )

    preset_def = presets[preset_key]
    preset_filters = preset_def.get("filters", {})
    logic = preset_def.get("logic", "AND")
    accelerating = preset_def.get("accelerating_revenue", False)

    if df is None:
        df = load_screener_universe(db_path=db_path)

    return filter_universe(
        df,
        filters=preset_filters,
        logic=logic,
        accelerating_revenue=accelerating,
    )


def run_all_presets(
    df: pd.DataFrame | None = None,
    config: dict[str, Any] | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, pd.DataFrame]:
    """Execute all 6 production presets and return a dictionary of result DataFrames.

    Args:
        df: Optional pre-loaded universe DataFrame.
        config: Optional pre-loaded configuration dict.
        db_path: Path to database if universe needs loading.

    Returns:
        Dict mapping preset_key to passing DataFrame.
    """
    if config is None:
        config = load_screener_config()

    if df is None:
        df = load_screener_universe(db_path=db_path)

    results: dict[str, pd.DataFrame] = {}
    presets = config.get("presets", {})
    for key in presets:
        results[key] = run_preset(key, df=df, config=config, db_path=db_path)

    return results
