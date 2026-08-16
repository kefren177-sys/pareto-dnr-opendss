from __future__ import annotations

import unittest

import pandas as pd

from dnr.selection import SAIDI_TOL, best_by_reliability_then_losses_df


class BestByReliabilityThenLossesTest(unittest.TestCase):
    def test_equal_saidi_selects_lower_losses(self) -> None:
        df = pd.DataFrame(
            [
                {"open_switches": "a", "objective_reliability": 1.0, "losses_kw": 20.0, "feasible": True},
                {"open_switches": "b", "objective_reliability": 1.0, "losses_kw": 10.0, "feasible": True},
            ]
        )

        selected = best_by_reliability_then_losses_df(df).iloc[0]

        self.assertEqual(selected["open_switches"], "b")

    def test_differences_inside_tolerance_are_ties(self) -> None:
        df = pd.DataFrame(
            [
                {"open_switches": "a", "objective_reliability": 1.0, "losses_kw": 20.0, "feasible": True},
                {
                    "open_switches": "b",
                    "objective_reliability": 1.0 + SAIDI_TOL / 2,
                    "losses_kw": 10.0,
                    "feasible": True,
                },
            ]
        )

        selected = best_by_reliability_then_losses_df(df).iloc[0]

        self.assertEqual(selected["open_switches"], "b")

    def test_differences_above_tolerance_are_not_ties(self) -> None:
        df = pd.DataFrame(
            [
                {"open_switches": "a", "objective_reliability": 1.0, "losses_kw": 20.0, "feasible": True},
                {
                    "open_switches": "b",
                    "objective_reliability": 1.0 + SAIDI_TOL * 2,
                    "losses_kw": 10.0,
                    "feasible": True,
                },
            ]
        )

        selected = best_by_reliability_then_losses_df(df).iloc[0]

        self.assertEqual(selected["open_switches"], "a")


if __name__ == "__main__":
    unittest.main()
