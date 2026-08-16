from __future__ import annotations

from pathlib import Path

import yaml

from .matpower import load_matpower_case
from .models import Branch, Bus, NetworkCase
from .opendss_case import load_opendss_excel_case


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "cases.yml"


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def case_names(config_path: Path = DEFAULT_CONFIG) -> list[str]:
    return sorted(load_config(config_path)["cases"])


def _built_in_five_node(cfg: dict, defaults: dict, operation_limits: dict) -> NetworkCase:
    reliability = {**defaults, **cfg.get("reliability", {})}
    buses = [
        Bus(1, 0.0, 0.0, 1),
        Bus(2, 855.0, 414.0, 154),
        Bus(3, 1488.0, 922.0, 133),
        Bus(4, 1395.0, 676.0, 196),
        Bus(5, 1464.0, 1098.0, 70),
    ]
    failure_rates = {1: 0.75, 2: 1.50, 3: 1.90, 4: 0.95, 5: 0.75, 6: 0.75}
    repair_hours = 6.0
    r1, x1 = 0.2881, 0.4021
    r0, x0 = 1.0183, 1.3670
    branches = [
        Branch(1, 1, 2, r1, x1, r0, x0, 2.5, failure_rates[1], repair_hours),
        Branch(2, 2, 3, r1, x1, r0, x0, 9.9, failure_rates[2], repair_hours),
        Branch(3, 3, 4, r1, x1, r0, x0, 12.5, failure_rates[3], repair_hours),
        Branch(4, 2, 5, r1, x1, r0, x0, 14.896, failure_rates[4], repair_hours),
        Branch(5, 2, 4, r1, x1, r0, x0, 6.301, failure_rates[5], repair_hours),
        Branch(6, 4, 5, r1, x1, r0, x0, 6.83, failure_rates[6], repair_hours),
    ]
    return NetworkCase(
        name="five_node",
        title=cfg["title"],
        base_kv=float(cfg["base_kv"]),
        slack_bus=int(cfg["slack_bus"]),
        buses=buses,
        branches=branches,
        normally_open=list(cfg["normally_open"]),
        candidate_switches=list(cfg["candidate_switches"]),
        open_count=int(cfg["open_count"]),
        reliability=reliability,
        operation_limits=operation_limits,
    )


def load_case(name: str, config_path: Path = DEFAULT_CONFIG) -> NetworkCase:
    config = load_config(config_path)
    cfg = config["cases"][name]
    defaults = config.get("reliability_defaults", {})
    operation_limits = {**config.get("operation_limits", {}), **cfg.get("operation_limits", {})}

    if cfg["source"] == "built_in":
        return _built_in_five_node(cfg, defaults, operation_limits)

    if cfg["source"] == "matpower":
        thesis_root = Path(config["thesis_root"])
        reliability = {**defaults, **cfg.get("reliability", {})}
        return load_matpower_case(
            name=name,
            title=cfg["title"],
            path=thesis_root / cfg["matpower_file"],
            base_kv=float(cfg["base_kv"]),
            slack_bus=int(cfg["slack_bus"]),
            normally_open=list(cfg["normally_open"]),
            candidate_switches=list(cfg["candidate_switches"]),
            open_count=int(cfg["open_count"]),
            reliability=reliability,
            operation_limits=operation_limits,
            metadata={
                key: value
                for key, value in cfg.items()
                if key.startswith("thesis_") or key in {"matpower_file"}
            },
        )

    if cfg["source"] == "opendss_excel":
        thesis_root = Path(config["thesis_root"])
        reliability = {**defaults, **cfg.get("reliability", {})}
        return load_opendss_excel_case(
            name=name,
            title=cfg["title"],
            dss_path=thesis_root / cfg["dss_file"],
            excel_path=thesis_root / cfg["excel_file"],
            excel_sheet=cfg.get("excel_sheet", "NETWORK_DATA"),
            base_kv=float(cfg["base_kv"]),
            slack_bus=int(cfg["slack_bus"]),
            normally_open=list(cfg["normally_open"]),
            candidate_switches=list(cfg["candidate_switches"]),
            open_count=int(cfg["open_count"]),
            reliability=reliability,
            operation_limits=operation_limits,
            metadata={
                key: value
                for key, value in cfg.items()
                if key.startswith("thesis_") or key in {"dss_file", "excel_file", "excel_sheet"}
            },
        )

    raise ValueError(f"Fuente de caso no soportada: {cfg['source']}")


def output_root(config_path: Path = DEFAULT_CONFIG) -> Path:
    return Path(load_config(config_path)["output_root"])


def generated_data_root(config_path: Path = DEFAULT_CONFIG) -> Path:
    return Path(load_config(config_path)["generated_data_root"])
