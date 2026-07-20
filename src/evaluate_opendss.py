from __future__ import annotations

from pathlib import Path


def solve_with_opendss(dss_file: Path, open_switches: tuple[int, ...]) -> dict[str, float | bool]:
    """Run OpenDSS as an electrical evaluator, not as an optimizer.

    This helper requires opendssdirect.py. If OpenDSS is unavailable, use the
    consolidated CSV files under results/ to verify the reported article values.
    """
    import opendssdirect as dss

    dss.Basic.ClearAll()
    dss.Text.Command(f'Compile "{dss_file}"')
    for switch in open_switches:
        dss.Text.Command(f"Disable Line.L{int(switch)}")
    dss.Text.Command("Solve")
    losses = dss.Circuit.Losses()
    voltages = dss.Circuit.AllBusMagPu()
    return {
        "opendss_converged": bool(dss.Solution.Converged()),
        "losses_kw": float(losses[0]) / 1000.0 if losses else None,
        "vmin_pu": min(voltages) if voltages else None,
        "vmax_pu": max(voltages) if voltages else None,
    }
