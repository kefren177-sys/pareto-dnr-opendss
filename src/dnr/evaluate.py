from __future__ import annotations

from pathlib import Path

from .dss import OpenDssRunner, write_dss
from .models import Evaluation, NetworkCase
from .reliability import reliability_indices
from .topology import topology_status


def reliability_objective_value(indices: dict[str, float], objective: str) -> float:
    objective = objective.lower()
    if objective == "saidi":
        return indices["saidi"]
    if objective == "saifi":
        return indices["saifi"]
    if objective in {"ens", "ens_mwh_year"}:
        return indices["ens_mwh_year"]
    raise ValueError("El objetivo de confiabilidad debe ser: saidi, saifi o ens.")


def _operation_limits(case: NetworkCase) -> tuple[float, float]:
    limits = case.operation_limits or {}
    return (
        float(limits.get("v_min_limit", 0.90)),
        float(limits.get("v_max_limit", 1.05)),
    )


def _voltage_feasible(min_voltage: float | None, max_voltage: float | None, v_min: float, v_max: float) -> bool | None:
    if min_voltage is None or max_voltage is None:
        return None
    return min_voltage >= v_min and max_voltage <= v_max


def _infeasibility_reasons(
    *,
    connected: bool,
    radial: bool,
    opendss_converged: bool,
    min_voltage: float | None,
    max_voltage: float | None,
    v_min: float,
    v_max: float,
    loading_check_available: bool,
    loading_feasible: bool | None,
    all_loads_served: bool | None,
) -> list[str]:
    reasons: list[str] = []
    if not connected:
        reasons.append("disconnected")
    if not radial:
        reasons.append("non_radial")
    if radial and connected and not opendss_converged:
        reasons.append("opendss_not_converged")
    if min_voltage is not None and min_voltage < v_min:
        reasons.append("voltage_below_limit")
    if max_voltage is not None and max_voltage > v_max:
        reasons.append("voltage_above_limit")
    if not loading_check_available:
        reasons.append("loading_limits_not_available")
    elif loading_feasible is False:
        reasons.append("thermal_overload")
    if all_loads_served is False:
        reasons.append("loads_not_served")
    if all_loads_served is None:
        reasons.append("load_serving_not_checked")
    return reasons


def evaluate(
    case: NetworkCase,
    open_switches: list[int] | tuple[int, ...],
    generated_dir: Path,
    reliability_objective: str = "saidi",
) -> Evaluation:
    open_tuple = tuple(sorted(int(x) for x in open_switches))
    radial, connected = topology_status(case, open_tuple)
    topologically_feasible = connected and radial
    v_min_limit, v_max_limit = _operation_limits(case)
    loading_check_available = False
    loading_feasible = None
    all_loads_served = connected
    if not radial:
        reasons = _infeasibility_reasons(
            connected=connected,
            radial=radial,
            opendss_converged=False,
            min_voltage=None,
            max_voltage=None,
            v_min=v_min_limit,
            v_max=v_max_limit,
            loading_check_available=loading_check_available,
            loading_feasible=loading_feasible,
            all_loads_served=all_loads_served,
        )
        return Evaluation(
            case_name=case.name,
            open_switches=open_tuple,
            radial=radial,
            connected=connected,
            converged=False,
            losses_kw=None,
            min_voltage_pu=None,
            saidi=None,
            saifi=None,
            ens_mwh_year=None,
            objective_reliability=None,
            objective_reliability_name=reliability_objective,
            feasible=False,
            topologically_feasible=topologically_feasible,
            opendss_converged=False,
            electrically_solved=False,
            v_min_limit=v_min_limit,
            v_max_limit=v_max_limit,
            voltage_feasible=None,
            loading_feasible=loading_feasible,
            loading_check_available=loading_check_available,
            all_loads_served=all_loads_served,
            operationally_feasible=False,
            infeasibility_reasons=reasons,
            message="La configuracion no es radial o no alimenta todas las cargas.",
        )

    dss_path = write_dss(case, generated_dir)
    power = OpenDssRunner(dss_path).solve(open_tuple)
    rel = reliability_indices(case, open_tuple)
    feasible = bool(power["converged"]) and power["losses_kw"] is not None
    opendss_converged = bool(power["converged"])
    electrically_solved = feasible
    min_voltage = power["min_voltage_pu"]
    max_voltage = power.get("max_voltage_pu")
    voltage_feasible = _voltage_feasible(min_voltage, max_voltage, v_min_limit, v_max_limit)
    operationally_feasible = (
        topologically_feasible
        and electrically_solved
        and voltage_feasible is True
        and loading_feasible is not False
        and all_loads_served is not False
    )
    reasons = _infeasibility_reasons(
        connected=connected,
        radial=radial,
        opendss_converged=opendss_converged,
        min_voltage=min_voltage,
        max_voltage=max_voltage,
        v_min=v_min_limit,
        v_max=v_max_limit,
        loading_check_available=loading_check_available,
        loading_feasible=loading_feasible,
        all_loads_served=all_loads_served,
    )
    return Evaluation(
        case_name=case.name,
        open_switches=open_tuple,
        radial=radial,
        connected=connected,
        converged=opendss_converged,
        losses_kw=power["losses_kw"],
        min_voltage_pu=min_voltage,
        max_voltage_pu=max_voltage,
        saidi=rel["saidi"],
        saifi=rel["saifi"],
        ens_mwh_year=rel["ens_mwh_year"],
        objective_reliability=reliability_objective_value(rel, reliability_objective),
        objective_reliability_name=reliability_objective,
        feasible=feasible,
        topologically_feasible=topologically_feasible,
        opendss_converged=opendss_converged,
        electrically_solved=electrically_solved,
        v_min_limit=v_min_limit,
        v_max_limit=v_max_limit,
        voltage_feasible=voltage_feasible,
        loading_feasible=loading_feasible,
        loading_check_available=loading_check_available,
        all_loads_served=all_loads_served,
        operationally_feasible=operationally_feasible,
        infeasibility_reasons=reasons,
        message="ok" if feasible else "OpenDSS no convergio.",
    )
