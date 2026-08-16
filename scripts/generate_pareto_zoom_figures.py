from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ARTICLE = PROJECT_ROOT / "results_article"
OUT_DIR = RESULTS_ARTICLE / "figures_pareto_zoom"
FINAL_RUNS = PROJECT_ROOT / "results" / "final_runs"


LOSS_COLUMNS = ["losses_kw", "P_loss_kW", "P_loss", "losses_kW", "technical_losses_kW", "ploss_kw"]
SAIDI_COLUMNS = ["saidi_h_user_year", "SAIDI_h_user_year", "SAIDI", "saidi", "SAIDI_h_customer_year"]
FEASIBLE_COLUMNS = ["feasible", "is_feasible"]
OP_FEASIBLE_COLUMNS = ["operationally_feasible", "op_feas", "operational_feasible"]
OPEN_COLUMNS = ["open_switches", "open_lines", "opened_switches"]
SOLUTION_COLUMNS = ["solution_type", "label", "category"]


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_column(df: pd.DataFrame, candidates: list[str], required: bool = True) -> str | None:
    normalized = {str(col).lower(): col for col in df.columns}
    for name in candidates:
        if name.lower() in normalized:
            return normalized[name.lower()]
    if required:
        raise KeyError(f"None of the expected columns were found: {candidates}. Available: {list(df.columns)}")
    return None


def to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y", "si", "sí"])


def canonical_solution_type(value: object) -> str:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "base": "base",
        "caso_base": "base",
        "minimum_loss": "min_loss",
        "min_loss": "min_loss",
        "menor_perdida": "min_loss",
        "minimum_saidi": "min_SAIDI",
        "min_saidi": "min_SAIDI",
        "menor_saidi": "min_SAIDI",
        "compromise": "compromise",
        "compromiso": "compromise",
    }
    return aliases.get(text, text)


def normalize_all(df: pd.DataFrame) -> pd.DataFrame:
    loss_col = find_column(df, LOSS_COLUMNS)
    saidi_col = find_column(df, SAIDI_COLUMNS)
    feasible_col = find_column(df, FEASIBLE_COLUMNS)
    op_col = find_column(df, OP_FEASIBLE_COLUMNS, required=False)
    open_col = find_column(df, OPEN_COLUMNS, required=False)

    out = df.copy()
    out["_losses_kw"] = pd.to_numeric(out[loss_col], errors="coerce")
    out["_saidi"] = pd.to_numeric(out[saidi_col], errors="coerce")
    out["_feasible"] = to_bool(out[feasible_col])
    out["_operationally_feasible"] = to_bool(out[op_col]) if op_col else False
    out["_open_switches"] = out[open_col].astype(str) if open_col else ""
    return out


def normalize_selected(df: pd.DataFrame) -> pd.DataFrame:
    loss_col = find_column(df, LOSS_COLUMNS)
    saidi_col = find_column(df, SAIDI_COLUMNS)
    feasible_col = find_column(df, FEASIBLE_COLUMNS, required=False)
    op_col = find_column(df, OP_FEASIBLE_COLUMNS, required=False)
    open_col = find_column(df, OPEN_COLUMNS, required=False)
    sol_col = find_column(df, SOLUTION_COLUMNS)

    out = pd.DataFrame()
    out["solution_type"] = df[sol_col].map(canonical_solution_type)
    out["losses_kw"] = pd.to_numeric(df[loss_col], errors="coerce")
    out["saidi"] = pd.to_numeric(df[saidi_col], errors="coerce")
    out["feasible"] = to_bool(df[feasible_col]) if feasible_col else None
    out["operationally_feasible"] = to_bool(df[op_col]) if op_col else None
    out["open_switches"] = df[open_col].astype(str) if open_col else ""
    return out


