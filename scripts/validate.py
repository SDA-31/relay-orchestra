#!/usr/bin/env python3
"""Validate Relay Orchestra without third-party packages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "relay-orchestra"
SKILL = SKILL_DIR / "SKILL.md"


def fail(message: str) -> None:
    raise ValueError(message)


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("SKILL.md must start with frontmatter")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            fail(f"unsupported frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def validate() -> None:
    text = SKILL.read_text(encoding="utf-8")
    metadata = frontmatter(text)
    if set(metadata) != {"name", "description"}:
        fail("frontmatter must contain only name and description")
    if metadata["name"] != SKILL_DIR.name:
        fail("skill name must match its directory")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", metadata["name"]):
        fail("skill name must use lowercase kebab-case")
    for phrase in ("EXPLICIT-ONLY", "run-scoped"):
        if phrase not in metadata["description"]:
            fail(f"description is missing {phrase!r}")
    if len(text.splitlines()) > 500:
        fail("SKILL.md must stay under 500 lines")

    required = (
        "Working without worktree isolation",
        "The skill imposes no fixed maximum",
        "fifteen agents",
        "Do not silently reduce",
        "return control to the user promptly",
        "Never reject a relevant update",
        "Live Run Ledger",
        "Milestone updates do not deactivate it",
        "Do not switch to worktree mode silently",
        "STATUS: DONE | BLOCKED | NEEDS_CONTEXT",
        "COMMANDS_AND_SIDE_EFFECTS",
        "deactivate Relay Orchestra",
        "ACTIVE -> STOPPING -> OFF",
        "persistence of loaded skill instructions across turns",
        "compact non-secret session token",
        "$relay-orchestra resume <token>",
        "Treat a user-specified total as `EXACT`",
        "Ask the user for a count delta",
        "A result arriving after `OFF`",
    )
    for phrase in required:
        if phrase not in text:
            fail(f"SKILL.md is missing {phrase!r}")

    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" not in target and not (SKILL_DIR / target).exists():
            fail(f"broken local link: {target}")

    openai = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for phrase in ("$relay-orchestra", "allow_implicit_invocation: false"):
        if phrase not in openai:
            fail(f"openai.yaml is missing {phrase!r}")

    stale = ("orchestrate-subagents", "scatter-gather", "Scatter Gather", "$orchestrate")
    suffixes = {".md", ".json", ".yaml", ".yml"}
    paths = [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts and path.suffix in suffixes]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for name in stale:
            if name in content:
                fail(f"stale name {name!r} in {path.relative_to(ROOT)}")
        if path.suffix == ".md":
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", content):
                if target.startswith("#") or "://" in target or target.startswith("mailto:"):
                    continue
                local_target = target.split("#", 1)[0]
                if local_target and not (path.parent / local_target).exists():
                    fail(f"broken local link {target!r} in {path.relative_to(ROOT)}")

    cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
    ids: set[str] = set()
    for case in cases:
        if set(case) != {"id", "prompt", "expected"} or not case["prompt"] or not case["expected"]:
            fail(f"invalid eval case: {case!r}")
        if case["id"] in ids:
            fail(f"duplicate eval id: {case['id']}")
        ids.add(case["id"])
    for required_id in (
        "one_agent",
        "fifteen_agents",
        "concurrency_limit",
        "return_after_dispatch",
        "compatible_followup",
        "urgent_redirect",
        "new_workstream",
        "held_idea",
        "research_to_implementation",
        "milestone_not_final",
        "exact_total_ceiling",
        "open_scheduler_addition",
        "persistence_capability_gate",
    ):
        if required_id not in ids:
            fail(f"missing eval case: {required_id}")

    transcript_path = ROOT / "evals" / "transcripts.json"
    transcripts = json.loads(transcript_path.read_text(encoding="utf-8"))
    if not isinstance(transcripts, list) or not transcripts:
        fail("transcripts.json must contain a non-empty list")
    transcript_ids: set[str] = set()
    capability_keys = {
        "skill_instructions_persist",
        "ledger_persists",
        "agent_handles_persist",
    }
    states = {"ACTIVE", "STOPPING", "OFF"}
    event_kinds: set[str] = set()
    expectation_tokens: set[str] = set()
    for transcript in transcripts:
        if set(transcript) != {"id", "capabilities", "initial_state", "steps", "final_state"}:
            fail(f"invalid transcript scenario keys: {transcript!r}")
        if transcript["id"] in transcript_ids:
            fail(f"duplicate transcript id: {transcript['id']}")
        transcript_ids.add(transcript["id"])
        capabilities = transcript["capabilities"]
        if set(capabilities) != capability_keys or not all(isinstance(value, bool) for value in capabilities.values()):
            fail(f"invalid transcript capabilities: {transcript['id']}")
        if transcript["initial_state"] not in states or transcript["final_state"] not in states:
            fail(f"invalid transcript state: {transcript['id']}")
        if not isinstance(transcript["steps"], list) or not transcript["steps"]:
            fail(f"transcript must have steps: {transcript['id']}")
        previous_turn = 0
        for step in transcript["steps"]:
            required_step = {"turn", "event", "detail", "expect"}
            allowed_step = required_step | {"inputs"}
            if not required_step.issubset(step) or not set(step).issubset(allowed_step):
                fail(f"invalid transcript step: {step!r}")
            if not isinstance(step["turn"], int) or step["turn"] < previous_turn:
                fail(f"transcript turns must be ordered: {transcript['id']}")
            previous_turn = step["turn"]
            if not step["detail"] or not isinstance(step["expect"], list) or not step["expect"]:
                fail(f"transcript step lacks detail or expectations: {step!r}")
            event_kinds.add(step["event"])
            expectation_tokens.update(step["expect"])
            if step["event"] == "delivery_batch":
                inputs = step.get("inputs")
                if not isinstance(inputs, list) or {item.get("kind") for item in inputs} != {"user", "worker_result"}:
                    fail("delivery_batch must contain user and worker_result inputs")

    required_transcripts = {
        "native_dispatch_yield_second_turn",
        "stop_during_shared_write_and_late_result",
        "persistence_fallback_rehydration",
    }
    if not required_transcripts.issubset(transcript_ids):
        fail("missing required multi-turn transcript scenario")
    for event in ("yield", "delivery_batch", "worker_result"):
        if event not in event_kinds:
            fail(f"transcripts are missing {event!r} event")
    for token in (
        "queued_input",
        "HELD_to_QUEUED",
        "ACTIVE_to_STOPPING",
        "STOPPING_to_OFF",
        "report_late_write",
        "session_token",
        "rehydrate",
        "explicit_skill_resume",
    ):
        if token not in expectation_tokens:
            fail(f"transcripts are missing {token!r} expectation")

    for relative in (
        "scripts/install.py",
        "install.sh",
        "install.ps1",
        "tests/test_install.py",
    ):
        if not (ROOT / relative).is_file():
            fail(f"missing repository file: {relative}")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Relay Orchestra validation passed.")
