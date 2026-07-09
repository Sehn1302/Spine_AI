"""Route user requests to specialist agents."""

from __future__ import annotations

import re
from pathlib import Path

AGENT_COMMANDS = {
    "research": "research",
    "study": "study",
    "files": "files",
    "pc": "pc",
}


def _extract_folder(text: str) -> str | None:
    match = re.search(r"[A-Za-z]:\\[^\s\"']+", text)
    if match:
        return match.group(0).rstrip(".,;")

    lowered = text.lower()
    home = Path.home()
    if "downloads" in lowered:
        return str(home / "Downloads")
    if "desktop" in lowered:
        return str(home / "Desktop")
    if "documents" in lowered:
        return str(home / "Documents")
    return None


def parse_natural_command(user_input: str) -> tuple[str, str] | None:
    """Map spoken/plain requests to agent commands."""
    lowered = user_input.lower().strip()

    if lowered.startswith("launch "):
        return "pc", f"launch {user_input[7:].strip()}"

    if lowered.startswith("open "):
        return "pc", f"open {user_input[5:].strip()}"

    if "what software" in lowered or "installed software" in lowered or "what can you use" in lowered:
        return "pc", "capabilities"

    if any(phrase in lowered for phrase in ("armoury crate", "armory crate", "nvidia broadcast", "g-helper", "lenovo vantage", "realtek audio")):
        for token in ("armoury crate", "armory crate", "nvidia broadcast", "g-helper", "lenovo vantage", "realtek audio"):
            if token in lowered:
                return "pc", f"launch {token}"

    if "write" in lowered and ("word" in lowered or "document" in lowered or "file" in lowered):
        return None

    if "remove duplicate" in lowered or "delete duplicate" in lowered:
        folder = _extract_folder(user_input) or str(Path.home() / "Downloads")
        return "pc", f"duplicates {folder}"

    if "organize" in lowered and ("file" in lowered or "folder" in lowered):
        folder = _extract_folder(user_input) or str(Path.home() / "Downloads")
        return "pc", f"organize {folder}"

    if "cleanup" in lowered or "clean up" in lowered or "clear up space" in lowered:
        folder = _extract_folder(user_input) or str(Path.home() / "Downloads")
        return "pc", f"cleanup {folder}"

    return None


def parse_agent_command(user_input: str) -> tuple[str, str] | None:
    """Return (agent_name, task) if input is an explicit agent command."""
    lowered = user_input.lower()

    for command, agent_name in AGENT_COMMANDS.items():
        prefix = f"{command} "
        if lowered.startswith(prefix):
            task = user_input[len(prefix) :].strip()
            if task:
                return agent_name, task

    return parse_natural_command(user_input)


def list_agents() -> str:
    return (
        "Available agents:\n"
        "  research <query>   — Web search and summary\n"
        "  study <query>      — Thesis and academic guidance\n"
        "  files <path>       — Folder scan (read-only advice)\n"
        "  pc <command>       — Apps, documents, folder control\n"
        "\n"
        "PC commands:\n"
        "  pc launch <app>          — Launch Minecraft, Chrome, Word, etc.\n"
        "  pc write <path> <text>   — Create .txt or .docx file\n"
        "  pc organize <folder>     — Sort files by type\n"
        "  pc duplicates <folder>   — Remove duplicate files\n"
        "  pc cleanup <folder>      — Organize + remove duplicates\n"
        "  pc capabilities          — Detected host software on this PC\n"
        "\n"
        "Natural voice/text also works:\n"
        "  launch minecraft\n"
        "  organize files in Downloads\n"
        "  remove duplicates in Downloads\n"
        "  clear up space in Downloads\n"
        "Then type confirm or cancel."
    )
