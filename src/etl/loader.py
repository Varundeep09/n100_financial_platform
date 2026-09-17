"""
N100 Financial Intelligence Platform — Excel Loader (Sprint 1, Module 1)

STUB for Day 1 (environment setup / smoke test only). Real ingestion
logic — normalize_year(), normalize_ticker(), header=1 parsing for the
7 core files, header=0 for the 5 supplementary files — gets written on
Day 2 per the confirmed real file structure (see docs/ for the verified
schema notes).

Confirmed against the real uploaded files (not just the spec doc):
  Core files (data/raw/, read with header=1 — row 0 is a title/metadata
  row, row 1 is the real header):
    companies.xlsx        92 rows
    profitandloss.xlsx    1,276 rows
    balancesheet.xlsx     1,312 rows
    cashflow.xlsx         1,187 rows
    analysis.xlsx         20 rows   (partial coverage — ~8 companies)
    documents.xlsx        1,585 rows
    prosandcons.xlsx      16 rows   (partial coverage — ~8 companies)

  Supplementary files (data/supporting/, read with header=0 — no title row):
    sectors.xlsx           92 rows
    stock_prices.xlsx      5,520 rows
    market_cap.xlsx        552 rows
    financial_ratios.xlsx  1,184 rows  (pre-computed — cross-check only,
                                        do not treat as ground truth)
    peer_groups.xlsx       56 rows

Note: year strings are NOT uniform even within one file — cashflow.xlsx
sample shows both 'Mar-13' and profitandloss shows 'Dec 2012' style
labels (different companies have different fiscal year-end months).
normalize_year() must handle both patterns robustly.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SUPPORTING_DIR = PROJECT_ROOT / "data" / "supporting"
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

CORE_FILES = [
    "companies.xlsx", "profitandloss.xlsx", "balancesheet.xlsx",
    "cashflow.xlsx", "analysis.xlsx", "documents.xlsx", "prosandcons.xlsx",
]
SUPPORTING_FILES = [
    "sectors.xlsx", "stock_prices.xlsx", "market_cap.xlsx",
    "financial_ratios.xlsx", "peer_groups.xlsx",
]


def normalize_year(value):
    """TODO (Day 2): normalize 'Mar-23', 'Dec 2012', 2019 (int), etc. to 'YYYY-MM' string."""
    raise NotImplementedError


def normalize_ticker(value):
    """TODO (Day 2): value.strip().upper(), validate length 2-12 chars (DQ-08)."""
    raise NotImplementedError


def main():
    print(f"Core files expected in:       {RAW_DIR}")
    print(f"Supporting files expected in: {SUPPORTING_DIR}")
    for label, folder, files in [("core", RAW_DIR, CORE_FILES), ("supporting", SUPPORTING_DIR, SUPPORTING_FILES)]:
        print(f"\n{label.upper()}:")
        for f in files:
            exists = (folder / f).exists()
            print(f"  [{'OK' if exists else 'MISSING'}] {f}")


if __name__ == "__main__":
    main()
