# Pareto-Based Multi-Objective Distribution Network Reconfiguration for Active Power Loss Reduction and Reliability Improvement Using OpenDSS

This repository is the companion package for the manuscript provisionally titled **"Pareto-Based Multi-Objective Distribution Network Reconfiguration for Active Power Loss Reduction and Reliability Improvement Using OpenDSS"**.

It contains the Python implementation, released input data, OpenDSS models, consolidated results, statistical robustness artifacts, tables, and figures used to support the manuscript. The optimization code implements an **NSGA-II-type adapted evolutionary search** coupled with **OpenDSS-based AC power flow evaluation**. OpenDSS is used as an electrical evaluator, not as an optimizer.

The public repository supports complete reruns of the synthetic five-node and IEEE 33-node cases when a compatible Python/OpenDSS environment is available. The real distribution-system case is released as an anonymized traceability package with consolidated results and structured Annex C data; original operator files needed for a complete private rerun are not published.

## Repository Structure

- `configs/`: case and experiment configuration files with relative paths.
- `data/`: public input data, including the IEEE 33-node MATPOWER case and anonymized real-system tables.
- `docs/`: methodology, reproducibility, data provenance, confidentiality, and real-system documentation.
- `figures/`: manuscript figures in PNG/PDF form.
- `opendss_models/`: released OpenDSS models and generated DSS files.
- `results/`: consolidated results, per-seed statistical artifacts, Pareto fronts, and representative solutions.
- `scripts/`: postprocessing, multi-run consolidation, article-output, and Phase 4 statistical scripts.
- `src/dnr/`: optimization, evaluation, reliability, graph, Pareto, selection, and CLI implementation.
- `tables/`: manuscript-support tables in CSV format.
- `tests/`: regression and postprocessing tests.

## Installation

Recommended setup:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Alternatively:

```bash
python -m pip install -r requirements.txt
```

OpenDSS-based evaluation requires `OpenDSSDirect.py` and a compatible OpenDSS backend. On machines without OpenDSS support, use the released CSV files for result verification.

## Environment

The code is Python-based and uses NumPy, pandas, NetworkX, matplotlib, Typer, PyYAML, and OpenDSSDirect.py. Version information available from the development environment is summarized in `docs/environment_and_software.md`. If an exact OpenDSS engine version is not recorded in the logs, it is marked as unresolved rather than inferred.

## IEEE 33-Node Case

The IEEE 33-node case can be executed from the released repository:

```bash
dnr run ieee33 --open 33,34,35,36,37
dnr optimize ieee33 --method evolutionary --population 100 --generations 100 --reliability-objective saidi --seed 1234 --output-dir results/example_runs/ieee33_seed_1234
```

The 20-run statistical campaign used for Phase 4 is stored under `results/phase4_runs/ieee33/`. To rerun the campaign in a new output directory, use the same command pattern and the seeds documented in `docs/reproducibility_guide.md`.

## Real Distribution-System Case

The real-system release is anonymized. It includes:

- anonymized topology exported from AutoCAD in `docs/real_system/`;
- `docs/real_system/real_system_annex_C_data.xlsx`;
- representative solutions and Pareto fronts under `results/real_system_anonymized/`;
- manuscript-support tables under `tables/`.

The public anonymized package documents 131 line sections, 109 load nodes, 22 reconfigurable links, 43,068 customers, and total demand of 20,849.76 kW / 10,098.05 kVAr. It does not publish original operator spreadsheets, geographic identifiers, or restricted reliability workbooks. Therefore, public users can verify reported values from consolidated outputs but cannot fully rerun the private real-system optimization from only the public files.

## Running a Single Optimization

After installation:

```bash
dnr optimize five_node --method evolutionary --population 20 --generations 10 --reliability-objective saidi --seed 1234 --output-dir results/example_runs/five_node_seed_1234
dnr optimize ieee33 --method evolutionary --population 100 --generations 100 --reliability-objective saidi --seed 1234 --output-dir results/example_runs/ieee33_seed_1234
```

Each run writes `all.csv`, `pareto.csv`, `summary.csv`, `summary.json`, `log.txt`, `generation_history.csv`, and `pareto_history.csv`.

## Running Multiple Independent Seeds

The IEEE 33-node statistical campaign used these seeds:

```text
1234, 2026, 31415, 27182, 4242,
8675, 13579, 24680, 11235, 22346,
33457, 44568, 55679, 66780, 77891,
88902, 99013, 10124, 21235, 32346
```

Use the same fixed population, generation count, and reliability objective:

```bash
dnr optimize ieee33 --method evolutionary --population 100 --generations 100 --reliability-objective saidi --seed 1234 --output-dir results/phase4_runs/ieee33/seed_1234
```

Repeat for each seed in a separate folder.

Or use the helper script:

```bash
python scripts/run_ieee33_phase4_campaign.py --output-root results/phase4_runs/ieee33
```

## Statistical Robustness Assessment

After all runs exist:

```bash
python scripts/phase4_postprocess.py results/phase4_runs/ieee33 --output-dir results/phase4_runs/ieee33/phase4
```

The script computes run-level metrics, empirical-reference-front IGD, normalized hypervolume with reference point `(1.05, 1.05)`, spacing, benchmark recovery, and convergence versus cumulative unique OpenDSS evaluations. The empirical reference front is not claimed to be the true Pareto front.

## Generating Tables

Use the released CSV files under `tables/` directly, or regenerate article-support outputs from consolidated results:

```bash
python scripts/generate_article_outputs.py
```

## Generating Figures

Selected figure-generation scripts are provided under `scripts/`:

```bash
python scripts/generate_article_outputs.py
python scripts/generate_pareto_zoom_figures.py
```

The Phase 4 HV convergence figure is stored in `results/phase4_runs/ieee33/phase4/`.

## Reproducibility

This repository supports:

- full algorithmic reruns for the released five-node and IEEE 33-node cases;
- per-seed traceability for the IEEE 33-node Phase 4 campaign;
- regeneration of statistical postprocessing from stored per-run results;
- verification of anonymized real-system manuscript values from consolidated CSV outputs.

It does not claim full public rerun capability for the restricted real-system optimization because the original operator files and restricted reliability workbook are excluded.

## Data Provenance and Limitations

See `docs/data_provenance_and_limitations.md`. The historical CSV field `operationally_feasible` should be read as a modeled-feasibility flag dominated by voltage compliance under the released constraints, not as a complete field-operability validation. Thermal ratings are not published as traceable branch-level data, so thermal feasibility is not claimed. Protection coordination, switching sequences, full source-capacity validation, ampacity verification, and field-operability beyond the modeled topology/voltage constraints are outside the public dataset.

## Citation

Use `CITATION.cff` for provisional citation metadata. Update DOI, journal, and final manuscript metadata after publication.

## Fixed Release / Commit

The manuscript revision is intended to be associated with the Git tag `manuscript-revision-2026`.
