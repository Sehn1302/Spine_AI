"""Spine — text interface entry point."""

from __future__ import annotations

import sys

from orchestrator import SpineOrchestrator
from router import list_agents


BANNER = """
================================================================
   S P I N E
   Executive AI Orchestrator — Local Interface
================================================================
  Commands:
    exit, quit, bye      — End session
    new                  — Start a fresh conversation
    index                — Index files in memory/knowledge/
    remember <text>      — Save a note to the knowledge base
    agents               — List specialist agents
    research <query>     — Web search and summary
    study <query>        — Thesis and academic guidance
    files <path>         — Scan a folder (read-only)
================================================================
"""


def main() -> None:
    print(BANNER)

    try:
        spine = SpineOrchestrator()
    except Exception as exc:
        print(f"Failed to initialize Spine: {exc}")
        sys.exit(1)

    title = spine.user_title
    print(f"Spine is online. At your service, {title}.\n")

    while True:
        try:
            user_input = input(f"{title}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\nShutting down. Good evening, {title}.")
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered in {"exit", "quit", "bye", "goodbye"}:
            print(f"\nSpine: Very good, {title}. I shall remain available when you return.")
            break

        if lowered == "new":
            spine.new_session()
            print(f"\nSpine: A fresh session has been initiated, {title}.\n")
            continue

        if lowered == "index":
            print("\nSpine: ", end="", flush=True)
            print(spine.index_knowledge())
            print()
            continue

        if lowered.startswith("remember "):
            note = user_input[len("remember ") :].strip()
            print("\nSpine: ", end="", flush=True)
            print(spine.remember(note))
            print()
            continue

        if lowered == "agents":
            print(f"\nSpine:\n{list_agents()}\n")
            continue

        print("\nSpine: ", end="", flush=True)
        reply = spine.handle(user_input)
        print(reply)
        print()


if __name__ == "__main__":
    main()
