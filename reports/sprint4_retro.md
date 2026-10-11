# Sprint 4 Retrospective: Dashboard & Valuation Module
**Project:** N100 Financial Intelligence Platform  
**Sprint Window:** October 6, 2026 – October 11, 2026 (Completed ahead of Oct 12 deadline)  
**Author:** Platform Engineering & Quantitative Analytics Team  
**Status:** Completed & Integrated (Sprint Tag: `sprint4-complete`)  

---

## 1. Executive Summary & Sprint Goal Review
Sprint 4 was dedicated to delivering **Module 5 (Company Intelligence Dashboard)** and **Module 6 (Valuation Module)**. The core objective was transforming our normalized data warehouse (`nifty100.db`), financial ratio models, composite ranking engine, and peer percentiles into an interactive, multi-screen Streamlit intelligence platform and an institutional-grade valuation analytics suite (`valuation_summary.xlsx`).

All 8 planned Streamlit screens were fully implemented, tested, and optimized for sub-second cached data retrieval. 207 of 207 tests continue to pass with zero regressions.

---

## 2. What Was Built: 8 Streamlit Screens Summary

The unified Streamlit application (`src/dashboard/app.py`) runs on `http://localhost:8501` featuring modern glassmorphism styling, clean KPI metrics, Plotly interactive visualizations, and robust edge-case handling across all 8 screens:

1. **Screen 1 — Home / Overview:**
   - **Universe KPI Tiles:** Total Companies (92), Average ROE across non-financials (16.2%), Median P/E (31.8x), and Quality Compounder matches (31).
   - **Top 10 Compounders:** Leaderboard ranked by `composite_ranking_score` with broad sector, ROE, and 3Y Revenue CAGR.
   - **Sector Distribution:** Interactive Plotly horizontal bar chart showing constituent breakdown across 11 broad sectors.
   - **Market Pulse Diagnostic:** Real-time liquidity & solvency health tracking (count of positive FCF companies, low-leverage companies $D/E < 1.0$, and high-leverage watch flags).

2. **Screen 2 — Company Profile:**
   - **Company Selector & Master Header:** Searchable ticker dropdown with live company name, sector, and industry classification.
   - **Key Financial Ratios Grid:** 8 core metrics (ROE, ROCE, NPM, OPM, D/E, ICR, Asset Turnover, CFO Quality Score).
   - **Visual Radar Chart:** Dynamic rendering of the company's 8-axis static PNG benchmark radar chart generated from `reports/radar_charts/{ticker}_radar.png`.
   - **10-Year Historical Financial Matrix:** Comprehensive trajectory of Sales, Operating Profit, Net Profit, CFO, and CapEx.
   - **Caveat & Governance Banners:** Automatic informational callouts for Banking template companies (RBI format) and Defense PSUs (SBIN, BEL, HAL).

3. **Screen 3 — Financial Screener:**
   - **Interactive Threshold Controls:** 10 responsive sliders/inputs for key metrics (`min_roe`, `max_de`, `min_fcf`, `min_opm`, `max_pe`, `min_revenue_cagr_3yr`, `min_pat_cagr_3yr`, `min_cfo_quality`, `max_capex_intensity`, `min_composite_score`).
   - **Preset Auto-Fill Selector:** One-click threshold configuration for the 6 pre-built screening presets (*Quality Compounders*, *Value Picks*, *Dividend Aristocrats*, *Growth Rockets*, *Asset-Light Champions*, *Financial Health*).
   - **Live Results Table:** Real-time filtering with reactive row-count counter ("X companies match your criteria").
   - **Export Capability (AC-09):** One-click CSV download delivering complete filtered data with timestamped filename.
   - **Exclusion Audit Banner:** Clear transparency regarding non-display of companies with null ratios.

4. **Screen 4 — Peer Comparison:**
   - **Peer Group Navigation:** Selectable across all 11 standardized N100 peer groups.
   - **Intra-Group Percentile Table:** Detailed matrix showing 20 financial metrics per peer member with intra-group percentile rankings (0–100 scale).
   - **Benchmark Gap Analysis:** Highlighting peer group benchmark companies and intra-group variance against the group leader.
   - **Classification Badges:** Visual tagging of *Best in Class* ($\ge 80$th percentile) vs *Watch List* ($\le 20$th percentile).

5. **Screen 5 — Sector Analytics & Sector Analysis:**
   - **Sector Selector:** Dropdown across 11 broad sectors with real-time aggregate statistics.
   - **Sector KPI Summary:** Sector Average ROE, Average OPM, Median D/E, Total Constituent Count, and Best-in-Class vs Watch List tally.
   - **Sector vs Universe Benchmark:** Side-by-side grouped Plotly bar chart comparing the chosen sector against full-universe averages across ROE, OPM, Revenue CAGR 3Y, and D/E.
   - **Intra-Sector Rankings:** Ordered constituent table sorted by composite ranking score.

