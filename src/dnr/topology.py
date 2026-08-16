from __future__ import annotations

import networkx as nx

from .models import NetworkCase


def closed_branches(case: NetworkCase, open_switches: list[int] | tuple[int, ...]):
    opened = set(int(x) for x in open_switches)
    return [branch for branch in case.branches if branch.idx not in opened]


def graph(case: NetworkCase, open_switches: list[int] | tuple[int, ...]) -> nx.Graph:
    g = nx.Graph()
    for bus in case.buses:
        g.add_node(bus.idx)
    for branch in closed_branches(case, open_switches):
        g.add_edge(branch.from_bus, branch.to_bus, idx=branch.idx, length_km=branch.length_km)
    return g


def topology_status(case: NetworkCase, open_switches: list[int] | tuple[int, ...]) -> tuple[bool, bool]:
    g = graph(case, open_switches)
    connected = nx.is_connected(g)
    radial = connected and g.number_of_edges() == g.number_of_nodes() - 1
    return radial, connected
