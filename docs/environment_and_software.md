# Environment and Software

This file records the environment information that could be verified from the local development environment used to prepare this repository revision.

## Verified Python Environment

- Operating system observed: Windows 10/11 family, `Windows-10-10.0.26200-SP0` in the Conda `DNR` environment report.
- Python: 3.11.15 in the Conda `DNR` environment.
- NumPy: 1.26.4.
- pandas: 2.2.3.
- NetworkX: 3.6.1.
- matplotlib: 3.10.9.
- PyYAML: 6.0.3.
- Typer: 0.25.0.
- openpyxl: 3.1.5.
- SciPy: 1.14.1.
- OpenDSSDirect.py: 0.9.4.

`rich` is used by Typer for CLI output, but its exact imported `__version__` was not resolved from the package object. `pytest` is included in `requirements.txt` for regression tests.

## OpenDSS Configuration

The code uses OpenDSS through OpenDSSDirect.py. The evaluator compiles a generated DSS file, disables the lines listed in the open-switch set, calls the OpenDSS solution, and reads convergence, losses, and bus voltage magnitudes.

The source code does not explicitly set all OpenDSS solver options such as solution mode, control mode, iteration limits, or tolerances. Options not explicitly set by the code should be treated as OpenDSS/OpenDSSDirect defaults for the installed backend.

## Hardware

The repository logs and metadata do not contain a complete, citable hardware specification. CPU model, RAM, and core count are therefore unresolved for the public revision.
