from __future__ import annotations

import sys
import json
import subprocess
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from dnr.cases import DEFAULT_CONFIG, generated_data_root, load_case

TABLE_DIR = PROJECT_ROOT / "results" / "article_tables"
FIG_DIR = PROJECT_ROOT / "results" / "article_figures"
DIAG_DIR = PROJECT_ROOT / "results" / "diagnostics"
FINAL_DIR = PROJECT_ROOT / "results" / "final_runs"

CASES = {
    "ieee33": {
        "label": "IEEE 33-bus system",
        "population": 100,
        "generations": 100,
        "seeds": [1234, 2026, 31415, 27182, 4242],
    },
    "operator": {
        "label": "Real distribution system",
        "population": 80,
        "generations": 80,
        "seeds": [1234, 2026, 31415],
    },
}

METRIC_COLS = {
    "losses": "losses_kw",
    "saidi": "saidi_h_user_year",
    "saifi": "saifi_int_user_year",
    "ens": "ens_mwh_year",
    "vmin": "vmin_pu",
    "vmax": "vmax_pu",
}


def ensure_dirs() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)


def read_combined(case: str) -> dict[str, pd.DataFrame]:
    base = FINAL_DIR / case / "combined"
    return {
        "all": pd.read_csv(base / "all_combined.csv"),
        "pareto_feasible": pd.read_csv(base / "pareto_feasible.csv"),
        "pareto_operational": pd.read_csv(base / "pareto_operationally_feasible.csv"),
        "best_loss": pd.read_csv(base / "best_by_losses.csv"),
        "best_saidi": pd.read_csv(base / "best_by_saidi.csv"),
        "compromise": pd.read_csv(base / "best_compromise.csv"),
        "summary": pd.read_csv(base / "run_summary.csv"),
    }


def write_table(df: pd.DataFrame, stem: str) -> tuple[Path, Path]:
    csv_path = TABLE_DIR / f"{stem}.csv"
    md_path = TABLE_DIR / f"{stem}.md"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    md_path.write_text(markdown_table(df), encoding="utf-8")
    return csv_path, md_path


def markdown_table(df: pd.DataFrame) -> str:
    def cell(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value).replace("|", "\\|")

    columns = list(df.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(cell(row[col]) for col in columns) + " |")
    return "\n".join(lines) + "\n"


