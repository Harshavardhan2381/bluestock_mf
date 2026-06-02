from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd


def inspect_csv_dataset(csv_path: Path) -> Dict[str, object]:
    df = pd.read_csv(csv_path)
    out: Dict[str, object] = {
        "file": str(csv_path),
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str).to_dict(),
        "head": df.head().to_string(index=False),
        "missing_values_total": int(df.isna().sum().sum()),
        "missing_values_by_column_top10": df.isna().sum().sort_values(ascending=False).head(10).to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
    }

    # Basic numeric anomaly: negative values
    numeric_cols = df.select_dtypes(include="number").columns
    negative_counts = {}
    for col in numeric_cols:
        neg_count = int((df[col] < 0).sum())
        if neg_count > 0:
            negative_counts[col] = neg_count
    out["negative_counts_by_column"] = negative_counts

    return out


def load_all_datasets(datasets_dir: Path) -> List[Dict[str, object]]:
    csv_paths = sorted(datasets_dir.glob("*.csv"))
    results: List[Dict[str, object]] = []

    if not csv_paths:
        print(f"[datasets] No CSV files found in {datasets_dir}. Continuing with MFAPI ingestion.")
        return results

    print(f"[datasets] Found {len(csv_paths)} CSV files. Inspecting...")

    for p in csv_paths:
        print(f"\n=== Inspecting {p.name} ===")
        r = inspect_csv_dataset(p)

        print(f"shape: {r['shape']}")
        print(f"dtypes: {r['dtypes']}")
        print("head:")
        print(r["head"])
        print(f"missing_values_total: {r['missing_values_total']}")
        print(f"missing_values_by_column_top10: {r['missing_values_by_column_top10']}")
        print(f"duplicate_rows: {r['duplicate_rows']}")

        if r["negative_counts_by_column"]:
            print(f"negative_counts_by_column: {r['negative_counts_by_column']}")
        else:
            print("negative_counts_by_column: none")

        results.append(r)

    return results


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    datasets_dir = project_root / "data" / "raw" / "datasets"
    load_all_datasets(datasets_dir)


if __name__ == "__main__":
    main()
