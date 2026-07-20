from __future__ import annotations

import pandas as pd


def saidi(load_points: pd.DataFrame) -> float:
    return float((load_points["unavailability_h_per_year"] * load_points["users"]).sum() / load_points["users"].sum())


def saifi(load_points: pd.DataFrame) -> float:
    return float((load_points["lambda_interruptions_per_year"] * load_points["users"]).sum() / load_points["users"].sum())


def ens_mwh_year(load_points: pd.DataFrame) -> float:
    return float((load_points["p_kw"] * load_points["unavailability_h_per_year"]).sum() / 1000.0)