def save_figure(fig: plt.Figure, stem: str) -> list[Path]:
    paths = []
    for ext in ("png", "pdf", "svg"):
        path = FIG_DIR / f"{stem}.{ext}"
        if ext == "png":
            fig.savefig(path, dpi=300, bbox_inches="tight")
        else:
            fig.savefig(path, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    return paths


def open_tuple(text: str) -> list[int]:
    return [int(part.strip()) for part in str(text).split(",") if part.strip()]


def pct_reduction(base_value: float, value: float) -> float:
    return 100.0 * (base_value - value) / base_value if base_value else 0.0


def base_evaluation(case_name: str) -> dict[str, object]:
    values = {
        "ieee33": {
            "open_switches": "33,34,35,36,37",
            "losses_kw": 185.68063610324225,
            "vmin_pu": 0.9159677286485081,
            "vmax_pu": 0.9983942382629303,
            "saidi_h_user_year": 3.8460948465937497,
            "saifi_int_user_year": 10.511327812500001,
            "ens_mwh_year": 14.4680767812,
            "feasible": True,
            "operationally_feasible": True,
            "infeasibility_reasons": "loading_limits_not_available",
        },
        "operator": {
            "open_switches": "110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131",
            "losses_kw": 1397.0260799406074,
            "vmin_pu": 0.8255565281657926,
            "vmax_pu": 0.9924711669219252,
            "saidi_h_user_year": 5.765254937425991,
            "saifi_int_user_year": 15.756367689057095,
            "ens_mwh_year": 118.50720169399997,
            "feasible": True,
            "operationally_feasible": False,
            "infeasibility_reasons": "voltage_below_limit;loading_limits_not_available",
        },
    }
    rec = values[case_name].copy()
    rec["source"] = "base_from_final_execution_report"
    return rec


def selected_rows(case_name: str, data: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    return {
        "Menor perdida": data["best_loss"].iloc[0],
        "Menor SAIDI": data["best_saidi"].iloc[0],
        "Compromiso": data["compromise"].iloc[0],
    }


def solution_record(case_name: str, solution_type: str, row: pd.Series | dict, base: dict[str, object]) -> dict[str, object]:
    get = row.get if isinstance(row, dict) else row.get
    base_losses = float(base["losses_kw"])
    base_saidi = float(base["saidi_h_user_year"])
    base_saifi = float(base["saifi_int_user_year"])
    base_ens = float(base["ens_mwh_year"])
    losses = float(get("losses_kw"))
    saidi = float(get("saidi_h_user_year"))
    saifi = float(get("saifi_int_user_year"))
    ens = float(get("ens_mwh_year"))
    return {
        "caso": case_name,
        "tipo_solucion": solution_type,
        "fuente": get("source_seed_dir", get("source", "")),
        "semilla": get("seed", ""),
        "interruptores_abiertos": get("open_switches", ""),
        "perdidas_kw": losses,
        "reduccion_perdidas_pct": pct_reduction(base_losses, losses),
        "saidi_h_usuario_anio": saidi,
        "reduccion_saidi_pct": pct_reduction(base_saidi, saidi),
        "saifi_int_usuario_anio": saifi,
        "reduccion_saifi_pct": pct_reduction(base_saifi, saifi),
        "ens_mwh_anio": ens,
        "reduccion_ens_pct": pct_reduction(base_ens, ens),
        "vmin_pu": get("vmin_pu", get("min_voltage_pu", None)),
        "vmax_pu": get("vmax_pu", get("max_voltage_pu", None)),
        "feasible": get("feasible", ""),
        "operationally_feasible": get("operationally_feasible", ""),
        "infeasibility_reasons": get("infeasibility_reasons", ""),
    }


def experimental_parameters(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for case_name, meta in CASES.items():
        case = load_case(case_name, DEFAULT_CONFIG)
        rows.append(
            {
                "caso": case_name,
                "sistema": meta["label"],
                "motor_flujo_carga": "OpenDSS",
                "metodo_optimizacion": "Algoritmo evolutivo",
                "poblacion": meta["population"],
                "generaciones": meta["generations"],
                "semillas": ", ".join(str(seed) for seed in meta["seeds"]),
                "objetivo_1": "Perdidas tecnicas [kW]",
                "objetivo_2": "SAIDI [h/usuario-anio]",
                "metricas_complementarias": "SAIFI, ENS, Vmin, Vmax, feasible, voltage-feasible flag",
                "limite_inferior_tension_pu": case.operation_limits.get("v_min_limit", 0.90),
                "limite_superior_tension_pu": case.operation_limits.get("v_max_limit", 1.05),
                "criterio_feasible": "radialidad/conectividad + convergencia OpenDSS",
                "criterio_operationally_feasible": "historical field: feasible + tension dentro de limites + cargas servidas; no certifica validacion operativa completa",
                "numero_semillas": len(meta["seeds"]),
                "observacion_limites_termicos": "loading_limits_not_available se reporta como advertencia porque no hay ratings trazables.",
            }
        )
    return pd.DataFrame(rows)


def computational_summary(summary: pd.DataFrame) -> pd.DataFrame:
    seeds = summary[summary["row_type"] == "seed"].copy()
    seeds["tiempo_total_min"] = seeds["elapsed_seconds"] / 60.0
    seeds["cache_hits_pct"] = 100.0 * seeds["cache_hits"] / seeds["total_candidate_evaluations"]
    seeds["operationally_feasible_pct"] = 100.0 * seeds["operationally_feasible_count"] / seeds["feasible_count"]
    return seeds[
        [
            "case",
            "seed",
            "population",
            "generations",
            "elapsed_seconds",
            "tiempo_total_min",
            "total_candidate_evaluations",
            "unique_evaluations",
            "cache_hits",
            "cache_hits_pct",
            "feasible_count",
            "operationally_feasible_count",
            "operationally_feasible_pct",
            "pareto_size",
            "best_losses_kw",
            "best_saidi",
        ]
    ].rename(
        columns={
            "case": "caso",
            "seed": "semilla",
            "population": "poblacion",
            "generations": "generaciones",
            "elapsed_seconds": "tiempo_total_s",
            "total_candidate_evaluations": "solicitudes_evaluacion",
            "unique_evaluations": "evaluaciones_unicas",
            "feasible_count": "soluciones_feasible",
            "operationally_feasible_count": "soluciones_operationally_feasible",
            "pareto_size": "tamano_pareto_semilla",
            "best_losses_kw": "mejor_perdida_kw",
            "best_saidi": "mejor_saidi",
        }
    )


def base_vs_extremes(all_data: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    rows = []
    for case_name, data in all_data.items():
        base = base_evaluation(case_name)
        rows.append(solution_record(case_name, "Base", base, base))
        for label, row in selected_rows(case_name, data).items():
            rows.append(solution_record(case_name, label, row, base))
    return pd.DataFrame(rows)


def top_pareto(case_name: str, data: dict[str, pd.DataFrame], base: dict[str, object], n: int = 10) -> pd.DataFrame:
    pareto = data["pareto_operational"]
    if pareto.empty:
        pareto = data["pareto_feasible"]
    work = pareto.sort_values(["losses_kw", "saidi_h_user_year"]).head(n).copy()
    rows = []
    for rank, (_, row) in enumerate(work.iterrows(), start=1):
        rec = solution_record(case_name, f"Pareto {rank}", row, base)
        rows.append(
            {
                "ranking": rank,
                "interruptores_abiertos": rec["interruptores_abiertos"],
                "perdidas_kw": rec["perdidas_kw"],
                "saidi": rec["saidi_h_usuario_anio"],
                "saifi": rec["saifi_int_usuario_anio"],
                "ens": rec["ens_mwh_anio"],
                "vmin_pu": rec["vmin_pu"],
                "vmax_pu": rec["vmax_pu"],
                "reduccion_perdidas_pct": rec["reduccion_perdidas_pct"],
                "reduccion_saidi_pct": rec["reduccion_saidi_pct"],
                "reduccion_saifi_pct": rec["reduccion_saifi_pct"],
                "reduccion_ens_pct": rec["reduccion_ens_pct"],
                "feasible": rec["feasible"],
                "operationally_feasible": rec["operationally_feasible"],
                "semilla_fuente": rec["fuente"],
            }
        )
    return pd.DataFrame(rows)


def plot_pareto(case_name: str, data: dict[str, pd.DataFrame], base: dict[str, object], stem: str) -> None:
    all_df = data["all"]
    feasible = all_df[all_df["feasible"] == True]
    pareto_f = data["pareto_feasible"]
    pareto_o = data["pareto_operational"]
    selections = selected_rows(case_name, data)

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.scatter(feasible["losses_kw"], feasible["saidi_h_user_year"], s=12, color="#b8c2cc", alpha=0.35, label="Soluciones feasible")
    ax.plot(pareto_f["losses_kw"], pareto_f["saidi_h_user_year"], "-o", color="#2563eb", lw=1.7, ms=4, label="Pareto feasible")
    if not pareto_o.empty:
        ax.plot(pareto_o["losses_kw"], pareto_o["saidi_h_user_year"], "-s", color="#15803d", lw=1.5, ms=3.8, label="Pareto operativo")
    ax.scatter([base["losses_kw"]], [base["saidi_h_user_year"]], marker="*", s=130, color="#111827", label="Caso base", zorder=5)
    markers = {"Menor perdida": "D", "Menor SAIDI": "P", "Compromiso": "X"}
    colors = {"Menor perdida": "#dc2626", "Menor SAIDI": "#9333ea", "Compromiso": "#f59e0b"}
    for label, row in selections.items():
        ax.scatter([row["losses_kw"]], [row["saidi_h_user_year"]], marker=markers[label], s=75, color=colors[label], label=label, zorder=6)
    ax.set_xlabel("Perdidas tecnicas [kW]")
    ax.set_ylabel("SAIDI [h/usuario-anio]")
    ax.set_title(f"Frente Pareto - {CASES[case_name]['label']}")
    ax.grid(True, color="#e5e7eb", linewidth=0.8)
    ax.legend(fontsize=8, frameon=True)
    save_figure(fig, stem)


def plot_reduction_bars(table3: pd.DataFrame) -> None:
    work = table3[table3["tipo_solucion"].isin(["Menor perdida", "Menor SAIDI", "Compromiso"])].copy()
    metrics = [
        ("reduccion_perdidas_pct", "Perdidas"),
        ("reduccion_saidi_pct", "SAIDI"),
        ("reduccion_saifi_pct", "SAIFI"),
        ("reduccion_ens_pct", "ENS"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for ax, case_name in zip(axes, CASES):
        sub = work[work["caso"] == case_name]
        x = range(len(sub))
        width = 0.18
        for i, (col, label) in enumerate(metrics):
            ax.bar([v + (i - 1.5) * width for v in x], sub[col], width=width, label=label)
        ax.set_xticks(list(x))
        ax.set_xticklabels(sub["tipo_solucion"], rotation=20, ha="right")
        ax.set_title(CASES[case_name]["label"])
        ax.grid(True, axis="y", color="#e5e7eb")
        ax.set_ylabel("Reduccion [%]")
    axes[1].legend(fontsize=8, loc="upper right")
    save_figure(fig, "fig_03_reduction_bars")


def plot_voltage_profiles(case_name: str, data: dict[str, pd.DataFrame]) -> Path:
    case = load_case(case_name, DEFAULT_CONFIG)
    scenarios = {"Base": case.normally_open}
    for label, row in selected_rows(case_name, data).items():
        scenarios[label] = open_tuple(row["open_switches"])
    csv_path = TABLE_DIR / f"voltage_profiles_{case_name}.csv"
    profiles = extract_voltage_profiles_subprocess(case_name, scenarios, csv_path)

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    for label, sub in profiles.sort_values("bus_numeric").groupby("scenario"):
        ax.plot(sub["bus_numeric"], sub["voltage_pu"], marker="o", ms=2.8, lw=1.2, label=label)
    ax.axhline(0.90, color="#dc2626", lw=1.0, ls="--", label="Limite 0.90 pu")
    ax.axhline(1.05, color="#6b7280", lw=1.0, ls=":", label="Limite 1.05 pu")
    ax.set_xlabel("Nodo / bus")
    ax.set_ylabel("Tension [pu]")
    ax.set_title(f"Perfiles de tension - {CASES[case_name]['label']}")
    ax.grid(True, color="#e5e7eb")
    ax.legend(fontsize=8, ncol=2)
    save_figure(fig, f"fig_04{'a' if case_name == 'ieee33' else 'b'}_{case_name}_voltage_profiles")
    return csv_path


def extract_voltage_profiles_subprocess(case_name: str, scenarios: dict[str, list[int]], csv_path: Path) -> pd.DataFrame:
    code = r"""
import json
import sys
from pathlib import Path
import pandas as pd
root = Path(sys.argv[1])
case_name = sys.argv[2]
scenarios = json.loads(sys.argv[3])
csv_path = Path(sys.argv[4])
sys.path.insert(0, str(root / "src"))
from dnr.cases import DEFAULT_CONFIG, generated_data_root, load_case
from dnr.dss import write_dss
import opendssdirect as dss

case = load_case(case_name, DEFAULT_CONFIG)
dss_path = write_dss(case, generated_data_root(DEFAULT_CONFIG))
rows = []
for label, switches in scenarios.items():
    dss.Basic.ClearAll()
    dss.Text.Command(f'Compile "{dss_path}"')
    for switch in switches:
        dss.Text.Command(f"Disable Line.L{int(switch)}")
    dss.Text.Command("Solve")
    names = dss.Circuit.AllBusNames()
    mags = dss.Circuit.AllBusMagPu()
    phases = max(1, len(mags) // max(1, len(names)))
    for idx, bus in enumerate(names):
        vals = mags[idx * phases : (idx + 1) * phases]
        text = str(bus)
        numeric = int(float(text)) if text.replace(".", "", 1).isdigit() else idx
        rows.append({
            "case": case_name,
            "scenario": label,
            "bus": bus,
            "bus_numeric": numeric,
            "voltage_pu": min(vals) if vals else None,
        })
pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8")
"""
    subprocess.run(
        [sys.executable, "-c", code, str(PROJECT_ROOT), case_name, json.dumps(scenarios), str(csv_path)],
        check=True,
        cwd=PROJECT_ROOT,
    )
    return pd.read_csv(csv_path)


def plot_feasibility_distribution(all_data: dict[str, dict[str, pd.DataFrame]]) -> None:
    rows = []
    for case_name, data in all_data.items():
        df = data["all"]
        reasons = df["infeasibility_reasons"].fillna("").astype(str)
        rows.append(
            {
                "case": case_name,
                "total": len(df),
                "feasible": int(df["feasible"].sum()),
                "operational": int(df["operationally_feasible"].sum()),
                "voltage_below": int(reasons.str.contains("voltage_below_limit", regex=False).sum()),
                "voltage_above": int(reasons.str.contains("voltage_above_limit", regex=False).sum()),
            }
        )
    dist = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    cols = [("total", "Total"), ("feasible", "Feasible"), ("operational", "Operativas"), ("voltage_below", "Bajo voltaje"), ("voltage_above", "Sobre voltaje")]
    x = range(len(dist))
    width = 0.15
    for i, (col, label) in enumerate(cols):
        ax.bar([v + (i - 2) * width for v in x], dist[col], width=width, label=label)
    ax.set_xticks(list(x))
    ax.set_xticklabels([CASES[c]["label"] for c in dist["case"]])
    ax.set_ylabel("Numero de soluciones")
    ax.set_title("Distribucion de factibilidad")
    ax.grid(True, axis="y", color="#e5e7eb")
    ax.legend(fontsize=8)
    save_figure(fig, "fig_05_feasibility_distribution")


def validate_values(all_data: dict[str, dict[str, pd.DataFrame]]) -> list[str]:
    checks = []
    ieee_best_loss = float(all_data["ieee33"]["best_loss"].iloc[0]["losses_kw"])
    ieee_best_saidi = float(all_data["ieee33"]["best_saidi"].iloc[0]["saidi_h_user_year"])
    op_best_loss = float(all_data["operator"]["best_loss"].iloc[0]["losses_kw"])
    op_best_saidi = float(all_data["operator"]["best_saidi"].iloc[0]["saidi_h_user_year"])
    op_comp = all_data["operator"]["compromise"].iloc[0]
    checks.append(f"ieee33 mejor perdida = {ieee_best_loss:.3f} kW")
    checks.append(f"ieee33 mejor SAIDI = {ieee_best_saidi:.6f}")
    checks.append(f"operator mejor perdida = {op_best_loss:.3f} kW")
    checks.append(f"operator mejor SAIDI = {op_best_saidi:.6f}")
    checks.append(f"operator compromiso = {float(op_comp['losses_kw']):.3f} kW, SAIDI {float(op_comp['saidi_h_user_year']):.6f}")
    return checks


# Matplotlib is unstable in this Windows/Conda thread, so article figures are
# rendered with Pillow for PNG/PDF and with small hand-written SVG primitives.
def _font(size: int = 18) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, size: int = 18, fill: str = "#111827", anchor: str | None = None) -> None:
    draw.text(xy, text, font=_font(size), fill=fill, anchor=anchor)


def _save_pil_and_svg(img: Image.Image, svg: str, stem: str) -> None:
    png = FIG_DIR / f"{stem}.png"
    pdf = FIG_DIR / f"{stem}.pdf"
    svg_path = FIG_DIR / f"{stem}.svg"
    img.save(png, dpi=(600, 600))
    img.convert("RGB").save(pdf, "PDF", resolution=600.0)
    svg_path.write_text(svg, encoding="utf-8")


def _chart_area(width: int, height: int) -> tuple[int, int, int, int]:
    return 90, 60, width - 45, height - 90


def _scale(xmin: float, xmax: float, ymin: float, ymax: float, area: tuple[int, int, int, int]):
    left, top, right, bottom = area
    xspan = xmax - xmin or 1.0
    yspan = ymax - ymin or 1.0

    def sx(x: float) -> float:
        return left + (x - xmin) / xspan * (right - left)

    def sy(y: float) -> float:
        return bottom - (y - ymin) / yspan * (bottom - top)

    return sx, sy


def _base_chart(title: str, xlabel: str, ylabel: str, width: int = 1500, height: int = 1050):
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    area = _chart_area(width, height)
    left, top, right, bottom = area
    _draw_text(draw, (width / 2, 22), title, 30, anchor="ma")
    _draw_text(draw, (width / 2, height - 34), xlabel, 24, anchor="mm")
    _draw_text(draw, (22, height / 2), ylabel, 22)
    draw.line((left, bottom, right, bottom), fill="#111827", width=2)
    draw.line((left, top, left, bottom), fill="#111827", width=2)
    for i in range(1, 5):
        x = left + i * (right - left) / 5
        y = top + i * (bottom - top) / 5
        draw.line((x, top, x, bottom), fill="#e5e7eb", width=1)
        draw.line((left, y, right, y), fill="#e5e7eb", width=1)
    return img, draw, area


def _draw_axes(draw: ImageDraw.ImageDraw, area: tuple[int, int, int, int], title: str, xlabel: str, ylabel: str, size: int = 20) -> None:
    left, top, right, bottom = area
    _draw_text(draw, ((left + right) / 2, top - 34), title, size, anchor="ma")
    _draw_text(draw, ((left + right) / 2, bottom + 42), xlabel, 18, anchor="ma")
    _draw_text(draw, (left - 62, (top + bottom) / 2), ylabel, 17)
    draw.line((left, bottom, right, bottom), fill="#111827", width=2)
    draw.line((left, top, left, bottom), fill="#111827", width=2)
    for i in range(1, 5):
        x = left + i * (right - left) / 5
        y = top + i * (bottom - top) / 5
        draw.line((x, top, x, bottom), fill="#e5e7eb", width=1)
        draw.line((left, y, right, y), fill="#e5e7eb", width=1)


def _inside(px: float, py: float, area: tuple[int, int, int, int] | None) -> bool:
    if area is None:
        return True
    left, top, right, bottom = area
    return left <= px <= right and top <= py <= bottom


def _scatter(draw: ImageDraw.ImageDraw, points, sx, sy, color: str, radius: int = 5, clip_area: tuple[int, int, int, int] | None = None) -> None:
    for x, y in points:
        px, py = sx(float(x)), sy(float(y))
        if not _inside(px, py, clip_area):
            continue
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color, outline=color)


def _line(draw: ImageDraw.ImageDraw, points, sx, sy, color: str, width: int = 4, radius: int = 6, clip_area: tuple[int, int, int, int] | None = None) -> None:
    pts = [(sx(float(x)), sy(float(y))) for x, y in points]
    visible = [(px, py) for px, py in pts if _inside(px, py, clip_area)]
    if len(visible) > 1:
        draw.line(visible, fill=color, width=width)
    for px, py in pts:
        if not _inside(px, py, clip_area):
            continue
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color, outline=color)


def _legend(draw: ImageDraw.ImageDraw, items: list[tuple[str, str]], x: int, y: int) -> None:
    for i, (label, color) in enumerate(items):
        yy = y + i * 30
        draw.rectangle((x, yy, x + 18, yy + 18), fill=color)
        _draw_text(draw, (x + 28, yy - 2), label, 18)


def _scatter_svg(stem: str, title: str, xlabel: str, ylabel: str, xmin, xmax, ymin, ymax, series: list[dict], width=900, height=620) -> str:
    area = (75, 45, width - 30, height - 70)
    sx, sy = _scale(xmin, xmax, ymin, ymax, area)
    left, top, right, bottom = area
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="24" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>',
        f'<text x="{width/2}" y="{height-18}" text-anchor="middle" font-family="Arial" font-size="14">{xlabel}</text>',
        f'<text x="16" y="{height/2}" font-family="Arial" font-size="14">{ylabel}</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#111827"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#111827"/>',
    ]
    for s in series:
        pts = [(sx(float(x)), sy(float(y))) for x, y in s["points"]]
        if s.get("line") and len(pts) > 1:
            poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            parts.append(f'<polyline points="{poly}" fill="none" stroke="{s["color"]}" stroke-width="1.5"/>')
        for x, y in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s.get("r", 3)}" fill="{s["color"]}" opacity="{s.get("opacity", 1)}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def plot_pareto(case_name: str, data: dict[str, pd.DataFrame], base: dict[str, object], stem: str) -> None:
    all_df = data["all"]
    feasible = all_df[all_df["feasible"] == True]
    pareto_f = data["pareto_feasible"]
    pareto_o = data["pareto_operational"]
    selections = selected_rows(case_name, data)
    xs = pd.concat([feasible["losses_kw"], pd.Series([base["losses_kw"]])])
    ys = pd.concat([feasible["saidi_h_user_year"], pd.Series([base["saidi_h_user_year"]])])
    xmin, xmax = float(xs.min()) * 0.98, float(xs.max()) * 1.02
    ymin, ymax = float(ys.min()) * 0.96, float(ys.max()) * 1.04
    pareto_all = pd.concat([pareto_f, pareto_o], ignore_index=True)
    zxmin, zxmax = float(pareto_all["losses_kw"].min()) * 0.985, float(pareto_all["losses_kw"].max()) * 1.015
    zymin, zymax = float(pareto_all["saidi_h_user_year"].min()) * 0.985, float(pareto_all["saidi_h_user_year"].max()) * 1.015

    title = "Pareto front for the IEEE 33-bus system" if case_name == "ieee33" else "Pareto front for the real distribution system"
    img = Image.new("RGB", (2200, 1200), "white")
    draw = ImageDraw.Draw(img)
    _draw_text(draw, (1100, 22), title, 32, anchor="ma")
    area_full = (105, 115, 1020, 860)
    area_zoom = (1160, 115, 2075, 860)
    _draw_axes(draw, area_full, "(a) Complete feasible solution cloud", "Technical losses [kW]", "SAIDI [h/customer-year]")
    _draw_axes(draw, area_zoom, "(b) Zoomed Pareto region", "Technical losses [kW]", "SAIDI [h/customer-year]")
    colors = {"Minimum-loss": "#dc2626", "Minimum-SAIDI": "#9333ea", "Compromise": "#f59e0b"}
    label_map = {"Menor perdida": "Minimum-loss", "Menor SAIDI": "Minimum-SAIDI", "Compromiso": "Compromise"}
    for area, bounds in [(area_full, (xmin, xmax, ymin, ymax)), (area_zoom, (zxmin, zxmax, zymin, zymax))]:
        sx, sy = _scale(*bounds, area)
        _scatter(draw, zip(feasible["losses_kw"], feasible["saidi_h_user_year"]), sx, sy, "#cbd5e1", 3 if area == area_full else 4, area)
        _line(draw, zip(pareto_f["losses_kw"], pareto_f["saidi_h_user_year"]), sx, sy, "#2563eb", 5, 7, area)
        if not pareto_o.empty:
            _line(draw, zip(pareto_o["losses_kw"], pareto_o["saidi_h_user_year"]), sx, sy, "#15803d", 4, 6, area)
        _scatter(draw, [(base["losses_kw"], base["saidi_h_user_year"])], sx, sy, "#111827", 11, area)
        for old_label, row in selections.items():
            label = label_map[old_label]
            _scatter(draw, [(row["losses_kw"], row["saidi_h_user_year"])], sx, sy, colors[label], 11, area)
    _legend(draw, [("Feasible solutions", "#cbd5e1"), ("Feasible Pareto", "#2563eb"), ("Operational Pareto", "#15803d"), ("Base case", "#111827"), ("Minimum-loss", "#dc2626"), ("Minimum-SAIDI", "#9333ea"), ("Compromise", "#f59e0b")], 1200, 930)
    series = [
        {"points": list(zip(feasible["losses_kw"], feasible["saidi_h_user_year"])), "color": "#cbd5e1", "opacity": 0.45, "r": 2},
        {"points": list(zip(pareto_f["losses_kw"], pareto_f["saidi_h_user_year"])), "color": "#2563eb", "line": True, "r": 4},
        {"points": list(zip(pareto_o["losses_kw"], pareto_o["saidi_h_user_year"])), "color": "#15803d", "line": True, "r": 3},
        {"points": [(base["losses_kw"], base["saidi_h_user_year"])], "color": "#111827", "r": 6},
    ]
    for label, row in selections.items():
        series.append({"points": [(row["losses_kw"], row["saidi_h_user_year"])], "color": colors[label_map[label]], "r": 5})
    svg = _scatter_svg(stem, title, "Technical losses [kW]", "SAIDI [h/customer-year]", xmin, xmax, ymin, ymax, series)
    _save_pil_and_svg(img, svg, stem)


def plot_reduction_bars(table3: pd.DataFrame) -> None:
    work = table3[table3["tipo_solucion"].isin(["Menor perdida", "Menor SAIDI", "Compromiso"])].copy()
    metrics = [("reduccion_perdidas_pct", "Losses"), ("reduccion_saidi_pct", "SAIDI"), ("reduccion_saifi_pct", "SAIFI"), ("reduccion_ens_pct", "ENS")]
    solution_names = {"Menor perdida": "Minimum-loss", "Menor SAIDI": "Minimum-SAIDI", "Compromiso": "Compromise"}
    img = Image.new("RGB", (1500, 850), "white")
    draw = ImageDraw.Draw(img)
    _draw_text(draw, (750, 24), "Reduction of performance indicators", 30, anchor="ma")
    maxv = float(work[[m[0] for m in metrics]].max().max()) * 1.15
    colors = ["#2563eb", "#15803d", "#dc2626", "#f59e0b"]
    for cidx, case_name in enumerate(CASES):
        sub = work[work["caso"] == case_name].reset_index(drop=True)
        x0 = 110 + cidx * 700
        y0, h = 720, 560
        _draw_text(draw, (x0 + 260, 64), CASES[case_name]["label"], 24, anchor="ma")
        draw.line((x0, y0, x0 + 520, y0), fill="#111827", width=2)
        draw.line((x0, y0, x0, y0 - h), fill="#111827", width=2)
        for i, (_, label) in enumerate(metrics):
            for j, sol in sub.iterrows():
                val = float(sol[metrics[i][0]])
                bx = x0 + 35 + j * 160 + i * 30
                by = y0 - val / maxv * h
                draw.rectangle((bx, by, bx + 24, y0), fill=colors[i])
                _draw_text(draw, (bx + 12, by - 18), f"{val:.1f}", 13, anchor="ma")
        for j, sol in sub.iterrows():
            _draw_text(draw, (x0 + 70 + j * 160, y0 + 12), solution_names[sol["tipo_solucion"]], 16, anchor="ma")
    _legend(draw, [(label, colors[i]) for i, (_, label) in enumerate(metrics)], 1220, 90)
    svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="560" viewBox="0 0 1000 560">', '<rect width="100%" height="100%" fill="white"/>', '<text x="500" y="28" text-anchor="middle" font-family="Arial" font-size="18">Reduction of performance indicators</text>']
    maxv_svg = maxv
    for cidx, case_name in enumerate(CASES):
        sub = work[work["caso"] == case_name].reset_index(drop=True)
        x0 = 70 + cidx * 470
        y0, h = 480, 350
        svg_parts.append(f'<text x="{x0+180}" y="58" text-anchor="middle" font-family="Arial" font-size="15">{CASES[case_name]["label"]}</text>')
        svg_parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0+360}" y2="{y0}" stroke="#111827"/>')
        svg_parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0-h}" stroke="#111827"/>')
        for i, (col, _) in enumerate(metrics):
            for j, sol in sub.iterrows():
                val = float(sol[col])
                bx = x0 + 22 + j * 112 + i * 19
                bh = val / maxv_svg * h
                svg_parts.append(f'<rect x="{bx:.1f}" y="{y0-bh:.1f}" width="16" height="{bh:.1f}" fill="{colors[i]}"/>')
                svg_parts.append(f'<text x="{bx+8:.1f}" y="{y0-bh-4:.1f}" text-anchor="middle" font-family="Arial" font-size="8">{val:.1f}</text>')
        for j, sol in sub.iterrows():
            svg_parts.append(f'<text x="{x0+56+j*112}" y="{y0+18}" text-anchor="middle" font-family="Arial" font-size="10">{solution_names[sol["tipo_solucion"]]}</text>')
    for i, (_, label) in enumerate(metrics):
        yy = 90 + i * 22
        svg_parts.append(f'<rect x="850" y="{yy}" width="14" height="14" fill="{colors[i]}"/><text x="870" y="{yy+12}" font-family="Arial" font-size="12">{label}</text>')
    svg_parts.append("</svg>")
    svg = "\n".join(svg_parts)
    _save_pil_and_svg(img, svg, "fig_03_reduction_bars")


