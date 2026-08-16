from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .cases import DEFAULT_CONFIG, case_names, generated_data_root, load_case, output_root
from .evaluate import evaluate
from .io import write_results
from .optimize import evolutionary_search, exhaustive, random_search
from .pareto import pareto_front
from .selection import best_by_reliability_then_losses

app = typer.Typer(help="DNR: Distribution Networks Reconfiguration desde consola.")
console = Console()
IEEE33_REFERENCE_OPEN = (7, 9, 14, 32, 37)
GENERATION_HISTORY_FIELDS = [
    "case",
    "run_id",
    "seed",
    "generation",
    "elapsed_time_s",
    "unique_evaluations_generation",
    "unique_evaluations_cumulative",
    "cache_hits_generation",
    "cache_hits_cumulative",
    "population_size",
    "feasible_population_size",
    "nondominated_size",
    "archive_nondominated_size",
    "best_loss",
    "best_saidi",
]
PARETO_HISTORY_FIELDS = [
    "case",
    "run_id",
    "seed",
    "generation",
    "unique_evaluations_cumulative",
    "open_switches",
    "losses_kw",
    "saidi",
]


def _parse_open(value: str | None, default: list[int]) -> list[int]:
    if not value:
        return list(default)
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def _validate_reliability_objective(value: str) -> str:
    value = value.lower()
    if value not in {"saidi", "saifi", "ens"}:
        raise typer.BadParameter("Use uno de estos objetivos: saidi, saifi o ens.")
    return value


def _objective_label(value: str) -> str:
    labels = {
        "saidi": "SAIDI [h/usuario-ano]",
        "saifi": "SAIFI [interrupciones/usuario-ano]",
        "ens": "ENS [MWh/ano]",
    }
    return labels.get(value.lower(), value)


def _open_text(ev) -> str | None:
    if ev is None:
        return None
    return ",".join(str(x) for x in ev.open_switches)


def _ieee33_reference_recovery(case_name: str, evaluations: list, front: list, best_loss) -> tuple[bool | None, bool | None, bool | None]:
    if case_name != "ieee33":
        return None, None, None
    recovered_evaluated = any(ev.open_switches == IEEE33_REFERENCE_OPEN for ev in evaluations)
    recovered_pareto = any(ev.open_switches == IEEE33_REFERENCE_OPEN for ev in front)
    recovered_min_loss = best_loss is not None and best_loss.open_switches == IEEE33_REFERENCE_OPEN
    return recovered_evaluated, recovered_pareto, recovered_min_loss


def _write_run_summary(output_dir: Path, summary: dict[str, object]) -> tuple[Path, Path]:
    csv_path = output_dir / "summary.csv"
    json_path = output_dir / "summary.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, json_path


def _write_run_log(output_dir: Path, summary: dict[str, object], warnings: list[str]) -> Path:
    log_path = output_dir / "log.txt"
    lines = [
        "DNR optimization run log",
        f"command: {summary['command']}",
        f"started_at: {summary['started_at']}",
        f"finished_at: {summary['finished_at']}",
        f"case: {summary['case']}",
        f"method: {summary['method']}",
        f"population: {summary['population']}",
        f"generations: {summary['generations']}",
        f"seed: {summary['seed']}",
        f"reliability_objective: {summary['reliability_objective']}",
        f"v_min_limit: {summary['v_min_limit']}",
        f"v_max_limit: {summary['v_max_limit']}",
        f"elapsed_seconds: {summary['elapsed_seconds']}",
        f"total_candidate_evaluations: {summary['total_candidate_evaluations']}",
        f"unique_evaluations: {summary['unique_evaluations']}",
        f"cache_hits: {summary['cache_hits']}",
        f"feasible_count: {summary['feasible_count']}",
        f"operationally_feasible_count: {summary['operationally_feasible_count']}",
        f"pareto_size: {summary['pareto_size']}",
        f"all_csv: {summary['all_csv']}",
        f"pareto_csv: {summary['pareto_csv']}",
        "warnings:",
    ]
    lines.extend(f"- {warning}" for warning in warnings)
    lines.append("errors: none")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path


def _write_rows(output_dir: Path, name: str, rows: list[dict[str, object]], fieldnames: list[str]) -> Path:
    path = output_dir / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _existing_run_files(output_dir: Path) -> list[Path]:
    names = [
        "all.csv",
        "all.json",
        "pareto.csv",
        "pareto.json",
        "summary.csv",
        "summary.json",
        "log.txt",
        "generation_history.csv",
        "pareto_history.csv",
    ]
    return [output_dir / name for name in names if (output_dir / name).exists()]


