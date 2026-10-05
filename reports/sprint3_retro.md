# Sprint 3 Retrospective: Fundamental Screener & Peer Intelligence Platform

**Sprint Duration:** Days 15 – 20 (September 30 – October 5, 2026)  
**Platform Version Tag:** `sprint3-complete`  
**Test Suite Status:** **206 / 206 Passing (100% Green, 0 Regressions)**  
**Core Deliverables:**
- Declarative Screener Engine & Configuration (`src/screener/engine.py`, `screener_config.yaml`)
- Multi-factor Composite Ranking Engine & Workbook (`src/screener/ranking.py`, `screener_output.xlsx` — 7 sheets)
- Intra-Group Peer Percentile Analytics Engine (`src/analytics/peer.py`, `peer_percentiles` SQLite table — 1,120 rows)
- 8-Axis Polar Radar Visualization Suite (`src/analytics/radar.py`, `reports/radar_charts/` — 92 PNGs)
- Multi-Tab Peer Comparison Heatmap Workbook (`src/analytics/peer_comparison.py`, `reports/peer_comparison.xlsx` — 12 sheets)
- Comprehensive End-to-End Integration Suite (`tests/test_sprint3_integration.py` — 6/6 acceptance tests passing)

---

## 1. Executive Summary & What Went Well

Sprint 3 successfully delivered the institutional screening and comparative peer intelligence layers for the N100 Financial Intelligence Platform. Across Days 15 through 20, the platform transitioned from raw ratio computation into actionable fundamental screening, composite market rankings, granular intra-industry benchmarking, and publication-ready visual and tabular reports.

