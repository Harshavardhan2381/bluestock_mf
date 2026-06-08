#!/usr/bin/env python3
"""Validate Power BI KPI expected values against processed CSVs."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas required. Run: pip install pandas")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

# Rough expected ranges from capstone spec (for sanity check)
EXPECTED = {
    "aum_crore_latest": (6_000_000, 8_500_000),  # ~62–81 lakh crore
    "sip_latest_cr": (30_000, 32_000),
    "folios_latest_cr": (25.0, 27.0),
    "schemes_performance": (30, 2_000),
    "yoy_sip_pct": (10.0, 25.0),
}


def in_range(value: float, bounds: tuple[float, float]) -> bool:
    lo, hi = bounds
    return lo <= value <= hi


def main() -> int:
    errors: list[str] = []

    aum = pd.read_csv(PROCESSED / "clean_aum.csv")
    aum["report_date"] = pd.to_datetime(aum["report_date"])
    latest_aum_date = aum["report_date"].max()
    total_aum = aum.loc[aum["report_date"] == latest_aum_date, "aum_crore"].sum()

    sip = pd.read_csv(PROCESSED / "clean_sip_inflows.csv")
    sip["month"] = pd.to_datetime(sip["month"])
    latest_sip_month = sip["month"].max()
    latest_sip = sip.loc[sip["month"] == latest_sip_month, "sip_inflow_crore"].iloc[0]

    folio = pd.read_csv(PROCESSED / "clean_folio_count.csv")
    folio["month"] = pd.to_datetime(folio["month"])
    latest_folio_month = folio["month"].max()
    latest_folios = folio.loc[folio["month"] == latest_folio_month, "total_folios_crore"].iloc[0]

    perf = pd.read_csv(PROCESSED / "clean_performance.csv")
    scheme_count = perf["scheme_code"].nunique()

    sip_sorted = sip.sort_values("month")
    curr_sip = sip_sorted.iloc[-1]["sip_inflow_crore"]
    prev_sip = sip_sorted.iloc[-13]["sip_inflow_crore"]
    yoy_pct = (curr_sip - prev_sip) / prev_sip * 100

    print("=" * 60)
    print("Bluestock MF — KPI Validation (from CSVs)")
    print("=" * 60)
    print(f"Total AUM (latest {latest_aum_date.date()}): {total_aum:,.2f} Cr")
    print(f"  ({total_aum / 100_000:,.2f} lakh crore)")
    print(f"Total SIP ({latest_sip_month.strftime('%Y-%m')}): {latest_sip:,.2f} Cr")
    print(f"Total Folios ({latest_folio_month.strftime('%Y-%m')}): {latest_folios:.2f} Cr")
    print(f"Total Schemes (clean_performance): {scheme_count}")
    print(f"YoY SIP Growth: {yoy_pct:.2f}%")
    print()

    checks = [
        ("AUM latest", total_aum, EXPECTED["aum_crore_latest"]),
        ("SIP latest", latest_sip, EXPECTED["sip_latest_cr"]),
        ("Folios latest", latest_folios, EXPECTED["folios_latest_cr"]),
        ("Schemes", scheme_count, EXPECTED["schemes_performance"]),
        ("YoY SIP %", yoy_pct, EXPECTED["yoy_sip_pct"]),
    ]

    print("Range checks:")
    for name, val, bounds in checks:
        ok = in_range(val, bounds)
        status = "OK" if ok else "OUT OF RANGE"
        print(f"  [{status}] {name}: {val:,.2f} (expected {bounds[0]:,.0f}–{bounds[1]:,.0f})")
        if not ok:
            errors.append(name)

    # Required files
    required = [
        "clean_aum.csv",
        "clean_sip_inflows.csv",
        "clean_category_inflows.csv",
        "clean_folio_count.csv",
        "clean_transactions.csv",
        "clean_performance.csv",
        "fund_scorecard.csv",
        "returns_computed.csv",
        "tracking_error.csv",
    ]
    print()
    print("Required CSV files:")
    for fname in required:
        path = PROCESSED / fname
        exists = path.exists()
        print(f"  [{'OK' if exists else 'MISSING'}] {fname}")
        if not exists:
            errors.append(f"missing:{fname}")

    print()
    if errors:
        print(f"FAILED: {len(errors)} issue(s)")
        return 1
    print("PASSED: All KPIs in range and required files present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
