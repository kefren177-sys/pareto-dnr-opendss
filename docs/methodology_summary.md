# Methodology Summary

The proposed workflow evaluates distribution network reconfiguration candidates through a Pareto-based multi-objective search.

1. A candidate solution is represented by the set of open switches.
2. Connectivity and radiality are checked using graph-based tests.
3. OpenDSS performs AC power flow evaluation for each candidate. OpenDSS is used as an electrical evaluator, not as an optimizer.
4. Active power losses, voltage profiles, and convergence status are extracted from OpenDSS.
5. SAIDI is used as the reliability objective. SAIFI and ENS are complementary reliability metrics.
6. Non-dominated solutions are selected using Pareto dominance over active power losses and SAIDI.
7. Operationally feasible solutions satisfy radiality, connectivity, OpenDSS convergence, load supply, and voltage limits of 0.90 to 1.05 p.u.
8. Thermal limits are reported only when traceable data are available. No thermal constraints are claimed for the anonymized real system.

The strategy is described as an NSGA-II-type strategy because the implementation follows non-dominated sorting and diversity-oriented selection, but it should not be represented as a canonical NSGA-II implementation with an explicit crossover operator.