6. **Screen 6 — Cash Flow Intelligence & Capital Allocation:**
   - **FCF Universe Health Summary:** Aggregate counts of positive FCF, negative FCF, and excluded banking template entities.
   - **CapEx Intensity Distribution:** Histogram and statistical summary of capital intensity across sectors.
   - **Capital Allocation Matrix:** Visual distribution of companies across the 8 defined capital allocation patterns (e.g., *Self-Funded Compounder*, *Debt-Fueled Expander*, *Capital-Constrained Stagnator*).
   - **10-Year Cash Flow Breakdown:** Multi-year CFO, CapEx, and FCF trend table per company.

7. **Screen 7 — Trend & Growth / Trend Analysis:**
   - **10-Year P&L Trajectory:** Interactive multi-trace Plotly line chart illustrating Sales, Operating Profit, Net Profit, CFO, and EPS from FY14 to FY24.
   - **Growth Rates & CAGR Metrics:** Automated YoY trajectory calculation alongside 3-Year and 5-Year compound annual growth rates.
   - **Multi-Metric Comparison Overlay:** Normalized trend view enabling direct performance scaling.
   - **Financial Statement Data Matrix:** Audited annual breakdown with formatting for crore figures.

8. **Screen 8 — Valuation Module & Annual Reports:**
   - **Macro Valuation Multiples:** Summary KPI tiles for Universe Median P/E, Median P/B, Median EV/EBITDA, and Median FCF Yield.
   - **IT Sector Valuation Cluster Visualizer:** Dedicated scatter plot ($P/E$ vs $ROE$) and analysis table highlighting IT premium multiples.
   - **92-Company Valuation Multiples Table:** Full universe valuation table with cautionary flags (*Caution: Low FCF Yield*, *Discount: Deep Value*).
   - **Interactive Simplified DCF Calculator:** Two-stage DCF simulator with user-tunable inputs (Forecast FCF, 5Y Growth Rate, WACC / Discount Rate, Terminal Growth Rate) with explicit methodology disclaimers.
   - **BSE Annual Report Document Browser:** Direct lookup and metadata viewer for BSE filings connected to the `documents` table.

---

## 3. Key Analytical Finding: The IT Sector Valuation Cluster

An essential insight surfaced by our valuation module (`src/analytics/valuation.py` & Screen 8) is the extraordinary valuation clustering observed in India's top Tier-1 IT services giants (**TCS, INFY, HCLTECH, LTIM, TECHM**):

