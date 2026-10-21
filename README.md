# N100 Financial Intelligence Platform

## N100 Financial Intelligence Platform
The N100 Financial Intelligence Platform is an institutional-grade equity research and financial analytics suite engineered for 92 key constituents of the NSE Nifty 100 index. Built over a disciplined 6-sprint engineering lifecycle, the platform integrates an audited relational data warehouse, a 50-metric fundamental and forensic accounting engine, a 6-preset multi-factor screener, dynamic peer ranking and 8-archetype capital allocation analyzers, an interactive 8-screen Streamlit analytical workstation, automated ReportLab PDF publication pipelines, unsupervised machine learning clustering, and a high-performance 16-endpoint FastAPI REST microservice.

---

## Quick Start (3 commands)
```bash
git clone https://github.com/Varundeep09/n100_financial_platform.git
make install
make load
```

---

## Platform Architecture
The platform is organized into a clean 7-layer decoupled enterprise architecture (L1–L7):

```
+-------------------------------------------------------------------------------+
|                      L7: INTEGRATION & REST API LAYER                         |
|   FastAPI Microservice (16 Endpoints, Pydantic V2 Models, OpenAPI 3.0 Specs)   |
+-------------------------------------------------------------------------------+
                                       |
+-------------------------------------------------------------------------------+
|                    L6: PRESENTATION & REPORTING LAYER                         |
|   Streamlit 8-Screen Workstation  |  ReportLab Automated Publication Engine   |
|   (Interactive Visual Dashboard)  |  (92 Tearsheets, 11 Sector PDFs, Guides)  |
+-------------------------------------------------------------------------------+
                                       |
+-------------------------------------------------------------------------------+
|               L5: SCREENING, PEER RANKING & CLUSTERING LAYER                  |
|   6-Preset Fundamental Screener   |  Intra-Peer Percentiles (20 KPIs)         |
|   Winsorized Composite Ranker     |  Unsupervised K-Means Archetype Clusters  |
+-------------------------------------------------------------------------------+
                                       |
+-------------------------------------------------------------------------------+
|                  L4: FINANCIAL ANALYTICS & KPI ENGINE                         |
|   50+ Financial Ratios (DuPont, Solvency, Margins, Working Capital, Valuations)|
|   Compound Annual Growth Rates    |  8-Pattern Capital Allocation Archetypes  |
|   DCF Intrinsic Valuation Engine  |  NLP Pros & Cons Fact Extraction Engine   |
+-------------------------------------------------------------------------------+
                                       |
+-------------------------------------------------------------------------------+
|                L3: RELATIONAL STORAGE & WAREHOUSE LAYER                       |
|   SQLite Data Warehouse (db/nifty100.db with 10 Relational Tables, FK Checks) |
|   Indexed Views, Foreign Key Integrity, Read-Optimized In-Memory Caching      |
+-------------------------------------------------------------------------------+
                                       |
+-------------------------------------------------------------------------------+
|               L2: DATA QUALITY & NORMALISATION GATEWAY                        |
|   16 Non-Negotiable Quality Gates (DQ-01 to DQ-16), Outlier Boundary Guards   |
|   Bilingual Fiscal Normalisation (FY-2024 / March-23 -> YYYY-03 ISO Standards)|
+-------------------------------------------------------------------------------+
                                       |
+-------------------------------------------------------------------------------+
|                      L1: RAW DATA & INGESTION LAYER                           |
|   12 Ingested Workbooks & Extracts (data/raw/*.xlsx, data/supporting/*.xlsx)  |
|   Companies, Income Statements, Balance Sheets, Cash Flows, Market Caps, Docs |
+-------------------------------------------------------------------------------+
```

---

## What's Built (23 Deliverables)

All 23 specification deliverables across Sprints 1 through 6 are fully implemented, verified, and audited:

