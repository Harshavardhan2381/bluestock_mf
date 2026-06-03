from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from sqlalchemy import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_MASTER_PATH = PROJECT_ROOT / "data" / "raw" / "master" / "fund_master.csv"
RAW_NAV_DIR = PROJECT_ROOT / "data" / "raw" / "nav_history"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_NAV_COMBINED_PATH = PROCESSED_DIR / "nav_history_combined.csv"
DB_PATH = PROJECT_ROOT / "data" / "db" / "bluestock_mf.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"


@dataclass(frozen=True)
class CleanConfig:
    # keep this list conservative; only touch obvious columns.
    # if column names are missing, we fall back.
    fund_master_keep_cols: Optional[List[str]] = None


def _normalize_column_names(cols: Iterable[str]) -> List[str]:
    out = []
    for c in cols:
        s = str(c).strip()
        s = s.replace(" ", "_")
        s = re.sub(r"[^0-9a-zA-Z_]+", "_", s)
        s = re.sub(r"_+", "_", s)
        s = s.strip("_")
        out.append(s.lower())
    return out


def _coerce_float(series: pd.Series) -> pd.Series:
    # MFAPI often returns nav as string; coerce robustly.
    return pd.to_numeric(series.astype(str).str.replace(",", ""), errors="coerce")


def clean_fund_master(path: Path, cfg: CleanConfig) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Standardize column names to snake_case-ish lowercase.
    df.columns = _normalize_column_names(df.columns)

    # De-duplicate exact rows first.
    df = df.drop_duplicates()

    # Normalize common MFAPI-ish columns to our schema names.
    # We'll create the columns we need even if they don't exist in raw.
    colmap = {
        "schemecode": "scheme_code",
        "scheme_code": "scheme_code",
        "schemename": "scheme_name",
        "scheme_name": "scheme_name",
        "fund_house": "fund_house",
        "scheme_category": "scheme_category",
        "schemecategory": "scheme_category",
        "fundhouse": "fund_house",
        "fundcategory": "scheme_category",
        "isingrowth": "raw_json",
        "isingrowthoption": "raw_json",
        "isindivereinvestment": "raw_json",
        "isdividendoption": "raw_json",
    }

    # Apply direct renames when possible.
    renames = {}
    for c in df.columns:
        if c in colmap and colmap[c] != c:
            renames[c] = colmap[c]
    if renames:
        df = df.rename(columns=renames)

    # Ensure required columns exist.
    for required in ["scheme_code", "scheme_name", "fund_house", "scheme_category"]:
        if required not in df.columns:
            df[required] = None

    if "raw_json" not in df.columns:
        # Keep raw flags/unknowns in raw_json if any exist.
        extra_cols = [c for c in df.columns if c not in ["scheme_code", "scheme_name", "fund_house", "scheme_category"]]
        if extra_cols:
            df["raw_json"] = df[extra_cols].astype(str).agg(lambda r: "|".join(r.values.tolist()), axis=1)
        else:
            df["raw_json"] = None

    # Keep only schema columns.
    df = df[["scheme_code", "scheme_name", "fund_house", "scheme_category", "raw_json"]]

    return df



