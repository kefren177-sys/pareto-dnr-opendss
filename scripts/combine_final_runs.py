from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dnr.selection import best_by_reliability_then_losses_df

FINAL_ROOT = PROJECT_ROOT / "results" / "final_runs"


def _read_seed_file(seed_dir: Path) -> pd.DataFrame | None:
    candidates = [seed_dir / "all.csv", *seed_dir.glob("*_all.csv")]
    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            df["source_seed_dir"] = seed_dir.name
            df["source_file"] = str(path)
            return df
    return None


def _pareto(df: pd.DataFrame, feasible_column: str) -> pd.DataFrame:
    work = df[
        (df[feasible_column] == True)
        & df["losses_kw"].notna()
        & df["objective_reliability"].notna()
    ].copy()
    keep: list[int] = []
    for idx, row in work.iterrows():
        dominated = (
            (work["losses_kw"] <= row["losses_kw"])
            & (work["objective_reliability"] <= row["objective_reliability"])
            & (
                (work["losses_kw"] < row["losses_kw"])
                | (work["objective_reliability"] < row["objective_reliability"])
            )
        ).any()
        if not dominated:
            keep.append(idx)
    return work.loc[keep].sort_values(["losses_kw", "objective_reliability"]).reset_index(drop=True)


def _best_compromise(pareto: pd.DataFrame) -> pd.DataFrame:
    if pareto.empty:
        return pareto
    work = pareto.copy()
    loss_span = work["losses_kw"].max() - work["losses_kw"].min()
    rel_span = work["objective_reliability"].max() - work["objective_reliability"].min()
    loss_span = loss_span if loss_span else 1.0
    rel_span = rel_span if rel_span else 1.0
    work["losses_norm"] = (work["losses_kw"] - work["losses_kw"].min()) / loss_span
    work["saidi_norm"] = (work["objective_reliability"] - work["objective_reliability"].min()) / rel_span
    work["ideal_distance"] = (work["losses_norm"] ** 2 + work["saidi_norm"] ** 2) ** 0.5
    return work.loc[[work["ideal_distance"].idxmin()]]


def combine(case: str) -> dict[str, object]:
    case_dir = FINAL_ROOT / case
    combined_dir = case_dir / "combined"
    combined_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for seed_dir in sorted(case_dir.glob("seed_*")):
        frame = _read_seed_file(seed_dir)
        if frame is not None:
            frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No se encontraron archivos all.csv en {case_dir}")

    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.sort_values(["open_switches", "losses_kw", "objective_reliability"])
    all_unique = all_df.drop_duplicates(subset=["open_switches"], keep="first").reset_index(drop=True)

    pareto_feasible = _pareto(all_unique, "feasible")
    pareto_operational = _pareto(all_unique, "operationally_feasible")

    best_by_losses = all_unique[all_unique["feasible"] == True].nsmallest(1, "losses_kw")
    best_by_saidi = best_by_reliability_then_losses_df(all_unique)
    best_compromise = _best_compromise(pareto_feasible)

    all_unique.to_csv(combined_dir / "all_combined.csv", index=False, encoding="utf-8")
    pareto_feasible.to_csv(combined_dir / "pareto_feasible.csv", index=False, encoding="utf-8")
    pareto_operational.to_csv(combined_dir / "pareto_operationally_feasible.csv", index=False, encoding="utf-8")
    best_by_losses.to_csv(combined_dir / "best_by_losses.csv", index=False, encoding="utf-8")
    best_by_saidi.to_csv(combined_dir / "best_by_saidi.csv", index=False, encoding="utf-8")
    best_compromise.to_csv(combined_dir / "best_compromise.csv", index=False, encoding="utf-8")

    summary = pd.DataFrame(
        [
            {
                "case": case,
                "seed_files_found": len(frames),
                "raw_rows": len(all_df),
                "unique_configurations": len(all_unique),
                "feasible": int(all_unique["feasible"].sum()),
                "operationally_feasible": int(all_unique["operationally_feasible"].sum()),
                "pareto_feasible": len(pareto_feasible),
                "pareto_operationally_feasible": len(pareto_operational),
            }
        ]
    )
    summary.to_csv(combined_dir / "run_summary.csv", index=False, encoding="utf-8")
    return summary.iloc[0].to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="Combina corridas definitivas DNR por caso.")
    parser.add_argument("case", choices=["ieee33", "operator"])
    args = parser.parse_args()
    result = combine(args.case)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
