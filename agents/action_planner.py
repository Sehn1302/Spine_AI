"""LLM-driven PC action planner — maps natural language to app control."""

from __future__ import annotations

import json
import logging
import re

import ollama

ACTION_SCHEMA = """
You control a Windows PC. Reply with ONLY valid JSON (no markdown).

Single action:
- {"action":"launch","target":"<app name or path>"}
- {"action":"exec","command":"<powershell or cmd command>"}
- {"action":"papers","topic":"<research topic>"}
- {"action":"spotify","query":"<song or artist>"}
- {"action":"browse","url":"<https://...>"}
- {"action":"focus","target":"<window title fragment>"}
- {"action":"keys","text":"<SendKeys syntax e.g. ^c for Ctrl+C>"}
- {"action":"kill","target":"<process name>"}
- {"action":"click","x":123,"y":456}
- {"action":"move","x":100,"y":200}
- {"action":"type","text":"hello"}
- {"action":"say","message":"<short reply if you cannot act>"}

Multi-step (use when user wants open + type, or launch then focus):
- {"actions":[
    {"action":"launch","target":"notepad"},
    {"action":"focus","target":"Notepad"},
    {"action":"type","text":"hello world"}
  ]}

Examples:
"play drake on spotify" -> {"action":"spotify","query":"drake"}
"open notepad and type hello" -> {"actions":[{"action":"launch","target":"notepad"},{"action":"focus","target":"Notepad"},{"action":"type","text":"hello"}]}
"show papers on transformers" -> {"action":"papers","topic":"transformers"}
"close chrome" -> {"action":"kill","target":"chrome"}
"""


def _parse_plan(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"action": "say", "message": raw[:300]}

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"action": "say", "message": "I could not parse the action plan."}


def plan_action(model: str, user_request: str) -> dict:
    prompt = (
        f"{ACTION_SCHEMA}\n\n"
        f"User request: {user_request}\n\n"
        "JSON:"
    )
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": "You output only JSON for PC control. No explanation."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response["message"]["content"].strip()
    except Exception as exc:
        logging.error("Action planner failed: %s", exc)
        return {"action": "say", "message": "I could not reach the language model to plan that action."}

    return _parse_plan(raw)
