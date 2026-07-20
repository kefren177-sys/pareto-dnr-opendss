from __future__ import annotations

import networkx as nx
import pandas as pd


def is_connected_radial(branches: pd.DataFrame, open_switches: set[int]) -> tuple[bool, bool]:
    """Check connectivity and radiality from a branch table with integer branch IDs."""
    graph = nx.Graph()
    for _, row in branches.iterrows():
        if int(row["branch_id"]) in open_switches:
            continue
        graph.add_edge(int(row["from_bus"]), int(row["to_bus"]))
    connected = nx.is_connected(graph) if graph.number_of_nodes() else False
    radial = connected and graph.number_of_edges() == graph.number_of_nodes() - 1
    return connected, radial
