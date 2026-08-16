from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from .models import Branch, Bus, NetworkCase


def _attrs(line: str) -> dict[str, str]:
    return {key.lower(): value for key, value in re.findall(r"(\w+)\s*=\s*([^\s]+)", line)}


def _number(value: str | int | float | None, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip().replace(",", ".")
    if not text:
        return default
    return float(text)


def _int_number(value: str | int | float | None, default: int = 0) -> int:
    return int(round(_number(value, float(default))))


def _excel_reference_data(excel_path: Path, sheet: str) -> tuple[dict[int, int], dict[int, float]]:
    df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    users_by_load: dict[int, int] = {}
    failure_by_section: dict[int, float] = {}

    for _, row in df.iloc[2:].iterrows():
        load_idx = _int_number(row.get(2), 0)
        if load_idx:
            users_by_load[load_idx] = max(1, _int_number(row.get(8), 1))

        section_text = row.get(10)
        if isinstance(section_text, str):
            match = re.search(r"S\s*-\s*(\d+)", section_text, re.I)
            if match:
                # In the restricted operator workbook, the formulas for the
                # load-point failure rates (columns "base/optimized case",
                # "lambda section [failures/year]")
                # multiply the path equation by column P (zero-based index 15),
                # whose values are 2/5/8. Column O (index 14) is length*1.4634
                # and is kept in the sheet, but it is not the rate used by those
                # reliability formulas.
                failure_by_section[int(match.group(1))] = _number(row.get(15), _number(row.get(14), 0.0))

    return users_by_load, failure_by_section


def _parse_dss_lines(dss_path: Path, failure_by_section: dict[int, float], repair_hours: float) -> list[Branch]:
    branches: list[Branch] = []
    pending_section: int | None = None

    for raw in dss_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        comment_match = re.search(r"-\s*S\s*(\d+)", raw, re.I)
        if comment_match:
            pending_section = int(comment_match.group(1))

        line = re.sub(r"^\s*//\s*", "", raw)
        if not re.search(r"^\s*New\s+Line\.", line, re.I):
            continue
        if pending_section is None:
            raise ValueError(f"No se pudo identificar la seccion antes de la linea DSS: {raw}")

        attrs = _attrs(line)
        idx = pending_section
        branches.append(
            Branch(
                idx=idx,
                from_bus=_int_number(attrs.get("bus1")),
                to_bus=_int_number(attrs.get("bus2")),
                r_ohm=_number(attrs.get("r1")),
                x_ohm=_number(attrs.get("x1")),
                r0_ohm=_number(attrs.get("r0")),
                x0_ohm=_number(attrs.get("x0")),
                length_km=_number(attrs.get("length"), 1.0),
                failure_rate_year=failure_by_section.get(idx),
                repair_time_hours=repair_hours,
            )
        )
        pending_section = None

    return sorted(branches, key=lambda branch: branch.idx)


def _parse_dss_loads(dss_path: Path, users_by_load: dict[int, int]) -> dict[int, tuple[float, float, int]]:
    pd_by_bus: defaultdict[int, float] = defaultdict(float)
    qd_by_bus: defaultdict[int, float] = defaultdict(float)
    users_by_bus: defaultdict[int, int] = defaultdict(int)

    for raw in dss_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        load_match = re.search(r"^\s*New\s+Load\.bus(\d+)\b", raw, re.I)
        if not load_match:
            continue

        load_idx = int(load_match.group(1))
        attrs = _attrs(raw)
        bus = _int_number(attrs.get("bus1"))
        pd_by_bus[bus] += _number(attrs.get("kw"))
        qd_by_bus[bus] += _number(attrs.get("kvar"))
        users_by_bus[bus] += users_by_load.get(load_idx, 1)

    return {
        bus: (pd_by_bus[bus], qd_by_bus[bus], max(1, users_by_bus[bus]))
        for bus in pd_by_bus
    }


def load_opendss_excel_case(
    name: str,
    title: str,
    dss_path: Path,
    excel_path: Path,
    excel_sheet: str,
    base_kv: float,
    slack_bus: int,
    normally_open: list[int],
    candidate_switches: list[int],
    open_count: int,
    reliability: dict[str, float],
    operation_limits: dict[str, float] | None = None,
    metadata: dict[str, object] | None = None,
) -> NetworkCase:
    repair_hours = float(reliability.get("repair_time_hours", 0.3659))
    users_by_load, failure_by_section = _excel_reference_data(excel_path, excel_sheet)
    branches = _parse_dss_lines(dss_path, failure_by_section, repair_hours)
    loads = _parse_dss_loads(dss_path, users_by_load)

    bus_ids = {slack_bus}
    for branch in branches:
        bus_ids.add(branch.from_bus)
        bus_ids.add(branch.to_bus)
    bus_ids.update(loads)

    buses = [
        Bus(
            idx=bus,
            pd_kw=loads.get(bus, (0.0, 0.0, 1))[0],
            qd_kvar=loads.get(bus, (0.0, 0.0, 1))[1],
            users=loads.get(bus, (0.0, 0.0, 1))[2],
        )
        for bus in sorted(bus_ids)
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
