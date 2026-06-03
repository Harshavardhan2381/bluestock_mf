# Data Dictionary (Star Schema)

This project builds a small star-schema in SQLite for NAV analytics.

## dim_fund
Fund/scheme descriptive attributes.

| Column | Type | Description |
|---|---|---|
| scheme_code | INTEGER | Unique AMFI scheme code |
| scheme_name | TEXT | Human-readable scheme name |
| fund_house | TEXT | Fund house / AMC name |
| scheme_category | TEXT | Scheme category |
| raw_json | TEXT | Optional raw/flags captured at ingestion |

## dim_category
Convenience dimension for category lookups (one row per scheme code).

| Column | Type | Description |
|---|---|---|
| scheme_code | INTEGER | Unique AMFI scheme code |
| scheme_category | TEXT | Category name |

## fact_nav
NAV fact table (one row per scheme per NAV date).

| Column | Type | Description |
|---|---|---|
| scheme_code | INTEGER | FK to dim_fund.scheme_code |
| date | DATE/TEXT | NAV date (stored as TEXT in SQLite) |
| nav | REAL | Net asset value |
| fund_house | TEXT | Denormalized fund house (copied from dim_fund at load time) |
| scheme_category | TEXT | Denormalized scheme category (copied from dim_fund at load time) |
| scheme_name | TEXT | Denormalized scheme name (copied from dim_fund at load time) |

## fact_transactions
Investor-level transaction facts (one row per transaction).

| Column | Type | Description |
|---|---|---|
| transaction_id | TEXT (PK) | Surrogate id derived from investor_id/date/scheme_code/amount/type |
| investor_id | TEXT | Investor identifier |
| scheme_code | INTEGER | FK to dim_fund.scheme_code |
| date | DATE/TEXT | Transaction date (YYYY-MM-DD) |
| amount_inr | REAL | Transaction amount in INR |
| transaction_type | TEXT | Type (SIP, Lumpsum, Redemption, etc.) |
| kyc_status | TEXT | KYC status at transaction time (if available) |
| payment_mode | TEXT | Payment mode (if available) |

## fact_performance
Scheme performance snapshot (latest row from `07_scheme_performance.csv` in this dataset).

| Column | Type | Description |
|---|---|---|
| scheme_code | INTEGER (PK) | FK to dim_fund.scheme_code |
| return_1yr_pct | REAL | 1Y return % |
| return_3yr_pct | REAL | 3Y return % |
| return_5yr_pct | REAL | 5Y return % |
| benchmark_3yr_pct | REAL | 3Y benchmark return % |
| alpha | REAL | Jensen's alpha |
| beta | REAL | Beta |
| sharpe_ratio | REAL | Sharpe ratio |
| sortino_ratio | REAL | Sortino ratio |
| std_dev_ann_pct | REAL | Annualized std dev |
| max_drawdown_pct | REAL | Max drawdown % |
| aum_crore | REAL | AUM in crores |
| expense_ratio_pct | REAL | Expense ratio % |
| morningstar_rating | INTEGER | Morningstar rating |
| risk_grade | TEXT | Risk grade |
| computed_on | DATE/TEXT | Computation timestamp |


