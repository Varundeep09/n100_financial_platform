"""Unit tests for Sprint 5 Company Tearsheet PDF Generator (Module 10 / D-16).

Verifies that all 92 company tearsheets exist in reports/tearsheets/,
are non-empty (> 20KB), and contain exactly 2 pages each.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "db" / "nifty100.db"
TEARSHEETS_DIR = REPO_ROOT / "reports" / "tearsheets"


def test_all_ninety_two_tearsheet_pdfs_exist() -> None:
    """Verify that exactly 92 PDF tearsheets exist matching universe company IDs."""
    assert TEARSHEETS_DIR.exists(), f"Missing tearsheets directory at: {TEARSHEETS_DIR}"

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM companies ORDER BY id;")
    company_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert len(company_ids) == 92, f"Expected 92 companies in DB, found {len(company_ids)}"

    missing_tearsheets = []
    for cid in company_ids:
        pdf_path = TEARSHEETS_DIR / f"{cid}_tearsheet.pdf"
        if not pdf_path.exists():
            missing_tearsheets.append(cid)

    assert not missing_tearsheets, f"Missing tearsheet PDFs for companies: {missing_tearsheets}"

    all_pdfs = list(TEARSHEETS_DIR.glob("*_tearsheet.pdf"))
    assert len(all_pdfs) == 92, f"Expected exactly 92 PDF tearsheets, found {len(all_pdfs)}"


def test_tearsheet_pdfs_non_empty_and_valid() -> None:
    """Verify each tearsheet PDF is non-empty (> 20KB) and has exactly 2 pages."""
    pdf_files = list(TEARSHEETS_DIR.glob("*_tearsheet.pdf"))
    assert len(pdf_files) == 92, "Missing tearsheets for validation"

    undersized_files = []
    invalid_header_files = []
    page_count_violations = []

    for pdf_path in pdf_files:
        data = pdf_path.read_bytes()
        file_size = len(data)

        # Size check (> 20KB = 20,000 bytes)
        if file_size <= 20000:
            undersized_files.append((pdf_path.name, file_size))

        # PDF header check
        if not data.startswith(b"%PDF-"):
            invalid_header_files.append(pdf_path.name)

        # 2-Page layout check
        page_tags = re.findall(rb"/Type\s*/Page(?!\w)", data)
        if len(page_tags) != 2:
            page_count_violations.append((pdf_path.name, len(page_tags)))

    assert not undersized_files, f"Tearsheets under 20KB: {undersized_files}"
    assert not invalid_header_files, f"Invalid PDF headers in: {invalid_header_files}"
    assert not page_count_violations, f"Tearsheets with != 2 pages: {page_count_violations}"
