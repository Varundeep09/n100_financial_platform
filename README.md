# N100 Financial Intelligence Platform

Bluestock Fintech internship project. Builds a validated financial data
warehouse for 92 Nifty 100 companies, a 50+ KPI ratio engine, an
investment screener with peer comparison, a Streamlit dashboard, an
NLP-driven PDF reporting layer, and a FastAPI server — across 6 sprints
/ 45 calendar days.

Full spec: see the project brief (Nifty100_Project_Document_FINAL.pdf) —
keep a copy in `docs/`.

## Project status
Scaffold only. Sprint 1 (Data Foundation, Days 1–7) starts here.

## Folder structure
```
data/raw/          7 core Excel files (companies, P&L, BS, CF, analysis,
                    documents, prosandcons) — never edited, header row = 1
data/supporting/   5 supplementary files (sectors, stock_prices, market_cap,
                    financial_ratios, peer_groups) — never edited, header row = 0
db/                schema.sql, nifty100.db (SQLite, git-ignored)
src/etl/           loader.py, validator.py, normaliser.py     (Sprint 1)
src/analytics/     ratios.py, cagr.py, cashflow_kpis.py       (Sprint 2)
src/dashboard/     app.py — Streamlit, 8 screens               (Sprint 4)
src/api/           FastAPI server, 16 endpoints                (Sprint 6)
tests/etl/         ETL unit tests (35+ required, Sprint 1)
tests/kpi/         KPI formula tests (Sprint 2)
tests/dq/          Data-quality rule tests
tests/api/         API endpoint tests (Sprint 6)
reports/           load_audit.csv, validation_failures.csv, pytest_report.html,
                    tearsheets/ (92 company PDFs, Sprint 5), sector reports
notebooks/         exploratory_queries.sql and analysis notebooks (not production path)
docs/              Project brief / spec documents
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
make install
cp .env.template .env
```

## Sprint 1 — Data Foundation (Days 1–7)
Goal: `db/nifty100.db` with all 10 tables loaded from 12 source files,
all 16 data-quality rules (DQ-01–DQ-16) applied with zero CRITICAL
failures, `load_audit.csv` and `validation_failures.csv` produced.

Confirmed against the real uploaded source files (not just the spec):
all 12 row counts match exactly (companies=92, profitandloss=1276,
balancesheet=1312, cashflow=1187, analysis=20, documents=1585,
prosandcons=16, sectors=92, stock_prices=5520, market_cap=552,
financial_ratios=1184, peer_groups=56). Core files use `header=1`
(row 0 is a title/metadata row); supplementary files use `header=0`.

Run `make load` once the loader is implemented, `make test` to run the
unit test suite.
