"""Scheduled tasks — run Spine commands at set times."""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = ROOT / "memory" / "scheduler.json"

DEFAULT_TASKS = [
    {
        "id": "morning_index",
        "time": "08:00",
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "command": "index",
        "enabled": True,
    },
]


def _load_tasks() -> list[dict[str, Any]]:
    if SCHEDULE_FILE.exists():
        try:
            with SCHEDULE_FILE.open(encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            pass
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(DEFAULT_TASKS, indent=2), encoding="utf-8")
    return list(DEFAULT_TASKS)


def _save_tasks(tasks: list[dict[str, Any]]) -> None:
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SCHEDULE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(tasks, handle, indent=2)


def list_tasks() -> str:
    tasks = _load_tasks()
    if not tasks:
        return "No scheduled tasks."
    lines = ["Scheduled tasks:", ""]
    for t in tasks:
        status = "on" if t.get("enabled", True) else "off"
        lines.append(
            f"  [{status}] {t.get('id')} — {t.get('time')} "
            f"({','.join(t.get('days', []))}) -> {t.get('command')}"
        )
    lines.append("")
    lines.append("Edit: memory/scheduler.json")
    lines.append("Or: schedule add 09:00 index")
    return "\n".join(lines)


def add_task(time_str: str, command: str, task_id: str = "") -> str:
    tasks = _load_tasks()
    tid = task_id or f"task_{len(tasks) + 1}"
    tasks.append({
        "id": tid,
        "time": time_str,
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "command": command,
        "enabled": True,
        "last_run": "",
    })
    _save_tasks(tasks)
    return f"Scheduled '{command}' daily at {time_str} (id: {tid})."


class TaskScheduler:
    def __init__(self, handler: Callable[[str], str], *, interval: int = 60) -> None:
        self.handler = handler
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._fired: set[str] = set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logging.info("Task scheduler started.")

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._tick()
            self._stop.wait(self.interval)

    def _tick(self) -> None:
        now = datetime.now()
        day = now.strftime("%a").lower()
        slot = now.strftime("%H:%M")
        date_key = now.strftime("%Y-%m-%d")

        for task in _load_tasks():
            if not task.get("enabled", True):
                continue
            if task.get("time") != slot:
                continue
            if day not in [d.lower() for d in task.get("days", [])]:
                continue

            fire_id = f"{task.get('id')}:{date_key}:{slot}"
            if fire_id in self._fired:
                continue

            cmd = task.get("command", "")
            logging.info("Scheduler running: %s", cmd)
            try:
                self.handler(cmd)
            except Exception as exc:
                logging.error("Scheduled task failed: %s", exc)
            self._fired.add(fire_id)

            if len(self._fired) > 200:
                self._fired.clear()


def handle_schedule_command(task: str) -> str:
    parts = task.strip().split(maxsplit=2)
    if not parts:
        return list_tasks()
    cmd = parts[0].lower()
    if cmd in {"list", "ls"}:
        return list_tasks()
    if cmd == "add" and len(parts) >= 3:
        return add_task(parts[1], parts[2])
    return list_tasks()
