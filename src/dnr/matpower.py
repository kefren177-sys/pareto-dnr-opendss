from __future__ import annotations

import ast
import re
from pathlib import Path

from .models import Branch, Bus, NetworkCase


IEEE33_USERS_BY_BUS = {
    bus: users
    for bus, users in zip(
        range(2, 34),
        [
            154,
            133,
            196,
            70,
            70,
            365,
            365,
            70,
            70,
            39,
            70,
            70,
            196,
            70,
            70,
            70,
            133,
            133,
            133,
            133,
            133,
            133,
            698,
            698,
            70,
            70,
            70,
            196,
            365,
            260,
            387,
            70,
        ],
    )
}


def _matrix_block(text: str, name: str) -> str:
    pattern = re.compile(rf"mpc\.{re.escape(name)}\s*=\s*\[(.*?)\];", re.S)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"No se encontro mpc.{name} en archivo MATPOWER")
    return match.group(1)


def _eval_number(expr: str) -> float:
    expr = expr.strip()
    expr = re.sub(r"[^0-9eE+\-*/().]", "", expr)
    if not expr:
        return 0.0
    tree = ast.parse(expr, mode="eval")
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
    )
    if not all(isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError(f"Expresion numerica no permitida: {expr}")
    return float(eval(compile(tree, "<matpower-number>", "eval"), {"__builtins__": {}}, {}))


def _parse_rows(block: str) -> list[list[float]]:
    rows: list[list[float]] = []
    for raw in block.splitlines():
        raw = raw.split("%", 1)[0].strip()
        if not raw:
            continue
        raw = raw.rstrip(";").strip()
        if not raw:
            continue
        parts = raw.split()
        rows.append([_eval_number(part) for part in parts])
    return rows


def load_matpower_case(
    name: str,
    title: str,
    path: Path,
    base_kv: float,
    slack_bus: int,
    normally_open: list[int],
    candidate_switches: list[int],
    open_count: int,
    reliability: dict[str, float],
    operation_limits: dict[str, float] | None = None,
    metadata: dict[str, object] | None = None,
) -> NetworkCase:
    text = path.read_text(encoding="utf-8", errors="ignore")
    bus_rows = _parse_rows(_matrix_block(text, "bus"))
    branch_rows = _parse_rows(_matrix_block(text, "branch"))

    users_by_bus = IEEE33_USERS_BY_BUS if name == "ieee33" else {}
    buses = [
        Bus(
            idx=int(row[0]),
            pd_kw=float(row[2]) * 1000.0,
            qd_kvar=float(row[3]) * 1000.0,
            users=users_by_bus.get(int(row[0]), max(1, int(round(float(row[2]) * 1000.0)))),
        )
        for row in bus_rows
    ]
    branches = [
        Branch(
            idx=i + 1,
            from_bus=int(row[0]),
            to_bus=int(row[1]),
            r_ohm=float(row[2]),
            x_ohm=float(row[3]),
            length_km=1.0,
            enabled=bool(int(row[10])) if len(row) > 10 else True,
        )
        for i, row in enumerate(branch_rows)
    ]

    return NetworkCase(
        name=name,
        title=title,
        base_kv=base_kv,
        slack_bus=slack_bus,
        buses=buses,
        branches=branches,
        normally_open=normally_open,
        candidate_switches=candidate_switches,
        open_count=open_count,
        reliability=reliability,
        operation_limits=operation_limits or {},
        metadata=metadata or {},
    )
