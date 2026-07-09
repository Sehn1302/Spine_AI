"""Files agent — read-only folder analysis and organization suggestions."""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from agents.base import AgentResult, BaseAgent

MAX_FILES = 200


class FilesAgent(BaseAgent):
    name = "files"
    description = "Scan folders and suggest organization (read-only)"

    def run(self, task: str) -> AgentResult:
        target = task.strip() or str(Path.home() / "Downloads")
        path = Path(target).expanduser()

        if not path.exists():
            return AgentResult(
                self.name,
                f"The path '{target}' does not exist, {self.user_title}.",
            )

        if not path.is_dir():
            return AgentResult(
                self.name,
                f"'{target}' is not a directory, {self.user_title}.",
            )

        logging.info("Files agent scanning: %s", path)

        files: list[Path] = []
        for item in path.iterdir():
            if item.is_file():
                files.append(item)
            if len(files) >= MAX_FILES:
                break

        if not files:
            return AgentResult(
                self.name,
                f"The folder '{path}' contains no files, {self.user_title}.",
            )

        extensions = Counter(f.suffix.lower() or "(no extension)" for f in files)
        total_size = sum(f.stat().st_size for f in files)
        listing = "\n".join(f"- {f.name} ({f.stat().st_size:,} bytes)" for f in files[:30])

        scan_report = (
            f"Folder: {path}\n"
            f"Files scanned: {len(files)}\n"
            f"Total size: {total_size:,} bytes\n"
            f"Extensions: {dict(extensions)}\n\n"
            f"Sample files:\n{listing}"
        )

        system = (
            f"You are the Files module of Spine. Analyze the folder scan for {self.user_title}. "
            "Suggest a clear organization plan. Read-only — do not claim to move or delete files. "
            "Ask for confirmation before any future file operations."
        )
        summary = self._ask(
            system,
            f"Task: {task or 'Analyze this folder'}\n\n{scan_report}",
        )

        return AgentResult(agent=self.name, summary=summary, details=scan_report)
