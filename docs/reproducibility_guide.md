# Reproducibility Guide

This repository distinguishes three reproducibility levels.

## Level 1. Verification from Consolidated CSV Files

This path does not require OpenDSS. It verifies the manuscript values from released consolidated files:

```bash
python src/run_case.py five_node
python src/run_case.py ieee33
python src/run_case.py real_system_anonymized
```

The script reads `results/<case>/representative_solutions.csv`. It is a verification utility, not the optimization driver.

## Level 2. Public Rerun of Released Optimization Cases

The released five-node and IEEE 33-node cases can be rerun with the actual evolutionary search:

```bash
python -m pip install -e .
dnr run ieee33 --open 33,34,35,36,37
dnr optimize ieee33 --method evolutionary --population 100 --generations 100 --reliability-objective saidi --seed 1234 --output-dir results/example_runs/ieee33_seed_1234
```

The optimization command executes population generation, graph-aware radial mutation, OpenDSS evaluation, reliability calculation, evaluation caching, non-dominated sorting, crowding distance, and elitist environmental selection.

For a short smoke run:

```bash
dnr optimize ieee33 --method evolutionary --population 10 --generations 5 --reliability-objective saidi --seed 1234 --output-dir results/example_runs/ieee33_smoke
```

## Level 3. IEEE 33-Node Statistical Campaign

The Phase 4 campaign used:

- case: `ieee33`
- method: `evolutionary`
- population: `100`
- generations: `100`
- reliability objective: `saidi`
- seeds:

```text
1234, 2026, 31415, 27182, 4242,
8675, 13579, 24680, 11235, 22346,
33457, 44568, 55679, 66780, 77891,
88902, 99013, 10124, 21235, 32346
```

Run each seed into a separate directory:

```bash
dnr optimize ieee33 --method evolutionary --population 100 --generations 100 --reliability-objective saidi --seed 1234 --output-dir results/phase4_runs/ieee33/seed_1234
```

Each run should produce:

- `all.csv`
- `pareto.csv`
- `summary.csv`
- `summary.json`
- `log.txt`
- `generation_history.csv`
- `pareto_history.csv`

Then run:

```bash
python scripts/phase4_postprocess.py results/phase4_runs/ieee33 --output-dir results/phase4_runs/ieee33/phase4
```

This regenerates:

- `phase4_run_metrics.csv`
- `phase4_statistical_summary.csv`
- `phase4_empirical_reference_front.csv`
- `phase4_convergence.csv`
- `phase4_protocol.json`

## Real-System Public Reproduction Boundary

The real distribution-system case is released as an anonymized traceability package. The public files include structured Annex C data, anonymized topology, representative solutions, and Pareto fronts. The original operator workbook used for private reliability data ingestion is not published.

Therefore:

- public users can verify the reported real-system results from CSV files;
- public users can inspect the anonymized topology and structural inputs;
- public users cannot fully rerun the private real-system optimization from only the public repository.

This limitation is intentional and is documented in `docs/confidentiality_note.md` and `docs/data_provenance_and_limitations.md`.

## Regenerating Figures and Tables

```bash
python scripts/generate_article_outputs.py
python scripts/generate_pareto_zoom_figures.py
```

The scripts operate on released consolidated results and do not rerun the optimizer.

## Expected OpenDSS Behavior

The evaluator compiles a generated DSS file, opens the requested line/switch elements, solves an AC power flow, and extracts active power losses and voltage magnitudes. OpenDSS is not used as an optimizer.