| Deliverable | Sprint | Location | Status |
| :--- | :--- | :--- | :--- |
| **D-01: SQLite Relational Database** | Sprint 1 | `db/nifty100.db` | COMPLETE |
| **D-02: ETL Audit Report** | Sprint 1 | `data/processed/load_audit.csv` | COMPLETE |
| **D-03: Validation Failures Log** | Sprint 1 | `data/processed/validation_failures.csv` | COMPLETE |
| **D-04: Exploratory Analysis Queries** | Sprint 1 | `data/processed/exploratory_queries.sql` | COMPLETE |
| **D-05: Financial Ratios Table** | Sprint 2 | `db/nifty100.db` (`financial_ratios`) | COMPLETE |
| **D-06: Capital Allocation Dataset** | Sprint 2 | `data/processed/capital_allocation.csv` | COMPLETE |
| **D-07: Master Screener Output** | Sprint 3 | `screener_output.xlsx` | COMPLETE |
| **D-08: Screener Configuration Engine** | Sprint 3 | `screener_config.yaml` | COMPLETE |
| **D-09: Peer Comparison Workbook** | Sprint 3 | `peer_comparison.xlsx` | COMPLETE |
| **D-10: Company Radar Charts Suite** | Sprint 3 | `reports/radar_charts/` (92 PNGs) | COMPLETE |
| **D-11: Streamlit Visual Dashboard** | Sprint 4 | `src/dashboard/app.py` | COMPLETE |
| **D-12: Valuation Summary Workbook** | Sprint 4 | `reports/valuation_summary.xlsx` | COMPLETE |
| **D-13: Cash Flow Intelligence Report** | Sprint 4 | `reports/cashflow_intelligence.xlsx` | COMPLETE |
| **D-14: NLP Pros & Cons Fact Base** | Sprint 5 | `data/processed/pros_cons_generated.csv` | COMPLETE |
| **D-15: Analysis Parsed Growth Base** | Sprint 5 | `data/processed/analysis_parsed.csv` | COMPLETE |
| **D-16: Executive Company Tearsheets** | Sprint 5 | `reports/tearsheets/*.pdf` (92 PDFs) | COMPLETE |
| **D-17: Macro Sector Research Reports** | Sprint 5 | `reports/sector_reports/*.pdf` (11 PDFs) | COMPLETE |
| **D-18: Portfolio Summary Report** | Sprint 5 | `reports/portfolio_summary.pdf` | COMPLETE |
| **D-19: Unsupervised Cluster Labels** | Sprint 6 | `data/processed/cluster_labels.csv` | COMPLETE |
| **D-20: FastAPI Microservice & OpenAPI**| Sprint 6 | `src/api/main.py` (`docs/openapi.json`)| COMPLETE |
| **D-21: Pytest Audit Execution Report** | Sprint 6 | `reports/pytest_report.html` | COMPLETE |
| **D-22: Institutional Analyst Guide** | Sprint 6 | `reports/analyst_guide.pdf` | COMPLETE |
| **D-23: Formal Acceptance Checklist** | Sprint 6 | `reports/acceptance_checklist.pdf` | COMPLETE |

---

## Running the Platform

- **`make load`**: Executes the end-to-end ETL ingestion and validation pipeline across all 12 raw data sources into SQLite in ~25 seconds.
- **`make test`**: Runs the complete 245-test automated pytest verification suite spanning ETL normalisation, DQ gates, KPI computations, API routes, and reporting artifacts.
- **`streamlit run src/dashboard/app.py`**: Launches the interactive 8-screen institutional research terminal on `http://localhost:8501`.
- **`uvicorn src.api.main:app --reload`**: Launches the asynchronous FastAPI REST service on `http://localhost:8000`.
- **Docs at `http://localhost:8000/docs`**: Explore and test all 16 interactive API endpoints via the auto-generated Swagger UI (or `http://localhost:8000/redoc`).

---

## Key Findings

1. **IT Sector Valuation & Profitability Premium:** Information Technology exhibits the highest capital efficiency in the universe (average ROE of 24.8% and median ROCE of 28.5%), translating into a structural valuation multiple premium (median P/E of 32.4x against a universe median of 23.8x).
2. **Quality Compounders Concentration:** Exactly 23 of 92 universe companies satisfied all strict multi-factor criteria for the Quality Compounder screen (ROE >= 15%, D/E <= 0.5, 3-year Revenue CAGR >= 10%, positive Free Cash Flow), dominated by capital-light consumer staples and software technology firms.
3. **IRFC Pre-IPO Capital Base Distortion:** Indian Railway Finance Corporation (IRFC) exhibited distorted raw historical CAGR growth rates (>4,500%) due to nominal pre-2021 capital restructuring prior to its public listing, requiring automated bounds validation and winsorization to prevent index-wide skewing.
4. **Banking-Template vs. Industrial Financial Dichotomy:** Financial institutions (banks and NBFCs such as HDFC Bank, ICICI Bank, SBIN) fundamentally operate on net interest margin (NIM) spreads with customer deposits acting as operating liabilities; standard industrial metrics (EBITDA, OPM, Debt/Equity, ICR) evaluate to `None` with diagnostic labels to avoid mathematical distortion.
5. **Capital Allocation Archetype Shifts:** Longitudinal analysis revealed that only ~38% of non-financial universe constituents maintained Archetype 1 (Healthy Compounder: CFO+, CFI-, CFF-) consistently across all 10 years, with cyclical heavy industrials oscillating into Debt-Funded Expansion (+ - +) during capital expenditure cycles.

---

## Data Sources

The platform ingests and standardizes 12 primary and supporting data sources:

