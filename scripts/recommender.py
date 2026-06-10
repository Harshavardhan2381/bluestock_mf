import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sharpe = pd.read_csv(PROJECT_ROOT / "data/processed/sharpe_values.csv")
    perf = pd.read_csv(PROJECT_ROOT / "data/processed/clean_performance.csv")

    df = sharpe.merge(
        perf[["scheme_code", "risk_grade"]],
        on="scheme_code",
        how="left",
    )

    def recommend_funds(risk_appetite: str) -> pd.DataFrame:
        risk_map = {
            "Low": ["Low"],
            "Moderate": ["Moderate"],
            "High": ["High", "Very High", "Moderately High"],
        }

        subset = df[df["risk_grade"].isin(risk_map[risk_appetite])]

        top3 = (
            subset.sort_values("sharpe_ratio", ascending=False)
            .head(3)
        )

        return top3[["scheme_code", "scheme_name", "risk_grade", "sharpe_ratio"]]

    print("\nLOW RISK")
    print(recommend_funds("Low"))

    print("\nMODERATE RISK")
    print(recommend_funds("Moderate"))

    print("\nHIGH RISK")
    print(recommend_funds("High"))


if __name__ == "__main__":
    main()