### What Went Exceptionally Well:
1. **Vectorized Declarative Screener Architecture:** The screener engine decoupled analyst-configurable parameters from execution logic via `screener_config.yaml`. Using pandas vectorized boolean masks with `numpy.logical_and.reduce`, screening execution across all 92 companies and 60 financial metrics operates sub-second (< 40ms per query), providing high throughput for interactive user filtering.
2. **Mathematically Sound Composite Scoring:** Designed and implemented a robust 4-pillar composite score (Profitability 35%, Cash Quality 30%, Growth 20%, Solvency 15%). The integration of 5th/95th percentile Winsorisation prior to percentile ranking successfully protected the rankings from extreme non-operating outliers (such as INDIGO's 56x asset turnover) without penalizing legitimate sector leaders.
3. **Audit-Grade Peer Benchmarking (1,120 Table Invariant):** Granular intra-industry benchmarking was established across 11 peer groups and 56 member companies for 20 key financial metrics. Rather than comparing disparate business models against the entire 92-company index, companies are ranked strictly against true direct competitors, calculating precise percentage gaps against designated industry benchmarks (e.g., TCS for IT Services, HDFCBANK for Private Banks).
4. **Rich Multi-Channel Artifact Generation:**
   - **92 High-Resolution Radar PNGs:** Generated uniform 8-axis polar charts for all 92 companies with dual overlays (individual profile vs. peer group/sector average), custom typography, and transparent fill aesthetics.
   - **12-Sheet Peer Comparison Excel Workbook:** Delivered a structured workbook featuring side-by-side matrices of 20 metrics and 20 benchmark gaps per peer group, complete with openpyxl 3-color gradient heatmaps (`ColorScaleRule`) and bolded benchmark headers.
   - **7-Sheet Screener Workbook:** Master `screener_output.xlsx` consolidating the 92-company master summary and 6 filtered preset portfolios.
5. **Ahead-of-Schedule Execution:** Delivered all 7 core Sprint 3 deliverables two days ahead of the original project document schedule, allowing Days 20 and 21 to combine into a thorough integration test suite and retrospective audit.

---

## 2. Sprint 3 Exit Criteria Verification (All 6 Explicitly Passed)

| # | Exit Criterion | Target Requirement | Actual Status | Result |
|:---:|:---|:---|:---|:---:|
| **1** | **6 Preset Screeners Operational** | Quality Compounder (27), Value Pick (2), Dividend Aristocrat (24), Growth Rocket (11), Asset Light Champion (3), Financial Health (30) | All 6 execute seamlessly with exact expected counts and 0 SQL/DataFrame errors | **PASS** |
| **2** | **Peer Percentiles DB Populated** | `peer_percentiles` SQLite table populated for all 11 groups (1,120 rows) | Exactly 1,120 rows (56 companies $\times$ 20 metrics) stored in `db/nifty100.db` | **PASS** |
| **3** | **Radar Charts Generated** | 92 company radar chart PNGs in `reports/radar_charts/` | Exactly 92 valid PNG files, all > 10KB with verified magic headers | **PASS** |
| **4** | **Peer Comparison Workbook** | `reports/peer_comparison.xlsx` with 12 sheets and conditional formatting | 12 sheets (Summary + 11 peer groups), 40 CF rules per group, 100% valid | **PASS** |
| **5** | **Screener Output Workbook** | `screener_output.xlsx` with 7 sheets and composite rankings | 7 sheets (Summary + 6 presets), 92 companies ranked, composite scores [0-100] | **PASS** |
| **6** | **Zero Test Regressions** | Full pytest suite passes with 200+ tests | **206 / 206 tests passing (100% green)** in 22.68 seconds | **PASS** |

---

## 3. Edge Cases Handled

During Sprint 3, several nuanced data characteristics from Sprint 1 and 2 required specialized mathematical and architectural handling:

### 1. Principled Null Handling & Non-Imputation in Percentiles
- **Problem:** 16 banking-template companies structurally do not report operating profit margin (OPM), interest coverage ratio (ICR), return on capital employed (ROCE), or CFO quality score. Imputing zero for these missing fields would unfairly penalize blue-chip institutions (e.g., HDFCBANK, ICICIBANK) with bottom-tier 0th percentiles, while imputing group medians would falsify regulatory metrics.
- **Remediation:** All percentile computations in `src/screener/ranking.py` and `src/analytics/peer.py` exclude `None` entries from the percentile ranking pool. A company with a `None` metric receives `None` for its intra-group percentile and `None` for its benchmark gap. In composite ranking, the company's pillar score is averaged exclusively across its valid sub-components, neither boosting nor penalizing the entity unfairly.

### 2. Debt-Free Companies & Asymptotic Interest Coverage Ratios
- **Problem:** Several peer groups (notably IT Services with TCS, INFY, TECHM, WIPRO, and FMCG leaders) have negligible or zero debt, resulting in near-zero finance costs. In raw data, this produced astronomical interest coverage ratios (e.g. > 10,000x) or division-by-zero `None`s.
- **Remediation:** In peer analytics and screener presets, solvency ranking relies on inverted Debt-to-Equity (where D/E = 0 receives the 100th percentile) and caps extreme ICR values at the 95th percentile, preventing infinite multiples from distorting intra-group spreads.

### 3. Neutralization of BEL, HAL, and SBIN from Market Rankings
- **Problem:** As documented in Sprint 2 Day 13-14, BEL and HAL suffer from a systematic ~100x scale error in raw source balance sheets (`extreme_magnitude_flag = 1`), while SBIN has missing operating cash flow data in raw source filings. Allowing these entities to enter market-wide composite rankings would generate misleading institutional scores.
- **Remediation:** In `src/screener/ranking.py`, companies with `extreme_magnitude_flag == 1` or unverified balance sheets are assigned `composite_ranking_score = None`. In `screener_output.xlsx`, they are explicitly flagged with notes (`Unreliable BS Data (Scale Error ~100x)` or `Missing Source Operating CF`). They are cleanly excluded from top-ranked compounder presets while remaining visible in raw summary sheets.

### 4. Inverted Percentiles for Leverage & Solvency
- **Problem:** For standard metrics (ROE, Revenue CAGR, FCF), higher values represent superior performance. For Debt-to-Equity (D/E), higher values indicate greater financial risk.
- **Remediation:** In both `src/analytics/peer.py` and `src/analytics/radar.py`, D/E is explicitly inverted ($100 - \text{percentile}$), ensuring that an axis or metric score of 100 uniformly signifies the healthiest, lowest-leverage balance sheet.

---

## 4. Known Limitations for Sprint 4+ (Dashboard & API Consumption)

The following known limitations must be factored into Sprint 4 dashboard cards, UI visualizations, and REST API serialization:

1. **Banking-Template Metrics in Radar Charts:**
   - On the 8-axis radar charts for the 16 banks and NBFCs, axes corresponding to OPM, ROCE, and CFO Quality Score render with 0 radius accompanied by an asterisk label (`*`) indicating inapplicable data.
   - *Sprint 4 Requirement:* The frontend interactive dashboard should conditionally swap radar axes for banking entities, replacing industrial axes (OPM, ROCE, D/E) with banking-specific metrics (e.g., Return on Assets, NIM, Gross NPA %, CASA Ratio).
2. **Non-Peer Group Companies (36 Out-of-Group Entities):**
   - 56 of the 92 Nifty 100 companies are mapped into one of the 11 high-homogeneity peer groups in `peer_groups`. The remaining 36 companies (spanning Metals, Cement, Chemicals, Conglomerates, Healthcare) do not belong to a dedicated peer group.
   - For these 36 companies, radar charts and peer analytics fall back to broad sector-level distributions (`sectors` table).
   - *Sprint 4 Requirement:* Dashboard UI cards must visually distinguish between "Peer Group Comparison" (for the 56 mapped companies) and "Broad Sector Comparison" (for the 36 fallback companies) using an informative badge.
3. **SBIN, BEL, and HAL Display in Peer Tables:**
   - In `reports/peer_comparison.xlsx`, SBIN appears in the Public Sector Banks sheet, while BEL and HAL appear in Industrials. Valid P&L and market valuation metrics (P/E, P/B, Dividend Yield, Revenue CAGR) are accurately compared against peers, but balance-sheet fields display `None`.
   - *Sprint 4 Requirement:* Frontend UI tables must render tooltip badges over `None` cells explaining: *"Data neutralized due to source scale error"* rather than displaying blank errors or missing rows.

---

## 5. Architectural Contracts & Design Decisions Inherited by Sprint 4

Sprint 4 (Interactive Web Dashboard, REST API, and Export Engine) inherits a clean, deterministic contract from Sprint 3:

1. **Database Schema & Table Contracts:**
   - `peer_percentiles` table is fully populated with 1,120 rows. Columns: `(company_id, peer_group_name, metric_name, metric_value, benchmark_value, benchmark_gap_pct, percentile_rank, classification, is_benchmark)`.
   - `financial_ratios` table provides latest snapshot records via `MAX(year) LIKE '%-03'`.
2. **Three-Tier Classification Standard:**
   - **Best in Class:** $\ge 75.0$th percentile (Emerald Green `#4CAF50` / `#66BB6A`)
   - **In Line:** $25.0$th to $74.99$th percentile (Amber `#FF9800` / `#FFA726`)
   - **Watch List:** $< 25.0$th percentile (Coral Red `#F44336` / `#EF5350`)
3. **Artifact Paths & Static Asset Hosting:**
   - Radar charts: `reports/radar_charts/{company_id}_radar.png` (Static asset directory ready for fast CDN/FastAPI mounting).
   - Screener workbooks: `screener_output.xlsx` and `reports/screener_output/{preset_name}.xlsx`.
   - Peer comparison workbook: `reports/peer_comparison.xlsx`.
4. **Acceptance Test Invariant:**
   - `tests/test_sprint3_integration.py` serves as the permanent regression guard for all Sprint 3 functionality and can be executed via `pytest` or standalone Python script.
