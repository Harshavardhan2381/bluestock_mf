# TODO — Day 5: Power BI Dashboard Development

> **Automated prep complete.** See `powerbi/BUILD_GUIDE.md`, `powerbi/dax_measures.dax`, `powerbi/relationship_map.md`, `powerbi/bluestock_theme.json`.  
> Run `python powerbi/validate_kpis.py` to confirm KPIs before building.

## Data status (verified)

| File | Status |
|------|--------|
| `clean_aum.csv` | ✅ Present (10 fund houses, 9 report dates) |
| `clean_sip_inflows.csv` | ✅ Present |
| `clean_category_inflows.csv` | ✅ Present |
| `clean_folio_count.csv` | ✅ Present |
| `clean_transactions.csv` | ✅ Present (no demographics) |
| `clean_performance.csv` | ✅ Present (40 schemes) |
| `fund_scorecard.csv` | ✅ Present |
| `returns_computed.csv` | ✅ Present (30 schemes with NAV) |
| `tracking_error.csv` | ✅ Present (2 schemes) |
| `clean_benchmark.csv` | ✅ Present (NIFTY50) — bonus for Page 4 |
| `clean_fund_master.csv` | ✅ Present — use as dimension |
| `data/db/bluestock_mf.db` | ✅ Present (star schema; no folio/category/benchmark) |
| Bluestock logo | ❌ **Missing** — place at `powerbi/assets/bluestock_logo.png` |

### KPI values from CSVs (Dec 2025 / latest)

| KPI | Actual | Spec note |
|-----|--------|-----------|
| Total AUM | **6,274,000 Cr** (62.74 lakh crore) | Spec ~81 lakh crore — dataset has 10 AMCs only |
| Total SIP | **31,002 Cr** | ✅ Matches spec |
| Total Folios | **26.12 Cr** | ✅ Matches spec |
| Total Schemes | **40** (`clean_performance`) | Spec ~1,908 — use `clean_fund_master` (9,577) if instructor expects full universe |
| YoY SIP Growth | **17.17%** | ✅ In range |

### Column name mismatches (use actual names in Power BI)

| Spec name | Actual column |
|-----------|---------------|
| `sip_amount_crore` | `sip_inflow_crore` |
| `folio_count_crore` | `total_folios_crore` |
| `scheme_code` on `clean_aum` | **Not present** — AUM is fund-house level |
| `state`, `age_group`, `city_tier` | Only in `data/raw/datasets/08_investor_transactions.csv` |
| `fund_scorecard[scheme_name]` | Numeric code — join `clean_fund_master[scheme_name]` |

---

## 1) Create PBIX + Load Data
- [ ] File → New Report
- [ ] Load CSVs from `data/processed/` per `powerbi/BUILD_GUIDE.md` (import mode)
- [ ] **Also load** `data/raw/datasets/08_investor_transactions.csv` as `investor_transactions_raw` (Page 3)
- [ ] Power Query: set `month`/`report_date`/`date` to Date type
- [ ] Rename `amfi_code` → `scheme_code` on raw investor file

## 2) Model Relationships (CSV mode)
- [ ] `clean_fund_master[scheme_code]` → one-to-many to performance, scorecard, tracking_error, returns, transactions, investor raw
- [ ] Leave industry tables disconnected (`clean_aum`, SIP, folio, category, benchmark) — see `powerbi/relationship_map.md`
- [ ] Verify no broken relationships

## 3) Measures (DAX)
- [ ] Copy from `powerbi/dax_measures.dax`:
  - [ ] Total AUM
  - [ ] Total SIP
  - [ ] Total Folios
  - [ ] Total Schemes
  - [ ] Current SIP / Previous SIP / YoY SIP Growth %
- [ ] Validate KPI cards match validation script output

## 4) Page 1 — Industry Overview
- [ ] KPI Cards (4): Total AUM, Total SIP, Total Folios, Total Schemes
- [ ] Line chart: `clean_aum[report_date]` × `SUM(aum_crore)` (2022–2025)
- [ ] Bar chart: Top 10 `fund_house` by AUM (latest `report_date`)

## 5) Page 2 — Fund Performance
- [ ] Scatter: `std_dev_ann_pct` vs `return_3yr_pct`, legend `risk_grade`
- [ ] Scorecard table: join `fund_scorecard` + `clean_fund_master`, sort by `score` DESC
- [ ] NAV vs NIFTY50: `returns_computed[nav]` + `clean_benchmark[close_value]` (filter NIFTY50)
- [ ] Slicers: Fund House, Category (`returns_computed` or `clean_fund_master`), Risk Grade

## 6) Page 3 — Investor Analytics
- [ ] Use `investor_transactions_raw` (not `clean_transactions`)
- [ ] Bar: Transaction amount by `state`, legend `transaction_type`
- [ ] Donut: `transaction_type` distribution
- [ ] Bar: Avg SIP by `age_group` (filter SIP)
- [ ] Line: Monthly transaction trend
- [ ] Slicers: State, Age Group, City Tier

## 7) Page 4 — SIP & Market Trends
- [ ] Dual axis: `sip_inflow_crore` vs monthly NIFTY50
- [ ] Heatmap matrix: `category` × `month`, values `net_inflow_crore`
- [ ] Top 5 categories FY25 (Apr 2024–Mar 2025)
- [ ] KPI: YoY SIP Growth %

## 8) Interactivity & Drillthrough
- [ ] Enable tooltips: Fund Name, AUM, Return, Risk
- [ ] Drill-through page: Fund Details (on `scheme_code`)
- [ ] Right-click fund → drill through

## 9) Branding
- [ ] Apply `powerbi/bluestock_theme.json` (#003366, #0057B8, #00A3E0, #F4F7FB)
- [ ] Add logo from `powerbi/assets/bluestock_logo.png` (top-right) — **add file first**

## 10) Export
- [ ] Save: `bluestock_mf_dashboard.pbix`
- [ ] Export PDF: `Dashboard.pdf`
- [ ] Export page images:
  - [ ] `Industry_Overview.png`
  - [ ] `Fund_Performance.png`
  - [ ] `Investor_Analytics.png`
  - [ ] `SIP_Market_Trends.png`
