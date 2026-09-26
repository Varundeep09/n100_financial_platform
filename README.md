# N100 Financial Intelligence Platform

Bluestock Fintech production platform for equity research and institutional intelligence across 92 Nifty 100 companies. Features a validated financial data warehouse, a 50-metric KPI and valuation ratio engine, an investment screener with peer benchmarking, a Streamlit analytics dashboard, an automated tearsheet reporting layer, and a FastAPI service layer.

Full specifications and project architecture: see `docs/Nifty100_Project_Document_FINAL.pdf` and `docs/ratio_edge_cases.log`.

---

## Project Status

- **Sprint 1 — Data Foundation & Validation (Days 1–7):** **COMPLETE** (Tagged `sprint1-complete`)
  - 10 relational tables in SQLite (`db/nifty100.db`) loaded from 12 source files with 0 foreign-key violations.
  - 16 automated Data Quality rules (DQ-01 to DQ-16) passing with 0 critical failures.
- **Sprint 2 — Financial Ratio Engine & Edge Cases (Days 8–14):** **COMPLETE** (Tagged `sprint2-complete`)
  - 50-column `financial_ratios` table populated with 1,155 rows across all 92 companies and reporting periods.
  - Evidence-based normalization for 16 banking templates, 23 Financials sector leverage carve-outs, exact calendar year-target CAGR matching, CFO quality NBFC carve-out, and active neutralization of corrupted balance-sheet data (BEL, HAL).
  - AC-07 screener acceptance test passing (34 quality preset companies).
- **Buffer Period — Audit & Quality Pass (Sep 26–29):** **COMPLETE**
- **Sprint 3 — Investment Screener Engine (Days 15–21):** Starts Sep 30, 2026.

---

## Directory Structure

```
data/raw/          7 core Excel source files (companies, P&L, BS, CF, analysis, documents, prosandcons)
data/supporting/   5 supplementary source files (sectors, stock_prices, market_cap, financial_ratios, peer_groups)
data/processed/    Derived classification artifacts (e.g. capital_allocation.csv)
db/                schema.sql, loader.py, and nifty100.db (SQLite database)
src/etl/           loader.py, validator.py (Sprint 1 data foundation)
src/analytics/     ratios.py, cagr.py, cashflow_kpis.py, populate_financial_ratios.py (Sprint 2 ratio engine)
src/dashboard/     Streamlit interactive visual platform (Sprint 4)
src/api/           FastAPI REST API service layer (Sprint 6)
tests/dq/          16 Data Quality rule unit tests (31 tests)
tests/etl/         Schema, normalization, and smoke tests (72 tests)
tests/kpi/         Profitability, leverage, CAGR, cash flow, and ratio table tests (65 tests)
tests/api/         API endpoint tests (Sprint 6)
reports/           load_audit.csv, validation_failures.csv, sprint1_retro.md, sprint2_retro.md
docs/              Project specifications, ratio_edge_cases.log, buffer_period_notes.md
```

---

## Setup & Full Pipeline Execution

### 1. Environment Setup
```bash
# Create virtual environment and activate
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# or .venv\Scripts\Activate.ps1   # Windows PowerShell

# Install dependencies
make install
# or: pip install -r requirements.txt
```

### 2. Run the Full End-to-End Pipeline
Execute the full data pipeline from raw Excel files to populated ratio database and regression verification:

```bash
# Step 1: Load and validate core and supporting datasets into SQLite
make load
# or: python db/loader.py

# Step 2: Run the full ratio calculation engine across all 92 companies
make ratios
# or: python src/analytics/populate_financial_ratios.py

# Step 3: Run the complete automated test suite (168 tests)
make test
# or: pytest tests/ -v --tb=short
```

---

## Verification & Quality Standards

- **Code Formatting:** Formatted with `black src/ tests/` (100% compliant).
- **Linting:** Enforced via `ruff check src/ tests/` (0 errors).
- **Type Annotations & Docstrings:** 100% of public functions across `src/analytics/` and `src/etl/` have complete type hints and descriptive docstrings.
- **Audit Logs:** Full decision logs and forensic edge cases documented in `docs/ratio_edge_cases.log` and `reports/sprint2_retro.md`.
