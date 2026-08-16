# Methodology Summary

The repository implements a Pareto-based multi-objective distribution network reconfiguration workflow. A candidate solution is represented by the set of open branches/switches.

## Optimization Workflow

1. Load the selected case from `configs/cases.yml`.
2. Build the graph representation of the distribution network.
3. Create an initial population from the base topology plus feasible randomly generated radial configurations.
4. Evaluate each configuration using topology checks, OpenDSS AC power flow, and analytical reliability indices.
5. Cache evaluated configurations by the sorted tuple of open branches.
6. Generate one offspring attempt per current population member using a graph-aware close-open radial mutation.
7. If mutation cannot produce a valid exchange, use the graph-pruning fallback implemented in the optimizer.
8. Combine parent and offspring populations.
9. Apply non-dominated sorting and crowding distance.
10. Select the next generation through elitist environmental selection.
11. Repeat for the configured number of generations.
12. Store per-seed outputs and optional generation/archive histories.
13. Combine run-level outputs and extract representative solutions.

The implementation is an **NSGA-II-type adapted evolutionary search**, not a canonical NSGA-II implementation. It contains non-dominated sorting, crowding distance, parent-offspring environmental selection, and rank/crowding survival. It does not implement binary tournament parent selection, a mating pool, or crossover.

## OpenDSS Role

OpenDSS is used only for AC electrical evaluation. It does not optimize. For each candidate topology, the Python code prepares the DSS model, opens the specified elements, solves the power flow, and reads losses, convergence status, and voltage magnitudes.

## Reliability Calculation

SAIDI is used as the reliability objective. SAIFI and ENS are complementary metrics. The implemented model is analytical and expected-value based:

- branch failure rates and repair times are associated with network sections;
- load-point interruption frequency and duration are accumulated over upstream affecting branches in the radial topology;
- SAIDI, SAIFI, and ENS are computed from load-point users and demand.

The public configuration documents `repair_time_hours = 0.3659` and `failure_rate_per_km_year = 1.4634` as legacy reliability parameters for the released benchmark cases. The real-system public package does not disclose the restricted operator reliability workbook.

## Feasibility Classes

- `feasible`: connected, radial, and OpenDSS-converged.
- `operationally_feasible`: feasible, voltage-feasible under 0.90 to 1.05 p.u., no failed load-supply check, and no reported thermal violation.

Thermal limits are reported only when traceable ratings are available. The public real-system package does not include branch-level ampacity/rating data, so thermal feasibility is not asserted.

## Representative Solutions

Representative solutions are selected from the final feasible Pareto front:

- minimum active power losses;
- minimum SAIDI, with an explicit tolerance-based tie-break by lower active power losses;
- compromise solution by minimum Euclidean distance to the normalized ideal point over the run/final feasible Pareto front.

The empirical reference front used in Phase 4 is:

```text
P_ref = ND(union of all final run-level Pareto fronts)
```

It is an empirical reference front, not the true Pareto front.
