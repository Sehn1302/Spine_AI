"""Stress test Spine multi-LLM brain — routing, agents, concurrency, router."""

from __future__ import annotations

import concurrent.futures
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spine"))


def log(msg: str) -> None:
    print(msg, flush=True)

import ollama
from router import parse_natural_command
from orchestrator import SpineOrchestrator


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str
    elapsed: float = 0.0


@dataclass
class StressReport:
    results: list[TestResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str, elapsed: float = 0.0) -> None:
        self.results.append(TestResult(name, passed, detail, elapsed))

    def summary(self) -> str:
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        lines = [
            "",
            "=" * 60,
            f"STRESS TEST: {passed}/{total} passed",
            "=" * 60,
        ]
        for r in self.results:
            mark = "PASS" if r.passed else "FAIL"
            timing = f" ({r.elapsed:.2f}s)" if r.elapsed else ""
            lines.append(f"  [{mark}] {r.name}{timing}")
            if not r.passed or "->" in r.detail:
                lines.append(f"         {r.detail}")
        lines.append("=" * 60)
        return "\n".join(lines)


def timed(fn, *args, **kwargs):
    start = time.perf_counter()
    try:
        out = fn(*args, **kwargs)
        return out, time.perf_counter() - start, None
    except Exception as exc:
        return None, time.perf_counter() - start, exc


def test_ollama_online(report: StressReport) -> bool:
    out, elapsed, err = timed(ollama.list)
    if err:
        report.add("Ollama online", False, str(err), elapsed)
        return False
    models = [m.model for m in out.get("models", [])]
    report.add("Ollama online", True, f"{len(models)} model(s): {', '.join(models[:5])}", elapsed)
    return True


def test_routing_map(report: StressReport, spine: SpineOrchestrator) -> None:
    m = spine.models
    expected = {
        "chat": m.primary,
        "pc": m.fast,
        "research": m.primary,
        "planner": m.fast,
        "files": m.fast,
    }
    ok = True
    details: list[str] = []
    for role, want in expected.items():
        got = m.model_for_role(role)
        match = got == want or got.split(":")[0] == want.split(":")[0]
        details.append(f"{role} -> {got} (want {want})")
        ok = ok and match
    report.add("Model routing map", ok, "; ".join(details))


def test_agent_models(report: StressReport, spine: SpineOrchestrator) -> None:
    checks = {
        "research": spine.models.model_for_role("research"),
        "study": spine.models.model_for_role("study"),
        "files": spine.models.model_for_role("files"),
        "pc": spine.models.model_for_role("planner"),
    }
    ok = True
    parts: list[str] = []
    for name, expected in checks.items():
        actual = spine.agents[name].model
        match = actual == expected
        parts.append(f"{name}.model={actual}")
        ok = ok and match
    report.add("Agent model assignment", ok, ", ".join(parts))


def test_router_natural_language(report: StressReport) -> None:
    cases = {
        "write down buy milk": ("pc", "write_down"),
        "remember dentist friday": ("remember", "dentist"),
        "organise all my files": ("pc", "organize_all"),
        "play jazz on spotify": ("pc", "spotify"),
        "switch to fast model": ("models", "use fast"),
        "show me research papers on AI": ("pc", "papers"),
        "open notepad and type hello": ("pc", "open_and_type"),
    }
    failed: list[str] = []
    for phrase, (want_agent, want_prefix) in cases.items():
        route = parse_natural_command(phrase)
        if not route:
            failed.append(f"{phrase!r} -> None")
            continue
        agent, task = route
        if agent != want_agent or not task.startswith(want_prefix):
            failed.append(f"{phrase!r} -> {route} (want {want_agent}, {want_prefix})")
    report.add(
        "Natural language router",
        not failed,
        "all ok" if not failed else "; ".join(failed),
    )


def test_dual_model_concurrent(report: StressReport, spine: SpineOrchestrator) -> None:
    primary = spine.models.model_for_role("chat")
    fast = spine.models.model_for_role("pc")
    if primary == fast:
        report.add("Concurrent dual-model", True, f"skipped — same model ({primary})", 0)
        return

    def ask(model: str, label: str) -> tuple[str, str, float]:
        start = time.perf_counter()
        r = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": f"Reply with exactly: {label}-ok"}],
        )
        return label, r["message"]["content"].strip()[:30], time.perf_counter() - start

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(ask, primary, "primary"),
            pool.submit(ask, fast, "fast"),
        ]
        outcomes = [f.result() for f in concurrent.futures.as_completed(futures)]
    total = time.perf_counter() - start
    detail = " | ".join(f"{label}={reply} ({t:.2f}s)" for label, reply, t in outcomes)
    report.add("Concurrent dual-model", True, detail, total)


