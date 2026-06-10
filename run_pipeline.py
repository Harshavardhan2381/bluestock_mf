"""Master pipeline runner.

This script orchestrates the ETL/analytics steps required for the capstone.
Run from the project root.
"""

from __future__ import annotations

import subprocess
from typing import List


def run_steps(steps: List[str]) -> None:
    """Run each python script path in sequence."""

    for step in steps:
        print(f"Running {step}")
        # Use the project root's python environment; scripts themselves resolve paths.
        subprocess.run(["python3", step], check=True)


def main() -> None:
    """Entry point."""

    steps = [
        "scripts/day4_performance_metrics.py",
        "scripts/day6_advanced_analytics.py",
    ]

    run_steps(steps)
    print("Pipeline completed.")


if __name__ == "__main__":
    main()

