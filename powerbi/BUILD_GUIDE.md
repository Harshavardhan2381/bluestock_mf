# Bluestock MF Dashboard — Power BI Build Guide

Step-by-step instructions for **this project’s** actual column names and files.  
Automated assets live in `powerbi/` (DAX, theme, relationships, validation).

---

## Prerequisites

- Power BI Desktop (latest)
- Data folder: `data/processed/` (and one raw file for Page 3)
- Run KPI check: `python powerbi/validate_kpis.py`

---

## Step 1 — New report & load data

1. **File → New report**
2. **Get data → Text/CSV** and import:

| Power BI table name | File path | Notes |
|---------------------|-----------|-------|
| `clean_aum` | `data/processed/clean_aum.csv` | |
| `clean_sip_inflows` | `data/processed/clean_sip_inflows.csv` | |
| `clean_category_inflows` | `data/processed/clean_category_inflows.csv` | |
| `clean_folio_count` | `data/processed/clean_folio_count.csv` | |
| `clean_transactions` | `data/processed/clean_transactions.csv` | No state/age |
| `clean_performance` | `data/processed/clean_performance.csv` | |
| `fund_scorecard` | `data/processed/fund_scorecard.csv` | |
| `returns_computed` | `data/processed/returns_computed.csv` | Large file |
| `tracking_error` | `data/processed/tracking_error.csv` | |
| `clean_benchmark` | `data/processed/clean_benchmark.csv` | NIFTY50 series |
| `clean_fund_master` | `data/processed/clean_fund_master.csv` | Dimension |

3. **Additional import for Page 3 (demographics):**

| Power BI table name | File path |
|---------------------|-----------|
| `investor_transactions_raw` | `data/raw/datasets/08_investor_transactions.csv` |

**Power Query transforms (apply before Close & Apply):**

```powerquery
// investor_transactions_raw — rename & types
Renamed Columns: amfi_code → scheme_code, transaction_date → date
Changed Type: scheme_code (Whole Number), date (Date), amount_inr (Decimal)
// Keep: state, city_tier, age_group, transaction_type, amount_inr
```

```powerquery
// clean_sip_inflows, clean_folio_count, clean_category_inflows
Changed Type: month → Date (first of month)
```

```powerquery
// clean_aum
Changed Type: report_date → Date, aum_crore → Decimal Number
```

```powerquery
// tracking_error
Changed Type: scheme_code → Whole Number
```

```powerquery
// clean_benchmark — optional: add MonthStart column
MonthStart = Date.StartOfMonth([date])
```

4. **Import mode** (not DirectQuery) for all tables.

---

## Step 2 — Relationships

Follow `powerbi/relationship_map.md`. In **Model view**:

1. Drag `clean_fund_master[scheme_code]` to each scheme-level table’s `scheme_code`.
2. Set **Cardinality**: Many to one; **Cross filter**: Single.
3. Leave `clean_aum`, `clean_sip_inflows`, `clean_folio_count`, `clean_category_inflows`, `clean_benchmark` **unconnected**.

---

## Step 3 — DAX measures

1. **Modeling → Enter data** → create table `_Measures` (one blank row) → Load.
2. Copy measures from `powerbi/dax_measures.dax` (Home → Enter data is not needed for measures — use **New measure** on `_Measures`).
3. Format:
   - `Total AUM`, `Total SIP`: `#,0` with suffix " Cr" in visual title
   - `Total Folios`: `0.00` with suffix " Cr"
   - `YoY SIP Growth %`: Percentage, 1 decimal

**Validate KPI cards after creation:**

| Measure | Expected (this dataset) |
|---------|-------------------------|
| Total AUM | 6,274,000 Cr |
| Total SIP | 31,002 Cr |
| Total Folios | 26.12 Cr |
| Total Schemes | 40 |
| YoY SIP Growth % | 17.17% |

---

## Step 4 — Apply theme & logo

