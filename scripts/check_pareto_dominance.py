from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _pareto(df: pd.DataFrame) -> pd.DataFrame:
    feasible = df[
        (df["feasible"] == True)
        & df["losses_kw"].notna()
        & df["objective_reliability"].notna()
    ].copy()
    keep: list[int] = []
    for idx, row in feasible.iterrows():
        dominated = (
            (feasible["losses_kw"] <= row["losses_kw"])
            & (feasible["objective_reliability"] <= row["objective_reliability"])
            & (
                (feasible["losses_kw"] < row["losses_kw"])
                | (feasible["objective_reliability"] < row["objective_reliability"])
            )
        ).any()
        if not dominated:
            keep.append(idx)
    return feasible.loc[keep].sort_values(["losses_kw", "objective_reliability"]).reset_index(drop=True)


def _key_set(df: pd.DataFrame) -> set[tuple[str, float, float]]:
    return {
        (str(row["open_switches"]), round(float(row["losses_kw"]), 9), round(float(row["objective_reliability"]), 9))
        for _, row in df.iterrows()
    }


def check(all_csv: Path, pareto_csv: Path | None = None) -> dict[str, object]:
    all_df = pd.read_csv(all_csv)
    if pareto_csv is None:
        inferred = all_csv.with_name(all_csv.stem.replace("_all", "_pareto") + all_csv.suffix)
        pareto_csv = inferred if inferred.exists() else all_csv
    reported = pd.read_csv(pareto_csv)
    recalculated = _pareto(all_df)

    dominated_reported = 0
    feasible = all_df[
        (all_df["feasible"] == True)
        & all_df["losses_kw"].notna()
        & all_df["objective_reliability"].notna()
    ]
    for _, row in reported.iterrows():
        dominated = (
            (feasible["losses_kw"] <= row["losses_kw"])
            & (feasible["objective_reliability"] <= row["objective_reliability"])
            & (
                (feasible["losses_kw"] < row["losses_kw"])
                | (feasible["objective_reliability"] < row["objective_reliability"])
            )
        ).any()
        dominated_reported += int(bool(dominated))

    return {
        "all_csv": str(all_csv),
        "pareto_csv": str(pareto_csv),
        "total_solutions": int(len(all_df)),
        "reported_pareto": int(len(reported)),
        "recalculated_pareto": int(len(recalculated)),
        "dominated_inside_reported": int(dominated_reported),
        "reported_matches_recalculated": _key_set(reported) == _key_set(recalculated),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica dominancia de un frente Pareto DNR.")
    parser.add_argument("all_csv", type=Path, help="Archivo *_all.csv generado por dnr optimize.")
    parser.add_argument("--pareto", type=Path, default=None, help="Archivo *_pareto.csv reportado.")
    args = parser.parse_args()

    result = check(args.all_csv, args.pareto)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
