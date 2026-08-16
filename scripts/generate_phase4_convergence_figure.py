from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def build_figure(input_csv: Path, output_dir: Path) -> None:
    df = pd.read_csv(input_csv)
    if "run_id" not in df.columns and "seed_dir" in df.columns:
        df = df.rename(columns={"seed_dir": "run_id"})
    if "hv_median" not in df.columns and "hypervolume" in df.columns:
        df = df.rename(columns={"hypervolume": "hv_median"})

    required = {
        "run_id",
        "unique_evaluations_cumulative",
        "hv_median",
        "hv_q1",
        "hv_q3",
        "n_runs_contributing",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    all_rows = df[df["run_id"].astype(str).str.upper() == "ALL"].copy()
    if all_rows.empty:
        raise ValueError("No aggregated ALL rows found.")

    total_runs = int(all_rows["n_runs_contributing"].max())
    plot_df = all_rows[all_rows["n_runs_contributing"] == total_runs].copy()
    plot_df = plot_df[plot_df["unique_evaluations_cumulative"] >= 200]
    if plot_df.empty:
        raise ValueError("No full-coverage rows with at least 200 evaluations found.")
    for column in ["unique_evaluations_cumulative", "hv_median", "hv_q1", "hv_q3"]:
        plot_df[column] = pd.to_numeric(plot_df[column], errors="raise")

    if plot_df[["hv_median", "hv_q1", "hv_q3"]].max().max() > 1.1025 + 1e-12:
        raise ValueError("Hypervolume exceeds the valid upper bound 1.1025.")

    x = plot_df["unique_evaluations_cumulative"].to_numpy()
    y = plot_df["hv_median"].to_numpy()
    q1 = plot_df["hv_q1"].to_numpy()
    q3 = plot_df["hv_q3"].to_numpy()

    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "font.size": 10,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.6,
        }
    )

    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    ax.fill_between(x, q1, q3, color="#4C78A8", alpha=0.20, label="IQR (Q1-Q3)")
    ax.plot(x, y, color="#1F4E79", linewidth=2.0, label="Median HV")
    ax.set_xlabel("Cumulative unique OpenDSS evaluations")
    ax.set_ylabel("Hypervolume (HV)")
    ax.set_xlim(left=200, right=float(x.max()))
    ax.set_ylim(bottom=max(0.0, float(q1.min()) - 0.02), top=min(1.1025, float(q3.max()) + 0.02))
    tick_count = 6
    ax.set_xticks([round(v) for v in pd.Series(np.linspace(200, float(x.max()), tick_count)).drop_duplicates()])
    ax.legend(frameon=False, loc="lower right")
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.18, top=0.96)

    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "ieee33_hv_convergence.png")
    fig.savefig(output_dir / "ieee33_hv_convergence.svg")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate IEEE33 Phase 4 HV convergence figure.")
    parser.add_argument(
        "input_csv",
        nargs="?",
        default="results/phase4_runs/ieee33/phase4/phase4_convergence.csv",
        type=Path,
    )
    parser.add_argument(
        "--output-dir",
        default="results/phase4_runs/ieee33/phase4",
        type=Path,
    )
    args = parser.parse_args()
    build_figure(args.input_csv, args.output_dir)


if __name__ == "__main__":
    main()