1. **View → Themes → Browse for themes** → select `powerbi/bluestock_theme.json`
2. **Logo:** No Bluestock logo exists in the repo. Place your file at:
   - `powerbi/assets/bluestock_logo.png` (recommended)
   - Insert → **Image** on each page, top-right, ~80×40 px

---

## Page 1 — Industry Overview

**Canvas:** 1280×720, background `#F4F7FB`

### KPI cards (row of 4)

| Card | Field |
|------|-------|
| Total AUM | `[Total AUM]` |
| Total SIP | `[Total SIP]` |
| Total Folios | `[Total Folios]` |
| Total Schemes | `[Total Schemes]` |

### Line chart — Industry AUM Trend (2022–2025)

| Role | Field |
|------|-------|
| X-axis | `clean_aum[report_date]` |
| Y-axis | `SUM(clean_aum[aum_crore])` or measure `[Industry AUM Trend]` |
| Filter | `report_date` between 2022-03-31 and 2025-12-31 |

### Bar chart — Top 10 fund houses by AUM

| Role | Field |
|------|-------|
| Y-axis | `clean_aum[fund_house]` |
| X-axis | `SUM(clean_aum[aum_crore])` |
| Filter | `report_date` = latest (2025-12-31) |
| Top N | Top 10 by AUM descending |

---

## Page 2 — Fund Performance

### Scatter — Risk vs Return

| Role | Field |
|------|-------|
| X-axis | `clean_performance[std_dev_ann_pct]` (Risk) |
| Y-axis | `clean_performance[return_3yr_pct]` (Return) |
| Details | `clean_fund_master[scheme_name]` or `returns_computed[scheme_name]` |
| Size | `clean_performance[aum_crore]` |
| Legend | `clean_performance[risk_grade]` |

### Table — Fund scorecard

| Column | Field |
|--------|-------|
| Fund | `clean_fund_master[scheme_name]` |
| Score | `fund_scorecard[score]` |
| 3Y CAGR rank | `fund_scorecard[rank_3yr_cagr]` |
| Sharpe rank | `fund_scorecard[rank_sharpe]` |
| Sort | `fund_scorecard[score]` descending |

### Line chart — NAV vs Benchmark

**Option A (scheme with NAV history):**

| Series | Table | Axis | Value |
|--------|-------|------|-------|
| Fund NAV | `returns_computed` | `date` | `nav` |
| Benchmark | `clean_benchmark` | `date` | `close_value` |

- Filter `clean_benchmark[index_name]` = `NIFTY50`
- Use **small multiples** or a **scheme slicer** on `returns_computed[scheme_name]` (only 30 schemes have NAV series)
- Normalize to index 100 in Power Query if scales differ wildly

**Option B:** Use `clean_performance[benchmark_3yr_pct]` vs `return_3yr_pct` in a clustered bar (snapshot, not time series).

### Slicers

| Slicer | Field | Source table |
|--------|-------|--------------|
| Fund House | `fund_house` | `returns_computed` or `clean_fund_master` |
| Category | `scheme_category` | `returns_computed` or `clean_fund_master` |
| Risk Grade | `risk_grade` | `clean_performance` |

---

## Page 3 — Investor Analytics

> Uses `investor_transactions_raw` (raw CSV) for `state`, `age_group`, `city_tier`.

### Stacked bar — Transaction amount by state

| Role | Field |
|------|-------|
| Y-axis | `investor_transactions_raw[state]` |
| X-axis | `SUM(investor_transactions_raw[amount_inr])` |
| Legend | `investor_transactions_raw[transaction_type]` (SIP / Lumpsum / Redemption) |

### Donut — Transaction type distribution

| Role | Field |
|------|-------|
| Legend | `investor_transactions_raw[transaction_type]` |
| Values | `COUNTROWS(investor_transactions_raw)` or `SUM(amount_inr)` |

### Bar — Avg SIP amount by age group

| Role | Field |
|------|-------|
| Axis | `investor_transactions_raw[age_group]` |
| Value | `AVERAGE(investor_transactions_raw[amount_inr])` |
| Filter | `transaction_type` = `SIP` |

