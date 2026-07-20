from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_open_switches(text: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in str(text).split(",") if part.strip())
