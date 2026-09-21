# Sprint 1 Retrospective — Data Foundation & Schema Engine
**Project:** N100 Financial Intelligence Platform  
**Sprint Window:** Days 01–07 (Target: Sep 17–22, 2026 | Completed: Sep 21, 2026 — 1 Day Ahead)  
**Status:** ✅ **SIGNED OFF & SPRINT 1 COMPLETE**

---

## 1. Executive Summary & Sprint Velocity
Sprint 1 delivered the foundational data architecture, automated extraction and normalization pipeline, 16-rule data quality (DQ) engine, relational SQLite database with strict foreign key constraints, and comprehensive audit and exploratory analytics infrastructure.

- **Target Velocity:** 7 sprint days.
- **Actual Execution:** Completed in 4 calendar days with 100% specification compliance.
- **Test Suite:** **103 / 103 passing unit tests** (72 ETL tests + 31 DQ rule tests).
- **Code Standards:** 100% clean under `black` and `ruff` with zero linting or formatting exceptions.
- **Database State:** 10 tables loaded with 0 foreign key violations (`PRAGMA foreign_key_check = 0`).

---

## 2. What Went Well

### 1. Robust Relational Schema Design
- Defined [`db/schema.sql`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/db/schema.sql) establishing clean DDL across all 10 platform tables (`companies`, `profitandloss`, `balancesheet`, `cashflow`, `analysis`, `documents`, `prosandcons`, `sectors`, `stock_prices`, `market_cap`).
- Activated `PRAGMA foreign_keys = ON;` with cascading updates and strict delete constraints.
- Built composite uniqueness constraints on `(company_id, year)` and `(company_id, date)` plus multi-column index coverage for high-speed joins in Sprint 2.

### 2. Comprehensive 16-Rule Data Quality Automation
- Implemented [`src/etl/validator.py`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/src/etl/validator.py) codifying all 16 specification DQ rules (DQ-01 to DQ-16).
- Partitioned rules into **CRITICAL** (pre-insert blockers: PK uniqueness, FK integrity, ticker format, fiscal year format) and **WARNING** (post-load financial anomaly diagnostics: balance sheet balance, OPM cross-checks, dividend payout bounds, URL validation).
- Automated reporting in [`reports/validation_failures.csv`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/reports/validation_failures.csv).

### 3. Production Ingestion & Audit Pipeline
- Engineered [`db/loader.py`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/db/loader.py) with automated fiscal period normalization, deduplication (`keep="last"`), and timing benchmarks.
- Generated [`reports/load_audit.csv`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/reports/load_audit.csv) tracking `rows_in`, `rows_out`, `rejected`, `timestamp`, and `runtime_s` across all 12 source files in 7.27 seconds.

---

## 3. Technical Challenges & Forensic Deep-Dives

### 1. Orphan Ticker Scope Analysis (`WIPRO`, `ZOMATO`, `VEDL`, etc.)
- **Observation:** 8 large-cap companies (`WIPRO`, `ZOMATO`, `VEDL`, `ULTRACEMCO`, `UNIONBANK`, `VBL`, `UNITDSPR`, `ZYDUSLIFE`) were present in raw statement dumps but absent from `companies.xlsx`.
- **Investigation:** Cross-checked against supplementary datasets: `sectors.xlsx` (0/8), `stock_prices.xlsx` (0/8), and `market_cap.xlsx` (0/8) confirmed these 8 tickers were completely omitted from supporting files.
- **Specification Confirmation:** Section 1 and Module 1 of the project document explicitly define the scope as *"Nifty 100 — 92 companies after data availability filter applied"*.
- **Conclusion:** `companies.xlsx` is the authoritative 92-company master universe. Rejecting the 8 orphan tickers via DQ-03 FK integrity is 100% intended and prevents un-indexed data pollution.

### 2. Typographical Error Recovery (`AGTL` $ightarrow$ `ATGL`)
- **Observation:** `cashflow.xlsx` contained 7 rows for `AGTL` (Mar 2018–Mar 2024), which was initially rejected as an orphan ticker.
- **Investigation:** `companies.xlsx`, `profitandloss.xlsx`, and `balancesheet.xlsx` all correctly identified the company as `ATGL` (**Adani Total Gas Ltd**).
- **Remediation:** Added `TICKER_ALIASES = {"AGTL": "ATGL"}` in [`src/etl/loader.py`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/src/etl/loader.py). Successfully recovered all 7 years of cashflow data into `db/nifty100.db`, increasing loaded cash flow records from 1,056 to 1,063 with zero orphan loss.

### 3. Balance Sheet Fiscal Year Month Distribution (`-03`, `-12`, `-06`, `-09`)
- **Observation:** In Day 7 Query 10, total balance sheet rows ($1,140$) broke down as $1,013$ March (`-03`), $94$ September interim (`-09`), leaving $33$ rows unaccounted for.
- **Investigation:** A comprehensive month-suffix distribution query revealed:
  - **December Fiscal Year-End (`-12`, 27 rows across 5 companies):** `NESTLEIND` (11 years: 2013–2023), `AMBUJACEM` (10 years: 2012–2021), `EICHERMOT` (3 years), `BOSCHLTD` (2 years), `ABB` (1 year).
  - **June Fiscal Year-End (`-06`, 6 rows across 2 companies):** `HCLTECH` (3 years: 2013–2015), `SHREECEM` (3 years: 2013–2015).
  - **September Interim (`-09`, 94 rows across 83 companies):** Mid-year H1 interim snapshot appended to non-financial companies.
