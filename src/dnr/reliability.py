from __future__ import annotations

import networkx as nx

from .models import NetworkCase
from .topology import closed_branches, graph


def reliability_indices(case: NetworkCase, open_switches: list[int] | tuple[int, ...]) -> dict[str, float]:
    params = case.reliability
    failure_rate = float(params.get("failure_rate_per_km_year", 1.4634))
    repair_hours = float(params.get("repair_time_hours", 0.3659))

    g = graph(case, open_switches)
    branch_by_edge = {
        frozenset((branch.from_bus, branch.to_bus)): branch
        for branch in closed_branches(case, open_switches)
    }

    total_users = 0.0
    weighted_lambda = 0.0
    weighted_unavailability = 0.0
    ens = 0.0

    for bus in case.buses:
        if bus.idx == case.slack_bus:
            continue
        users = max(1, bus.users)
        total_users += users
        try:
            path = nx.shortest_path(g, case.slack_bus, bus.idx)
        except nx.NetworkXNoPath:
            return {"saifi": float("inf"), "saidi": float("inf"), "ens_mwh_year": float("inf")}

        lambda_load = 0.0
        unavailability = 0.0
        for a, b in zip(path, path[1:]):
            branch = branch_by_edge[frozenset((a, b))]
            lam = (
                branch.failure_rate_year
                if branch.failure_rate_year is not None
                else failure_rate * branch.length_km
            )
            repair = (
                branch.repair_time_hours
                if branch.repair_time_hours is not None
                else repair_hours
            )
            lambda_load += lam
            unavailability += lam * repair

        weighted_lambda += users * lambda_load
        weighted_unavailability += users * unavailability
        ens += bus.pd_kw * unavailability / 1000.0

    if total_users == 0:
        return {"saifi": 0.0, "saidi": 0.0, "ens_mwh_year": 0.0}
    return {
        "saifi": weighted_lambda / total_users,
        "saidi": weighted_unavailability / total_users,
        "ens_mwh_year": ens,
    }