def _resolve_output_dir(path: Path, config: Path) -> Path:
    if path.is_absolute():
        return path
    return config.resolve().parents[1] / path


@app.command("list-cases")
def list_cases(config: Path = DEFAULT_CONFIG):
    """Lista los experimentos configurados."""
    table = Table("Caso", "Titulo", "Buses", "Ramas", "Abiertos")
    for name in case_names(config):
        case = load_case(name, config)
        table.add_row(
            case.name,
            case.title,
            str(len(case.buses)),
            str(len(case.branches)),
            ",".join(str(x) for x in case.normally_open),
        )
    console.print(table)


@app.command()
def run(
    case_name: str,
    open: str | None = typer.Option(None, "--open", help="Interruptores/lineas abiertas, separados por coma."),
    reliability_objective: str = typer.Option("saidi", "--reliability-objective", help="saidi, saifi o ens."),
    config: Path = DEFAULT_CONFIG,
):
    """Evalua una configuracion: radialidad, OpenDSS, perdidas e indices."""
    case = load_case(case_name, config)
    open_switches = _parse_open(open, case.normally_open)
    objective = _validate_reliability_objective(reliability_objective)
    ev = evaluate(case, open_switches, generated_data_root(config), objective)
    table = Table("Metrica", "Valor")
    for key, value in ev.to_record().items():
        table.add_row(key, str(value))
    console.print(table)


