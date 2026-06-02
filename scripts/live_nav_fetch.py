from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests


BASE_URL = "https://api.mfapi.in"
MF_BASE = f"{BASE_URL}/mf"


@dataclass(frozen=True)
class SchemeSpec:
    scheme_code: int
    label: str


KEY_SCHEMES: List[SchemeSpec] = [
    SchemeSpec(125497, "HDFC_Top_100_Direct_Growth"),
    SchemeSpec(119551, "SBI_Bluechip"),
    SchemeSpec(120503, "ICICI_Bluechip"),
    SchemeSpec(118632, "Nippon_Large_Cap"),
    SchemeSpec(119092, "Axis_Bluechip"),
    SchemeSpec(120841, "Kotak_Bluechip"),
]


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
        payload = fetch_json(url)

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
) -> pd.DataFrame:
    """
    Fetches /mf/{scheme_code} and saves the historical NAV to CSV.

    MFAPI typical shape:
      { meta: {...}, data: [{date: 'dd-mm-yyyy', nav: '...'}, ...], status: 'SUCCESS' }
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{MF_BASE}/{scheme_code}"
    payload = fetch_json(url)

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
        nav_df = pd.read_csv(nav_file)
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


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw"
    master_dir = raw_dir / "master"
    nav_dir = raw_dir / "nav_history"

    master_path = master_dir / "fund_master.csv"
    fund_master_df = fetch_fund_master(out_path=master_path)
    print(f"[fund_master] saved: {master_path} rows={len(fund_master_df)}")

    for spec in KEY_SCHEMES:
        nav_path = nav_dir / f"{spec.scheme_code}.csv"
        df = fetch_scheme_nav_history(scheme_code=spec.scheme_code, out_path=nav_path)
        print(f"[nav_history] saved: {nav_path} rows={len(df)}")

    validate_option_a(
        fund_master_path=master_path,
        nav_history_dir=nav_dir,
        expected_scheme_codes=[s.scheme_code for s in KEY_SCHEMES],
    )


if __name__ == "__main__":
    main()