def plot_voltage_profiles(case_name: str, data: dict[str, pd.DataFrame]) -> Path:
    case = load_case(case_name, DEFAULT_CONFIG)
    scenarios = {"Base": case.normally_open}
    for label, row in selected_rows(case_name, data).items():
        scenarios[label] = open_tuple(row["open_switches"])
    csv_path = TABLE_DIR / f"voltage_profiles_{case_name}.csv"
    profiles = extract_voltage_profiles_subprocess(case_name, scenarios, csv_path)
    title = "Voltage profiles for the IEEE 33-bus system" if case_name == "ieee33" else "Voltage profiles for the real distribution system"
    img, draw, area = _base_chart(title, "Bus", "Voltage magnitude [p.u.]", width=1800 if case_name == "operator" else 1500, height=1050)
    xmin, xmax = profiles["bus_numeric"].min(), profiles["bus_numeric"].max()
    ymin, ymax = min(0.88, profiles["voltage_pu"].min() * 0.995), max(1.055, profiles["voltage_pu"].max() * 1.005)
    sx, sy = _scale(float(xmin), float(xmax), float(ymin), float(ymax), area)
    colors = {"Base": "#111827", "Menor perdida": "#dc2626", "Menor SAIDI": "#9333ea", "Compromiso": "#f59e0b"}
    label_map = {"Base": "Base", "Menor perdida": "Minimum-loss", "Menor SAIDI": "Minimum-SAIDI", "Compromiso": "Compromise"}
    if case_name == "operator":
        draw.rectangle((area[0], sy(0.90), area[2], area[3]), fill="#fee2e2")
    for label, sub in profiles.sort_values("bus_numeric").groupby("scenario"):
        _line(draw, zip(sub["bus_numeric"], sub["voltage_pu"]), sx, sy, colors.get(label, "#2563eb"), 3, 3)
    draw.line((area[0], sy(0.90), area[2], sy(0.90)), fill="#dc2626", width=2)
    draw.line((area[0], sy(1.05), area[2], sy(1.05)), fill="#6b7280", width=2)
    _legend(draw, [(label_map[k], v) for k, v in colors.items()] + [("Lower limit 0.90", "#dc2626"), ("Upper limit 1.05", "#6b7280")], 1280 if case_name == "operator" else 1080, 85)
    series = [{"points": list(zip(sub["bus_numeric"], sub["voltage_pu"])), "color": colors.get(label, "#2563eb"), "line": True, "r": 2} for label, sub in profiles.groupby("scenario")]
    svg = _scatter_svg("voltage", title, "Bus", "Voltage magnitude [p.u.]", float(xmin), float(xmax), float(ymin), float(ymax), series)
    _save_pil_and_svg(img, svg, f"fig_04{'a' if case_name == 'ieee33' else 'b'}_{case_name}_voltage_profiles")
    return csv_path


