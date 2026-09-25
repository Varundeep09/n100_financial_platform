"""Tests for SQLite database schema, foreign key constraints, and loader pipeline."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from db.loader import (
    load_all_tables,
    transform_companies,
    transform_profitandloss,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "db" / "schema.sql"


@pytest.fixture
def memory_db() -> sqlite3.Connection:
    """Provide an in-memory SQLite database instance with loaded schema."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    return conn


def test_schema_creates_all_10_tables(memory_db: sqlite3.Connection) -> None:
    """Verify that schema.sql creates exactly the 10 expected business tables."""
    cursor = memory_db.cursor()
    tables = [
        r[0]
        for r in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
    ]
    expected_tables = {
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "stock_prices",
        "market_cap",
        "financial_ratios",
    }
    assert set(tables) == expected_tables


def test_foreign_key_enforcement_blocks_orphan(memory_db: sqlite3.Connection) -> None:
    """Verify that foreign key constraints reject child rows with non-existent company_id."""
    cursor = memory_db.cursor()
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO profitandloss (company_id, year, sales) VALUES ('ORPHAN_CO', '2023-24', 1000.0);"
        )


def test_foreign_key_allows_valid_company(memory_db: sqlite3.Connection) -> None:
    """Verify that valid company_id allows inserting child records."""
    cursor = memory_db.cursor()
    cursor.execute(
        "INSERT INTO companies (id, company_name) VALUES ('TCS', 'Tata Consultancy Services Ltd');"
    )
    cursor.execute(
        "INSERT INTO profitandloss (company_id, year, sales) VALUES ('TCS', '2023-24', 240893.0);"
    )
    memory_db.commit()
    row = cursor.execute(
        "SELECT company_id, year, sales FROM profitandloss WHERE company_id = 'TCS';"
    ).fetchone()
    assert row == ("TCS", "2023-24", 240893.0)


def test_unique_constraint_on_company_year(memory_db: sqlite3.Connection) -> None:
    """Verify unique constraint prevents duplicate annual records for the same company."""
    cursor = memory_db.cursor()
    cursor.execute(
        "INSERT INTO companies (id, company_name) VALUES ('INFY', 'Infosys Ltd');"
    )
    cursor.execute(
        "INSERT INTO profitandloss (company_id, year, sales) VALUES ('INFY', '2023-24', 153670.0);"
    )
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO profitandloss (company_id, year, sales) VALUES ('INFY', '2023-24', 160000.0);"
        )


def test_transform_companies_dedup_and_clean() -> None:
    """Verify transform_companies normalises tickers and deduplicates."""
    raw = pd.DataFrame(
        {
            "id": [" infy ", "INFY", "TCS"],
            "company_name": [
                "Infosys\nLtd",
                "Infosys Limited",
                "Tata Consultancy Services",
            ],
        }
    )
    cleaned = transform_companies(raw)
    assert len(cleaned) == 2
    assert set(cleaned["id"]) == {"INFY", "TCS"}
    assert (
        cleaned.loc[cleaned["id"] == "INFY", "company_name"].iloc[0]
        == "Infosys Limited"
    )


def test_transform_profitandloss_rejects_orphans_and_ttm() -> None:
    """Verify transform_profitandloss filters orphans and invalid years."""
    raw = pd.DataFrame(
        {
            "company_id": ["TCS", "ORPHAN", "TCS"],
            "year": ["Mar 2023", "Mar 2023", "TTM"],
            "sales": [100.0, 200.0, 300.0],
        }
    )
    valid_tickers = {"TCS"}
    cleaned = transform_profitandloss(raw, valid_tickers)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["company_id"] == "TCS"
    assert cleaned.iloc[0]["year"] == "2023-03"