- **Join Verification:** In all non-March cases, P&L, Balance Sheet, and Cash Flow share the exact same fiscal month. An exact join on `(company_id, year)` between `profitandloss` and `balancesheet` yields **1,058 matching annual pairs** across all 92 companies.

---

## 4. Known Limitations & Corrected Design Rules for Sprint 2+

### Rule 1: State Bank of India (`SBIN`) Balance Sheet Data Gap
- **Finding:** `SBIN` has 12 complete years of P&L (`2013-03` to `2024-03`) and 12 complete years of Cash Flow (`2013-03` to `2024-03`), but zero balance sheet rows in `balancesheet.xlsx` at source.
- **Downstream Impact:** All balance-sheet-dependent financial ratios (ROE, ROCE, Debt-to-Equity, Asset Turnover, Current Ratio) will evaluate to `NULL` for `SBIN` in Sprint 2. Pure P&L ratios (Sales Growth, PAT Margin, OPM) and Cash Flow ratios will remain fully functional.

### Rule 2: Short History Tickers (`JIOFIN`)
- **Finding:** `JIOFIN` (Jio Financial Services Ltd) only contains FY23 and FY24 annual records due to its recent demerger from RIL and listing in August 2023.
- **Downstream Impact:** Multi-year growth metrics (e.g., 3-year or 5-year CAGR) must output `NULL` / `INSUFFICIENT_DATA` per Section 14 edge case handling.

### Rule 3: Correct Annual Balance Sheet Join Rule (Do NOT Hardcode `%-03`)
- **Flawed Initial Rule:** Hardcoding `year LIKE '%-03'` would silently exclude 11 years of `NESTLEIND` (December FY) and 10 years of `AMBUJACEM` (December FY), producing false `NULL` ratios for 7 top companies.
- **Correct Sprint 2 Design Rule:** 
  1. For annual financial ratios, join `profitandloss` and `balancesheet` directly on **exact matching `(company_id, year)`**.
  2. Because `profitandloss` contains strictly annual rows (interim `TTM` rows were already rejected by ETL), the exact join naturally includes all legitimate annual fiscal years (March `-03`, December `-12`, and June `-06`) while seamlessly excluding the un-matched `2024-09` interim H1 balance sheet rows.
  3. The `2024-09` interim records are reserved strictly for point-in-time latest solvency/health snapshots.

### Rule 4: Permanent Exclusion of 8 Orphan Tickers
- The 8 orphan companies (`WIPRO`, `ZOMATO`, `VEDL`, `ULTRACEMCO`, `UNIONBANK`, `VBL`, `UNITDSPR`, `ZYDUSLIFE`) remain permanently excluded from the 92-company database by design.

---

## 5. Sprint 1 Exit Criteria Verification

| # | Exit Criteria Requirement | Target / Baseline | Actual Verification Output | Status |
|---|---|---|---|---|
| **1** | Master Company Count | `COUNT(*) == 92` | `SELECT COUNT(*) FROM companies;` $ightarrow$ **92** | ✅ **PASS** |
| **2** | Foreign Key Integrity | 0 violations | `PRAGMA foreign_key_check;` $ightarrow$ **0 rows** | ✅ **PASS** |
| **3** | Clean Rejection Accounting | Zero CRITICAL passed silently | [`reports/load_audit.csv`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/reports/load_audit.csv) accounts for all 1,276 P&L, 1,312 BS, 1,187 CF rows with zero unlogged drops | ✅ **PASS** |
| **4** | Unit Test Suite Coverage | $\ge 35$ ETL tests | `pytest tests/etl/` $ightarrow$ **72 passed** (Total: **103 passed**) | ✅ **PASS** |
| **5** | Live Database Manual Spot-Checks | 5 companies verified | `RELIANCE`, `TCS`, `HDFCBANK`, `TATAMOTORS`, `ITC` verified with 100% numerical fidelity | ✅ **PASS** |
| **6** | Sprint Review & Sign-Off | Formal sign-off | Completed Day 7 review and verified all deliverables | ✅ **PASS** |

---

## 6. Sprint 2 Transition Readiness
- **Module 2 Target:** Financial Ratio Engine (computing 50+ financial KPIs across 92 companies $	imes$ 14 years).
- **Core Input:** `db/nifty100.db` with 10 verified tables.
- **Ingestion Artifacts:** [`db/schema.sql`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/db/schema.sql), [`db/loader.py`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/db/loader.py), [`reports/load_audit.csv`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/reports/load_audit.csv), [`reports/validation_failures.csv`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/reports/validation_failures.csv), [`notebooks/exploratory_queries.sql`](file:///f:/Bluestock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/n100_financial_platform/notebooks/exploratory_queries.sql).
- **Sprint 1 Conclusion:** **100% Complete & Signed Off.**
