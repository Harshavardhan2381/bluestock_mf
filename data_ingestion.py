from __future__ import annotations

from pathlib import Path

from scripts.etl_pipeline import load_all_datasets
from scripts.live_nav_fetch import KEY_SCHEMES, main as nav_fetch_main
from scripts.live_nav_fetch import validate_option_a


def main() -> None:
    project_root = Path(__file__).resolve().parent
    datasets_dir = project_root / "data" / "raw" / "datasets"
    raw_dir = project_root / "data" / "raw"

    # 1) Load provided datasets (if any)
    load_all_datasets(datasets_dir)

    # 2) Fetch MFAPI raw data (fund master + key scheme NAV histories)
    nav_fetch_main()

    # 3) Validate AMFI codes — Option A (only validate the 6 key schemes)
    validate_option_a(
        fund_master_path=raw_dir / "master" / "fund_master.csv",
        nav_history_dir=raw_dir / "nav_history",