def pareto_front(df: pd.DataFrame, feasible_mask: pd.Series) -> pd.DataFrame:
    work = df[feasible_mask & df["_losses_kw"].notna() & df["_saidi"].notna()].copy()
    keep = []
    losses = work["_losses_kw"].to_numpy()
    saidi = work["_saidi"].to_numpy()
    indices = list(work.index)
    for pos, idx in enumerate(indices):
        dominated = (
            (losses <= losses[pos])
            & (saidi <= saidi[pos])
            & ((losses < losses[pos]) | (saidi < saidi[pos]))
        ).any()
        if not dominated:
            keep.append(idx)
    return work.loc[keep].sort_values(["_losses_kw", "_saidi"]).reset_index(drop=True)


def compromise_from_front(front: pd.DataFrame) -> pd.Series:
    if front.empty:
        raise ValueError("Cannot compute compromise from an empty Pareto front.")
    loss_span = front["_losses_kw"].max() - front["_losses_kw"].min()
    saidi_span = front["_saidi"].max() - front["_saidi"].min()
    loss_span = loss_span if loss_span else 1.0
    saidi_span = saidi_span if saidi_span else 1.0
    tmp = front.copy()
    tmp["_loss_norm"] = (tmp["_losses_kw"] - tmp["_losses_kw"].min()) / loss_span
    tmp["_saidi_norm"] = (tmp["_saidi"] - tmp["_saidi"].min()) / saidi_span
    tmp["_distance"] = (tmp["_loss_norm"] ** 2 + tmp["_saidi_norm"] ** 2) ** 0.5
    return tmp.loc[tmp["_distance"].idxmin()]


def load_case_data(case: str) -> dict[str, object]:
    combined = FINAL_RUNS / case / "combined"
    table = RESULTS_ARTICLE / "tables" / f"table_results_{case}.csv"
    if not combined.exists() or not table.exists():
        raise FileNotFoundError(f"Missing combined outputs or representative table for {case}.")

    all_df = normalize_all(pd.read_csv(combined / "all_combined.csv"))
    selected = normalize_selected(pd.read_csv(table))
    feasible_front = pareto_front(all_df, all_df["_feasible"])
    op_front = pareto_front(all_df, all_df["_operationally_feasible"])

    selected_by_type: dict[str, pd.Series] = {}
    for solution_type in ["base", "min_loss", "min_SAIDI", "compromise"]:
        subset = selected[selected["solution_type"] == solution_type]
        if not subset.empty:
            selected_by_type[solution_type] = subset.iloc[0]

    warnings: list[str] = ["Pareto fronts recalculated from all_combined.csv for traceability."]
    if "compromise" not in selected_by_type:
        source_front = op_front if not op_front.empty else feasible_front
        comp = compromise_from_front(source_front)
        selected_by_type["compromise"] = pd.Series(
            {
                "solution_type": "compromise",
                "losses_kw": comp["_losses_kw"],
                "saidi": comp["_saidi"],
                "feasible": comp["_feasible"],
                "operationally_feasible": comp["_operationally_feasible"],
                "open_switches": comp["_open_switches"],
            }
        )
        warnings.append("Compromise solution was recomputed because it was missing from the representative table.")

    return {
        "all": all_df,
        "feasible": all_df[all_df["_feasible"]].copy(),
        "pareto_feasible": feasible_front,
        "pareto_operational": op_front,
        "selected": selected_by_type,
        "warnings": warnings,
        "input_files": [
            str(combined / "all_combined.csv"),
            str(combined / "pareto_feasible.csv"),
            str(combined / "pareto_operationally_feasible.csv"),
            str(table),
        ],
    }


