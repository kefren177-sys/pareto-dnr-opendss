# Pareto-Based Multi-Objective Distribution Network Reconfiguration for Active Power Loss Reduction and Reliability Improvement Using OpenDSS

This repository provides a clean and traceable companion package for a scientific article on Pareto-based multi-objective distribution network reconfiguration. It is designed primarily to verify the consolidated results reported in the manuscript. Partial reproduction is supported from the released CSV files and scripts; complete reruns require a compatible OpenDSS/Python environment.

The study uses an **NSGA-II-type strategy** coupled with **OpenDSS-based AC power flow evaluation**. OpenDSS is used as an electrical evaluator, not as an optimizer. The primary objectives are active power losses and SAIDI. SAIFI and ENS are reported as complementary reliability metrics.

## Study Cases

1. `five_node`: synthetic 5-node validation system.
2. `ieee33`: IEEE 33-bus distribution benchmark.
3. `real_system_anonymized`: anonymized real distribution system.

## Repository Structure

- `data/`: public CSV input data extracted from the simulation models.
- `opendss_models/`: OpenDSS models used for electrical evaluation. The real system model is anonymized.
- `src/`: lightweight verification and analysis utilities.
- `configs/`: relative YAML configuration files.
- `results/`: consolidated evaluated solutions, representative configurations, and Pareto fronts.
- `figures/`: article figures in PNG/PDF.
- `tables/`: compact article tables and cross-case summaries.
- `docs/`: methodology, reproducibility, confidentiality, and consistency documentation.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

OpenDSS verification requires `opendssdirect.py` and an OpenDSS-compatible environment. If OpenDSS is not available, the consolidated CSV files under `results/` provide the supported verification path for the reported values.

## Quick Verification

```bash
python src/run_case.py five_node
python src/run_case.py ieee33
python src/run_case.py real_system_anonymized
```

## Key Results

- Five-node validation: base active power losses 418.91 kW and controlled optimum 309.77 kW. This case is an algorithmic validation and is not operationally admissible because Vmin < 0.90 p.u.
- IEEE 33-bus system: minimum-loss solution opens 7, 9, 14, 32, 37 and yields 137.34 kW with SAIDI 3.355 h/customer-year.
- Real anonymized system: the compromise solution yields 856.42 kW, SAIDI 4.413 h/customer-year, SAIFI 12.060 interruptions/customer-year, ENS 95.775 MWh/year, and is operationally feasible.

## Confidentiality

The real-system case is anonymized. Original operator files, geographic names, commercial identifiers, internal feeder names, geolocation data, original spreadsheets, and the full evaluated-solution cloud are excluded. See `docs/confidentiality_note.md`.

## Citation

Please cite the companion article and this repository. A provisional `CITATION.cff` file is included and should be updated with DOI, journal, and final author metadata after publication.
