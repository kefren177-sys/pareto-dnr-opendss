from __future__ import annotations


def percent_reduction(base_value: float, new_value: float) -> float:
    """Return percentage reduction from base_value to new_value."""
    if base_value == 0:
        return 0.0
    return 100.0 * (base_value - new_value) / base_value
