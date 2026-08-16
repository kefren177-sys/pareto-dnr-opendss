from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IEEE33_REFERENCE_OPEN = "7,9,14,32,37"
OBJECTIVES = ["losses_kw", "saidi"]
NOT_AVAILABLE = "NOT_AVAILABLE"
SAIDI_TOL = 1e-9


def _canonical_open(value: object) -> str:
    parts = [part.strip() for part in str(value).replace('"', "").split(",") if part.strip()]
    return ",".join(str(int(float(part))) for part in parts)


def _saidi_column(df: pd.DataFrame) -> str:
    for column in ("saidi", "saidi_h_user_year", "objective_reliability"):
        if column in df.columns:
            return column
    raise KeyError("No SAIDI column found. Expected saidi, saidi_h_user_year, or objective_reliability.")


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _run_dirs(runs_dir: Path) -> list[Path]:
    seed_dirs = sorted(path for path in runs_dir.glob("seed_*") if path.is_dir())
    if seed_dirs:
        return seed_dirs
    if (runs_dir / "all.csv").exists() and (runs_dir / "pareto.csv").exists():
        return [runs_dir]
    return []


def _pareto(df: pd.DataFrame, loss_col: str = "losses_kw", saidi_col: str = "saidi") -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df[df[loss_col].notna() & df[saidi_col].notna()].copy()
    keep: list[int] = []
    for idx, row in work.iterrows():
        dominated = (
            (work[loss_col] <= row[loss_col])
            & (work[saidi_col] <= row[saidi_col])
            & ((work[loss_col] < row[loss_col]) | (work[saidi_col] < row[saidi_col]))
        ).any()
        if not dominated:
            keep.append(idx)
    return work.loc[keep].sort_values([loss_col, saidi_col]).reset_index(drop=True)


def _normalization_bounds(frames: Iterable[pd.DataFrame]) -> dict[str, dict[str, float]]:
    values: dict[str, list[float]] = {key: [] for key in OBJECTIVES}
    for frame in frames:
        if frame.empty:
            continue
        saidi_col = _saidi_column(frame)
        for value in pd.to_numeric(frame["losses_kw"], errors="coerce").dropna():
            values["losses_kw"].append(float(value))
        for value in pd.to_numeric(frame[saidi_col], errors="coerce").dropna():
            values["saidi"].append(float(value))
    bounds = {}
    for key, data in values.items():
        if not data:
            raise ValueError(f"No finite values available for {key}.")
        low = min(data)
        high = max(data)
        bounds[key] = {"min": low, "max": high, "span": high - low if high > low else 1.0}
    return bounds