def selected_point_dataframe(selected: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for key in ["base", "min_loss", "min_SAIDI", "compromise"]:
        if key not in selected:
            continue
        row = selected[key]
        rows.append(
            {
                "solution_type": key,
                "losses_kw": row["losses_kw"],
                "saidi_h_customer_year": row["saidi"],
                "feasible": row.get("feasible"),
                "operationally_feasible": row.get("operationally_feasible"),
                "open_switches": row.get("open_switches", ""),
            }
        )
    return pd.DataFrame(rows)


def combined_plot_dataframe(data: dict[str, object]) -> pd.DataFrame:
    feasible = data["feasible"][["_losses_kw", "_saidi", "_open_switches", "_feasible", "_operationally_feasible"]].copy()
    feasible["category"] = "feasible_solution"
    p_feas = data["pareto_feasible"][["_losses_kw", "_saidi", "_open_switches", "_feasible", "_operationally_feasible"]].copy()
    p_feas["category"] = "pareto_feasible"
    p_op = data["pareto_operational"][["_losses_kw", "_saidi", "_open_switches", "_feasible", "_operationally_feasible"]].copy()
    p_op["category"] = "pareto_operational"
    out = pd.concat([feasible, p_feas, p_op], ignore_index=True)
    return out.rename(
        columns={
            "_losses_kw": "losses_kw",
            "_saidi": "saidi_h_customer_year",
            "_open_switches": "open_switches",
            "_feasible": "feasible",
            "_operationally_feasible": "operationally_feasible",
        }
    )


def zoom_limits(data: dict[str, object]) -> tuple[tuple[float, float], tuple[float, float]]:
    frames = [data["pareto_feasible"], data["pareto_operational"]]
    selected = data["selected"]
    selected_rows = []
    for key in ["base", "min_loss", "min_SAIDI", "compromise"]:
        if key in selected:
            selected_rows.append((float(selected[key]["losses_kw"]), float(selected[key]["saidi"])))

    x_vals = []
    y_vals = []
    for frame in frames:
        if not frame.empty:
            x_vals.extend(frame["_losses_kw"].tolist())
            y_vals.extend(frame["_saidi"].tolist())
    for x, y in selected_rows:
        x_vals.append(x)
        y_vals.append(y)

    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    x_pad = max((x_max - x_min) * 0.08, 1e-6)
    y_pad = max((y_max - y_min) * 0.10, 1e-6)
    return (x_min - x_pad, x_max + x_pad), (y_min - y_pad, y_max + y_pad)


def draw_panel(ax, data: dict[str, object], zoom: bool) -> None:
    feasible = data["feasible"]
    p_feas = data["pareto_feasible"]
    p_op = data["pareto_operational"]
    selected = data["selected"]

    ax.scatter(feasible["_losses_kw"], feasible["_saidi"], s=10, c="#9baec8", alpha=0.32, edgecolors="none")
    if not p_feas.empty:
        ax.plot(p_feas["_losses_kw"].to_numpy(), p_feas["_saidi"].to_numpy(), "-o", color="#1f77b4", lw=1.9, ms=4.2)
    if not p_op.empty:
        ax.plot(p_op["_losses_kw"].to_numpy(), p_op["_saidi"].to_numpy(), "-o", color="#2ca02c", lw=1.9, ms=4.0)

    markers = {
        "base": {"marker": "s", "color": "#222222", "label": "Base case", "size": 72},
        "min_loss": {"marker": "*", "color": "#d62728", "label": "Minimum loss", "size": 135},
        "min_SAIDI": {"marker": "D", "color": "#7b3294", "label": "Minimum SAIDI", "size": 82},
        "compromise": {"marker": "P", "color": "#ff8c00", "label": "Compromise", "size": 92},
    }
    for key, style in markers.items():
        if key not in selected:
            continue
        row = selected[key]
        ax.scatter(
            [row["losses_kw"]],
            [row["saidi"]],
            marker=style["marker"],
            c=style["color"],
            s=style["size"],
            edgecolor="black",
            linewidth=0.5,
            zorder=6,
        )

    if zoom:
        xlim, ylim = zoom_limits(data)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)

    ax.set_xlabel("Technical losses [kW]")
    ax.set_ylabel("SAIDI [h/customer-year]")
    ax.grid(True, color="#d7d7d7", linewidth=0.7, alpha=0.75)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_case(case: str, title: str, stems: list[str]) -> list[Path]:
    data = load_case_data(case)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=False)
    draw_panel(axes[0], data, zoom=False)
    draw_panel(axes[1], data, zoom=True)
    axes[0].set_title("(a) Complete feasible solution cloud", fontsize=12)
    axes[1].set_title("(b) Zoomed Pareto region", fontsize=12)
    fig.suptitle(title, fontsize=15, y=0.98)

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#9baec8", alpha=0.45, markersize=6, label="Feasible solutions"),
        Line2D([0], [0], marker="o", color="#1f77b4", markerfacecolor="#1f77b4", lw=1.9, markersize=5, label="Feasible Pareto"),
        Line2D([0], [0], marker="o", color="#2ca02c", markerfacecolor="#2ca02c", lw=1.9, markersize=5, label="Operational Pareto"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor="#222222", markeredgecolor="black", markersize=7, label="Base case"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor="#d62728", markeredgecolor="black", markersize=11, label="Minimum loss"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="#7b3294", markeredgecolor="black", markersize=7, label="Minimum SAIDI"),
        Line2D([0], [0], marker="P", color="none", markerfacecolor="#ff8c00", markeredgecolor="black", markersize=8, label="Compromise"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=7, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.005))
    fig.subplots_adjust(left=0.07, right=0.985, top=0.86, bottom=0.17, wspace=0.22)

    paths = []
    for stem in stems:
        for ext in ["png", "pdf"]:
            path = OUT_DIR / f"{stem}.{ext}"
            fig.savefig(path, dpi=300 if ext == "png" else None, bbox_inches="tight")
            paths.append(path)
    plt.close(fig)

    return paths


