from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


IEEE33_PHASE4_SEEDS = [
    1234,
    2026,
    31415,
    27182,
    4242,
    8675,
    13579,
    24680,
    11235,
    22346,
    33457,
    44568,
    55679,
    66780,
    77891,
    88902,
    99013,
    10124,
    21235,
    32346,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fixed IEEE33 Phase 4 campaign.")
    parser.add_argument("--output-root", type=Path, default=Path("results/phase4_runs/ieee33"))
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--generations", type=int, default=100)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    for seed in IEEE33_PHASE4_SEEDS:
        output_dir = args.output_root / f"seed_{seed}"
        cmd = [
            "dnr",
            "optimize",
            "ieee33",
            "--method",
            "evolutionary",
            "--population",
            str(args.population),
            "--generations",
            str(args.generations),
            "--reliability-objective",
            "saidi",
            "--seed",
            str(seed),
            "--output-dir",
            str(output_dir),
        ]
        if args.overwrite:
            cmd.append("--overwrite")
        print(" ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