@app.command()
def optimize(
    case_name: str,
    method: str = typer.Option("evolutionary", "--method", help="evolutionary, random o exhaustive."),
    samples: int = typer.Option(1000, "--samples", help="Muestras para busqueda aleatoria."),
    population: int = typer.Option(40, "--population", help="Tamano de poblacion para evolutivo."),
    generations: int = typer.Option(25, "--generations", help="Generaciones para evolutivo."),
    reliability_objective: str = typer.Option("saidi", "--reliability-objective", help="Segundo objetivo: saidi, saifi o ens."),
    seed: int = typer.Option(1234, "--seed", help="Semilla reproducible."),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Carpeta de salida para una corrida reproducible."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Permite sobrescribir archivos existentes en --output-dir."),
    config: Path = DEFAULT_CONFIG,
):
    """Optimiza y exporta resultados junto con el frente de Pareto."""
    started = datetime.now()
    tic = time.perf_counter()
    case = load_case(case_name, config)
    generated = generated_data_root(config)
    objective = _validate_reliability_objective(reliability_objective)
    run_stats: dict[str, int] = {}
    run_id = f"{case.name}_seed_{seed}"
    generation_history: list[dict[str, object]] | None = None
    pareto_history: list[dict[str, object]] | None = None
    resolved_output_dir = _resolve_output_dir(output_dir, config) if output_dir is not None else None
    if resolved_output_dir is not None:
        resolved_output_dir.mkdir(parents=True, exist_ok=True)
        existing = _existing_run_files(resolved_output_dir)
        if existing and not overwrite:
            names = ", ".join(path.name for path in existing)
            raise typer.BadParameter(
                f"--output-dir ya contiene resultados ({names}). Use otra carpeta o agregue --overwrite."
            )
    if method == "exhaustive":
        evaluations = exhaustive(case, generated, objective)
        run_stats = {
            "evaluation_requests": len(evaluations),
            "real_evaluations": len(evaluations),
            "cache_hits": 0,
        }
    elif method == "random":
        evaluations = random_search(case, generated, samples=samples, seed=seed, reliability_objective=objective)
        run_stats = {
            "evaluation_requests": len(evaluations),
            "real_evaluations": len(evaluations),
            "cache_hits": 0,
        }
    elif method == "evolutionary":
        if resolved_output_dir is not None:
            generation_history = []
            pareto_history = []
        evaluations = evolutionary_search(
            case,
            generated,
            population_size=population,
            generations=generations,
            seed=seed,
            reliability_objective=objective,
            stats=run_stats,
            generation_history=generation_history,
            pareto_history=pareto_history,
            run_id=run_id,
        )
    else:
        raise typer.BadParameter("method debe ser evolutionary, random o exhaustive")

    out = resolved_output_dir if resolved_output_dir is not None else output_root(config) / case.name
    stem = "" if output_dir is not None else f"{case.name}_{method}_{objective}_"
    result_metadata = {
        "seed": seed,
        "population": population,
        "generations": generations,
        "method": method,
    }
    csv_path, json_path = write_results(evaluations, out, f"{stem}all", result_metadata)
    front = pareto_front(evaluations)
    front_csv, front_json = write_results(front, out, f"{stem}pareto", result_metadata)

    best_loss = min((ev for ev in evaluations if ev.feasible), key=lambda ev: ev.losses_kw or float("inf"), default=None)
    best_rel = best_by_reliability_then_losses(evaluations)
    recovered_evaluated, recovered_pareto, recovered_min_loss = _ieee33_reference_recovery(
        case.name, evaluations, front, best_loss
    )
    finished = datetime.now()
    elapsed = time.perf_counter() - tic
    warnings = sorted(
        {
            reason
            for ev in evaluations
            for reason in ev.infeasibility_reasons
            if reason
        }
    )
    summary = {
        "case": case.name,
        "run_id": run_id,
        "method": method,
        "population": population,
        "generations": generations,
        "seed": seed,
        "reliability_objective": objective,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "elapsed_seconds": round(elapsed, 6),
        "total_candidate_evaluations": run_stats.get("evaluation_requests", len(evaluations)),
        "unique_evaluations": run_stats.get("real_evaluations", len(evaluations)),
        "cache_hits": run_stats.get("cache_hits", 0),
        "feasible_count": sum(1 for ev in evaluations if ev.feasible),
        "operationally_feasible_count": sum(1 for ev in evaluations if ev.operationally_feasible),
        "pareto_size": len(front),
        "best_losses_open_switches": _open_text(best_loss),
        "best_losses_kw": None if best_loss is None else best_loss.losses_kw,
        "best_losses_saidi": None if best_loss is None else best_loss.saidi,
        "best_saidi_open_switches": _open_text(best_rel),
        "best_saidi_losses_kw": None if best_rel is None else best_rel.losses_kw,
        "best_saidi": None if best_rel is None else best_rel.objective_reliability,
        "recovered_ieee33_reference_evaluated": recovered_evaluated,
        "recovered_ieee33_reference_pareto": recovered_pareto,
        "recovered_ieee33_reference_min_loss": recovered_min_loss,
        "v_min_limit": case.operation_limits.get("v_min_limit", 0.90),
        "v_max_limit": case.operation_limits.get("v_max_limit", 1.05),
        "output_dir": str(out),
        "all_csv": str(csv_path),
        "pareto_csv": str(front_csv),
        "command": " ".join(sys.argv),
        "warnings": ";".join(warnings),
    }
    summary_csv = summary_json = log_path = None
    if resolved_output_dir is not None:
        if generation_history is not None:
            _write_rows(out, "generation_history.csv", generation_history, GENERATION_HISTORY_FIELDS)
        if pareto_history is not None:
            _write_rows(out, "pareto_history.csv", pareto_history, PARETO_HISTORY_FIELDS)
        summary_csv, summary_json = _write_run_summary(out, summary)
        log_path = _write_run_log(out, summary, warnings)

    console.print(f"[green]Evaluaciones:[/] {len(evaluations)}")
    console.print(f"[green]Factibles:[/] {sum(1 for ev in evaluations if ev.feasible)}")
    console.print(f"[green]Operativamente factibles:[/] {sum(1 for ev in evaluations if ev.operationally_feasible)}")
    console.print(f"[green]Cache hits:[/] {run_stats.get('cache_hits', 0)}")
    console.print(f"[green]Frente Pareto:[/] {len(front)}")
    console.print(f"Resultados: {csv_path}")
    console.print(f"Resultados JSON: {json_path}")
    console.print(f"Pareto: {front_csv}")
    console.print(f"Pareto JSON: {front_json}")
    if summary_csv and summary_json and log_path:
        console.print(f"Resumen CSV: {summary_csv}")
        console.print(f"Resumen JSON: {summary_json}")
        console.print(f"Log: {log_path}")
    if best_loss:
        console.print(f"Menor perdida: {best_loss.losses_kw:.6g} kW con abiertos {best_loss.open_switches}")
    if best_rel:
        console.print(
            f"Menor {_objective_label(objective)}: {best_rel.objective_reliability:.6g} con abiertos {best_rel.open_switches}",
            markup=False,
        )