def _normalize(df: pd.DataFrame, bounds: dict[str, dict[str, float]], saidi_col: str | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    saidi_col = saidi_col or _saidi_column(df)
    work = df.copy()
    work["losses_norm"] = (work["losses_kw"] - bounds["losses_kw"]["min"]) / bounds["losses_kw"]["span"]
    work["saidi_norm"] = (work[saidi_col] - bounds["saidi"]["min"]) / bounds["saidi"]["span"]
    return work


def _hypervolume_2d_min(normalized_front: pd.DataFrame, reference_point: tuple[float, float]) -> float:
    if normalized_front.empty:
        return 0.0
    ref_x, ref_y = reference_point
    contributing = normalized_front[
        (normalized_front["losses_norm"] < ref_x)
        & (normalized_front["saidi_norm"] < ref_y)
    ].copy()
    if contributing.empty:
        return 0.0
    front = _pareto(contributing, "losses_norm", "saidi_norm")
    front = front.sort_values(["losses_norm", "saidi_norm"]).reset_index(drop=True)
    hv = 0.0
    for idx, row in front.iterrows():
        next_x = ref_x if idx == len(front) - 1 else float(front.loc[idx + 1, "losses_norm"])
        width = max(0.0, min(next_x, ref_x) - float(row["losses_norm"]))
        height = max(0.0, ref_y - float(row["saidi_norm"]))
        hv += width * height
    return hv


def _igd(normalized_front: pd.DataFrame, normalized_reference: pd.DataFrame) -> float | str:
    if normalized_front.empty or normalized_reference.empty:
        return NOT_AVAILABLE
    distances = []
    points = normalized_front[["losses_norm", "saidi_norm"]].to_numpy(dtype=float)
    for _, ref in normalized_reference.iterrows():
        dx = points[:, 0] - float(ref["losses_norm"])
        dy = points[:, 1] - float(ref["saidi_norm"])
        distances.append(float((dx * dx + dy * dy).min() ** 0.5))
    return float(sum(distances) / len(distances))


def _spacing(normalized_front: pd.DataFrame) -> float | str:
    if len(normalized_front) < 2:
        return NOT_AVAILABLE
    points = normalized_front[["losses_norm", "saidi_norm"]].to_numpy(dtype=float)
    nearest = []
    for i, point in enumerate(points):
        distances = [
            abs(float(point[0] - other[0])) + abs(float(point[1] - other[1]))
            for j, other in enumerate(points)
            if i != j
        ]
        nearest.append(min(distances))
    mean_d = sum(nearest) / len(nearest)
    if len(nearest) < 2:
        return NOT_AVAILABLE
    return float((sum((value - mean_d) ** 2 for value in nearest) / (len(nearest) - 1)) ** 0.5)


def _minimum_saidi_representative(pareto: pd.DataFrame, saidi_col: str) -> pd.Series:
    saidi_min = float(pareto[saidi_col].min())
    tied = pareto[(pareto[saidi_col] - saidi_min).abs() <= SAIDI_TOL].copy()
    return tied.sort_values(["losses_kw", "open_switches"]).iloc[0]


def _compromise_run_local(pareto: pd.DataFrame, saidi_col: str) -> pd.Series | None:
    if pareto.empty:
        return None
    work = pareto.copy()
    loss_span = work["losses_kw"].max() - work["losses_kw"].min()
    saidi_span = work[saidi_col].max() - work[saidi_col].min()
    loss_span = loss_span if loss_span else 1.0
    saidi_span = saidi_span if saidi_span else 1.0
    work["loss_norm_run"] = (work["losses_kw"] - work["losses_kw"].min()) / loss_span
    work["saidi_norm_run"] = (work[saidi_col] - work[saidi_col].min()) / saidi_span
    work["ideal_distance"] = (work["loss_norm_run"] ** 2 + work["saidi_norm_run"] ** 2) ** 0.5
    return work.sort_values(["ideal_distance", "losses_kw", saidi_col, "open_switches"]).iloc[0]


def _summary_stat(series: pd.Series) -> dict[str, object]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {
            "mean": NOT_AVAILABLE,
            "standard_deviation": NOT_AVAILABLE,
            "median": NOT_AVAILABLE,
            "q1": NOT_AVAILABLE,
            "q3": NOT_AVAILABLE,
            "iqr": NOT_AVAILABLE,
            "minimum": NOT_AVAILABLE,
            "maximum": NOT_AVAILABLE,
        }
    q1 = float(numeric.quantile(0.25))
    q3 = float(numeric.quantile(0.75))
    return {
        "mean": float(numeric.mean()),
        "standard_deviation": float(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0,
        "median": float(numeric.median()),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "minimum": float(numeric.min()),
        "maximum": float(numeric.max()),
    }


def _run_metrics(runs_dir: Path, bounds: dict[str, dict[str, float]], reference_point: tuple[float, float]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    pareto_frames = []
    for seed_dir in _run_dirs(runs_dir):
        summary = _read_csv(seed_dir / "summary.csv")
        pareto = _read_csv(seed_dir / "pareto.csv")
        all_df = _read_csv(seed_dir / "all.csv")
        if pareto.empty:
            continue
        saidi_col = _saidi_column(pareto)
        pareto = pareto.copy()
        pareto["seed_dir"] = seed_dir.name
        pareto["seed"] = int(summary.iloc[0]["seed"]) if not summary.empty and "seed" in summary else 0
        pareto["open_switches"] = pareto["open_switches"].map(_canonical_open)
        normalized = _normalize(pareto, bounds, saidi_col)
        hv = _hypervolume_2d_min(normalized, reference_point)
        spacing = _spacing(normalized)
        pareto_frames.append(pareto)

        min_loss = pareto.sort_values(["losses_kw", saidi_col]).iloc[0]
        min_saidi = _minimum_saidi_representative(pareto, saidi_col)
        comp = _compromise_run_local(pareto, saidi_col)
        all_opens = set(all_df["open_switches"].map(_canonical_open)) if not all_df.empty else set()
        pareto_opens = set(pareto["open_switches"].map(_canonical_open))
        rows.append(
            {
                "seed_dir": seed_dir.name,
                "seed": int(pareto["seed"].iloc[0]),
                "runtime_s": None if summary.empty else float(summary.iloc[0].get("elapsed_seconds", math.nan)),
                "unique_evaluations": None if summary.empty else int(summary.iloc[0].get("unique_evaluations", len(all_df))),
                "cache_hits": None if summary.empty else int(summary.iloc[0].get("cache_hits", 0)),
                "final_pareto_size": len(pareto),
                "min_loss": float(min_loss["losses_kw"]),
                "min_loss_switches": min_loss["open_switches"],
                "min_saidi": float(min_saidi[saidi_col]),
                "min_saidi_switches": min_saidi["open_switches"],
                "compromise_loss": None if comp is None else float(comp["losses_kw"]),
                "compromise_saidi": None if comp is None else float(comp[saidi_col]),
                "compromise_switches": None if comp is None else comp["open_switches"],
                "hypervolume": hv,
                "igd": None,
                "spacing": spacing,
                "benchmark_recovery_evaluated": IEEE33_REFERENCE_OPEN in all_opens,
                "benchmark_recovery_pareto": IEEE33_REFERENCE_OPEN in pareto_opens,
                "benchmark_recovery_min_loss": min_loss["open_switches"] == IEEE33_REFERENCE_OPEN,
            }
        )
    return pd.DataFrame(rows), pd.concat(pareto_frames, ignore_index=True) if pareto_frames else pd.DataFrame()


def _fill_igd(metrics: pd.DataFrame, runs_dir: Path, bounds: dict[str, dict[str, float]], empirical_ref: pd.DataFrame) -> pd.DataFrame:
    if metrics.empty:
        return metrics
    normalized_ref = _normalize(empirical_ref, bounds, _saidi_column(empirical_ref))
    run_dir_by_name = {path.name: path for path in _run_dirs(runs_dir)}
    rows = []
    for _, row in metrics.iterrows():
        run_dir = run_dir_by_name[str(row["seed_dir"])]
        pareto = _read_csv(run_dir / "pareto.csv")
        normalized = _normalize(pareto, bounds, _saidi_column(pareto))
        item = row.to_dict()
        item["igd"] = _igd(normalized, normalized_ref)
        rows.append(item)
    return pd.DataFrame(rows)


def _convergence(runs_dir: Path, bounds: dict[str, dict[str, float]], reference_point: tuple[float, float]) -> pd.DataFrame:
    rows = []
    for seed_dir in _run_dirs(runs_dir):
        hist = _read_csv(seed_dir / "pareto_history.csv")
        if hist.empty:
            continue
        hist["open_switches"] = hist["open_switches"].map(_canonical_open)
        seed = int(hist["seed"].iloc[0])
        for generation, frame in hist.groupby("generation", sort=True):
            normalized = _normalize(frame, bounds, _saidi_column(frame))
            rows.append(
                {
                    "seed_dir": seed_dir.name,
                    "seed": seed,
                    "generation": int(generation),
                    "unique_evaluations_cumulative": int(frame["unique_evaluations_cumulative"].max()),
                    "hypervolume": _hypervolume_2d_min(normalized, reference_point),
                    "archive_pareto_size": len(_pareto(frame, "losses_kw", _saidi_column(frame))),
                }
            )
    convergence = pd.DataFrame(rows)
    if convergence.empty:
        return convergence

    grid = sorted(convergence["unique_evaluations_cumulative"].unique())
    grid_rows = []
    for seed, frame in convergence.groupby("seed"):
        frame = frame.sort_values("unique_evaluations_cumulative")
        last = None
        for value in grid:
            eligible = frame[frame["unique_evaluations_cumulative"] <= value]
            if not eligible.empty:
                last = eligible.iloc[-1]
            if last is None:
                continue
            grid_rows.append(
                {
                    "seed": int(seed),
                    "unique_evaluations_grid": int(value),
                    "hv_last_observation_carried_forward": float(last["hypervolume"]),
                }
            )
    grid_df = pd.DataFrame(grid_rows)
    stats = []
    total_runs = int(convergence["seed"].nunique())
    first_full_coverage = None
    for value, frame in grid_df.groupby("unique_evaluations_grid"):
        hv = frame["hv_last_observation_carried_forward"]
        n_runs_contributing = int(frame["seed"].nunique())
        full_run_coverage = n_runs_contributing == total_runs
        if full_run_coverage and first_full_coverage is None:
            first_full_coverage = int(value)
        stats.append(
            {
                "seed_dir": "ALL",
                "seed": "ALL",
                "generation": "LOCFE",
                "unique_evaluations_cumulative": int(value),
                "hypervolume": float(hv.median()),
                "hv_q1": float(hv.quantile(0.25)),
                "hv_q3": float(hv.quantile(0.75)),
                "n_runs_contributing": n_runs_contributing,
                "full_run_coverage": full_run_coverage,
                "archive_pareto_size": NOT_AVAILABLE,
            }
        )
    result = pd.concat([convergence, pd.DataFrame(stats)], ignore_index=True)
    result.attrs["first_full_coverage_unique_evaluations"] = first_full_coverage
    return result


def postprocess(runs_dir: Path, output_dir: Path | None = None) -> dict[str, Path]:
    runs_dir = runs_dir.resolve()
    output_dir = (output_dir or runs_dir / "phase4").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dirs = _run_dirs(runs_dir)
    final_paretos = [_read_csv(seed_dir / "pareto.csv") for seed_dir in run_dirs]
    pareto_union = pd.concat(
        [frame for frame in final_paretos if not frame.empty],
        ignore_index=True,
    ) if any(not frame.empty for frame in final_paretos) else pd.DataFrame()
    empirical_ref = _pareto(pareto_union, "losses_kw", _saidi_column(pareto_union)) if not pareto_union.empty else pd.DataFrame()
    if not empirical_ref.empty:
        empirical_ref = empirical_ref.drop_duplicates(subset=["open_switches"]).reset_index(drop=True)
    bounds = _normalization_bounds([empirical_ref])
    reference_point = (1.05, 1.05)

    metrics, pareto_union = _run_metrics(runs_dir, bounds, reference_point)
    metrics = _fill_igd(metrics, runs_dir, bounds, empirical_ref)
    convergence = _convergence(runs_dir, bounds, reference_point)

    summary_rows = []
    for metric in ["hypervolume", "igd", "spacing", "runtime_s", "unique_evaluations", "final_pareto_size"]:
        item = {"metric": metric}
        item.update(_summary_stat(metrics[metric] if metric in metrics else pd.Series(dtype=float)))
        summary_rows.append(item)
    if not metrics.empty:
        summary_rows.extend(
            [
                {
                    "metric": "recovery_rate_evaluated",
                    "mean": float(metrics["benchmark_recovery_evaluated"].mean()),
                    "standard_deviation": NOT_AVAILABLE,
                    "median": NOT_AVAILABLE,
                    "q1": NOT_AVAILABLE,
                    "q3": NOT_AVAILABLE,
                    "iqr": NOT_AVAILABLE,
                    "minimum": NOT_AVAILABLE,
                    "maximum": NOT_AVAILABLE,
                },
                {
                    "metric": "recovery_rate_pareto",
                    "mean": float(metrics["benchmark_recovery_pareto"].mean()),
                    "standard_deviation": NOT_AVAILABLE,
                    "median": NOT_AVAILABLE,
                    "q1": NOT_AVAILABLE,
                    "q3": NOT_AVAILABLE,
                    "iqr": NOT_AVAILABLE,
                    "minimum": NOT_AVAILABLE,
                    "maximum": NOT_AVAILABLE,
                },
                {
                    "metric": "recovery_rate_min_loss",
                    "mean": float(metrics["benchmark_recovery_min_loss"].mean()),
                    "standard_deviation": NOT_AVAILABLE,
                    "median": NOT_AVAILABLE,
                    "q1": NOT_AVAILABLE,
                    "q3": NOT_AVAILABLE,
                    "iqr": NOT_AVAILABLE,
                    "minimum": NOT_AVAILABLE,
                    "maximum": NOT_AVAILABLE,
                },
            ]
        )
    statistical_summary = pd.DataFrame(summary_rows)

    run_metrics_path = output_dir / "phase4_run_metrics.csv"
    summary_path = output_dir / "phase4_statistical_summary.csv"
    ref_path = output_dir / "phase4_empirical_reference_front.csv"
    convergence_path = output_dir / "phase4_convergence.csv"
    protocol_path = output_dir / "phase4_protocol.json"

    metrics.to_csv(run_metrics_path, index=False, encoding="utf-8")
    statistical_summary.to_csv(summary_path, index=False, encoding="utf-8")
    empirical_ref.to_csv(ref_path, index=False, encoding="utf-8")
    convergence.to_csv(convergence_path, index=False, encoding="utf-8")

    protocol = {
        "objectives": {
            "objective_1": "active power losses [kW]",
            "objective_2": "SAIDI [h/customer-year]",
            "sense": "minimization",
        },
        "normalization_bounds": bounds,
        "normalization_bounds_source": (
            "ideal and nadir values of the empirical reference front constructed from the "
            "union of all final run-level Pareto fronts"
        ),
        "normalization": "z = (value - empirical_min) / (empirical_max - empirical_min); span is set to 1 if max == min.",
        "hypervolume": {
            "reference_point": list(reference_point),
            "reference_point_definition": "5% margin beyond the normalized empirical upper bound for both objectives.",
        },
        "igd": {
            "reference_front_definition": "empirical reference front = nondominated set of the union of all final run-level Pareto fronts.",
            "true_pareto_front_claimed": False,
        },
        "spacing": {
            "formula": "sample standard deviation of nearest-neighbor Manhattan distances in normalized objective space.",
            "not_available_rule": "NOT_AVAILABLE when Pareto front has fewer than two points.",
        },
        "convergence": {
            "x_axis": "cumulative unique OpenDSS evaluations",
            "aggregation": "last-observation-carried-forward on a common unique-evaluation grid; median, Q1, and Q3 are stored.",
            "first_full_coverage_unique_evaluations": convergence.attrs.get("first_full_coverage_unique_evaluations"),
        },
        "recovery_definition": {
            "benchmark_configuration": IEEE33_REFERENCE_OPEN,
            "primary": "recovered in final run-level Pareto front",
            "secondary": ["evaluated at least once", "selected as minimum-loss solution"],
        },
        "number_of_runs": int(len(metrics)),
        "seeds": [] if metrics.empty else [int(x) for x in metrics["seed"].tolist()],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "pandas": pd.__version__,
        },
    }
    protocol_path.write_text(json.dumps(protocol, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "run_metrics": run_metrics_path,
        "statistical_summary": summary_path,
        "empirical_reference_front": ref_path,
        "convergence": convergence_path,
        "protocol": protocol_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 statistical postprocessing for DNR runs.")
    parser.add_argument("runs_dir", type=Path, help="Directory containing seed_* run folders.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for phase4 output files.")
    args = parser.parse_args()
    outputs = postprocess(args.runs_dir, args.output_dir)
    for key, path in outputs.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
