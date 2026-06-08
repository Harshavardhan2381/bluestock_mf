# Bluestock MF — Power BI Relationship Map

This document maps the **actual** project tables and join keys. Several industry-level tables have **no `scheme_code`** and remain disconnected (use separately on their pages).

## Core dimension

| Table | Role | Primary Key | Notes |
|-------|------|-------------|-------|
| `clean_fund_master` | Scheme dimension | `scheme_code` | 9,577 schemes; names available |
| `returns_computed` | Scheme attributes + NAV history | `scheme_code` + `date` | Denormalized `fund_house`, `scheme_name`, `scheme_category` for 30 schemes with NAV series |

## Fact tables (scheme-level)

| From (Many) | To (One) | Column | Cardinality | Active? | Notes |
|-------------|----------|--------|-------------|-------|-------|
| `clean_performance` | `clean_fund_master` | `scheme_code` | Many → One | Yes | 40 schemes; snapshot metrics |
| `fund_scorecard` | `clean_fund_master` | `scheme_code` | Many → One | Yes | 40 rows; `scheme_name` column is numeric code — use `clean_fund_master[scheme_name]` |
| `tracking_error` | `clean_fund_master` | `scheme_code` | Many → One | Yes | Cast `tracking_error[scheme_code]` to Whole Number in PQ if needed |
| `returns_computed` | `clean_fund_master` | `scheme_code` | Many → One | Yes | Large NAV fact; 30 schemes |
| `clean_transactions` | `clean_fund_master` | `scheme_code` | Many → One | Yes | No demographics |
| `investor_transactions_raw` | `clean_fund_master` | `scheme_code` | Many → One | Yes | Load from `data/raw/datasets/08_investor_transactions.csv`; rename `amfi_code` → `scheme_code` |

### Optional bridge (if `clean_fund_master` join is sparse)

| From | To | Column | Notes |
|------|-----|--------|-------|
| `clean_performance` | `returns_computed` | `scheme_code` | Gets `fund_house` / `scheme_category` for 8/40 schemes that overlap |

## Industry-level facts (no scheme_code — disconnected)

These tables **do not** relate to `scheme_code`. Do **not** force relationships; use them on Pages 1 and 4 only.

| Table | Grain | Key columns |
|-------|-------|-------------|
| `clean_aum` | Fund house × report date | `fund_house`, `report_date`, `aum_crore` |
| `clean_sip_inflows` | Month | `month`, `sip_inflow_crore` |
| `clean_folio_count` | Month | `month`, `total_folios_crore` |
| `clean_category_inflows` | Month × category | `month`, `category`, `net_inflow_crore` |
| `clean_benchmark` | Date × index | `date`, `index_name`, `close_value` |

## Date handling (recommended)

Create a **Date** table (`Calendar`) or use Auto Date/Time:

| Table | Date column | Transform in Power Query |
|-------|-------------|--------------------------|
| `clean_aum` | `report_date` | Date type |
| `clean_sip_inflows` | `month` | `Date.FromText` or `Date.StartOfMonth` |
| `clean_folio_count` | `month` | Same as SIP |
| `clean_category_inflows` | `month` | Same as SIP |
| `clean_benchmark` | `date` | Date type |
| `returns_computed` | `date` | Date type |
| `clean_transactions` | `date` | Date type |

### Optional inactive relationships to a shared `Date` table

| From | To | Column | Active |
|------|-----|--------|--------|
| `clean_sip_inflows[month]` | `Date[Date]` | month-start | No (use USERELATIONSHIP in DAX if needed) |
| `clean_benchmark[date]` | `Date[Date]` | date | No |

For **SIP vs NIFTY50 dual axis**, aggregate NIFTY50 to month in Power Query (average or month-end `close_value`) — no direct relationship required; use synchronized axis by month label.

## Relationship diagram (logical)

```
                    ┌─────────────────────┐
                    │  clean_fund_master  │
                    │   (scheme_code PK)  │
                    └──────────┬──────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
clean_performance      fund_scorecard         returns_computed
tracking_error         clean_transactions     investor_transactions_raw


  DISCONNECTED (industry / market):
  ┌────────────┐  ┌──────────────────┐  ┌─────────────────────┐
  │ clean_aum  │  │ clean_sip_inflows│  │ clean_category_inflows│
  └────────────┘  └──────────────────┘  └─────────────────────┘
  ┌──────────────────┐  ┌────────────────┐
  │clean_folio_count │  │ clean_benchmark │
  └──────────────────┘  └────────────────┘
```

## SQLite (`data/db/bluestock_mf.db`) — alternative data source

If connecting to SQLite instead of CSVs:

| Table | Rows purpose |
|-------|----------------|
| `dim_fund` | Same as `clean_fund_master` |
| `dim_category` | `scheme_code` → `scheme_category` |
| `dim_date` | Pre-built date dimension |
| `fact_aum` | Subset of AUM (no folio/category) |
| `fact_sip_inflows` | `month`, `sip_inflow_crore`, `yoy_growth_pct` |
| `fact_performance` | Same as `clean_performance` |
| `fact_transactions` | Same as `clean_transactions` (no demographics) |
| `fact_nav` | NAV history |

Relationships in SQLite mirror the scheme_code star above; industry tables still need CSV import for folio/category/benchmark.

## Verify in Power BI

1. **Model view** → Layout → confirm 5–6 active `scheme_code` relationships.
2. **No ambiguous paths** — only one active path between any two tables.
3. **Industry tables** float with no relationships (expected).
4. Run **View → Performance analyzer** after build to catch high-cardinality issues on `returns_computed`.
