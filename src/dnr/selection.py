from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .models import Evaluation


SAIDI_TOL = 1e-9


def best_by_reliability_then_losses(
    evaluations: Iterable[Evaluation],
    reliability_tol: float = SAIDI_TOL,
) -> Evaluation | None:
    feasible = [
        ev
        for ev in evaluations
        if ev.feasible and ev.objective_reliability is not None and ev.losses_kw is not None
    ]
    if not feasible:
        return None

    best_reliability = min(float(ev.objective_reliability) for ev in feasible)
    tied = [
        ev
        for ev in feasible
        if abs(float(ev.objective_reliability) - best_reliability) <= reliability_tol
    ]
    return min(tied, key=lambda ev: (float(ev.losses_kw), ev.open_switches))


def best_by_reliability_then_losses_df(
    df: pd.DataFrame,
    reliability_col: str = "objective_reliability",
    losses_col: str = "losses_kw",
    feasible_col: str = "feasible",
    reliability_tol: float = SAIDI_TOL,
) -> pd.DataFrame:
    work = df[
        (df[feasible_col] == True)
        & df[reliability_col].notna()
        & df[losses_col].notna()
    ].copy()
    if work.empty:
        return work

    best_reliability = float(work[reliability_col].min())
    tied = work[(work[reliability_col].astype(float) - best_reliability).abs() <= reliability_tol].copy()
    return tied.sort_values([losses_col, "open_switches"]).head(1)