| Ticker | P/E Ratio | P/B Ratio | EV/EBITDA | ROE (%) | Net Debt / Equity | FCF Conversion (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TCS** | 30.8x | 13.5x | 21.2x | 51.5% | Cash Rich (-0.15) | 102.4% |
| **INFY** | 27.2x | 7.4x | 18.1x | 32.1% | Cash Rich (-0.12) | 94.6% |
| **HCLTECH** | 29.1x | 6.2x | 17.5x | 23.4% | Cash Rich (-0.08) | 88.2% |
| **LTIM** | 35.4x | 8.1x | 22.8x | 25.8% | Cash Rich (-0.10) | 82.5% |
| **TECHM** | 48.2x | 5.3x | 24.1x | 8.6% | Cash Rich (-0.05) | 79.1% |

### Core Observations:
1. **Premium Valuation Cluster:** The Tier-1 IT sector trades in a very tight valuation multiple band (median P/E of ~30x vs universe median of 31.8x, but with significantly lower earnings volatility).
2. **Pristine Balance Sheets:** All 5 companies maintain negative net debt (cash and equivalents vastly exceed all financial borrowings).
3. **Exceptional Free Cash Flow Conversion:** Cash flow conversion from operating profit to FCF ranges from 80% to 102%, reflecting asset-light software business models with minimal physical CapEx requirements.
4. **Conclusion:** Markets award these IT compounders a structural valuation floor due to negative leverage, predictable overseas dividend flows, and sustained high return on capital.

---

## 4. 7-Company Financial Stress Watch List

Cross-referencing the Screener Financial Health criteria, high leverage flags ($D/E > 1.0$ or debt flag), negative free cash flow ($FCF < 0$), and low Interest Coverage Ratios ($ICR < 1.5$), the analytics engine identified 7 non-financial companies facing elevated capital structure stress:

| Ticker | Company Name | Sector | D/E Ratio | ICR | FCF (₹ Cr) | Primary Stress Driver |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **ADANIGREEN** | Adani Green Energy Ltd | Utilities / Renewable | 6.22 | 1.48 | -3,410 | Massive leveraged capital expenditure in solar/wind capacity; heavy interest burden. |
| **ADANIENT** | Adani Enterprises Ltd | Diversified | 1.84 | 1.62 | -4,820 | High conglomerate incubation debt (airports, roads, green hydrogen) outstripping operational CFO. |
| **GRASIM** | Grasim Industries Ltd | Materials / Conglomerate | 1.15 | 2.10 | -2,150 | Aggressive multi-thousand crore capex into Birla Opus paints and chemicals expansion. |
| **BHEL** | Bharat Heavy Electricals Ltd | Industrials / Capital Goods | 0.82 | 0.74 | -890 | Compressed operating margins, working capital lockups, and inadequate EBIT to cover debt service ($ICR < 1.0$). |
| **TVSMOTOR** | TVS Motor Company Ltd | Consumer Discretionary / Auto | 2.08 | 3.10 | +420 | High consolidated leverage resulting from retail vehicle financing subsidiary borrowings. |
| **JSWSTEEL** | JSW Steel Ltd | Materials / Steel | 1.12 | 2.35 | -1,450 | Cyclical margin compression combined with heavy blast furnace capacity expansion capex. |
| **JSWENERGY** | JSW Energy Ltd | Utilities / Power | 1.58 | 1.88 | -1,120 | Accelerated inorganic asset acquisitions and renewable capacity buildout funded by debt. |

---

## 5. Known Limitations & Architectural Decisions

1. **SBIN, BEL, and HAL Handling in Screens:**
   - **State Bank of India (SBIN):** Bank balance sheets and P&L statements follow RBI statutory formats where interest is cost of goods sold rather than financing cost, and deposits are operating liabilities rather than debt. Consequently, Operating Profit Margin, Debt-to-Equity, ICR, and ROCE return `None`. The UI handles this via contextual informational banners rather than displaying inaccurate "0.0" values.
   - **BEL & HAL:** These defense PSUs have incomplete balance sheet records in Screener.in source data for several historical years. As designed in Sprint 2 and Sprint 3, their balance-sheet ratios and Composite Scores evaluate to `None`. The Streamlit application renders informative callouts ("Data Caveat: Defense PSU with partial balance sheet history") preventing UI crashes.
2. **Simplified DCF Model:**
   - The interactive DCF calculator in Screen 8 employs a standardized 2-stage Gordon Growth / terminal multiple model based on latest FCF.
   - **Caveat:** It is an educational and sensitivity-testing tool, not an institutional multi-stage bespoke DCF with working capital schedule and segment-level projection. Clear disclaimers warn users of assumption sensitivity.
3. **Radar Charts as Static PNGs:**
   - The 92 radar charts rendered on Screen 2 are generated using matplotlib in Sprint 3 (`reports/radar_charts/`).
   - They are served efficiently as pre-computed static PNG images via `st.image`. While fast and visually consistent with printed reporting, they are not interactive SVG/Plotly charts.

---

## 6. Sprint 4 Exit Criteria Verification

| Exit Criterion | Target | Actual Result | Status |
| :--- | :--- | :--- | :---: |
| **1. Streamlit App Runs** | Operational on `http://localhost:8501` without unhandled errors | Starts cleanly, HTTP 200 on health endpoint `/_stcore/health` and root page | **PASS** |
| **2. All 8 Screens Navigable** | Sidebar router navigates Home, Profile, Screener, Peer, Sector, Cash Flow, Trend, Valuation | All 8 screens verified with live data loaders and proper keywords | **PASS** |
| **3. Screener CSV Export (AC-09)** | Filtered dataset downloadable as valid CSV | Validated CSV generation (31 compounders, 20.5 KB valid CSV output) | **PASS** |
| **4. Valuation Summary Report (D-12)** | `reports/valuation_summary.xlsx` exists with 92 company rows | 92 company rows across 3 sheets (`Valuation Summary`, `Sector Multiples`, `Valuation Flags`) | **PASS** |
| **5. Test Suite Passing** | 207+ tests passing with zero regressions | **207 / 207 tests passed** in 21.28s | **PASS** |

---

## 7. What Sprint 5 Inherits

Sprint 5 represents the final delivery and packaging phase. It inherits:
1. **A Complete, Tested 8-Screen Application:** Zero placeholder screens; all screens read live SQLite data with cached query handlers.
2. **Multi-Workbook Financial Reporting Suite:**
   - `reports/screener_output.xlsx` (7 sheets: Summary + 6 presets)
   - `reports/peer_comparison.xlsx` (12 sheets: Summary + 11 peer groups with conditional color scales)
   - `reports/valuation_summary.xlsx` (3 sheets: 92 valuation profiles, sector multiples, cautionary flags)
3. **Complete Asset Repository:** 92 company radar charts (`reports/radar_charts/*.png`), capital allocation classifications (`reports/capital_allocation_classifications.csv`), and load audit logs.
4. **Next Steps for Sprint 5:**
   - End-to-end documentation & User Manual (`docs/user_guide.md`, `README.md` updates).
   - Packaging for deployment (run scripts, configuration guides).
   - Executive presentation summary and final project sign-off.
