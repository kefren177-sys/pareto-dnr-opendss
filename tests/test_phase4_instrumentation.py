from __future__ import annotations

import unittest
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from dnr.cli import IEEE33_REFERENCE_OPEN, _ieee33_reference_recovery
from dnr.models import Branch, Bus, Evaluation, NetworkCase
from dnr.optimize import evolutionary_search, nondominated_configs, seeded_configurations
from scripts.phase4_postprocess import (
    _compromise_run_local,
    _hypervolume_2d_min,
    _igd,
    _spacing,
    postprocess,
)


def _test_case() -> NetworkCase:
    return NetworkCase(
        name="test_case",
        title="Synthetic test case",
        base_kv=12.66,
        slack_bus=1,
        buses=[Bus(idx) for idx in range(1, 5)],
        branches=[
            Branch(1, 1, 2, 0.1, 0.1),
            Branch(2, 2, 3, 0.1, 0.1),
            Branch(3, 3, 4, 0.1, 0.1),
            Branch(4, 4, 1, 0.1, 0.1),
            Branch(5, 1, 3, 0.1, 0.1),
            Branch(6, 2, 4, 0.1, 0.1),
        ],
        normally_open=[4, 5, 6],
        candidate_switches=[1, 2, 3, 4, 5, 6],
        open_count=3,
        operation_limits={"v_min_limit": 0.90, "v_max_limit": 1.05},
    )


def _fake_evaluate(case: NetworkCase, open_switches, generated_dir, reliability_objective: str = "saidi") -> Evaluation:
    open_tuple = tuple(sorted(int(x) for x in open_switches))
    losses = float(sum(x * x for x in open_tuple))
    saidi = float(sum(open_tuple) / 10.0)
    return Evaluation(
        case_name=case.name,
        open_switches=open_tuple,
        radial=True,
        connected=True,
        converged=True,
        losses_kw=losses,
        min_voltage_pu=0.95,
        max_voltage_pu=1.0,
        saidi=saidi,
        saifi=saidi / 2.0,
        ens_mwh_year=losses / 10.0,
        objective_reliability=saidi,
        objective_reliability_name=reliability_objective,
        feasible=True,
        topologically_feasible=True,
        opendss_converged=True,
        electrically_solved=True,
        voltage_feasible=True,
        loading_check_available=False,
        all_loads_served=True,
        operationally_feasible=True,
        infeasibility_reasons=["loading_limits_not_available"],
        message="ok",
    )