def plot_feasibility_distribution(all_data: dict[str, dict[str, pd.DataFrame]]) -> None:
    rows = []
    for case_name, data in all_data.items():
        df = data["all"]
        reasons = df["infeasibility_reasons"].fillna("").astype(str)
        rows.append({"case": case_name, "Total evaluated": len(df), "Feasible": int(df["feasible"].sum()), "Voltage-feasible under modeled constraints": int(df["operationally_feasible"].sum()), "Voltage below limit": int(reasons.str.contains("voltage_below_limit", regex=False).sum()), "Voltage above limit": int(reasons.str.contains("voltage_above_limit", regex=False).sum())})
    dist = pd.DataFrame(rows)
    img = Image.new("RGB", (1300, 820), "white")
    draw = ImageDraw.Draw(img)
    _draw_text(draw, (650, 24), "Distribution of feasible and voltage-feasible solutions", 28, anchor="ma")
    colors = ["#111827", "#2563eb", "#15803d", "#dc2626", "#f59e0b"]
    cols = ["Total evaluated", "Feasible", "Voltage-feasible under modeled constraints", "Voltage below limit", "Voltage above limit"]
    maxv = float(dist[cols].max().max()) * 1.1
    for cidx, row in dist.iterrows():
        x0 = 130 + cidx * 560
        y0, h = 700, 560
        _draw_text(draw, (x0 + 220, 64), CASES[row["case"]]["label"], 24, anchor="ma")
        draw.line((x0, y0, x0 + 430, y0), fill="#111827", width=2)
        draw.line((x0, y0, x0, y0 - h), fill="#111827", width=2)
        for i, col in enumerate(cols):
            val = float(row[col])
            bx = x0 + 30 + i * 78
            by = y0 - val / maxv * h
            draw.rectangle((bx, by, bx + 42, y0), fill=colors[i])
            _draw_text(draw, (bx + 21, by - 18), f"{int(val)}", 13, anchor="ma")
            _draw_text(draw, (bx + 21, y0 + 10), str(i + 1), 14, anchor="ma")
    _legend(draw, list(zip(cols, colors)), 1020, 90)
    svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="560" viewBox="0 0 1050 560">', '<rect width="100%" height="100%" fill="white"/>', '<text x="525" y="28" text-anchor="middle" font-family="Arial" font-size="18">Distribution of feasible and voltage-feasible solutions</text>']
    for cidx, row in dist.iterrows():
        x0 = 80 + cidx * 405
        y0, h = 480, 350
        svg_parts.append(f'<text x="{x0+160}" y="58" text-anchor="middle" font-family="Arial" font-size="15">{CASES[row["case"]]["label"]}</text>')
        svg_parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0+315}" y2="{y0}" stroke="#111827"/>')
        svg_parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0-h}" stroke="#111827"/>')
        for i, col in enumerate(cols):
            val = float(row[col])
            bx = x0 + 26 + i * 56
            bh = val / maxv * h
            svg_parts.append(f'<rect x="{bx:.1f}" y="{y0-bh:.1f}" width="34" height="{bh:.1f}" fill="{colors[i]}"/>')
            svg_parts.append(f'<text x="{bx+17:.1f}" y="{y0-bh-4:.1f}" text-anchor="middle" font-family="Arial" font-size="8">{int(val)}</text>')
            svg_parts.append(f'<text x="{bx+17:.1f}" y="{y0+16}" text-anchor="middle" font-family="Arial" font-size="9">{i+1}</text>')
    for i, col in enumerate(cols):
        yy = 90 + i * 22
        svg_parts.append(f'<rect x="790" y="{yy}" width="14" height="14" fill="{colors[i]}"/><text x="810" y="{yy+12}" font-family="Arial" font-size="12">{col}</text>')
    svg_parts.append("</svg>")
    svg = "\n".join(svg_parts)
    _save_pil_and_svg(img, svg, "fig_05_feasibility_distribution")


