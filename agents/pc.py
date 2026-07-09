"""PC agent — controlled system tools with confirmation for file operations."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from agents.base import AgentResult, BaseAgent

WINDOWS_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "paint": "mspaint.exe",
}

FORBIDDEN_ROOTS = {
    Path("C:/Windows"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/ProgramData"),
}

MAX_ORGANIZE_FILES = 100


@dataclass
class OrganizePlan:
    source_dir: Path
    moves: list[tuple[Path, Path]] = field(default_factory=list)

    @property
    def description(self) -> str:
        if not self.moves:
            return "No file moves proposed."

        lines = [f"Organize {len(self.moves)} file(s) in {self.source_dir}:"]
        for src, dst in self.moves[:20]:
            lines.append(f"  {src.name}  ->  {dst.parent.name}/")
        if len(self.moves) > 20:
            lines.append(f"  ... and {len(self.moves) - 20} more")
        lines.append("Type 'confirm' to apply or 'cancel' to abort.")
        return "\n".join(lines)


class PcAgent(BaseAgent):
    name = "pc"
    description = "Controlled PC tools — open apps, list processes, organize folders"

    def __init__(self, model: str, user_title: str = "Sir", action_log=None) -> None:
        super().__init__(model, user_title)
        self.action_log = action_log
        self.pending_plan: OrganizePlan | None = None

    def _log(self, action: str, target: str, status: str, details: dict | None = None) -> None:
        if self.action_log:
            self.action_log.record(action, target, status, details)

    def _resolve_path(self, raw: str) -> Path:
        return Path(raw).expanduser().resolve()

    def _is_forbidden(self, path: Path) -> bool:
        for root in FORBIDDEN_ROOTS:
            try:
                path.relative_to(root.resolve())
                return True
            except ValueError:
                continue
        return False

    def run(self, task: str) -> AgentResult:
        parts = task.strip().split(maxsplit=1)
        if not parts:
            return AgentResult(self.name, self._help())

        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command == "open":
            return self._open(argument)
        if command == "processes":
            return self._processes()
        if command == "organize":
            return self._organize(argument)
        if command in {"help", "commands"}:
            return AgentResult(self.name, self._help())

        return AgentResult(
            self.name,
            f"Unknown PC command '{command}', {self.user_title}. Type 'pc help' for options.",
        )

    def _help(self) -> str:
        return (
            f"PC module commands for {self.user_title}:\n"
            "  pc open <app|path>     — Open an application or file\n"
            "  pc processes           — List running processes (read-only)\n"
            "  pc organize <folder>   — Plan folder organization (requires confirm)\n"
            "  pc help                — Show this help\n"
            "After 'pc organize', use 'confirm' or 'cancel'."
        )

    def _open(self, target: str) -> AgentResult:
        if not target:
            return AgentResult(self.name, f"Specify an app or path to open, {self.user_title}.")

        lowered = target.lower()
        try:
            if lowered in WINDOWS_APPS:
                subprocess.Popen([WINDOWS_APPS[lowered]], shell=False)
                self._log("open", lowered, "success")
                return AgentResult(self.name, f"Opened {lowered}, {self.user_title}.")

            path = self._resolve_path(target)
            if self._is_forbidden(path):
                self._log("open", str(path), "blocked", {"reason": "forbidden path"})
                return AgentResult(self.name, f"That path is protected, {self.user_title}.")

            os.startfile(path)  # type: ignore[attr-defined]
            self._log("open", str(path), "success")
            return AgentResult(self.name, f"Opened {path}, {self.user_title}.")
        except Exception as exc:
            logging.error("Open failed: %s", exc)
            self._log("open", target, "error", {"error": str(exc)})
            return AgentResult(self.name, f"Could not open '{target}', {self.user_title}. {exc}")

    def _processes(self) -> AgentResult:
        try:
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            output = result.stdout.strip()
            lines = output.splitlines()
            preview = "\n".join(lines[:25])
            if len(lines) > 25:
                preview += f"\n... ({len(lines) - 25} more lines)"

            self._log("processes", "tasklist", "success", {"lines": len(lines)})
            return AgentResult(
                self.name,
                f"Running processes report, {self.user_title}:\n\n{preview}",
                details=output,
            )
        except Exception as exc:
            logging.error("Process list failed: %s", exc)
            self._log("processes", "tasklist", "error", {"error": str(exc)})
            return AgentResult(self.name, f"Could not list processes, {self.user_title}.")

    def _organize(self, target: str) -> AgentResult:
        if not target:
            return AgentResult(self.name, f"Specify a folder to organize, {self.user_title}.")

        folder = self._resolve_path(target)
        if not folder.is_dir():
            return AgentResult(self.name, f"'{target}' is not a valid folder, {self.user_title}.")

        if self._is_forbidden(folder):
            self._log("organize", str(folder), "blocked", {"reason": "forbidden path"})
            return AgentResult(self.name, f"That folder is protected, {self.user_title}.")

        groups: dict[str, list[Path]] = defaultdict(list)
        count = 0
        for item in folder.iterdir():
            if not item.is_file() or item.name.startswith("."):
                continue
            ext = item.suffix.lower().lstrip(".") or "other"
            groups[ext].append(item)
            count += 1
            if count >= MAX_ORGANIZE_FILES:
                break

        if not groups:
            return AgentResult(self.name, f"No files to organize in {folder}, {self.user_title}.")

        plan = OrganizePlan(source_dir=folder)
        for ext, files in groups.items():
            dest_dir = folder / ext.upper()
            for file_path in files:
                plan.moves.append((file_path, dest_dir / file_path.name))

        self.pending_plan = plan
        self._log("organize", str(folder), "planned", {"files": len(plan.moves)})
        return AgentResult(
            self.name,
            f"Organization plan prepared, {self.user_title}.\n\n{plan.description}",
            details=plan.description,
        )

    def apply_pending(self) -> AgentResult:
        if not self.pending_plan:
            return AgentResult(self.name, f"No pending action to confirm, {self.user_title}.")

        plan = self.pending_plan
        moved = 0
        errors: list[str] = []

        for src, dst in plan.moves:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                moved += 1
            except Exception as exc:
                errors.append(f"{src.name}: {exc}")

        self.pending_plan = None
        status = "success" if not errors else "partial"
        self._log("organize_apply", str(plan.source_dir), status, {"moved": moved, "errors": len(errors)})

        if errors:
            detail = "\n".join(errors[:5])
            return AgentResult(
                self.name,
                f"Partially complete, {self.user_title}. Moved {moved} file(s). "
                f"{len(errors)} error(s):\n{detail}",
            )

        return AgentResult(
            self.name,
            f"Confirmed, {self.user_title}. Moved {moved} file(s) in {plan.source_dir}.",
        )

    def cancel_pending(self) -> AgentResult:
        if not self.pending_plan:
            return AgentResult(self.name, f"No pending action to cancel, {self.user_title}.")

        folder = str(self.pending_plan.source_dir)
        self.pending_plan = None
        self._log("organize_apply", folder, "cancelled")
        return AgentResult(self.name, f"Action cancelled, {self.user_title}. No files were changed.")
