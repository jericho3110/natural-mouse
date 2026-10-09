"""Persists the name -> template-image-path mapping the GUI shows in its
target list, so captured targets survive closing and reopening the app."""

from __future__ import annotations

import json
from pathlib import Path

TARGETS_FILE = Path("targets.json")


def load_targets() -> dict[str, str]:
    if not TARGETS_FILE.exists():
        return {}
    return json.loads(TARGETS_FILE.read_text())


def save_targets(targets: dict[str, str]) -> None:
    TARGETS_FILE.write_text(json.dumps(targets, indent=2))
