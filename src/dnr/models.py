from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Bus:
    idx: int
    pd_kw: float = 0.0
    qd_kvar: float = 0.0
    users: int = 1


@dataclass(frozen=True)
class Branch:
    idx: int
    from_bus: int
    to_bus: int
    r_ohm: float
    x_ohm: float
    r0_ohm: float | None = None
    x0_ohm: float | None = None
    length_km: float = 1.0
    failure_rate_year: float | None = None
    repair_time_hours: float | None = None
    enabled: bool = True


@dataclass
class NetworkCase:
    name: str
    title: str
    base_kv: float
    slack_bus: int
    buses: list[Bus]
    branches: list[Branch]
    normally_open: list[int]
    candidate_switches: list[int]
    open_count: int
    reliability: dict[str, float] = field(default_factory=dict)
    operation_limits: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class Evaluation:
    case_name: str
    open_switches: tuple[int, ...]
    radial: bool
    connected: bool
    converged: bool
    losses_kw: float | None
    min_voltage_pu: float | None
    saidi: float | None
    saifi: float | None
    ens_mwh_year: float | None
    objective_reliability: float | None
    feasible: bool
    max_voltage_pu: float | None = None
    objective_reliability_name: str = "saidi"
    message: str = ""
    topologically_feasible: bool = False
    opendss_converged: bool = False
    electrically_solved: bool = False
    v_min_limit: float = 0.90
    v_max_limit: float = 1.05
    voltage_feasible: bool | None = None
    max_loading_percent: float | None = None
    loading_feasible: bool | None = None
    loading_check_available: bool = False
    all_loads_served: bool | None = None
    operationally_feasible: bool = False
    infeasibility_reasons: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, object]:
        return {
            "case": self.case_name,
            "open_switches": ",".join(str(x) for x in self.open_switches),
            "radial": self.radial,
            "connected": self.connected,
            "converged": self.converged,
            "opendss_converged": self.opendss_converged,
            "electrically_solved": self.electrically_solved,
            "losses_kw": self.losses_kw,
            "min_voltage_pu": self.min_voltage_pu,
            "vmin_pu": self.min_voltage_pu,
            "max_voltage_pu": self.max_voltage_pu,
            "vmax_pu": self.max_voltage_pu,
            "v_min_limit": self.v_min_limit,
            "v_max_limit": self.v_max_limit,
            "voltage_feasible": self.voltage_feasible,
            "saidi_h_user_year": self.saidi,
            "saifi_int_user_year": self.saifi,
            "ens_mwh_year": self.ens_mwh_year,
            "objective_reliability": self.objective_reliability,
            "objective_reliability_name": self.objective_reliability_name,
            "topologically_feasible": self.topologically_feasible,
            "max_loading_percent": self.max_loading_percent,
            "loading_feasible": self.loading_feasible,
            "loading_check_available": self.loading_check_available,
            "all_loads_served": self.all_loads_served,
            "operationally_feasible": self.operationally_feasible,
            "feasible": self.feasible,
            "infeasibility_reasons": ";".join(self.infeasibility_reasons),
            "message": self.message,
        }
