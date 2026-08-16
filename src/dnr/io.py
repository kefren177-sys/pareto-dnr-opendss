from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .models import Evaluation


def write_results(
    evaluations: list[Evaluation],
    output_dir: Path,
    stem: str,
    metadata: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [ev.to_record() for ev in evaluations]
    if metadata:
        for record in records:
            record.update(metadata)
    csv_path = output_dir / f"{stem}.csv"
    json_path = output_dir / f"{stem}.json"
    pd.DataFrame(records).to_csv(csv_path, index=False, encoding="utf-8")
    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, json_path
