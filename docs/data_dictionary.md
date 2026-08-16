# Data Dictionary

## Common Result Columns

- `case`: study case identifier.
- `solution_type`: base, min_loss, min_SAIDI, or compromise.
- `open_switches`: comma-separated switch/branch IDs open in the configuration.
- `P_loss_kW` or `losses_kw`: active power losses in kW.
- `Vmin_pu`, `vmin_pu`: minimum voltage magnitude in p.u.
- `Vmax_pu`, `vmax_pu`: maximum voltage magnitude in p.u.
- `SAIDI_h_user_year`, `saidi_h_user_year`: SAIDI in h/customer-year.
- `SAIFI_int_user_year`, `saifi_int_user_year`: SAIFI in interruptions/customer-year.
- `ENS_MWh_year`, `ens_mwh_year`: expected energy not supplied in MWh/year.
- `feasible`: radial, connected, and OpenDSS-converged solution.
- `operationally_feasible`: feasible solution satisfying voltage limits and load-supply checks; thermal limits are not asserted unless traceable data exist.
- `infeasibility_reasons`: semicolon-separated diagnostic flags.

## Input Data Columns

- `loads.csv`: load bus, active/reactive demand, users, and source status.
- `branches.csv`: branch endpoints, impedance, length, switch status, and thermal-limit availability.
- `switches.csv`: candidate and normally open switch definitions.
- `reliability_inputs.csv`: failure rate and repair time per branch.

## Repository Tables

- `tables/table_case_summary.csv`: case-level network size, required open switches, load points, users, and study purpose.
- `tables/table_pareto_summary.csv`: total evaluated solutions, feasible counts, operationally feasible counts, non-dominated counts, runtime, and power-flow evaluation counts.
- `tables/table_compromise_vs_minloss.csv`: comparison between minimum-loss and compromise solutions.
- `tables/table_benchmark_bpso_opendss.csv`: manuscript benchmark support values.
- `tables/table_computational_summary_by_seed.csv`: final-run summary by case and random seed.
- `tables/table_network_input_summary.csv`: electrical input summary by case.
- `tables/table_operational_assumptions.csv`: voltage limits, topology requirements, convergence requirement, and thermal-limit policy.
- `tables/table_optimization_input_parameters.csv`: population, generations, seed count, objectives, and evaluator.
- `tables/table_reliability_summary.csv`: number of reliability elements, failure-rate statistics, repair-time statistics, and data-source notes.

## Phase 4 Statistical Files

- `generation_history.csv`: per-generation observational log with generation index, elapsed time, unique OpenDSS evaluations, cache hits, population size, feasible population size, population-level non-dominated size, archive non-dominated size, best loss, and best SAIDI.
- `pareto_history.csv`: cumulative feasible archive front at the end of each generation; columns include case, run ID, seed, generation, cumulative unique evaluations, open switches, losses, and SAIDI.
- `phase4_run_metrics.csv`: run-level HV, IGD, spacing, runtime, evaluation counts, representative solutions, and benchmark-recovery flags.
- `phase4_statistical_summary.csv`: mean, standard deviation, median, Q1, Q3, IQR, minimum, and maximum for Phase 4 metrics.
- `phase4_empirical_reference_front.csv`: non-dominated set of the union of final run-level Pareto fronts; this is an empirical reference front, not the true Pareto front.
- `phase4_convergence.csv`: HV convergence summary versus cumulative unique OpenDSS evaluations, including median HV, Q1, Q3, and number of contributing runs.
- `phase4_protocol.json`: objectives, normalization bounds, reference point, empirical-reference-front definition, spacing formula, recovery definition, seeds, and software metadata.

## Real-System Publication Policy

For `real_system_anonymized`, `all_combined.csv` is intentionally not published in this clean repository. The public result files are `representative_solutions.csv`, `summarized_results.csv`, `pareto_feasible.csv`, `pareto_operationally_feasible.csv`, `best_by_losses.csv`, `best_by_saidi.csv`, `best_compromise.csv`, and `run_summary.csv`.