def test_database_loader_full_integration(tmp_path: Path) -> None:
    """Verify full database load runs without foreign key violations."""
    db_file = tmp_path / "test_nifty100.db"
    counts = load_all_tables(db_path=db_file, schema_path=SCHEMA_PATH)
    assert counts["companies"] == 92
    assert counts["profitandloss"] > 1000
    assert counts["balancesheet"] > 1000
    assert counts["cashflow"] > 1000
    assert counts["sectors"] == 92
    assert counts["stock_prices"] == 5520
    assert counts["market_cap"] == 552

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    fk_violations = cursor.execute("PRAGMA foreign_key_check;").fetchall()
    conn.close()
    assert len(fk_violations) == 0


def test_raw_row_count_reconciliation() -> None:
    """Verify that raw file row counts match Day 1 profiling and reconcile perfectly."""
    from src.etl.loader import load_core_file, load_supporting_file

    expected_raw = {
        "companies.xlsx": 92,
        "profitandloss.xlsx": 1276,
        "balancesheet.xlsx": 1312,
        "cashflow.xlsx": 1187,
        "analysis.xlsx": 20,
        "documents.xlsx": 1585,
        "prosandcons.xlsx": 16,
        "sectors.xlsx": 92,
        "stock_prices.xlsx": 5520,
        "market_cap.xlsx": 552,
        "financial_ratios.xlsx": 1184,
        "peer_groups.xlsx": 56,
    }

    core_set = {
        "companies.xlsx",
        "profitandloss.xlsx",
        "balancesheet.xlsx",
        "cashflow.xlsx",
        "analysis.xlsx",
        "documents.xlsx",
        "prosandcons.xlsx",
    }

    for filename, count in expected_raw.items():
        if filename in core_set:
            df = load_core_file(filename)
        else:
            df = load_supporting_file(filename)
        assert df is not None, f"File {filename} could not be loaded"
        assert len(df) == count, f"{filename}: expected {count} raw rows, got {len(df)}"


def test_load_audit_file_generation(tmp_path: Path) -> None:
    """Verify that load_all_tables generates a valid load_audit.csv with all 12 files."""
    db_file = tmp_path / "test_audit_db.db"
    audit_file = tmp_path / "load_audit.csv"

    load_all_tables(db_path=db_file, schema_path=SCHEMA_PATH, audit_path=audit_file)

    assert audit_file.exists()
    audit_df = pd.read_csv(audit_file)
    expected_cols = [
        "table",
        "rows_in",
        "rows_out",
        "rejected",
        "timestamp",
        "runtime_s",
    ]
    assert list(audit_df.columns) == expected_cols
    assert len(audit_df) == 12

    companies_row = audit_df[audit_df["table"] == "companies"].iloc[0]
    assert companies_row["rows_in"] == 92
    assert companies_row["rows_out"] == 92
    assert companies_row["rejected"] == 0

    pl_row = audit_df[audit_df["table"] == "profitandloss"].iloc[0]
    assert pl_row["rows_in"] == 1276
    assert pl_row["rows_out"] == 1073
    assert pl_row["rejected"] == 203

    cf_row = audit_df[audit_df["table"] == "cashflow"].iloc[0]
    assert cf_row["rows_in"] == 1187
    assert cf_row["rows_out"] == 1063
    assert cf_row["rejected"] == 124


def test_atgl_cashflow_recovery(tmp_path: Path) -> None:
    """Verify raw typo 'AGTL' in cashflow.xlsx is recovered to valid ticker 'ATGL' with 7 rows."""
    db_file = tmp_path / "test_atgl_db.db"
    counts = load_all_tables(db_path=db_file, schema_path=SCHEMA_PATH)
    assert counts["cashflow"] == 1063

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    atgl_cf = cursor.execute(
        "SELECT COUNT(*) FROM cashflow WHERE company_id='ATGL';"
    ).fetchone()[0]
    agtl_cf = cursor.execute(
        "SELECT COUNT(*) FROM cashflow WHERE company_id='AGTL';"
    ).fetchone()[0]
    conn.close()

    assert atgl_cf == 7
    assert agtl_cf == 0
