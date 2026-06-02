from pathlib import Path
import pandas as pd

from scripts.live_nav_fetch import main as run_nav_pipeline

RAW_PATH = Path("data/raw/datasets")

EXPECTED_COUNT = 10


def validate_dataset_folder():

    if not RAW_PATH.exists():

        raise FileNotFoundError(
            f"Dataset folder not found: {RAW_PATH}"
        )

    csv_files = list(RAW_PATH.glob("*.csv"))

    if len(csv_files) == 0:

        print("=" * 60)
        print(
            "[datasets] No CSV files found in "
            "data/raw/datasets/"
        )
        print(
            "Continuing with MFAPI ingestion."
        )
        print("=" * 60)

        return []

    if len(csv_files) != EXPECTED_COUNT:

        print("=" * 60)
        print(
            f"Warning: Expected {EXPECTED_COUNT} CSV files "
            f"but found {len(csv_files)}"
        )
        print("=" * 60)

    return csv_files


def analyze_csv(file):

    print("\n" + "=" * 60)
    print(f"Processing: {file.name}")
    print("=" * 60)

    try:

        df = pd.read_csv(file)

        print("\nShape:")
        print(df.shape)

        print("\nData Types:")
        print(df.dtypes)

        print("\nHead:")
        print(df.head())

        print("\nMissing Values:")
        print(df.isnull().sum())

        print("\nDuplicate Rows:")
        print(df.duplicated().sum())

        numeric_cols = df.select_dtypes(
            include=["number"]
        ).columns

        if len(numeric_cols) > 0:

            negative_values = (
                df[numeric_cols] < 0
            ).sum()

            print("\nNegative Numeric Values:")
            print(negative_values)

    except Exception as e:

        print(
            f"Error processing {file.name}: {e}"
        )


def main():

    csv_files = validate_dataset_folder()

    if len(csv_files) > 0:

        for file in csv_files:
            analyze_csv(file)

    print("\n[MFAPI] Starting NAV ingestion...")

    run_nav_pipeline()

    print("\n[DONE] Day 1 data ingestion complete.")


if __name__ == "__main__":
    main()

