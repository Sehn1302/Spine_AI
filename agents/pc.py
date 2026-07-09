"""PC agent — apps, browser, Spotify, documents, folder cleanup."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import time
import urllib.parse
import webbrowser
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from agents.app_control import (
    focus_window,
    kill_process,
    launch_app,
    list_windows,
    open_url,
    research_paper_urls,
    run_powershell,
    run_shell,
    send_keys,
    spotify_play,
)
from agents.action_planner import plan_action
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
    "chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "spotify": "spotify",
    "browser": "chrome",
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

    def __init__(
        self,
        model: str,
        user_title: str = "Sir",
        action_log=None,
        host_caps=None,
        *,
        unrestricted: bool = True,
    ) -> None:
        super().__init__(model, user_title)
        self.action_log = action_log
        self.host_caps = host_caps
        self.unrestricted = unrestricted
        self.pending: PendingAction | None = None

    def _log(self, action: str, target: str, status: str, details: dict | None = None) -> None:
        if self.action_log:
            self.action_log.record(action, target, status, details)

    def _resolve_path(self, raw: str) -> Path:
        return Path(raw).expanduser().resolve()

    def _is_forbidden(self, path: Path) -> bool:
        if self.unrestricted:
            return False
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
            "do": self._do,
            "exec": self._exec,
            "run": self._exec,
            "focus": self._focus,
            "keys": self._keys,
            "kill": self._kill,
            "windows": lambda _: self._windows(),
            "open": self._open,
            "launch": self._launch,
            "write": self._write,
            "write_down": self._write_down,
            "open_and_type": self._open_and_type,
            "processes": lambda _: self._processes(),
            "organize": self._organize,
            "organize_all": self._organize_all,
            "duplicates": self._duplicates,
            "cleanup": self._cleanup,
            "cleanup_all": self._cleanup_all,
            "capabilities": self._capabilities,
            "software": self._capabilities,
            "papers": self._papers,
            "browse": self._browse,
            "spotify": self._spotify,
            "music": self._spotify,
            "help": lambda _: AgentResult(self.name, self._help()),
            "commands": lambda _: AgentResult(self.name, self._help()),
        }

        handler = handlers.get(command)
        if handler:
            return handler(argument)

        if self.unrestricted:
            return self._do(task)

        return AgentResult(
            self.name,
            f"Unknown PC command '{command}', {self.user_title}. Type 'pc help' for options.",
        )

    def _help(self) -> str:
        mode = "UNRESTRICTED — full PC control" if self.unrestricted else "restricted"
        return (
            f"PC control ({mode}) for {self.user_title}:\n"
            "  pc do <anything>       — AI figures out how to control your PC\n"
            "  pc exec <command>     — Run any shell/PowerShell command\n"
            "  pc launch <app>       — Launch any installed app\n"
            "  pc papers <topic>     — Open research papers in browser\n"
            "  pc spotify <query>    — Play on Spotify\n"
            "  pc focus <window>     — Bring app window to front\n"
            "  pc keys <keys>        — Send keystrokes to active window\n"
            "  pc kill <process>     — Close an app by process name\n"
            "  pc windows            — List open windows\n"
            "  pc browse <url>       — Open any website\n"
            "\nVoice: just say what you want — 'play drake on spotify', "
            "'show research papers on AI', 'open discord'."
        )

    def _execute_plan(self, plan: dict) -> AgentResult:
        if "actions" in plan:
            return self._execute_actions(plan["actions"])

        action = plan.get("action", "say")

        if action == "launch":
            ok, msg = launch_app(str(plan.get("target", "")))
            self._log("launch", str(plan.get("target")), "success" if ok else "error")
            return AgentResult(self.name, msg if ok else f"Failed, {self.user_title}. {msg}")

        if action == "exec":
            cmd = str(plan.get("command", ""))
            if "powershell" in cmd.lower():
                code, out, err = run_powershell(cmd)
            else:
                code, out, err = run_shell(cmd)
            self._log("exec", cmd[:80], "success" if code == 0 else "error")
            detail = out or err or "Done."
            return AgentResult(self.name, f"Executed, {self.user_title}. {detail[:500]}")

        if action == "papers":
            topic = str(plan.get("topic", ""))
            urls = research_paper_urls(topic)
            for url in urls:
                open_url(url)
            return AgentResult(self.name, f"Opened research papers on '{topic}', {self.user_title}.")

        if action == "spotify":
            ok, msg = spotify_play(str(plan.get("query", "top hits")))
            return AgentResult(
                self.name,
                f"Playing on Spotify, {self.user_title}." if ok else f"Spotify failed: {msg}",
            )

        if action == "browse":
            url = str(plan.get("url", ""))
            if open_url(url):
                return AgentResult(self.name, f"Opened {url}, {self.user_title}.")
            return AgentResult(self.name, f"Could not open browser, {self.user_title}.")

        if action == "focus":
            ok, msg = focus_window(str(plan.get("target", "")))
            return AgentResult(self.name, msg)

        if action == "keys":
            ok, msg = send_keys(str(plan.get("text", "")))
            return AgentResult(self.name, "Sent keystrokes." if ok else msg)

        if action == "kill":
            ok, msg = kill_process(str(plan.get("target", "")))
            return AgentResult(self.name, msg if ok else f"Could not close app: {msg}")

        if action == "windows":
            return AgentResult(self.name, list_windows())

        if action == "click":
            from agents.app_control import screen_click

            ok, msg = screen_click(int(plan.get("x", 0)), int(plan.get("y", 0)))
            return AgentResult(self.name, msg)

        if action == "move":
            from agents.app_control import screen_move

            ok, msg = screen_move(int(plan.get("x", 0)), int(plan.get("y", 0)))
            return AgentResult(self.name, msg)

        if action == "type":
            from agents.app_control import screen_type_text

            ok, msg = screen_type_text(str(plan.get("text", "")))
            return AgentResult(self.name, msg)

        message = plan.get("message", "I cannot do that yet.")
        return AgentResult(self.name, str(message))

    def _execute_actions(self, actions: list[dict], *, pause: float = 0.9) -> AgentResult:
        messages: list[str] = []
        for index, step in enumerate(actions):
            if index > 0 and step.get("action") in {"type", "keys", "focus", "click"}:
                time.sleep(pause)
            result = self._execute_plan(step)
            if result.summary:
                messages.append(result.summary)
            if result.summary.startswith("Failed") or "Could not" in result.summary:
                break
        return AgentResult(self.name, " ".join(messages) if messages else f"Done, {self.user_title}.")

    def _write_down(self, argument: str) -> AgentResult:
        text = argument.strip()
        actions: list[dict] = [
            {"action": "launch", "target": "notepad"},
            {"action": "focus", "target": "Notepad"},
        ]
        if text:
            actions.append({"action": "type", "text": text})
        result = self._execute_actions(actions)
        if text:
            self._log("write_down", "notepad", "success", {"chars": len(text)})
            return AgentResult(
                self.name,
                f"Opened Notepad and wrote your text, {self.user_title}.",
            )
        return AgentResult(self.name, f"Notepad is open, {self.user_title}. Tell me what to write.")

    def _open_and_type(self, argument: str) -> AgentResult:
        if "|" not in argument:
            return AgentResult(self.name, f"Could not parse open-and-type request, {self.user_title}.")
        app, text = argument.split("|", 1)
        app = app.strip()
        text = text.strip()
        if not app:
            return AgentResult(self.name, f"Specify an app to open, {self.user_title}.")
        actions: list[dict] = [
            {"action": "launch", "target": app},
            {"action": "focus", "target": app},
        ]
        if text:
            actions.append({"action": "type", "text": text})
        self._execute_actions(actions)
        return AgentResult(
            self.name,
            f"Opened {app} and typed your text, {self.user_title}." if text else f"Opened {app}, {self.user_title}.",
        )

    def _do(self, request: str) -> AgentResult:
        if not request.strip():
            return AgentResult(self.name, f"Tell me what to do on your PC, {self.user_title}.")
        plan = plan_action(self.model, request)
        logging.info("PC plan for '%s': %s", request, plan)
        return self._execute_plan(plan)

    def _exec(self, command: str) -> AgentResult:
        if not command:
            return AgentResult(self.name, f"Provide a command to run, {self.user_title}.")
        return self._execute_plan({"action": "exec", "command": command})

    def _focus(self, target: str) -> AgentResult:
        ok, msg = focus_window(target)
        return AgentResult(self.name, msg)

    def _keys(self, keys: str) -> AgentResult:
        ok, msg = send_keys(keys)
        return AgentResult(self.name, "Keystrokes sent." if ok else msg)

    def _kill(self, target: str) -> AgentResult:
        ok, msg = kill_process(target)
        return AgentResult(self.name, msg)

    def _windows(self) -> AgentResult:
        return AgentResult(self.name, list_windows())

    def _papers(self, topic: str) -> AgentResult:
        return self._execute_plan({"action": "papers", "topic": topic})

    def _browse(self, target: str) -> AgentResult:
        url = target.strip()
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        return self._execute_plan({"action": "browse", "url": url})

    def _spotify(self, argument: str) -> AgentResult:
        return self._execute_plan({"action": "spotify", "query": argument or "top hits"})

    def _capabilities(self, _: str = "") -> AgentResult:
        if not self.host_caps:
            return AgentResult(self.name, f"No host scan available, {self.user_title}.")
        return AgentResult(self.name, self.host_caps.format_report())

    def _launch(self, target: str) -> AgentResult:
        if not target:
            return AgentResult(self.name, f"Specify an application to launch, {self.user_title}.")
        ok, msg = launch_app(target)
        self._log("launch", target, "success" if ok else "error")
        return AgentResult(self.name, msg if ok else f"Could not launch, {self.user_title}. {msg}")

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

    def _organize_all(self, _: str = "") -> AgentResult:
        home = Path.home()
        folders = [home / "Downloads", home / "Desktop", home / "Documents"]
        plan = PendingAction(action="organize", source_dir=home)
        for folder in folders:
            if folder.is_dir():
                sub = self._organize_plan(folder)
                plan.moves.extend(sub.moves)

        if not plan.moves:
            return AgentResult(self.name, f"No files to organize, {self.user_title}.")

        self.pending = plan
        self._log("organize_all", str(home), "planned", {"files": len(plan.moves)})
        return AgentResult(
            self.name,
            f"Organization plan for Downloads, Desktop, and Documents, {self.user_title}.\n\n{plan.description}",
        )

    def _cleanup_all(self, _: str = "") -> AgentResult:
        home = Path.home()
        folders = [home / "Downloads", home / "Desktop", home / "Documents"]
        plan = PendingAction(action="cleanup", source_dir=home)
        for folder in folders:
            if folder.is_dir():
                sub = self._organize_plan(folder)
                plan.moves.extend(sub.moves)
                plan.deletes.extend(self._find_duplicates(folder))

        if not plan.moves and not plan.deletes:
            return AgentResult(self.name, f"Nothing to clean, {self.user_title}.")

        self.pending = plan
        self._log("cleanup_all", str(home), "planned", {"moves": len(plan.moves), "deletes": len(plan.deletes)})
        return AgentResult(self.name, f"Cleanup plan for your main folders, {self.user_title}.\n\n{plan.description}")

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
