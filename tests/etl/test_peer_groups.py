"""Tests for peer_groups table schema, data ingestion, and relational integrity."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from db.loader import transform_peer_groups

DB_PATH = Path("db/nifty100.db")


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Fixture providing a read-only connection to the live SQLite database."""
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    yield conn
    conn.close()


def test_peer_groups_table_exists_and_row_count(db_conn: sqlite3.Connection) -> None:
    """Verify peer_groups table exists and contains exactly 56 mapped records."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM peer_groups;")
    count = cursor.fetchone()[0]
    assert count == 56


def test_peer_groups_unique_groups_count(db_conn: sqlite3.Connection) -> None:
    """Verify exactly 11 unique peer groups are present in the table."""
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name;"
    )
    groups = [r[0] for r in cursor.fetchall()]
    assert len(groups) == 11
    expected_groups = [
        "Automobiles",
        "Consumer Finance",
        "FMCG",
        "IT Services",
        "Life Insurance",
        "Oil & Gas",
        "Pharmaceuticals",
        "Power & Utilities",
        "Private Banks",
        "Public Sector Banks",
        "Steel",
    ]
    assert groups == expected_groups


def test_peer_groups_foreign_key_integrity(db_conn: sqlite3.Connection) -> None:
    """Verify all company_id entries in peer_groups map to existing companies without violations."""
    cursor = db_conn.cursor()
    violations = cursor.execute("PRAGMA foreign_key_check(peer_groups);").fetchall()
    assert len(violations) == 0


def test_peer_groups_benchmarks_assigned(db_conn: sqlite3.Connection) -> None:
    """Verify each of the 11 peer groups has designated benchmark companies."""
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT peer_group_name, COUNT(*) FROM peer_groups WHERE is_benchmark = 1 GROUP BY peer_group_name;"
    )
    benchmarks = cursor.fetchall()
    assert len(benchmarks) == 11
    for group, count in benchmarks:
        assert count >= 1, f"Group {group} lacks a designated benchmark leader"


def test_peer_groups_unique_constraint() -> None:
    """Verify that duplicate (peer_group_name, company_id) insertions are rejected."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("CREATE TABLE companies (id VARCHAR(20) PRIMARY KEY);")
    cursor.execute("INSERT INTO companies VALUES ('TCS');")
    cursor.execute("""
        CREATE TABLE peer_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            peer_group_name VARCHAR(100) NOT NULL,
            company_id VARCHAR(20) NOT NULL,
            is_benchmark BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            UNIQUE (peer_group_name, company_id)
        );
    """)
    cursor.execute(
        "INSERT INTO peer_groups (peer_group_name, company_id) VALUES ('IT Services', 'TCS');"
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO peer_groups (peer_group_name, company_id) VALUES ('IT Services', 'TCS');"
        )
    conn.close()


def test_transform_peer_groups_clean_and_filter() -> None:
    """Verify transform_peer_groups standardizes tickers, trims strings, and filters orphans."""
    raw_data = pd.DataFrame(
        {
            "peer_group_name": [" IT Services  ", "Private Banks", "Automobiles"],
            "company_id": ["  infy ", "HDFCBANK", "ORPHAN_TICKER"],
            "is_benchmark": [True, False, False],
        }
    )
    valid_tickers = {"INFY", "HDFCBANK"}
    cleaned = transform_peer_groups(raw_data, valid_tickers)

    assert len(cleaned) == 2
    assert set(cleaned["company_id"]) == {"INFY", "HDFCBANK"}
    assert (
        cleaned.loc[cleaned["company_id"] == "INFY", "peer_group_name"].iloc[0]
        == "IT Services"
    )


def test_peer_groups_exact_group_distributions(db_conn: sqlite3.Connection) -> None:
    """Verify the exact member counts per group match the specification dataset."""
    expected_counts = {
        "Automobiles": 7,
        "Consumer Finance": 3,
        "FMCG": 7,
        "IT Services": 5,
        "Life Insurance": 4,
        "Oil & Gas": 5,
        "Pharmaceuticals": 5,
        "Power & Utilities": 7,
        "Private Banks": 5,
        "Public Sector Banks": 4,
        "Steel": 4,
    }
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT peer_group_name, COUNT(*) FROM peer_groups GROUP BY peer_group_name;"
    )
    actual_counts = dict(cursor.fetchall())
    assert actual_counts == expected_counts
