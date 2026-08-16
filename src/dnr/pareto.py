from __future__ import annotations

from .models import Evaluation


def pareto_front(evaluations: list[Evaluation]) -> list[Evaluation]:
    feasible = [
        ev
        for ev in evaluations
        if ev.feasible and ev.losses_kw is not None and ev.objective_reliability is not None
    ]
    front: list[Evaluation] = []
    for candidate in feasible:
        dominated = False
        for other in feasible:
            if other is candidate:
                continue
            better_or_equal = (
                other.losses_kw <= candidate.losses_kw
                and other.objective_reliability <= candidate.objective_reliability
            )
            strictly_better = (
                other.losses_kw < candidate.losses_kw
                or other.objective_reliability < candidate.objective_reliability
            )
            if better_or_equal and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(candidate)
    return sorted(front, key=lambda ev: (ev.losses_kw or 0.0, ev.objective_reliability or 0.0))