class Phase4InstrumentationTest(unittest.TestCase):
    def test_hypervolume_is_bounded_by_reference_rectangle(self) -> None:
        frame = pd.DataFrame(
            [
                {"losses_norm": 0.0, "saidi_norm": 0.0},
                {"losses_norm": 1.30, "saidi_norm": 0.10},
            ]
        )

        hv = _hypervolume_2d_min(frame, (1.05, 1.05))

        self.assertLessEqual(hv, 1.05 * 1.05)
        self.assertAlmostEqual(hv, 1.05 * 1.05)

    def test_hypervolume_ignores_points_beyond_loss_reference(self) -> None:
        inside = pd.DataFrame([{"losses_norm": 0.20, "saidi_norm": 0.20}])
        with_outside = pd.concat(
            [
                inside,
                pd.DataFrame([{"losses_norm": 1.30, "saidi_norm": 0.10}]),
            ],
            ignore_index=True,
        )

        self.assertAlmostEqual(
            _hypervolume_2d_min(inside, (1.05, 1.05)),
            _hypervolume_2d_min(with_outside, (1.05, 1.05)),
        )

    def test_hypervolume_ignores_points_beyond_saidi_reference(self) -> None:
        inside = pd.DataFrame([{"losses_norm": 0.20, "saidi_norm": 0.20}])
        with_outside = pd.concat(
            [
                inside,
                pd.DataFrame([{"losses_norm": 0.10, "saidi_norm": 1.30}]),
            ],
            ignore_index=True,
        )

        self.assertAlmostEqual(
            _hypervolume_2d_min(inside, (1.05, 1.05)),
            _hypervolume_2d_min(with_outside, (1.05, 1.05)),
        )

    def test_ieee33_final_front_hypervolume_is_unchanged_inside_reference(self) -> None:
        losses = [
            137.3403817568125,
            137.63400755669326,
            138.26747691143908,
            139.15707296498272,
            142.0958063322025,
        ]
        saidi = [
            3.355444214531249,
            3.01855185178125,
            3.012044548968749,
            3.005537246156249,
            2.99902994334375,
        ]
        loss_min, loss_max = min(losses), max(losses)
        saidi_min, saidi_max = min(saidi), max(saidi)
        frame = pd.DataFrame(
            {
                "losses_norm": [(value - loss_min) / (loss_max - loss_min) for value in losses],
                "saidi_norm": [(value - saidi_min) / (saidi_max - saidi_min) for value in saidi],
            }
        )

        hv = _hypervolume_2d_min(frame, (1.05, 1.05))

        self.assertAlmostEqual(hv, 1.0153445202052596)
        self.assertLessEqual(hv, 1.05 * 1.05)

    def test_non_hv_phase4_metrics_keep_expected_behavior(self) -> None:
        front = pd.DataFrame(
            [
                {"open_switches": "a", "losses_kw": 100.0, "saidi": 5.0, "losses_norm": 0.0, "saidi_norm": 1.0},
                {"open_switches": "b", "losses_kw": 120.0, "saidi": 3.2, "losses_norm": 0.5, "saidi_norm": 0.1},
                {"open_switches": "c", "losses_kw": 150.0, "saidi": 3.0, "losses_norm": 1.0, "saidi_norm": 0.0},
            ]
        )
        reference = front[["losses_norm", "saidi_norm"]].copy()

        self.assertEqual(_igd(front, reference), 0.0)
        self.assertFalse(math.isnan(float(_spacing(front))))
        self.assertEqual(_compromise_run_local(front, "saidi")["open_switches"], "b")

    def test_generation_logging_does_not_change_evaluated_results(self) -> None:
        case = _test_case()
        stats_without: dict[str, int] = {}
        stats_with: dict[str, int] = {}
        generation_history: list[dict[str, object]] = []
        pareto_history: list[dict[str, object]] = []

        with patch("dnr.optimize.evaluate", side_effect=_fake_evaluate):
            without_logging = evolutionary_search(
                case,
                generated_dir=".",
                population_size=4,
                generations=3,
                seed=1234,
                stats=stats_without,
            )
            with_logging = evolutionary_search(
                case,
                generated_dir=".",
                population_size=4,
                generations=3,
                seed=1234,
                stats=stats_with,
                generation_history=generation_history,
                pareto_history=pareto_history,
                run_id="test_run",
            )

        without_records = [(ev.open_switches, ev.losses_kw, ev.saidi) for ev in without_logging]
        with_records = [(ev.open_switches, ev.losses_kw, ev.saidi) for ev in with_logging]
        self.assertEqual(with_records, without_records)
        self.assertEqual(stats_with, stats_without)

    def test_generation_counters_are_cumulative(self) -> None:
        case = _test_case()
        stats: dict[str, int] = {}
        generation_history: list[dict[str, object]] = []
        pareto_history: list[dict[str, object]] = []

        with patch("dnr.optimize.evaluate", side_effect=_fake_evaluate):
            evaluations = evolutionary_search(
                case,
                generated_dir=".",
                population_size=4,
                generations=3,
                seed=2026,
                stats=stats,
                generation_history=generation_history,
                pareto_history=pareto_history,
                run_id="test_run",
            )

        self.assertEqual(len(generation_history), 3)
        self.assertEqual(generation_history[-1]["unique_evaluations_cumulative"], stats["real_evaluations"])
        self.assertEqual(generation_history[-1]["cache_hits_cumulative"], stats["cache_hits"])
        self.assertIn("archive_nondominated_size", generation_history[-1])
        self.assertEqual(
            sum(int(row["unique_evaluations_generation"]) for row in generation_history),
            stats["real_evaluations"],
        )
        self.assertLessEqual(len(evaluations), stats["real_evaluations"])

    def test_pareto_history_contains_only_evaluated_configurations(self) -> None:
        case = _test_case()
        stats: dict[str, int] = {}
        generation_history: list[dict[str, object]] = []
        pareto_history: list[dict[str, object]] = []

        with patch("dnr.optimize.evaluate", side_effect=_fake_evaluate):
            evaluations = evolutionary_search(
                case,
                generated_dir=".",
                population_size=4,
                generations=3,
                seed=31415,
                stats=stats,
                generation_history=generation_history,
                pareto_history=pareto_history,
                run_id="test_run",
            )

        evaluated = {",".join(str(x) for x in ev.open_switches) for ev in evaluations}
        self.assertTrue(pareto_history)
        self.assertTrue({str(row["open_switches"]) for row in pareto_history}.issubset(evaluated))

    def test_archive_front_is_nondominated_and_matches_history_size(self) -> None:
        case = _test_case()
        stats: dict[str, int] = {}
        generation_history: list[dict[str, object]] = []
        pareto_history: list[dict[str, object]] = []

        with patch("dnr.optimize.evaluate", side_effect=_fake_evaluate):
            evaluations = evolutionary_search(
                case,
                generated_dir=".",
                population_size=4,
                generations=3,
                seed=27182,
                stats=stats,
                generation_history=generation_history,
                pareto_history=pareto_history,
                run_id="test_run",
            )

        cache = {ev.open_switches: ev for ev in evaluations}
        archive_front = nondominated_configs([cfg for cfg, ev in cache.items() if ev.feasible], cache)
        last_generation = max(int(row["generation"]) for row in pareto_history)
        last_rows = [row for row in pareto_history if int(row["generation"]) == last_generation]
        self.assertEqual(len(last_rows), len(archive_front))
        self.assertEqual(generation_history[-1]["archive_nondominated_size"], len(archive_front))
        for cfg in archive_front:
            ev = cache[cfg]
            for other_cfg, other in cache.items():
                if other_cfg == cfg or not other.feasible:
                    continue
                dominates = (
                    (other.losses_kw or float("inf")) <= (ev.losses_kw or float("inf"))
                    and (other.saidi or float("inf")) <= (ev.saidi or float("inf"))
                    and (
                        (other.losses_kw or float("inf")) < (ev.losses_kw or float("inf"))
                        or (other.saidi or float("inf")) < (ev.saidi or float("inf"))
                    )
                )
                self.assertFalse(dominates)

    def test_ieee33_reference_recovery_detection(self) -> None:
        reference = Evaluation(
            case_name="ieee33",
            open_switches=IEEE33_REFERENCE_OPEN,
            radial=True,
            connected=True,
            converged=True,
            losses_kw=137.0,
            min_voltage_pu=0.94,
            saidi=3.35,
            saifi=9.17,
            ens_mwh_year=12.3,
            objective_reliability=3.35,
            feasible=True,
        )
        other = Evaluation(
            case_name="ieee33",
            open_switches=(7, 10, 14, 27, 36),
            radial=True,
            connected=True,
            converged=True,
            losses_kw=142.0,
            min_voltage_pu=0.93,
            saidi=2.99,
            saifi=8.19,
            ens_mwh_year=11.1,
            objective_reliability=2.99,
            feasible=True,
        )

        self.assertEqual(
            _ieee33_reference_recovery("ieee33", [reference, other], [reference], reference),
            (True, True, True),
        )
        self.assertEqual(
            _ieee33_reference_recovery("operator", [reference], [reference], reference),
            (None, None, None),
        )

    def test_ieee33_reference_is_not_seeded_by_default(self) -> None:
        case = NetworkCase(
            name="ieee33",
            title="IEEE 33 test",
            base_kv=12.66,
            slack_bus=1,
            buses=[],
            branches=[],
            normally_open=[33, 34, 35, 36, 37],
            candidate_switches=list(range(1, 38)),
            open_count=5,
            metadata={},
        )

        self.assertNotIn(IEEE33_REFERENCE_OPEN, seeded_configurations(case))

    def test_phase4_postprocess_with_synthetic_runs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for seed, rows in {
                1: [
                    ("7,9,14,32,37", 100.0, 5.0),
                    ("7,10,14,27,36", 120.0, 3.2),
                    ("6,10,14,27,36", 140.0, 3.0000000005),
                    ("6,10,13,27,36", 150.0, 3.0),
                ],
                2: [
                    ("7,9,14,32,37", 110.0, 4.8),
                    ("7,10,14,28,36", 142.0, 3.0),
                    ("1,2,3,4,5", 165.0, 5.5),
                ],
            }.items():
                run_dir = root / f"seed_{seed}"
                run_dir.mkdir()
                all_df = pd.DataFrame(
                    [
                        {
                            "case": "ieee33",
                            "open_switches": open_switches,
                            "losses_kw": loss,
                            "saidi_h_user_year": saidi,
                            "objective_reliability": saidi,
                            "feasible": True,
                            "operationally_feasible": True,
                        }
                        for open_switches, loss, saidi in rows
                    ]
                )
                pareto_df = all_df[all_df["open_switches"] != "1,2,3,4,5"].copy()
                history = pareto_df.copy()
                history["run_id"] = f"ieee33_seed_{seed}"
                history["seed"] = seed
                history["generation"] = 1
                history["unique_evaluations_cumulative"] = 3 if seed == 1 else 5
                history["saidi"] = history["saidi_h_user_year"]
                summary = pd.DataFrame(
                    [
                        {
                            "case": "ieee33",
                            "seed": seed,
                            "elapsed_seconds": 10.0 * seed,
                            "unique_evaluations": len(all_df),
                            "cache_hits": seed,
                        }
                    ]
                )
                all_df.to_csv(run_dir / "all.csv", index=False)
                pareto_df.to_csv(run_dir / "pareto.csv", index=False)
                history[
                    [
                        "case",
                        "run_id",
                        "seed",
                        "generation",
                        "unique_evaluations_cumulative",
                        "open_switches",
                        "losses_kw",
                        "saidi",
                    ]
                ].to_csv(run_dir / "pareto_history.csv", index=False)
                summary.to_csv(run_dir / "summary.csv", index=False)

            outputs = postprocess(root)
            metrics = pd.read_csv(outputs["run_metrics"])
            protocol = (outputs["protocol"]).read_text(encoding="utf-8")
            convergence = pd.read_csv(outputs["convergence"])
            reference = pd.read_csv(outputs["empirical_reference_front"])
            protocol_data = __import__("json").loads(protocol)

            self.assertEqual(len(metrics), 2)
            self.assertIn("hypervolume", metrics.columns)
            self.assertTrue((metrics["benchmark_recovery_pareto"] == True).all())
            seed1 = metrics[metrics["seed"] == 1].iloc[0]
            self.assertEqual(seed1["min_saidi_switches"], "6,10,14,27,36")
            self.assertEqual(seed1["compromise_switches"], "7,10,14,27,36")
            self.assertIn('"reference_point": [', protocol)
            self.assertEqual(protocol_data["hypervolume"]["reference_point"], [1.05, 1.05])
            self.assertIn("empirical reference front", protocol_data["normalization_bounds_source"])
            self.assertEqual(protocol_data["normalization_bounds"]["losses_kw"]["min"], 100.0)
            self.assertEqual(protocol_data["normalization_bounds"]["losses_kw"]["max"], 142.0)
            self.assertEqual(protocol_data["normalization_bounds"]["saidi"]["min"], 3.0)
            self.assertEqual(protocol_data["normalization_bounds"]["saidi"]["max"], 5.0)
            self.assertEqual(len(reference), 4)
            self.assertFalse(convergence.empty)
            aggregated = convergence[convergence["seed"].astype(str) == "ALL"].sort_values("unique_evaluations_cumulative")
            self.assertEqual(int(aggregated.iloc[0]["n_runs_contributing"]), 1)
            self.assertEqual(int(aggregated.iloc[-1]["n_runs_contributing"]), 2)
            self.assertEqual(protocol_data["convergence"]["first_full_coverage_unique_evaluations"], 5)


if __name__ == "__main__":
    unittest.main()
