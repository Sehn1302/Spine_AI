"""Route user requests to specialist agents."""

from __future__ import annotations

import re
from pathlib import Path

AGENT_COMMANDS = {
    "research": "research",
    "study": "study",
    "files": "files",
    "pc": "pc",
    "models": "models",
    "schedule": "schedule",
    "remember": "remember",
}

_PAPER_PATTERNS = (
    re.compile(r"(?:show me |find |search for |get )?(?:some )?research papers?(?: on| about| for)? (.+)", re.I),
    re.compile(r"(?:show me |find )?(?:some )?papers?(?: on| about| for) (.+)", re.I),
    re.compile(r"academic (?:articles?|papers?)(?: on| about| for)? (.+)", re.I),
)

_SPOTIFY_PATTERNS = (
    re.compile(r"play (.+?) on spotify", re.I),
    re.compile(r"spotify play (.+)", re.I),
    re.compile(r"play (?:some )?music on spotify(?:[:\s]+(.+))?", re.I),
    re.compile(r"play music(?:[:\s]+(.+))?", re.I),
    re.compile(r"put on (?:some )?music(?:[:\s]+(.+))?", re.I),
)

_WRITE_DOWN_PATTERNS = (
    re.compile(r"^(?:spine[, ]+)?(?:write|note|jot) down(?: (?:that|this|my text))?[:\s]+(.+)", re.I),
    re.compile(r"^(?:spine[, ]+)?(?:write|note|jot) (?:this|that|my text)(?: down)?[:\s]+(.+)", re.I),
)

_REMEMBER_PATTERNS = (
    re.compile(r"^(?:spine[, ]+)?remember(?: (?:that|this))?[:\s]+(.+)", re.I),
    re.compile(r"^(?:spine[, ]+)?(?:save|store) (?:this|that)(?: for later)?[:\s]+(.+)", re.I),
    re.compile(r"^(?:spine[, ]+)?don'?t forget[:\s]+(.+)", re.I),
)

_OPEN_TYPE_PATTERN = re.compile(
    r"^(?:spine[, ]+)?open (.+?) and (?:type|write|say)(?: down)?[:\s]+(.+)",
    re.I,
)

_ORGANIZE_PATTERN = re.compile(
    r"(?:organis|organiz|sort|tidy|clean up)(?:e|ing|ed)?\s+(?:all\s+)?(?:my\s+)?(?:files?|folders?|downloads?|desktop|documents?)",
    re.I,
)


def _strip_spine_prefix(text: str) -> str:
    lowered = text.lower().strip()
    if lowered.startswith("spine "):
        return text[6:].strip()
    if lowered.startswith("spine,"):
        return text[6:].strip()
    return text.strip()


def _extract_paper_topic(text: str) -> str | None:
    cleaned = text.strip().rstrip(".")
    for pattern in _PAPER_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            topic = match.group(1).strip()
            if topic and len(topic) >= 2:
                return topic
    return None


def _extract_spotify_query(text: str) -> str | None:
    cleaned = text.strip().rstrip(".")
    for pattern in _SPOTIFY_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            groups = [g.strip() for g in match.groups() if g and g.strip()]
            if groups:
                return groups[-1]
            return "top hits"
    if "spotify" in cleaned.lower() and "play" in cleaned.lower():
        return "top hits"
    return None


def _extract_write_down(text: str) -> str | None:
    cleaned = _strip_spine_prefix(text).rstrip(".")
    for pattern in _WRITE_DOWN_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return match.group(1).strip()
    if re.match(r"^(?:write|note|jot) down\.?$", cleaned, re.I):
        return ""
    return None


def _extract_remember(text: str) -> str | None:
    cleaned = _strip_spine_prefix(text).rstrip(".")
    for pattern in _REMEMBER_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return match.group(1).strip()
    if re.match(r"^remember\.?$", cleaned, re.I):
        return ""
    return None


def _extract_open_and_type(text: str) -> tuple[str, str] | None:
    cleaned = _strip_spine_prefix(text).rstrip(".")
    match = _OPEN_TYPE_PATTERN.search(cleaned)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None


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


def _wants_organize(text: str) -> bool:
    lowered = text.lower()
    if _ORGANIZE_PATTERN.search(lowered):
        return True
    return any(
        word in lowered
        for word in ("organize", "organise", "sort my files", "tidy my files", "tidy up my files")
    ) and ("file" in lowered or "folder" in lowered)