def point_summary(case_label: str, selected: dict[str, pd.Series]) -> list[str]:
    lines = []
    labels = {
        "base": "base",
        "min_loss": "minimum loss",
        "min_SAIDI": "minimum SAIDI",
        "compromise": "compromise",
    }
    for key in ["base", "min_loss", "min_SAIDI", "compromise"]:
        if key not in selected:
            continue
        row = selected[key]
        lines.append(
            f"- {labels[key]}: ({float(row['losses_kw']):.6f} kW, "
            f"{float(row['saidi']):.6f} h/customer-year), "
            f"voltage_feasible_modeled_constraints={row.get('operationally_feasible')}, "
            f"open switches `{row.get('open_switches', '')}`."
        )
    return lines


def write_case_csvs(case_alias: str, data: dict[str, object]) -> tuple[Path, Path]:
    plot_data = combined_plot_dataframe(data)
    selected = selected_point_dataframe(data["selected"])
    plot_path = OUT_DIR / f"pareto_plot_data_{case_alias}.csv"
    selected_path = OUT_DIR / f"selected_points_{case_alias}.csv"
    plot_data.to_csv(plot_path, index=False, encoding="utf-8")
    selected.to_csv(selected_path, index=False, encoding="utf-8")
    return plot_path, selected_path


def main() -> None:
    ensure_out_dir()

    available_cases = [p.name for p in FINAL_RUNS.iterdir() if p.is_dir() and (p / "combined" / "all_combined.csv").exists()]
    ieee_cases = []
    for candidate in ["ieee30", "ieee_30", "IEEE30", "ieee33", "ieee_33", "IEEE33"]:
        canonical = candidate.lower().replace("_", "")
        for case in available_cases:
            if case.lower().replace("_", "") == canonical and case not in ieee_cases:
                ieee_cases.append(case)

    operator_case = None
    for candidate in ["operator", "real", "operador", "operator_colombian", "or_colombiano"]:
        canonical = candidate.lower().replace("_", "")
        for case in available_cases:
            if case.lower().replace("_", "") == canonical:
                operator_case = case
                break
        if operator_case:
            break

    generated: list[Path] = []
    report_lines = [
        "# Pareto Zoom Figures",
        "",
        "## Inputs and Case Detection",
        f"- Available final-run cases inspected: {', '.join(available_cases) if available_cases else 'NONE'}.",
    ]

    case_reports: list[tuple[str, str, dict[str, object]]] = []

    if ieee_cases:
        report_lines.append(f"- IEEE cases found: {', '.join(ieee_cases)}.")
        if "ieee33" in ieee_cases and not any(case.lower().replace("_", "") == "ieee30" for case in ieee_cases):
            report_lines.append("- No IEEE 30 case was found; figures were generated for the available IEEE 33-bus system.")
        for case in ieee_cases:
            data = load_case_data(case)
            title = "Pareto front for the IEEE 33-bus system" if "33" in case else "Pareto front for the IEEE 30-bus system"
            stems = ["fig_ieee_pareto_losses_saidi"]
            if "33" in case:
                stems.append("fig_ieee33_pareto_losses_saidi")
                alias = "ieee"
            elif "30" in case:
                stems.append("fig_ieee30_pareto_losses_saidi")
                alias = "ieee30"
            else:
                alias = case
            generated.extend(plot_case(case, title, stems))
            plot_path, selected_path = write_case_csvs(alias, data)
            generated.extend([plot_path, selected_path])
            if alias != case and "33" in case:
                # Also keep an explicit ieee33 copy for traceability.
                plot_data = combined_plot_dataframe(data)
                selected_data = selected_point_dataframe(data["selected"])
                p = OUT_DIR / "pareto_plot_data_ieee33.csv"
                s = OUT_DIR / "selected_points_ieee33.csv"
                plot_data.to_csv(p, index=False, encoding="utf-8")
                selected_data.to_csv(s, index=False, encoding="utf-8")
                generated.extend([p, s])
            case_reports.append((case, title, data))
    else:
        report_lines.append("- No IEEE 30/33 final-run case was found; no IEEE figure was generated.")

    if operator_case:
        data = load_case_data(operator_case)
        generated.extend(plot_case(operator_case, "Pareto front for the real distribution system", ["fig_operator_pareto_losses_saidi"]))
        generated.extend(write_case_csvs("operator", data))
        case_reports.append((operator_case, "Pareto front for the real distribution system", data))
        report_lines.append(f"- Operator-equivalent case found: `{operator_case}`.")
    else:
        report_lines.append("- No operator-equivalent final-run case was found; no operator figure was generated.")

    report_lines.extend(["", "## Case Summaries"])
    for case, title, data in case_reports:
        feasible = data["feasible"]
        op = data["all"][data["all"]["_operationally_feasible"]]
        p_feas = data["pareto_feasible"]
        p_op = data["pareto_operational"]
        selected = data["selected"]
        min_saidi_op = selected.get("min_SAIDI", {}).get("operationally_feasible", "NOT_AVAILABLE")
        report_lines.extend(
            [
                f"### {case}",
                f"- Figure title: {title}.",
                "- Input files:",
                *[f"  - `{path}`" for path in data["input_files"]],
                f"- Feasible solutions: {len(feasible)}.",
                f"- Voltage-feasible under modeled constraints: {len(op)}.",
                f"- Feasible Pareto points: {len(p_feas)}.",
                f"- Voltage-feasible Pareto points under modeled constraints: {len(p_op)}.",
                f"- Minimum SAIDI voltage-feasible under modeled constraints: {min_saidi_op}.",
                "- Selected coordinates:",
                *point_summary(case, selected),
                "- Warnings:",
                *[f"  - {warning}" for warning in data["warnings"]],
                "",
            ]
        )

    report_lines.extend(
        [
            "## Global Warnings",
            "- No optimization runs were executed.",
            "- No literature values were used or invented.",
            "- Pareto fronts were recalculated from the consolidated evaluated-solution CSV files to ensure consistent feasible and modeled voltage-feasibility filters.",
            "- The minimum-SAIDI solution is plotted even when it is not voltage-feasible under the modeled constraints.",
            "",
            "## Generated Files",
            *[f"- `{path}`" for path in generated],
        ]
    )
    readme = OUT_DIR / "README_pareto_figures.md"
    readme.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    generated.append(readme)

    print("Generated Pareto zoom outputs:")
    for path in generated:
        print(path)


if __name__ == "__main__":
    main()
