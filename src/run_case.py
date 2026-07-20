from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify representative DNR results from consolidated CSV files.")
    parser.add_argument("case", choices=["five_node", "ieee33", "real_system_anonymized"])
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    table = root / "results" / args.case / "representative_solutions.csv"
    df = pd.read_csv(table)
    cols = [
        "solution_type",
        "open_switches",
        "P_loss_kW",
        "Vmin_pu",
        "SAIDI_h_user_year",
        "SAIFI_int_user_year",
        "ENS_MWh_year",
        "feasible",
        "operationally_feasible",
    ]
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