@app.command()
def pareto(
    results_csv: Path,
):
    """Reconstruye un frente de Pareto desde un CSV exportado por optimize."""
    import pandas as pd

    df = pd.read_csv(results_csv)
    objective = (
        str(df["objective_reliability_name"].dropna().iloc[0])
        if "objective_reliability_name" in df.columns and not df["objective_reliability_name"].dropna().empty
        else "saidi"
    )
    feasible = df[df["feasible"] == True].copy()
    keep = []
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
    front = feasible.loc[keep].sort_values(["losses_kw", "objective_reliability"])
    out = results_csv.with_name(results_csv.stem + "_pareto_rebuilt.csv")
    front.to_csv(out, index=False, encoding="utf-8")
    console.print(f"Frente reconstruido con {_objective_label(objective)}: {out}")


@app.command("plot-pareto")
def plot_pareto(results_csv: Path):
    """Genera una figura SVG del frente de Pareto a partir de un CSV."""
    import pandas as pd

    df = pd.read_csv(results_csv)
    objective = (
        str(df["objective_reliability_name"].dropna().iloc[0])
        if "objective_reliability_name" in df.columns and not df["objective_reliability_name"].dropna().empty
        else "saidi"
    )
    feasible = df[df["feasible"] == True].copy()
    if feasible.empty:
        raise typer.BadParameter("El archivo no contiene evaluaciones factibles.")

    keep = []
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
    front = feasible.loc[keep].sort_values(["losses_kw", "objective_reliability"])

    out = results_csv.with_name(results_csv.stem + "_pareto.svg")
    write_pareto_svg(feasible, front, out, _objective_label(objective))
    console.print(f"Figura Pareto: {out}")


def write_pareto_svg(feasible, front, out: Path, y_label: str) -> None:
    width, height = 900, 560
    left, right, top, bottom = 90, 30, 35, 80
    plot_w = width - left - right
    plot_h = height - top - bottom
    x_min, x_max = feasible["losses_kw"].min(), feasible["losses_kw"].max()
    y_min = feasible["objective_reliability"].min()
    y_max = feasible["objective_reliability"].max()
    x_span = x_max - x_min or 1.0
    y_span = y_max - y_min or 1.0

    def sx(x):
        return left + (float(x) - x_min) / x_span * plot_w

    def sy(y):
        return top + plot_h - (float(y) - y_min) / y_span * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222"/>',
        f'<text x="{width/2}" y="{height-22}" text-anchor="middle" font-family="Arial" font-size="16">Perdidas tecnicas [kW]</text>',
        f'<text x="22" y="{height/2}" text-anchor="middle" font-family="Arial" font-size="16" transform="rotate(-90 22 {height/2})">{y_label}</text>',
    ]
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        x = left + frac * plot_w
        y = top + frac * plot_h
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="#e5e7eb"/>')
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb"/>')
    for _, row in feasible.iterrows():
        parts.append(
            f'<circle cx="{sx(row["losses_kw"]):.2f}" cy="{sy(row["objective_reliability"]):.2f}" r="3" fill="#64748b" opacity="0.35"/>'
        )
    points = " ".join(
        f'{sx(row["losses_kw"]):.2f},{sy(row["objective_reliability"]):.2f}'
        for _, row in front.iterrows()
    )
    if points:
        parts.append(f'<polyline points="{points}" fill="none" stroke="#dc2626" stroke-width="2"/>')
    for _, row in front.iterrows():
        parts.append(
            f'<circle cx="{sx(row["losses_kw"]):.2f}" cy="{sy(row["objective_reliability"]):.2f}" r="5" fill="#dc2626"/>'
        )
    parts.extend(
        [
            f'<text x="{left}" y="{top + plot_h + 24}" font-family="Arial" font-size="12">{x_min:.4g}</text>',
            f'<text x="{left + plot_w}" y="{top + plot_h + 24}" text-anchor="end" font-family="Arial" font-size="12">{x_max:.4g}</text>',
            f'<text x="{left - 10}" y="{top + plot_h}" text-anchor="end" font-family="Arial" font-size="12">{y_min:.4g}</text>',
            f'<text x="{left - 10}" y="{top + 4}" text-anchor="end" font-family="Arial" font-size="12">{y_max:.4g}</text>',
            '<circle cx="690" cy="35" r="4" fill="#64748b" opacity="0.45"/><text x="702" y="40" font-family="Arial" font-size="13">Factibles</text>',
            '<circle cx="790" cy="35" r="5" fill="#dc2626"/><text x="804" y="40" font-family="Arial" font-size="13">Pareto</text>',
            "</svg>",
        ]
    )
    out.write_text("\n".join(parts), encoding="utf-8")
