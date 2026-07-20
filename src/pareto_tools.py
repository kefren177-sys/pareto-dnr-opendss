from __future__ import annotations

import pandas as pd


def pareto_front(df: pd.DataFrame, loss_col: str = "losses_kw", saidi_col: str = "saidi_h_user_year") -> pd.DataFrame:
    """Return non-dominated rows for minimization of active power losses and SAIDI."""
    work = df[df[loss_col].notna() & df[saidi_col].notna()].copy()
    keep = []
    for idx, row in work.iterrows():
        dominated = (
            (work[loss_col] <= row[loss_col])
            & (work[saidi_col] <= row[saidi_col])
            & ((work[loss_col] < row[loss_col]) | (work[saidi_col] < row[saidi_col]))
        ).any()
        if not dominated:
            keep.append(idx)
    return work.loc[keep].sort_values([loss_col, saidi_col]).reset_index(drop=True)


def compromise_solution(pareto: pd.DataFrame, loss_col: str = "losses_kw", saidi_col: str = "saidi_h_user_year") -> pd.Series:
    """Select the closest point to the ideal normalized objective vector."""
    work = pareto.copy()
    loss_span = work[loss_col].max() - work[loss_col].min()
    saidi_span = work[saidi_col].max() - work[saidi_col].min()
    loss_span = loss_span if loss_span else 1.0
    saidi_span = saidi_span if saidi_span else 1.0
    work["losses_norm"] = (work[loss_col] - work[loss_col].min()) / loss_span
    work["saidi_norm"] = (work[saidi_col] - work[saidi_col].min()) / saidi_span
    work["ideal_distance"] = (work["losses_norm"] ** 2 + work["saidi_norm"] ** 2) ** 0.5
    return work.loc[work["ideal_distance"].idxmin()]
