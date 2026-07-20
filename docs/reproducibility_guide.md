# Reproducibility Guide

This repository supports three levels of traceability. It should not be read as a promise that every final optimization run can be repeated on every machine without the original working environment.

## 1. Verification from Consolidated CSV Files

This is the primary supported path for reviewers. It does not require OpenDSS and verifies the reported representative solutions from released CSV files.

Run:

```bash
python src/run_case.py five_node
python src/run_case.py ieee33
python src/run_case.py real_system_anonymized
```

These commands read the consolidated CSV files and print representative base, minimum-loss, minimum-SAIDI, and compromise solutions.

## 2. Partial Reproduction from Released Data

The released CSV files allow independent verification of:

- representative configurations;
- active power losses, voltage limits, SAIDI, SAIFI, and ENS reported in the article;
- feasible and operationally feasible Pareto fronts;
- tables and figures derived from consolidated outputs.

The anonymized real-system release excludes the full evaluated-solution cloud. For that case, public verification uses `representative_solutions.csv`, `summarized_results.csv`, and the Pareto-front CSV files.

## 3. Inspect Pareto Fronts

Use:

- `results/ieee33/pareto_feasible.csv`
- `results/ieee33/pareto_operationally_feasible.csv`
- `results/real_system_anonymized/pareto_feasible.csv`
- `results/real_system_anonymized/pareto_operationally_feasible.csv`

The fronts minimize active power losses and SAIDI.

## 4. Complete Reproduction with OpenDSS

OpenDSS models are under `opendss_models/`. Complete reproduction of electrical evaluations requires:

- a Python environment compatible with the packages in `requirements.txt`;
- `opendssdirect.py`;
- a working OpenDSS backend for the operating system;
- the released anonymized OpenDSS models.

Use `src/evaluate_opendss.py` as a starting helper for point evaluations. Some environments, especially non-Windows systems, may not support OpenDSS directly. In that case, use the consolidated CSV files for traceability.

## 5. Real-System Confidentiality

The real-system case is intentionally anonymized. Public verification focuses on consolidated electrical and reliability outputs rather than original operator files.
