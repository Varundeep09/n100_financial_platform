"""Unit tests for Sprint 5 Sector Reports & Portfolio Summary PDF (Module 10 / D-17 & D-18).

Verifies that exactly 11 sector report PDFs exist in reports/sector_reports/
and that reports/portfolio_summary.pdf exists and is > 50KB.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SECTOR_REPORTS_DIR = REPO_ROOT / "reports" / "sector_reports"
PORTFOLIO_SUMMARY_PDF = REPO_ROOT / "reports" / "portfolio_summary.pdf"

EXPECTED_SECTORS = [
    "Communication_Services",
    "Consumer_Discretionary",
    "Consumer_Staples",
    "Energy",
    "Financials",
    "Healthcare",
    "Industrials",
    "Information_Technology",
    "Materials",
    "Real_Estate",
    "Utilities",
]


def test_eleven_sector_report_pdfs_exist() -> None:
    """Verify that exactly 11 sector report PDFs exist in reports/sector_reports/."""
    assert (
        SECTOR_REPORTS_DIR.exists()
    ), f"Sector reports directory not found at: {SECTOR_REPORTS_DIR}"

    all_pdfs = sorted(SECTOR_REPORTS_DIR.glob("*_report.pdf"))
    assert (
        len(all_pdfs) == 11
    ), f"Expected exactly 11 sector report PDFs, found {len(all_pdfs)}: {[f.name for f in all_pdfs]}"

    for sector in EXPECTED_SECTORS:
        pdf_path = SECTOR_REPORTS_DIR / f"{sector}_report.pdf"
        assert pdf_path.exists(), f"Missing sector report for {sector}: {pdf_path}"

        data = pdf_path.read_bytes()
        assert data.startswith(b"%PDF-"), f"Invalid PDF header in {pdf_path.name}"
        assert (
            len(data) > 5000
        ), f"Sector report {pdf_path.name} is unusually small ({len(data)} bytes)"

        # Verify page count is 3 pages
        page_tags = re.findall(rb"/Type\s*/Page(?!\w)", data)
        assert (
            len(page_tags) == 3
        ), f"Sector report {pdf_path.name} expected 3 pages, found {len(page_tags)}"


def test_portfolio_summary_pdf_exists_and_size() -> None:
    """Verify that reports/portfolio_summary.pdf exists and is > 50KB."""
    assert (
        PORTFOLIO_SUMMARY_PDF.exists()
    ), f"Missing portfolio summary PDF at: {PORTFOLIO_SUMMARY_PDF}"

    file_size = PORTFOLIO_SUMMARY_PDF.stat().st_size
    assert (
        file_size > 50 * 1024
    ), f"portfolio_summary.pdf size is {file_size:,} bytes, expected > 50KB (51,200 bytes)"

    data = PORTFOLIO_SUMMARY_PDF.read_bytes()
    assert data.startswith(b"%PDF-"), "portfolio_summary.pdf has an invalid PDF header"

    page_tags = re.findall(rb"/Type\s*/Page(?!\w)", data)
    assert (
        len(page_tags) >= 3
    ), f"portfolio_summary.pdf expected >= 3 pages, found {len(page_tags)}"