def main() -> None:
    ensure_dirs()
    summary = pd.read_csv(DIAG_DIR / "final_runs_execution_summary.csv")
    all_data = {case: read_combined(case) for case in CASES}

    outputs: list[Path] = []
    table1 = experimental_parameters(summary)
    outputs.extend(write_table(table1, "table_01_experimental_parameters"))
    table2 = computational_summary(summary)
    outputs.extend(write_table(table2, "table_02_computational_summary_by_seed"))
    table3 = base_vs_extremes(all_data)
    outputs.extend(write_table(table3, "table_03_base_vs_pareto_extremes"))
    table4 = top_pareto("operator", all_data["operator"], base_evaluation("operator"), n=10)
    outputs.extend(write_table(table4, "table_04_operator_top_pareto"))
    table5 = top_pareto("ieee33", all_data["ieee33"], base_evaluation("ieee33"), n=10)
    outputs.extend(write_table(table5, "table_05_ieee33_top_pareto"))

    plot_pareto("ieee33", all_data["ieee33"], base_evaluation("ieee33"), "fig_01_ieee33_pareto_losses_saidi")
    plot_pareto("operator", all_data["operator"], base_evaluation("operator"), "fig_02_operator_pareto_losses_saidi")
    plot_reduction_bars(table3)
    voltage_csvs = [plot_voltage_profiles("ieee33", all_data["ieee33"]), plot_voltage_profiles("operator", all_data["operator"])]
    plot_feasibility_distribution(all_data)

    figure_files = sorted(FIG_DIR.glob("fig_*.*"))
    checks = validate_values(all_data)
    report_lines = [
        "# Reporte de tablas y figuras para articulo",
        "",
        "## Entradas usadas",
        "- results/final_runs/ieee33/combined/*.csv",
        "- results/final_runs/operator/combined/*.csv",
        "- results/diagnostics/final_runs_execution_summary.csv",
        "",
        "## Tablas generadas",
        *[f"- {path}" for path in sorted(TABLE_DIR.glob("table_*.csv"))],
        *[f"- {path}" for path in sorted(TABLE_DIR.glob("table_*.md"))],
        "",
        "## Figuras generadas",
        *[f"- {path}" for path in figure_files],
        "",
        "## Criterios de seleccion",
        "- Menor perdida: minimo de `losses_kw` entre soluciones feasible combinadas.",
        "- Menor SAIDI: minimo de `saidi_h_user_year` entre soluciones feasible combinadas.",
        "- Compromiso: menor distancia normalizada al punto ideal en el Pareto feasible combinado.",
        "- Top Pareto: se uso el archivo historico `pareto_operationally_feasible.csv`; su nombre se conserva por compatibilidad y debe interpretarse como voltage-feasible under modeled constraints.",
        "",
        "## Perfiles de tension",
        "Los perfiles por nodo no estaban en los CSV combinados. Se evaluaron unicamente las configuraciones puntuales base, menor perdida, menor SAIDI y compromiso, sin optimizacion.",
        *[f"- {path}" for path in voltage_csvs],
        "",
        "## Advertencias",
        "- `loading_limits_not_available` se conserva como advertencia porque no hay ratings termicos trazables.",
        "- No se ejecutaron optimizaciones ni se modificaron resultados definitivos.",
        "",
        "## Validaciones",
        *[f"- {check}" for check in checks],
        "- La validacion previa de Pareto combinado reporto cero soluciones dominadas.",
    ]
    report_path = DIAG_DIR / "article_outputs_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Tablas: {TABLE_DIR}")
    print(f"Figuras: {FIG_DIR}")
    print(f"Reporte: {report_path}")


if __name__ == "__main__":
    main()
