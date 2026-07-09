"""Structured action logging for thesis evaluation and audit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ActionLog:
    def __init__(self, logs_dir: str) -> None:
        self.path = Path(logs_dir) / "actions.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, action: str, target: str, status: str, details: dict[str, Any] | None = None) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target": target,
            "status": status,
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
