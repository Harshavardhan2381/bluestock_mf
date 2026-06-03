from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests



BASE_URL = "https://api.mfapi.in"
MF_BASE = f"{BASE_URL}/mf"


def load_scheme_master(master_csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(master_csv_path)
    # normalize column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    required = {"scheme_code", "scheme_name", "category"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"selected_schemes.csv missing required columns: {sorted(missing)}. "
            f"Found columns: {sorted(df.columns.tolist())}"
        )

    df["scheme_code"] = pd.to_numeric(df["scheme_code"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["scheme_code"]).copy()
    df["scheme_code"] = df["scheme_code"].astype(int)

    # De-dupe by code
    df = df.drop_duplicates(subset=["scheme_code"]).reset_index(drop=True)
    return df



def _safe_filename(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in s)


def fetch_json(url: str, *, timeout_s: int = 60) -> Dict[str, Any]:
    resp = requests.get(url, timeout=timeout_s)
    resp.raise_for_status()
    return resp.json()


def fetch_fund_master(
    *,
    out_path: Path,
    limit: int = 1000,
    sleep_s: float = 0.25,
    max_pages: Optional[int] = None,
) -> pd.DataFrame:
    """
    Fetches MFAPI /mf endpoint with pagination and saves fund_master.csv.

    Expected fields include schemeCode, scheme_name / schemeName, fund_house, etc.
    We keep the raw JSON fields but normalize some common names later in ETL.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict[str, Any]] = []
    offset = 0
    page = 0

    while True:
        if max_pages is not None and page >= max_pages:
            break

        url = f"{MF_BASE}?limit={limit}&offset={offset}"

        success = False
        last_exc: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                payload = fetch_json(url)
                success = True
                break
            except requests.exceptions.RequestException as e:
                last_exc = e
                print(
                    f"[fund_master retry] page={page + 1} attempt={attempt} error={e}"
                )
                import time as _time
                _time.sleep(2 * attempt)




        if not success:
            print(f"[fund_master skipped] offset={offset} error={last_exc}")
            break


        # MFAPI typically returns a list for /mf. If it returns dict, handle gracefully.
        if isinstance(payload, dict):
            rows = payload.get("data") or payload.get("result") or []
        else:
            rows = payload

        if not rows:
            break

        all_rows.extend(rows)
        page += 1

        offset += limit
        if sleep_s:
            import time

            time.sleep(sleep_s)

        print(f"[fund_master] page={page} fetched={len(rows)} total={len(all_rows)}")

    df = pd.DataFrame(all_rows)
    df.to_csv(out_path, index=False)
    return df


def fetch_scheme_nav_history(
    *,
    scheme_code: int,
    out_path: Path,
    timeout_s: int = 60,
) -> pd.DataFrame:

    """
    Fetches /mf/{scheme_code} and saves the historical NAV to CSV.

    MFAPI typical shape:
      { meta: {...}, data: [{date: 'dd-mm-yyyy', nav: '...'}, ...], status: 'SUCCESS' }
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{MF_BASE}/{scheme_code}"
    payload = fetch_json(url, timeout_s=timeout_s)


    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    data = payload.get("data", []) if isinstance(payload, dict) else payload

    if not isinstance(data, list):
        raise ValueError(f"Unexpected NAV history shape for scheme_code={scheme_code}: {type(data)}")

    nav_df = pd.DataFrame(data)

    if nav_df.empty:
        nav_df.to_csv(out_path, index=False)
        return nav_df

    if "date" in nav_df.columns:
        nav_df["date"] = pd.to_datetime(nav_df["date"], format="%d-%m-%Y", errors="coerce")

    if "nav" in nav_df.columns:
        nav_df["nav"] = nav_df["nav"].astype(float)

    # Add metadata columns where available
    nav_df["scheme_code"] = meta.get("scheme_code", scheme_code)
    nav_df["fund_house"] = meta.get("fund_house")
    nav_df["scheme_category"] = meta.get("scheme_category")
    nav_df["scheme_name"] = meta.get("scheme_name")

    nav_df = nav_df.sort_values("date", ascending=True)
    nav_df.to_csv(out_path, index=False)
    return nav_df


def validate_option_a(
    *,
    fund_master_path: Path,
    nav_history_dir: Path,
    expected_scheme_codes: Iterable[int],
) -> Dict[str, Any]:
    """
    Option A validation (Day 1):
    - Validate each expected scheme code exists in fund_master.csv
    - Validate each expected scheme has a corresponding nav_history CSV present & non-empty
    """
    fund_master = pd.read_csv(fund_master_path)

    # MFAPI field naming: schemeCode or scheme_code
    if "schemeCode" in fund_master.columns:
        master_codes = set(fund_master["schemeCode"].dropna().astype(int).tolist())
        detected_col = "schemeCode"
    elif "scheme_code" in fund_master.columns:
        master_codes = set(fund_master["scheme_code"].dropna().astype(int).tolist())
        detected_col = "scheme_code"
    else:
        master_codes = set()
        detected_col = None

    missing_in_master = sorted(set(expected_scheme_codes) - master_codes)

    missing_nav_files: List[int] = []
    empty_nav_files: List[int] = []

    for code in expected_scheme_codes:
        nav_file = nav_history_dir / f"{code}.csv"
        if not nav_file.exists():
            missing_nav_files.append(code)
            continue
        try:
            nav_df = pd.read_csv(nav_file)
        except pd.errors.EmptyDataError:
            empty_nav_files.append(code)
            continue
        if nav_df.empty:
            empty_nav_files.append(code)

    summary: Dict[str, Any] = {
        "expected_scheme_codes": sorted(list(expected_scheme_codes)),

        "master_scheme_code_column_detected": detected_col,
        "missing_in_fund_master": missing_in_master,
        "missing_nav_files": missing_nav_files,
        "empty_nav_files": empty_nav_files,
    }

    print("[AMFI CODE VALIDATION - Option A]")
    print(summary)

    return summary


def fetch_with_retry(fn, *, max_retries: int = 3, sleep_s: float = 1.0):
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < max_retries:
                time.sleep(sleep_s * attempt)
            else:
                raise

    # should not reach
    if last_err:
        raise last_err
    raise RuntimeError("fetch_with_retry failed with unknown error")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw"
    master_dir = raw_dir / "master"
    nav_dir = raw_dir / "nav_history"

    # 1) fetch fund_master (for validation)
    master_path = master_dir / "fund_master.csv"

    # Cap pages to keep ingestion stable + fast.
    # Selected schemes are a small subset; we don't need the entire universe.
    fund_master_df = fetch_fund_master(out_path=master_path, max_pages=40)

    print(f"[fund_master] saved: {master_path} rows={len(fund_master_df)}")

    # 2) load curated scheme universe
    scheme_master_path = master_dir / "selected_schemes.csv"
    scheme_master = load_scheme_master(scheme_master_path)
    print(f"[scheme_master] loaded: {scheme_master_path} rows={len(scheme_master)}")

    expected_codes = scheme_master["scheme_code"].tolist()

    # 3) fetch NAV for each scheme with rate limiting + retry
    for _, row in scheme_master.iterrows():
        code = int(row["scheme_code"])
        nav_path = nav_dir / f"{code}.csv"

        def _do_fetch():
            return fetch_scheme_nav_history(scheme_code=code, out_path=nav_path)

        df = fetch_with_retry(_do_fetch, max_retries=3, sleep_s=1.0)
        print(f"[nav_history] saved: {nav_path} rows={len(df)}")

        # rate limiting to avoid API throttling
        time.sleep(0.3)

    validate_option_a(
        fund_master_path=master_path,
        nav_history_dir=nav_dir,
        expected_scheme_codes=expected_codes,
    )



if __name__ == "__main__":
    main()
