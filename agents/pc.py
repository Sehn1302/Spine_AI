"""PC agent — apps, documents, folder cleanup with confirmation."""

from __future__ import annotations

import hashlib
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
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
}

FORBIDDEN_ROOTS = {
    Path("C:/Windows"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/ProgramData"),
}

MAX_SCAN_FILES = 500
HASH_CHUNK = 65536


@dataclass
class PendingAction:
    action: str
    source_dir: Path
    moves: list[tuple[Path, Path]] = field(default_factory=list)
    deletes: list[Path] = field(default_factory=list)

    @property
    def description(self) -> str:
        lines = [f"Action: {self.action} in {self.source_dir}"]

        if self.moves:
            lines.append(f"Move {len(self.moves)} file(s):")
            for src, dst in self.moves[:15]:
                lines.append(f"  {src.name}  ->  {dst.parent.name}/")
            if len(self.moves) > 15:
                lines.append(f"  ... and {len(self.moves) - 15} more")

        if self.deletes:
            freed = sum(p.stat().st_size for p in self.deletes if p.exists())
            lines.append(f"Delete {len(self.deletes)} duplicate file(s) (~{freed / 1_048_576:.1f} MB):")
            for path in self.deletes[:15]:
                lines.append(f"  {path.name}")
            if len(self.deletes) > 15:
                lines.append(f"  ... and {len(self.deletes) - 15} more")

        lines.append("Type 'confirm' to apply or 'cancel' to abort.")
        return "\n".join(lines)


class PcAgent(BaseAgent):
    name = "pc"
    description = "Launch apps, write documents, organize folders, remove duplicates"

    def __init__(self, model: str, user_title: str = "Sir", action_log=None, host_caps=None) -> None:
        super().__init__(model, user_title)
        self.action_log = action_log
        self.host_caps = host_caps
        self.pending: PendingAction | None = None

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

    def _safe_folder(self, target: str) -> Path | None:
        if not target:
            return None
        folder = self._resolve_path(target)
        if not folder.is_dir():
            return None
        if self._is_forbidden(folder):
            return None
        return folder

    def run(self, task: str) -> AgentResult:
        parts = task.strip().split(maxsplit=1)
        if not parts:
            return AgentResult(self.name, self._help())

        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""

        handlers = {
            "open": self._open,
            "launch": self._launch,
            "write": self._write,
            "processes": lambda _: self._processes(),
            "organize": self._organize,
            "duplicates": self._duplicates,
            "cleanup": self._cleanup,
            "capabilities": self._capabilities,
            "software": self._capabilities,
            "help": lambda _: AgentResult(self.name, self._help()),
            "commands": lambda _: AgentResult(self.name, self._help()),
        }

        handler = handlers.get(command)
        if handler:
            return handler(argument)

        return AgentResult(
            self.name,
            f"Unknown PC command '{command}', {self.user_title}. Type 'pc help' for options.",
        )

    def _help(self) -> str:
        return (
            f"PC module commands for {self.user_title}:\n"
            "  pc launch <app>         — Launch any app (Minecraft, Chrome, Word, etc.)\n"
            "  pc open <app|path>      — Open app or file path\n"
            "  pc write <path> <text>  — Create a text or Word (.docx) file\n"
            "  pc organize <folder>    — Sort files into type folders\n"
            "  pc duplicates <folder>  — Find and remove duplicate files\n"
            "  pc cleanup <folder>     — Organize + remove duplicates\n"
            "  pc processes            — List running processes\n"
            "  pc capabilities         — Show detected host software\n"
            "  pc help                   — Show this help\n"
            "After organize/duplicates/cleanup, use 'confirm' or 'cancel'.\n"
            "Voice examples: 'launch minecraft', 'remove duplicates in Downloads'"
        )

    def _capabilities(self, _: str = "") -> AgentResult:
        if not self.host_caps:
            return AgentResult(self.name, f"No host scan available, {self.user_title}.")
        return AgentResult(self.name, self.host_caps.format_report())

    def _launch(self, target: str) -> AgentResult:
        if not target:
            return AgentResult(self.name, f"Specify an application to launch, {self.user_title}.")

        name = target.strip()
        lowered = name.lower()

        if self.host_caps:
            host_target = self.host_caps.launch_target(name)
            if host_target:
                try:
                    subprocess.run(
                        ["powershell", "-Command", f'Start-Process "{host_target}"'],
                        check=False,
                        timeout=15,
                    )
                    self._log("launch", host_target, "success", {"source": "host_caps"})
                    return AgentResult(
                        self.name,
                        f"Launched {host_target} using detected host software, {self.user_title}.",
                    )
                except Exception as exc:
                    logging.debug("Host launch failed, falling back: %s", exc)

        try:
            if lowered in WINDOWS_APPS:
                subprocess.Popen([WINDOWS_APPS[lowered]], shell=False)
                self._log("launch", lowered, "success")
                return AgentResult(self.name, f"Launched {lowered}, {self.user_title}.")

            subprocess.run(
                ["powershell", "-Command", f'Start-Process "{name}"'],
                check=False,
                timeout=15,
            )
            self._log("launch", name, "success")
            return AgentResult(self.name, f"Launch command sent for '{name}', {self.user_title}.")
        except Exception as exc:
            logging.error("Launch failed: %s", exc)
            self._log("launch", name, "error", {"error": str(exc)})
            return AgentResult(self.name, f"Could not launch '{name}', {self.user_title}. {exc}")

    def _open(self, target: str) -> AgentResult:
        if not target:
            return AgentResult(self.name, f"Specify an app or path, {self.user_title}.")

        lowered = target.lower()
        try:
            if lowered in WINDOWS_APPS:
                subprocess.Popen([WINDOWS_APPS[lowered]], shell=False)
                self._log("open", lowered, "success")
                return AgentResult(self.name, f"Opened {lowered}, {self.user_title}.")

            path = self._resolve_path(target)
            if path.exists():
                if self._is_forbidden(path):
                    return AgentResult(self.name, f"That path is protected, {self.user_title}.")
                os.startfile(path)  # type: ignore[attr-defined]
                self._log("open", str(path), "success")
                return AgentResult(self.name, f"Opened {path}, {self.user_title}.")
        except Exception:
            pass

        return self._launch(target)

    def _write(self, argument: str) -> AgentResult:
        if not argument:
            return AgentResult(self.name, f"Usage: pc write <filepath> <content>, {self.user_title}.")

        parts = argument.split(maxsplit=1)
        if len(parts) < 2:
            return AgentResult(self.name, f"Provide file path and content, {self.user_title}.")

        raw_path, content = parts[0], parts[1]
        path = self._resolve_path(raw_path)
        parent = path.parent

        if self._is_forbidden(parent):
            return AgentResult(self.name, f"That location is protected, {self.user_title}.")

        try:
            parent.mkdir(parents=True, exist_ok=True)

            if path.suffix.lower() == ".docx":
                from docx import Document

                doc = Document()
                doc.add_paragraph(content)
                doc.save(str(path))
            else:
                path.write_text(content + "\n", encoding="utf-8")

            self._log("write", str(path), "success", {"chars": len(content)})
            return AgentResult(self.name, f"Written to {path}, {self.user_title}.")
        except Exception as exc:
            logging.error("Write failed: %s", exc)
            self._log("write", str(path), "error", {"error": str(exc)})
            return AgentResult(self.name, f"Could not write file, {self.user_title}. {exc}")

    def _processes(self) -> AgentResult:
        try:
            result = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=15, check=False)
            output = result.stdout.strip()
            lines = output.splitlines()
            preview = "\n".join(lines[:25])
            if len(lines) > 25:
                preview += f"\n... ({len(lines) - 25} more lines)"
            self._log("processes", "tasklist", "success")
            return AgentResult(self.name, f"Running processes, {self.user_title}:\n\n{preview}", details=output)
        except Exception as exc:
            return AgentResult(self.name, f"Could not list processes, {self.user_title}.")

    def _scan_files(self, folder: Path) -> list[Path]:
        files: list[Path] = []
        for item in folder.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                files.append(item)
                if len(files) >= MAX_SCAN_FILES:
                    break
        return files

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.md5()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(HASH_CHUNK), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _find_duplicates(self, folder: Path) -> list[Path]:
        by_size: dict[int, list[Path]] = defaultdict(list)
        for path in self._scan_files(folder):
            try:
                by_size[path.stat().st_size].append(path)
            except OSError:
                continue

        to_delete: list[Path] = []
        for size_group in by_size.values():
            if len(size_group) < 2:
                continue
            by_hash: dict[str, list[Path]] = defaultdict(list)
            for path in size_group:
                try:
                    by_hash[self._hash_file(path)].append(path)
                except OSError:
                    continue
            for paths in by_hash.values():
                if len(paths) > 1:
                    paths.sort(key=lambda p: p.stat().st_mtime)
                    to_delete.extend(paths[1:])
        return to_delete

    def _organize_plan(self, folder: Path) -> PendingAction:
        plan = PendingAction(action="organize", source_dir=folder)
        groups: dict[str, list[Path]] = defaultdict(list)
        for item in folder.iterdir():
            if not item.is_file() or item.name.startswith("."):
                continue
            ext = item.suffix.lower().lstrip(".") or "other"
            groups[ext].append(item)

        for ext, files in groups.items():
            dest_dir = folder / ext.upper()
            for file_path in files:
                plan.moves.append((file_path, dest_dir / file_path.name))
        return plan

    def _organize(self, target: str) -> AgentResult:
        folder = self._safe_folder(target)
        if not folder:
            return AgentResult(self.name, f"Specify a valid folder, {self.user_title}.")

        plan = self._organize_plan(folder)
        if not plan.moves:
            return AgentResult(self.name, f"No files to organize in {folder}, {self.user_title}.")

        self.pending = plan
        self._log("organize", str(folder), "planned", {"files": len(plan.moves)})
        return AgentResult(self.name, f"Organization plan prepared, {self.user_title}.\n\n{plan.description}")

    def _duplicates(self, target: str) -> AgentResult:
        folder = self._safe_folder(target)
        if not folder:
            return AgentResult(self.name, f"Specify a valid folder, {self.user_title}.")

        deletes = self._find_duplicates(folder)
        if not deletes:
            return AgentResult(self.name, f"No duplicates found in {folder}, {self.user_title}.")

        self.pending = PendingAction(action="duplicates", source_dir=folder, deletes=deletes)
        self._log("duplicates", str(folder), "planned", {"count": len(deletes)})
        return AgentResult(self.name, f"Duplicate removal plan prepared, {self.user_title}.\n\n{self.pending.description}")

    def _cleanup(self, target: str) -> AgentResult:
        folder = self._safe_folder(target)
        if not folder:
            return AgentResult(self.name, f"Specify a valid folder, {self.user_title}.")

        plan = self._organize_plan(folder)
        plan.action = "cleanup"
        plan.deletes = self._find_duplicates(folder)

        if not plan.moves and not plan.deletes:
            return AgentResult(self.name, f"Nothing to clean in {folder}, {self.user_title}.")

        self.pending = plan
        self._log("cleanup", str(folder), "planned", {"moves": len(plan.moves), "deletes": len(plan.deletes)})
        return AgentResult(self.name, f"Cleanup plan prepared, {self.user_title}.\n\n{plan.description}")

    def apply_pending(self) -> AgentResult:
        if not self.pending:
            return AgentResult(self.name, f"No pending action to confirm, {self.user_title}.")

        plan = self.pending
        moved = deleted = 0
        errors: list[str] = []

        for src, dst in plan.moves:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                moved += 1
            except Exception as exc:
                errors.append(f"move {src.name}: {exc}")

        for path in plan.deletes:
            try:
                if path.exists():
                    path.unlink()
                    deleted += 1
            except Exception as exc:
                errors.append(f"delete {path.name}: {exc}")

        self.pending = None
        self._log(plan.action, str(plan.source_dir), "success", {"moved": moved, "deleted": deleted})

        msg = f"Confirmed, {self.user_title}. "
        if moved:
            msg += f"Moved {moved} file(s). "
        if deleted:
            msg += f"Removed {deleted} duplicate(s). "
        if errors:
            msg += f"{len(errors)} error(s) occurred."
        return AgentResult(self.name, msg.strip())

    def cancel_pending(self) -> AgentResult:
        if not self.pending:
            return AgentResult(self.name, f"No pending action to cancel, {self.user_title}.")
        self.pending = None
        self._log("cancel", "pending", "cancelled")
        return AgentResult(self.name, f"Action cancelled, {self.user_title}. No changes were made.")