def test_rapid_agent_cycle(report: StressReport, spine: SpineOrchestrator) -> None:
    """Hit different agents back-to-back — simulates mixed workload."""
    tasks = [
        ("models", "routing"),
        ("pc", "capabilities"),
        ("remember", "stress test note alpha"),
    ]
    errors: list[str] = []
    start = time.perf_counter()
    for agent, task in tasks:
        try:
            if agent == "remember":
                spine.remember(task)
            elif agent == "models":
                spine.handle_models(task)
            else:
                spine.delegate(agent, task)
        except Exception as exc:
            errors.append(f"{agent}:{exc}")
    elapsed = time.perf_counter() - start
    report.add(
        "Rapid agent cycle (4 tasks)",
        not errors,
        "ok" if not errors else "; ".join(errors),
        elapsed,
    )


def test_chat_then_fast_planner(report: StressReport, spine: SpineOrchestrator) -> None:
    """Primary chat then fast planner in sequence — typical voice session."""
    start = time.perf_counter()
    errors: list[str] = []
    try:
        spine.chat("Reply in 3 words: spine brain online")
    except Exception as exc:
        errors.append(f"chat:{exc}")
    try:
        from agents.action_planner import plan_action

        plan = plan_action(spine.agents["pc"].model, "open calculator")
        if plan.get("action") not in {"launch", "say"} and "actions" not in plan:
            errors.append(f"planner odd plan: {plan}")
    except Exception as exc:
        errors.append(f"planner:{exc}")
    elapsed = time.perf_counter() - start
    report.add("Chat + fast planner sequence", not errors, "ok" if not errors else "; ".join(errors), elapsed)


def test_model_switch_resync(report: StressReport, spine: SpineOrchestrator) -> None:
    installed = spine.models.list_installed()
    fast_ref = spine.models.fast
    if not any(m.startswith(fast_ref.split(":")[0]) for m in installed):
        report.add("Model switch resync", False, f"{fast_ref} not installed — run: ollama pull {fast_ref}")
        return

    original = spine.model
    start = time.perf_counter()
    try:
        spine.handle_models("use fast")
        after_fast = spine.agents["pc"].model
        spine.handle_models(f"use {original}")
        after_restore = spine.agents["research"].model
        ok = after_fast == spine.models.fast
        detail = f"pc->{after_fast}, restored research->{after_restore}"
        report.add("Model switch resync", ok, detail, time.perf_counter() - start)
    except Exception as exc:
        report.add("Model switch resync", False, str(exc), time.perf_counter() - start)


def test_bench_models(report: StressReport, spine: SpineOrchestrator) -> None:
    """Bench only primary + fast — full bench is slow."""
    targets = []
    for name in (spine.models.primary, spine.models.fast):
        if name not in targets:
            targets.append(name)
    lines: list[str] = []
    failed = False
    start = time.perf_counter()
    for name in targets:
        try:
            t0 = time.perf_counter()
            response = ollama.chat(
                model=name,
                messages=[{"role": "user", "content": "Reply with one word: online"}],
            )
            elapsed = time.perf_counter() - t0
            reply = response["message"]["content"].strip()[:30]
            lines.append(f"{name}={elapsed:.2f}s ({reply})")
        except Exception as exc:
            failed = True
            lines.append(f"{name}=FAIL ({exc})")
    report.add("Model bench (primary+fast)", not failed, " | ".join(lines), time.perf_counter() - start)


def test_organize_plan_no_apply(report: StressReport, spine: SpineOrchestrator) -> None:
    """PC organize creates plan without destructive apply."""
    start = time.perf_counter()
    try:
        reply = spine.delegate("pc", f"organize {Path.home() / 'Downloads'}")
        ok = "confirm" in reply.lower() or "no files" in reply.lower() or "organization plan" in reply.lower()
        spine.cancel_pending()
        report.add("PC organize (plan only)", ok, reply[:120].replace("\n", " "), time.perf_counter() - start)
    except Exception as exc:
        report.add("PC organize (plan only)", False, str(exc), time.perf_counter() - start)


def main() -> int:
    log("Spine multi-LLM stress test")
    log(f"Root: {ROOT}\n")

    report = StressReport()
    log("Checking Ollama...")
    if not test_ollama_online(report):
        log(report.summary())
        return 1

    log("Loading orchestrator (quiet)...")
    spine, elapsed, err = timed(lambda: SpineOrchestrator(quiet=True))
    if err:
        report.add("Orchestrator init", False, traceback.format_exc(), elapsed)
        log(report.summary())
        return 1
    report.add("Orchestrator init", True, f"session={spine.session_id}", elapsed)

    log("Running routing tests...")
    test_routing_map(report, spine)
    test_agent_models(report, spine)
    test_router_natural_language(report)

    log("Running concurrent dual-model test...")
    test_dual_model_concurrent(report, spine)

    log("Running rapid agent cycle...")
    test_rapid_agent_cycle(report, spine)

    log("Running chat + planner sequence...")
    test_chat_then_fast_planner(report, spine)

    log("Running model switch test...")
    test_model_switch_resync(report, spine)

    log("Running model bench...")
    test_bench_models(report, spine)

    log("Running organize plan test...")
    test_organize_plan_no_apply(report, spine)

    log(report.summary())
    failed = sum(1 for r in report.results if not r.passed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