### Line — Monthly transaction trend

| Role | Field |
|------|-------|
| Axis | `investor_transactions_raw[date]` (month hierarchy) |
| Values | `SUM(amount_inr)` |
| Legend | `transaction_type` |

### Slicers

- `state`, `age_group`, `city_tier` from `investor_transactions_raw`

---

## Page 4 — SIP & Market Trends

### Combo chart — SIP inflow vs NIFTY50

1. In Power Query on `clean_benchmark`, add `MonthStart = Date.StartOfMonth([date])`, filter `index_name = NIFTY50`, group by month → `Avg Close` or last `close_value`.
2. Visual: **Line and clustered column chart**

| Role | Field |
|------|-------|
| Shared axis | Month (`clean_sip_inflows[month]` aligned with benchmark month) |
| Column | `clean_sip_inflows[sip_inflow_crore]` |
| Line | Monthly NIFTY50 `close_value` |

*Tip:* If months don’t align, build a single PQ query that joins SIP and benchmark on `MonthStart`.

### Matrix heatmap — Category × Month

| Role | Field |
|------|-------|
| Rows | `clean_category_inflows[category]` |
| Columns | `clean_category_inflows[month]` |
| Values | `SUM(net_inflow_crore)` |
| Conditional formatting | Background color on values (diverging: red/blue) |

### Bar — Top 5 categories FY25

| Role | Field |
|------|-------|
| Axis | `category` |
| Values | `SUM(net_inflow_crore)` |
| Filter | `month` >= 2024-04-01 AND `month` <= 2025-03-31 |
| Top N | 5 |

### KPI card

- `[YoY SIP Growth %]` formatted as percentage

---

## Step 5 — Interactivity & drillthrough

### Tooltips (all major visuals)

Create **Tooltip page** or use built-in tooltips with:

- `clean_fund_master[scheme_name]`
- `clean_performance[aum_crore]`
- `clean_performance[return_3yr_pct]`
- `clean_performance[risk_grade]`

### Drill-through page — Fund Details

1. New page named **Fund Details**; set **Drill through** field = `scheme_code` or `scheme_name`.
2. Add: NAV line (`returns_computed`), performance card, scorecard row, tracking error.
3. On scatter/table: right-click a fund → **Drill through → Fund Details**.

---

## Step 6 — Export

1. **File → Save as** → `bluestock_mf_dashboard.pbix` (project root or `powerbi/`)
2. **File → Export → Export to PDF** → `Dashboard.pdf`
3. **File → Export → Export with live data / page images:**
   - `Industry_Overview.png`
   - `Fund_Performance.png`
   - `Investor_Analytics.png`
   - `SIP_Market_Trends.png`

---

## Known data limitations (this capstone)

| Spec / expectation | Actual data |
|--------------------|-------------|
| `sip_amount_crore` | Column is `sip_inflow_crore` |
| `folio_count_crore` | Column is `total_folios_crore` |
| AUM ~81 lakh crore | Latest sum = **62.74 lakh crore** (10 fund houses only) |
| Schemes ~1,908 | **40** in `clean_performance`; 9,577 in `clean_fund_master` |
| State / age / city slicers | Not in `clean_transactions`; use **raw** `08_investor_transactions.csv` |
| `fund_scorecard[scheme_name]` | Stores scheme **code**; join to `clean_fund_master` for names |
| `tracking_error` | Only **2** schemes |
| `returns_computed` NAV | **30** schemes (not all 40 in performance) |

---

## Quick checklist

- [ ] 12 tables loaded (11 processed + 1 raw investor)
- [ ] Date columns typed as Date
- [ ] 5–6 `scheme_code` relationships active
- [ ] Measures from `dax_measures.dax` pasted
- [ ] Theme `bluestock_theme.json` applied
- [ ] Logo placed in `powerbi/assets/bluestock_logo.png`
- [ ] 4 report pages + drill-through page
- [ ] KPI values match `validate_kpis.py` output
- [ ] PBIX + PDF + 4 PNG exports saved