def parse_natural_command(user_input: str) -> tuple[str, str] | None:
    """Map spoken/plain requests to agent commands."""
    lowered = user_input.lower().strip()
    cleaned = _strip_spine_prefix(user_input)

    if any(p in lowered for p in ("switch to fast", "use fast model", "fast model", "quick model")):
        return "models", "use fast"
    if any(p in lowered for p in ("switch to smart", "use smart model", "main model", "brain model", "use primary")):
        return "models", "use primary"
    if lowered in {"model routing", "brain routing", "show brain", "show models"}:
        return "models", "routing"
    if lowered in {"benchmark models", "bench models", "test models"}:
        return "models", "bench"
    if lowered.startswith("schedule "):
        return "schedule", user_input[9:].strip()

    remember_text = _extract_remember(user_input)
    if remember_text is not None:
        return "remember", remember_text

    write_text = _extract_write_down(user_input)
    if write_text is not None:
        return "pc", f"write_down {write_text}"

    open_type = _extract_open_and_type(user_input)
    if open_type:
        app, text = open_type
        return "pc", f"open_and_type {app}|{text}"

    paper_topic = _extract_paper_topic(user_input)
    if paper_topic:
        return "pc", f"papers {paper_topic}"

    spotify_query = _extract_spotify_query(user_input)
    if spotify_query is not None:
        return "pc", f"spotify {spotify_query}"

    if lowered.startswith("launch "):
        return "pc", f"launch {user_input[7:].strip()}"

    if lowered.startswith("open "):
        return "pc", f"open {user_input[5:].strip()}"

    if lowered.startswith("spine "):
        rest = user_input[6:].strip()
        if rest:
            return parse_natural_command(rest) or parse_agent_command(rest)

    if "what software" in lowered or "installed software" in lowered or "what can you use" in lowered:
        return "pc", "capabilities"

    if any(phrase in lowered for phrase in ("armoury crate", "armory crate", "nvidia broadcast", "g-helper", "lenovo vantage", "realtek audio")):
        for token in ("armoury crate", "armory crate", "nvidia broadcast", "g-helper", "lenovo vantage", "realtek audio"):
            if token in lowered:
                return "pc", f"launch {token}"

    if "remove duplicate" in lowered or "delete duplicate" in lowered:
        folder = _extract_folder(user_input) or str(Path.home() / "Downloads")
        return "pc", f"duplicates {folder}"

    if _wants_organize(cleaned):
        folder = _extract_folder(user_input)
        if not folder and ("all my" in lowered or "my files" in lowered or "everything" in lowered):
            return "pc", "organize_all"
        return "pc", f"organize {folder or Path.home() / 'Downloads'}"

    if "cleanup" in lowered or "clean up" in lowered or "clear up space" in lowered:
        folder = _extract_folder(user_input) or str(Path.home() / "Downloads")
        if not folder and ("all my" in lowered or "my files" in lowered):
            return "pc", "cleanup_all"
        return "pc", f"cleanup {folder}"

    return None


_PC_CONTROL_HINTS = (
    "open ",
    "launch ",
    "start ",
    "close ",
    "shut ",
    "kill ",
    "play ",
    "run ",
    "spotify",
    "music",
    "browser",
    "chrome",
    "discord",
    "notepad",
    "calculator",
    "window",
    "app ",
    "papers",
    "research paper",
    "show me",
    "type ",
    "click",
    "focus ",
    "write down",
    "note down",
    "jot down",
    "remember",
    "don't forget",
    "organize",
    "organise",
    "sort my",
    "tidy",
    "search for",
    "look up",
)


def wants_pc_control(text: str) -> bool:
    lowered = text.lower().strip()
    if parse_natural_command(text):
        return True
    return any(hint in lowered for hint in _PC_CONTROL_HINTS)


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
        "  remember <text>    — Save a note to your knowledge base\n"
        "\n"
        "PC commands:\n"
        "  pc do <request>           — AI controls any app on your PC\n"
        "  pc exec <command>         — Run shell/PowerShell directly\n"
        "  pc launch <app>          — Launch any installed app\n"
        "  pc papers <topic>        — Open research papers in browser\n"
        "  pc spotify <song>        — Play music on Spotify\n"
        "  pc browse <url>          — Open a website\n"
        "  pc write <path> <text>   — Create .txt or .docx file\n"
        "  pc organize <folder>     — Sort files by type\n"
        "  pc duplicates <folder>   — Remove duplicate files\n"
        "  pc cleanup <folder>      — Organize + remove duplicates\n"
        "  pc capabilities          — Detected host software on this PC\n"
        "\n"
        "Model supervision (local LLMs via Ollama):\n"
        "  models list              — Installed models\n"
        "  models pull <name>       — Download a model\n"
        "  models use <name>        — Switch active assistant model\n"
        "  models recommend         — Hardware-based model suggestions\n"
        "\n"
        "Natural voice/text also works:\n"
        "  write down buy milk tomorrow\n"
        "  remember dentist appointment Friday\n"
        "  open notepad and type hello world\n"
        "  show me research papers on machine learning\n"
        "  play jazz on Spotify\n"
        "  organise all my files\n"
        "  organize files in Downloads\n"
        "Then type confirm or cancel for file plans."
    )
