"""Route user requests to specialist agents."""

from __future__ import annotations

AGENT_COMMANDS = {
    "research": "research",
    "study": "study",
    "files": "files",
}


def parse_agent_command(user_input: str) -> tuple[str, str] | None:
    """Return (agent_name, task) if input is an explicit agent command."""
    lowered = user_input.lower()

    for command, agent_name in AGENT_COMMANDS.items():
        prefix = f"{command} "
        if lowered.startswith(prefix):
            task = user_input[len(prefix) :].strip()
            if task:
                return agent_name, task

    return None


def list_agents() -> str:
    return (
        "Available agents:\n"
        "  research <query>  — Web search and summary\n"
        "  study <query>     — Thesis and academic guidance\n"
        "  files <path>      — Folder scan and organization advice (read-only)"
    )
