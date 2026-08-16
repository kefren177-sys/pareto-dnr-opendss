# Results

This directory contains consolidated results used for article traceability.

- `representative_solutions.csv`: base, minimum-loss, minimum-SAIDI, and compromise configurations.
- `all_combined.csv`: unique evaluated configurations from final runs, where available. This file is included for IEEE 33. It is intentionally excluded for the anonymized real system to avoid publishing more configuration-level information than needed.
- `summarized_results.csv`: public replacement for the full evaluated-solution cloud in the anonymized real-system case.
- `pareto_feasible.csv`: Pareto front filtered by `feasible=True`.
- `pareto_operationally_feasible.csv`: historical filename retained for traceability. It is filtered by `operationally_feasible=True`, where this field mainly represents voltage-feasible solutions under the modeled constraints, not complete operational validation.

The five-node case includes exhaustive enumeration outputs for validation. IEEE 33 includes consolidated final-run outputs. The anonymized real system includes representative solutions, Pareto fronts, and run summaries only.

`results/phase4_runs/ieee33/` stores the 20 independent IEEE 33-node runs used for the statistical robustness assessment. Each seed directory contains per-run raw outputs and generation/archive histories. The `phase4/` subdirectory contains postprocessed HV, IGD, spacing, empirical-reference-front, and convergence files.