1. **`data/raw/companies.xlsx`** (93 rows): Master registry of universe companies including NSE/BSE tickers, corporate names, industry sectors, and brand logo links.
2. **`data/raw/profitandloss.xlsx`** (1,277 rows): 10+ years of audited income statements covering Sales/Revenue, Expenses, Operating Profit, OPM, Other Income, Interest, Depreciation, PBT, Tax, PAT, and EPS.
3. **`data/raw/balancesheet.xlsx`** (1,313 rows): 10+ years of audited balance sheets detailing Equity Capital, Reserves, Borrowings, Other Liabilities, Fixed Assets, CWIP, Investments, and Other Assets.
4. **`data/raw/cashflow.xlsx`** (1,188 rows): 10+ years of audited cash flow statements disaggregating Cash Flow from Operating Activities (CFO), Investing Activities (CFI), and Financing Activities (CFF).
5. **`data/raw/documents.xlsx`** (1,586 rows): Historical repository of annual report filing links and regulatory document disclosure URLs across fiscal periods.
6. **`data/raw/analysis.xlsx`** (21 rows): Benchmark compound growth tables providing verification targets for Compounded Sales, Compounded Profit, Stock Price CAGR, and Return on Equity.
7. **`data/raw/prosandcons.xlsx`** (17 rows): Qualitative management observations, credit agency commentary, and strategic operational risks.
8. **`data/supporting/sectors.xlsx`** (92 rows): Standardized sector classification mapping every constituent into 11 canonical institutional broad sectors and sub-industries.
9. **`data/supporting/peer_groups.xlsx`** (56 rows): Industry peer grouping taxonomy establishing intra-sector comparative cohorts and designated benchmark anchor firms.
10. **`data/supporting/financial_ratios.xlsx`** (1,184 rows): Supplementary vendor ratio baselines (ROCE, ROE, Debtor Days, Inventory Turnover) utilized for cross-validation reconciliation.
11. **`data/supporting/market_cap.xlsx`** (552 rows): Multi-year historical market capitalizations used for sizing valuation multiples and weighting composite ranks.
12. **`data/supporting/stock_prices.xlsx`** (5,520 rows): Monthly and annual adjusted stock pricing history enabling 1-year, 3-year, and 5-year returns and valuation multiple benchmarking.

---

## Known Limitations

1. **State Bank of India (SBIN) Balance Sheet Omission:** SBIN source records follow banking regulatory schedules that omit standard corporate share capital and reserves splits; balance sheet-dependent ratios (ROE, D/E, Asset Turnover) safely return documented `None` values rather than misleading estimates.
2. **BEL & HAL Source Reporting Anomalies:** Bharat Electronics Limited and Hindustan Aeronautics Limited contain non-standard line-item alignments in specific historical balance sheet filings; data integrity rules neutralize affected years to prevent skewing peer percentiles.
3. **Simulated Data Disclosure:** Certain supplementary market datasets (e.g., forward P/E estimates and multi-year stock price histories) incorporate modeled proxies to achieve 100% complete universe coverage where vendor filing gaps exist.
4. **Simplified Intrinsic DCF Estimation:** The valuation engine implements a streamlined two-stage Free Cash Flow to Firm (FCFF) discounted model (5-year explicit horizon + terminal growth) intended for comparative screening rather than full transaction-grade equity appraisal.
5. **Banking-Template Structural Carve-Out:** In accordance with institutional research standards, financial institutions (banks and NBFCs) are structurally exempted from operating margins, interest coverage ratios, and corporate leverage metrics; these fields evaluate strictly to `None` with analytical tags.

---

## Tech Stack

- **`python`** (`3.13`): Core programming language and runtime environment
- **`pandas`** (`>=2.0`): High-performance DataFrame manipulation, aggregation, and tabular transformations
- **`numpy`** (`>=1.24`): Vectorized numeric array operations and mathematical ratio calculations
- **`openpyxl`** (`>=3.1`): Excel workbook generation with multi-tab architectures, custom fonts, and 3-color scales
- **`scipy`** (`>=1.11`): Statistical distributions, winsorization functions, and percentile calculations
- **`scikit-learn`** (`>=1.3`): Unsupervised K-Means clustering, feature standard scaling, and PCA dimension reduction
- **`matplotlib`** (`>=3.7`): Static chart rendering for publication-quality figures embedded in ReportLab PDFs
- **`plotly`** (`>=5.18`): Interactive web-based visualizations, scatter plots, and time-series overlays in Streamlit
- **`streamlit`** (`>=1.30`): Modern responsive multi-screen web dashboard for exploratory equity analysis
- **`fastapi`** (`>=0.110`): High-throughput asynchronous REST microservice framework with Pydantic validation
- **`uvicorn`** (`>=0.27`): Production ASGI web server hosting the FastAPI application
- **`reportlab`** (`>=4.1`): Enterprise PDF publishing engine generating pixel-perfect multi-page tearsheets and reports
- **`nltk`** (`>=3.8`): Natural language processing and tokenization for corporate pros and cons fact extraction
- **`pytest`** (`>=7.4`): Automated unit, integration, and data quality testing framework
- **`pytest-html`** (`>=4.0`): Automated self-contained HTML test execution reporting
- **`black`** (`>=24.0`): Deterministic PEP 8 code formatting enforcement
- **`ruff`** (`>=0.4`): Ultra-fast Python linter for static code analysis, type adherence, and import sorting
- **`pre-commit`** (`>=3.7`): Pre-commit Git hook automation ensuring clean code before repository ingestion
- **`python-dotenv`** (`>=1.0`): Twelve-factor environment variable configuration management
- **`requests`** (`>=2.30`): HTTP networking client for regulatory document link validation (DQ-13)
- **`sqlite3`** (Standard Library): Serverless ACID-compliant relational SQL data warehouse engine