def clean_and_merge_nav_history(nav_dir: Path, out_path: Path) -> pd.DataFrame:
    csvs = sorted(nav_dir.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No NAV CSV files found in {nav_dir}")

    frames: List[pd.DataFrame] = []

    for p in csvs:
        df = pd.read_csv(p)

        # Normalize columns
        df.columns = _normalize_column_names(df.columns)

        # expected columns: date, nav; also metadata might exist
        if "date" not in df.columns:
            # common alternative
            for alt in ["nav_date", "navdate", "as_on_date"]:
                if alt in df.columns:
                    df = df.rename(columns={alt: "date"})
                    break

        if "nav" not in df.columns:
            for alt in ["nav_value", "navvalue", "navamount"]:
                if alt in df.columns:
                    df = df.rename(columns={alt: "nav"})
                    break

        if "date" in df.columns:
            # Dates are expected to be in YYYY-MM-DD format in this project.
            df["date"] = pd.to_datetime(df["date"], errors="coerce")






        if "nav" in df.columns:
            df["nav"] = _coerce_float(df["nav"])

        # Remove invalid rows
        if "date" in df.columns and "nav" in df.columns:
            df = df.dropna(subset=["date", "nav"])

        # Try to infer scheme code
        if "scheme_code" not in df.columns:
            # If file name is code.csv
            m = re.match(r"(\d+)\.csv$", p.name)
            if m:
                df["scheme_code"] = int(m.group(1))

        frames.append(df)

    merged = pd.concat(frames, ignore_index=True)

    # De-duplicate on (scheme_code, date, nav) if columns exist
    subset = [c for c in ["scheme_code", "date", "nav"] if c in merged.columns]
    if len(subset) >= 2:
        merged = merged.drop_duplicates(subset=subset)

    # Sort chronologically
    if "date" in merged.columns:
        sort_cols = [c for c in ["scheme_code", "date"] if c in merged.columns]
        merged = merged.sort_values(sort_cols)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    return merged


# Note: we no longer use the older load_into_sqlite() placeholder approach.
# Day2 now performs schema creation + loading directly in main().




def clean_transactions(transactions_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(transactions_csv)

    # Normalize columns
    df.columns = _normalize_column_names(df.columns)

    # expected: investor_id, transaction_date, amfi_code, transaction_type, amount_inr, state, city, ... , kyc_status
    rename_map = {
        "transaction_date": "date",
        "transactiondate": "date",
        "amfi_code": "scheme_code",
        "schemecode": "scheme_code",
        "amount_inr": "amount_inr",
    }

    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # Canonical transaction_type mapping
    if "transaction_type" not in df.columns:
        # fallback
        for alt in ["transactiontype", "type"]:
            if alt in df.columns:
                df = df.rename(columns={alt: "transaction_type"})
                break

    tx = df.copy()
    if "transaction_type" in tx.columns:
        tx["transaction_type"] = (
            tx["transaction_type"]
            .astype(str)
            .str.strip()
            .replace(
                {
                    "SIP": "SIP",
                    "sip": "SIP",
                    "Lumpsum": "Lumpsum",
                    "lumpsum": "Lumpsum",
                    "Redemption": "Redemption",
                    "redemption": "Redemption",
                    "Redemption/Withdrawal": "Redemption",
                }
            )
        )

    # Standardize kyc_status/payment_mode
    for col in ["kyc_status", "payment_mode"]:
        if col not in tx.columns:
            tx[col] = None

    if "date" not in tx.columns:
        raise ValueError("transactions CSV missing transaction_date")

    tx["date"] = pd.to_datetime(tx["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # amount
    if "amount_inr" not in tx.columns:
        for alt in ["amount", "amount_inr_inferred"]:
            if alt in tx.columns:
                tx = tx.rename(columns={alt: "amount_inr"})
                break

    tx["amount_inr"] = pd.to_numeric(tx["amount_inr"], errors="coerce")

    # Filter invalid
    tx = tx.dropna(subset=["investor_id", "scheme_code", "date", "amount_inr"])
    tx = tx[tx["amount_inr"] > 0]

    # Ensure scheme_code integer
    tx["scheme_code"] = pd.to_numeric(tx["scheme_code"], errors="coerce").astype("Int64")
    tx = tx.dropna(subset=["scheme_code"])
    tx["scheme_code"] = tx["scheme_code"].astype(int)

    # Create transaction_id surrogate
    tx["transaction_id"] = (
        tx["investor_id"].astype(str)
        + "|"
        + tx["date"].astype(str)
        + "|"
        + tx["scheme_code"].astype(str)
        + "|"
        + tx["amount_inr"].round(2).astype(str)
        + "|"
        + tx["transaction_type"].fillna("").astype(str)
    )

    # Return only needed columns
    keep_cols = [
        "transaction_id",
        "investor_id",
        "scheme_code",
        "date",
        "amount_inr",
        "transaction_type",
        "kyc_status",
        "payment_mode",
    ]
    for c in keep_cols:
        if c not in tx.columns:
            tx[c] = None

    tx = tx[keep_cols].drop_duplicates(subset=["transaction_id"])
    return tx


def clean_performance(performance_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(performance_csv)
    df.columns = _normalize_column_names(df.columns)

    if "amfi_code" in df.columns:
        df = df.rename(columns={"amfi_code": "scheme_code"})
    if "scheme_code" not in df.columns:
        raise ValueError("performance CSV missing amfi_code/scheme_code")

    df["scheme_code"] = pd.to_numeric(df["scheme_code"], errors="coerce")
    df = df.dropna(subset=["scheme_code"])
    df["scheme_code"] = df["scheme_code"].astype(int)

    numeric_cols = [
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "alpha",
        "beta",
        "sharpe_ratio",
        "sortino_ratio",
        "std_dev_ann_pct",
        "max_drawdown_pct",
        "aum_crore",
        "expense_ratio_pct",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = None

    # Plausibility filters
    # Remove extreme sharpe_ratio outliers
    if "sharpe_ratio" in df.columns:
        df = df[(df["sharpe_ratio"].isna()) | (df["sharpe_ratio"].abs() <= 10)]

    # Expense ratio: keep 0..10 (conservative)
    if "expense_ratio_pct" in df.columns:
        df = df[(df["expense_ratio_pct"].isna()) | ((df["expense_ratio_pct"] >= 0) & (df["expense_ratio_pct"] <= 10))]

    keep_cols = [
        "scheme_code",
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "alpha",
        "beta",
        "sharpe_ratio",
        "sortino_ratio",
        "std_dev_ann_pct",
        "max_drawdown_pct",
        "aum_crore",
        "expense_ratio_pct",
        "morningstar_rating",
        "risk_grade",
    ]
    for c in keep_cols:
        if c not in df.columns:
            df[c] = None

    df = df[keep_cols].copy()
    if "morningstar_rating" in df.columns:
        df["morningstar_rating"] = pd.to_numeric(df["morningstar_rating"], errors="coerce")
    df["computed_on"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")

    df = df.drop_duplicates(subset=["scheme_code"])
    return df


def main() -> None:
    cfg = CleanConfig(fund_master_keep_cols=None)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    processed_timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")

    print("[Day2] Cleaning fund_master...")
    fund_master_df = clean_fund_master(RAW_MASTER_PATH, cfg)
    fund_master_out = PROCESSED_DIR / "clean_fund_master.csv"
    fund_master_df.assign(source_file=str(RAW_MASTER_PATH.name), processed_timestamp=processed_timestamp).to_csv(
        fund_master_out, index=False
    )
    print(f"[Day2] fund_master cleaned rows={len(fund_master_df)} cols={len(fund_master_df.columns)}")

    print("[Day2] Cleaning + merging nav_history...")
    nav_df = clean_and_merge_nav_history(RAW_NAV_DIR, PROCESSED_NAV_COMBINED_PATH)
    # attach metadata + write clean_nav_history
    nav_df_out = PROCESSED_DIR / "clean_nav_history.csv"
    nav_df.assign(source_file="nav_history/*.csv", processed_timestamp=processed_timestamp).to_csv(nav_df_out, index=False)
    print(f"[Day2] nav_history merged rows={len(nav_df)} cols={len(nav_df.columns)}")

    # Load raw datasets
    raw_transactions_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "08_investor_transactions.csv"
    raw_performance_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "07_scheme_performance.csv"
    raw_aum_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "03_aum_by_fund_house.csv"
    raw_sip_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "04_monthly_sip_inflows.csv"
    raw_cat_inflows_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "05_category_inflows.csv"
    raw_folio_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "06_industry_folio_count.csv"
    raw_holdings_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "09_portfolio_holdings.csv"
    raw_benchmark_csv = PROJECT_ROOT / "data" / "raw" / "datasets" / "10_benchmark_indices.csv"

    print("[Day2] Cleaning investor transactions...")
    transactions_df = clean_transactions(raw_transactions_csv)
    clean_transactions_path = PROCESSED_DIR / "clean_transactions.csv"
    transactions_df.assign(source_file=raw_transactions_csv.name, processed_timestamp=processed_timestamp).to_csv(
        clean_transactions_path, index=False
    )

    print("[Day2] Cleaning scheme performance...")
    performance_df = clean_performance(raw_performance_csv)
    clean_performance_path = PROCESSED_DIR / "clean_performance.csv"
    performance_df.assign(source_file=raw_performance_csv.name, processed_timestamp=processed_timestamp).to_csv(
        clean_performance_path, index=False
    )

    # --- Additional cleaned outputs (rubric) ---
    # AUM
    aum_df = pd.read_csv(raw_aum_csv)
    aum_df.columns = _normalize_column_names(aum_df.columns)
    for c in ["aum_crore", "aum_lakh_crore"]:
        if c in aum_df.columns:
            aum_df[c] = pd.to_numeric(aum_df[c], errors="coerce")
    if "aum_crore" not in aum_df.columns and "aum_lakh_crore" in aum_df.columns:
        # if only lakh crores exist, treat as crore-equivalent missing conversion was unknown; fallback to aum_lakh_crore
        aum_df["aum_crore"] = aum_df["aum_lakh_crore"]
    if "date" in aum_df.columns:
        aum_df["date"] = pd.to_datetime(aum_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    elif "report_date" in aum_df.columns:
        aum_df["date"] = pd.to_datetime(aum_df["report_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        # dataset shows date? ensure report_date
        aum_df["date"] = None
    # dataset 03_aum_by_fund_house.csv has no category; keep category NULL to satisfy fact_aum grain
    aum_clean = aum_df[["fund_house", "aum_crore", "date"]].rename(columns={"date": "report_date"})
    aum_clean["category"] = None

    clean_aum_path = PROCESSED_DIR / "clean_aum.csv"
    aum_clean.assign(source_file=raw_aum_csv.name, processed_timestamp=processed_timestamp).to_csv(clean_aum_path, index=False)

    # SIP inflows
    sip_df = pd.read_csv(raw_sip_csv)
    sip_df.columns = _normalize_column_names(sip_df.columns)
    if "month" in sip_df.columns:
        sip_df["month"] = sip_df["month"].astype(str).str.strip()
    if "sip_inflow_crore" in sip_df.columns:
        sip_df["sip_inflow_crore"] = pd.to_numeric(sip_df["sip_inflow_crore"], errors="coerce")
    if "yoy_growth_pct" in sip_df.columns:
        sip_df["yoy_growth_pct"] = pd.to_numeric(sip_df["yoy_growth_pct"], errors="coerce")
    clean_sip_path = PROCESSED_DIR / "clean_sip_inflows.csv"
    sip_df.assign(source_file=raw_sip_csv.name, processed_timestamp=processed_timestamp).to_csv(clean_sip_path, index=False)

    # Category inflows
    cat_in_df = pd.read_csv(raw_cat_inflows_csv)
    cat_in_df.columns = _normalize_column_names(cat_in_df.columns)
    if "month" in cat_in_df.columns:
        cat_in_df["month"] = cat_in_df["month"].astype(str).str.strip()
    if "net_inflow_crore" in cat_in_df.columns:
        cat_in_df["net_inflow_crore"] = pd.to_numeric(cat_in_df["net_inflow_crore"], errors="coerce")
    # keep consistent name
    if "category" not in cat_in_df.columns:
        cat_in_df["category"] = cat_in_df.get("category", None)
    clean_cat_path = PROCESSED_DIR / "clean_category_inflows.csv"
    cat_in_df.assign(source_file=raw_cat_inflows_csv.name, processed_timestamp=processed_timestamp).to_csv(
        clean_cat_path, index=False
    )

    # Holdings
    holdings_df = pd.read_csv(raw_holdings_csv)
    holdings_df.columns = _normalize_column_names(holdings_df.columns)
    for col in ["weight_pct", "market_value_cr", "current_price_inr"]:
        if col in holdings_df.columns:
            holdings_df[col] = pd.to_numeric(holdings_df[col], errors="coerce")
    if "stock_name" in holdings_df.columns:
        holdings_df["stock_name"] = holdings_df["stock_name"].astype(str).str.strip()
    if "stock_symbol" in holdings_df.columns:
        holdings_df["stock_symbol"] = holdings_df["stock_symbol"].astype(str).str.strip()
    if "portfolio_date" in holdings_df.columns:
        holdings_df["portfolio_date"] = pd.to_datetime(holdings_df["portfolio_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    clean_holdings_path = PROCESSED_DIR / "clean_holdings.csv"
    holdings_df.assign(source_file=raw_holdings_csv.name, processed_timestamp=processed_timestamp).to_csv(
        clean_holdings_path, index=False
    )

    # Industry folio count
    folio_df = pd.read_csv(raw_folio_csv)
    folio_df.columns = _normalize_column_names(folio_df.columns)
    if "month" in folio_df.columns:
        folio_df["month"] = folio_df["month"].astype(str).str.strip()
    for col in ["total_folios_crore", "equity_folios_crore", "debt_folios_crore", "hybrid_folios_crore", "others_folios_crore"]:
        if col in folio_df.columns:
            folio_df[col] = pd.to_numeric(folio_df[col], errors="coerce")
    clean_folio_path = PROCESSED_DIR / "clean_folio_count.csv"
    folio_df.assign(source_file=raw_folio_csv.name, processed_timestamp=processed_timestamp).to_csv(
        clean_folio_path, index=False
    )

    # Benchmark
    benchmark_df = pd.read_csv(raw_benchmark_csv)
    benchmark_df.columns = _normalize_column_names(benchmark_df.columns)
    if "date" in benchmark_df.columns:
        benchmark_df["date"] = pd.to_datetime(benchmark_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "close_value" in benchmark_df.columns:
        benchmark_df["close_value"] = pd.to_numeric(benchmark_df["close_value"], errors="coerce")
    benchmark_df = benchmark_df.drop_duplicates(subset=["date", "index_name"])
    clean_benchmark_path = PROCESSED_DIR / "clean_benchmark.csv"
    benchmark_df.assign(source_file=raw_benchmark_csv.name, processed_timestamp=processed_timestamp).to_csv(
        clean_benchmark_path, index=False
    )

    print("[Day2] Loading SQLite...")
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"SQL schema not found: {SCHEMA_PATH}")

    if DB_PATH.exists():
        DB_PATH.unlink()

    engine = create_engine(f"sqlite:///{DB_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        for stmt in schema_sql.split(";"):
            s = stmt.strip()
            if s:
                conn.exec_driver_sql(s + ";")

    # dim_fund
    dim_fund_df = fund_master_df[["scheme_code", "scheme_name", "fund_house", "scheme_category", "raw_json"]].copy()
    dim_fund_df.to_sql("dim_fund", engine, if_exists="append", index=False)

    # dim_category
    dim_category_df = fund_master_df[["scheme_code", "scheme_category"]].copy()
    dim_category_df.to_sql("dim_category", engine, if_exists="append", index=False)

    # fact_nav: ensure fund_house/scheme_category/scheme_name are present
    # nav history already carries these columns from raw NAV CSVs in this project.
    if "fund_house" not in nav_df.columns or "scheme_category" not in nav_df.columns or "scheme_name" not in nav_df.columns:
        dim_lookup = fund_master_df[["scheme_code", "fund_house", "scheme_category", "scheme_name"]].copy()
        nav_df = nav_df.merge(dim_lookup, on="scheme_code", how="left")

    fact_nav_df = nav_df[["scheme_code", "date", "nav", "fund_house", "scheme_category", "scheme_name"]].copy()
    fact_nav_df.to_sql("fact_nav", engine, if_exists="append", index=False)


    # fact_transactions
    transactions_df.to_sql("fact_transactions", engine, if_exists="append", index=False)

    # fact_performance
    performance_df.to_sql("fact_performance", engine, if_exists="append", index=False)

    # fact_aum
    aum_clean = aum_clean.rename(columns={"aum_crore": "aum_crore"})
    fact_aum_df = aum_clean[["fund_house", "category", "aum_crore", "report_date"]].copy()
    fact_aum_df.to_sql("fact_aum", engine, if_exists="append", index=False)

    # fact_sip_inflows (warehouse table) + dim_date
    # Create fact_sip_inflows dynamically to match queries.sql without changing rubric core tables.
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS fact_sip_inflows (month TEXT, sip_inflow_crore REAL, yoy_growth_pct REAL);"
        )
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_sip_month ON fact_sip_inflows(month);")

    sip_warehouse = sip_df[["month", "sip_inflow_crore", "yoy_growth_pct"]].copy()
    sip_warehouse.to_sql("fact_sip_inflows", engine, if_exists="append", index=False)

    # dim_date: from all available date fields
    date_values = set()
    if "date" in nav_df.columns:
        date_values |= set(pd.to_datetime(nav_df["date"], errors="coerce").dropna().dt.strftime("%Y-%m-%d").tolist())
    if "date" in transactions_df.columns:
        date_values |= set(pd.to_datetime(transactions_df["date"], errors="coerce").dropna().dt.strftime("%Y-%m-%d").tolist())
    if "report_date" in aum_clean.columns:
        date_values |= set(pd.to_datetime(aum_clean["report_date"], errors="coerce").dropna().dt.strftime("%Y-%m-%d").tolist())

    # Build dim_date rows
    dlist = sorted(date_values)
    dim_date_rows = []
    for ds in dlist:
        dt = pd.to_datetime(ds)
        dim_date_rows.append(
            {
                "date_key": ds,
                "year": int(dt.year),
                "month": int(dt.month),
                "quarter": int((dt.month - 1) // 3 + 1),
                "weekday": dt.strftime("%A"),
            }
        )
    dim_date_df = pd.DataFrame(dim_date_rows)
    if not dim_date_df.empty:
        dim_date_df.to_sql("dim_date", engine, if_exists="append", index=False)

    print(f"[Day2] SQLite DB created: {DB_PATH}")


if __name__ == "__main__":
    main()


