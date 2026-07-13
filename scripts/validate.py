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


def validate_one_shot(transcript: dict[str, object], expectation_tokens: set[str]) -> None:
    transcript_id = transcript["id"]
    steps = transcript["steps"]
    if transcript["initial_state"] != "OFF" or transcript["final_state"] != "OFF":
        fail(f"one-shot transcript must start and finish OFF: {transcript_id}")
    if len({step["turn"] for step in steps}) != 1:
        fail(f"one-shot transcript must stay in one turn: {transcript_id}")

    forbidden = {
        "OFF_to_ACTIVE",
        "ACTIVE_to_STOPPING",
        "STOPPING_to_OFF",
        "ACTIVE",
        "live_scope",
        "default_live_scope",
        "session_active",
        "responsive_session",
        "yield_main_turn",
        "native_completion_polling",
        "short_bounded_poll_interval",
        "repeat_bounded_poll",
        "remain_ACTIVE",
        "completion_candidate",
        "later_close_confirmation_required",
        "pending_close_confirmation",
        "ask_close",
        "close_question_ends_turn",
        "direct_close_confirmation",
        "close_confirmation_revision_match",
        "confirmation_authorizes_STOPPING",
        "no_same_turn_shutdown",
        "explicit_skill_resume",
        "portable_resume_payload",
        "rehydrate",
        "session_token",
    }
    tokens = {token for step in steps for token in step["expect"]}
    expectation_tokens.update(tokens)
    if forbidden.intersection(tokens):
        fail(f"one-shot transcript uses live-session machinery: {transcript_id}")
    if not {"one_shot_scope", "no_cross_turn_persistence", "no_close_question", "same_turn_deactivation", "OFF"}.issubset(tokens):
        fail(f"one-shot transcript lacks deactivation guarantees: {transcript_id}")
    if steps[0]["event"] != "user" or "one_shot_scope" not in steps[0]["expect"]:
        fail(f"one-shot scope must be user-authored: {transcript_id}")
    terminal = steps[-1]
    terminal_required = {
        "no_cross_turn_persistence",
        "controllable_workers_closed",
        "no_close_question",
        "same_turn_deactivation",
        "OFF",
    }
    if terminal["event"] != "coordinator" or not terminal_required.issubset(terminal["expect"]):
        fail(f"one-shot handoff must close controllable workers: {transcript_id}")
    completed = {
        "bounded_wave",
        "no_later_user_wake_dependency",
        "no_cross_turn_persistence",
        "one_shot_complete",
    }
    blocked = {"capability_or_authorization_blocked", "clear_incomplete_handoff"}
    if not completed.issubset(tokens) and not blocked.issubset(tokens):
        fail(f"one-shot transcript lacks completion or blocked handoff: {transcript_id}")
    wait_count = sum("single_native_bounded_wait" in step["expect"] for step in steps)
    if wait_count > 1:
        fail(f"one-shot dependency wait must occur at most once: {transcript_id}")
    wait_guards = {
        "one_shot_wait_opt_in_exception",
        "strict_dependency_wait",
        "bounded_timeout",
        "main_turn_in_progress_disclosure",
        "new_input_may_be_delayed",
        "no_shell_sleep",
        "no_busy_poll",
        "no_wait_loop",
        "no_repeated_wait",
    }
    if wait_count and not wait_guards.issubset(tokens):
        fail(f"one-shot dependency wait lacks its safety guards: {transcript_id}")


def validate() -> None:
    text = SKILL.read_text(encoding="utf-8")
    metadata = frontmatter(text)
    if set(metadata) != {"name", "description"}:
        fail("frontmatter must contain only name and description")
    if metadata["name"] != SKILL_DIR.name:
        fail("skill name must match its directory")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", metadata["name"]):
        fail("skill name must use lowercase kebab-case")
    for phrase in (
        "EXPLICIT-ONLY",
        "one-shot scope that deactivates in the same response without a close question",
        "run-scoped live session (the bare explicit default)",
        "later direct explicit close confirmation",
    ):
        if phrase not in metadata["description"]:
            fail(f"description is missing {phrase!r}")
    if len(text.splitlines()) > 500:
        fail("SKILL.md must stay under 500 lines")

    required_skill = (
        "bare explicit Relay invocation also defaults to a live session",
        "Do not persist a session or ask a close question",
        "Live closure invariant",
        "user-authored on a later turn",
        "provisional closure authorization",
        "drain already-delivered safety events and material results",
        "mixed assent plus new work",
        "resume <token>: <next instruction>",
        "exact used-handle accounting",
        "freeze repository operations and overlapping writer dispatch",
        "result delivery or notification",
        "notification-triggered automatic coordinator wake",
        "Notification presence alone does not prove wake support",
        "continue through worker completion, authorized dependent waves, integration, verification, and a completion candidate without requiring another user message",
        "resume natively on that wake",
        "automatically use native completion waits or completion polling at short bounded intervals",
        "Do not require wait opt-in or another user or manual wake",
        "coordinator remains `In Progress` and a message may wait up to one poll interval",
        "process newer user input first and delivered worker results next",
        "Start another interval only while active work remains and a specific completion or status condition can be observed",
        "After processing an event, poll again only if active work remains",
        "Never use shell sleep, a single long blind block, blind busy-polling, or polling with no active work or next condition",
        "ordinary one-off instruction",
        "Do not create a mode, option, scope, toggle, or persistent policy",
        "explicitly chosen one-shot",
        "at most one bounded native wait without separate wait opt-in",
        "all controllable workers are closed",
        "distinct hand-back question",
        "Working without worktree isolation",
        "The skill imposes no fixed maximum",
        "fifteen agents",
        "Do not silently reduce",
        "Never reject a relevant update",
        "Live Run Ledger",
        "completion candidates do not deactivate it",
        "Do not switch to worktree mode silently",
        "stable functional role",
        "completed-but-open handle",
        "STATUS: DONE | BLOCKED | NEEDS_CONTEXT",
        "COMMANDS_AND_SIDE_EFFECTS",
        "deactivate Relay Orchestra",
        "ACTIVE -> STOPPING -> OFF",
        "persistence of loaded skill instructions across turns",
        "compact non-secret session token",
        "Treat a user-specified total as `EXACT`",
        "Ask the user for a count delta",
        "A result arriving after `OFF`",
        "pending close confirmation",
        "answer any non-close question never authorizes closure",
        "The coordinator remains the only dispatcher",
        "Leaf agents must not spawn agents or invoke orchestration skills",
    )
    for phrase in required_skill:
        if phrase not in text:
            fail(f"SKILL.md is missing {phrase!r}")
    for coupled in ("Cavecrew", "Claude", "Codex", "OpenAI", "plugin"):
        if coupled in text:
            fail(f"portable SKILL.md must not couple to {coupled!r}")

    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" not in target and not (SKILL_DIR / target).exists():
            fail(f"broken local link: {target}")

    openai = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for phrase in ("live $relay-orchestra session", "directly confirm closure in a later message", "allow_implicit_invocation: false"):
        if phrase not in openai:
            fail(f"openai.yaml is missing {phrase!r}")
    if "latest objective is complete" in openai:
        fail("openai.yaml must not make objective completion a close trigger")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in (
        "bare explicit invocation defaults to a live session",
        "Start a live Relay Orchestra session",
        "$relay-orchestra For this message only",
        "You:<br/>close or continue",
        "Result notifications",
        "Automatic coordinator wake",
        "later direct answer to its current close question",
        "without a close question or cross-turn persistence",
        "continues through dependent waves, integration, verification, and a completion candidate without requiring another user message",
        "coordinator remains **In Progress** and a message may wait up to one poll interval",
        "never uses shell sleep, a single long blind block, blind busy-polling, or polling with no active work or next condition",
        "not a mode, option, scope, toggle, or persistent policy",
    ):
        if phrase not in readme:
            fail(f"README.md is missing {phrase!r}")
    if "\n## License\n" in readme:
        fail("README.md must keep the license badge without a redundant License section")

    platforms = (SKILL_DIR / "references" / "platforms.md").read_text(encoding="utf-8")
    for phrase in (
        "Snapshot: 2026-07-13",
        "queueing a completed-subagent notification",
        "without proven auto-wake",
        "automatically use native completion waits or polling at short bounded intervals while active work remains",
        "coordinator remains `In Progress` and a message may wait up to one poll interval",
        "process newer input and delivered results before advancing dependent waves, integration, verification, and synthesis",
        "never use shell sleep, a single long blind block, or polling without active work or a next condition",
    ):
        if phrase not in platforms:
            fail(f"platforms.md is missing {phrase!r}")

    live_session = (SKILL_DIR / "references" / "live-session.md").read_text(encoding="utf-8")
    for phrase in (
        "queued notification may not start a coordinator turn",
        "automatically use native completion waits or polling at short bounded intervals",
        "coordinator remains `In Progress` and a message may wait up to one poll interval",
        "process newer user input first and delivered results next",
        "advance dependent waves, integration, verification, and synthesis",
        "Poll again after processing only while active work remains",
        "Never use shell sleep, a single long blind block, blind busy-polling, or polling with no active work or next condition",
        "Do not record a mode, option, scope, toggle, or persistent policy",
    ):
        if phrase not in live_session:
            fail(f"live-session.md is missing {phrase!r}")

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    if "explicit one-shot auto-deactivation" not in contributing or "explicit live-session lifecycle" not in contributing:
        fail("CONTRIBUTING.md must preserve both invocation scopes")

    stale_names = ("orchestrate-subagents", "scatter-gather", "Scatter Gather", "$orchestrate")
    suffixes = {".md", ".json", ".yaml", ".yml"}
    paths = [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts and path.suffix in suffixes]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for name in stale_names:
            if name in content:
                fail(f"stale name {name!r} in {path.relative_to(ROOT)}")
        if "for this request only" in content.lower():
            fail(f"ambiguous invocation scope in {path.relative_to(ROOT)}")
        if path.suffix == ".md":
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", content):
                if target.startswith("#") or "://" in target or target.startswith("mailto:"):
                    continue
                local_target = target.split("#", 1)[0]
                if local_target and not (path.parent / local_target).exists():
                    fail(f"broken local link {target!r} in {path.relative_to(ROOT)}")

    cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        fail("cases.json must contain a non-empty list")
    case_expectations: dict[str, set[str]] = {}
    for case in cases:
        if set(case) != {"id", "prompt", "expected"} or not case["prompt"] or not case["expected"]:
            fail(f"invalid eval case: {case!r}")
        if case["id"] in case_expectations:
            fail(f"duplicate eval id: {case['id']}")
        if not isinstance(case["expected"], list) or not all(isinstance(token, str) and token for token in case["expected"]):
            fail(f"invalid eval expectations: {case['id']}")
        case_expectations[case["id"]] = set(case["expected"])

    required_case_expectations = {
        "explicit_one_shot_auto_deactivates_without_close_question": {
            "one_shot_scope", "bounded_wave", "single_native_bounded_wait", "one_shot_wait_opt_in_exception", "strict_dependency_wait", "bounded_timeout", "main_turn_in_progress_disclosure", "new_input_may_be_delayed", "no_shell_sleep", "no_busy_poll", "no_wait_loop", "no_later_user_wake_dependency", "no_repeated_wait", "no_cross_turn_persistence", "controllable_workers_closed", "no_close_question", "same_turn_deactivation", "OFF"
        },
        "bare_explicit_invocation_defaults_to_live_session": {
            "default_live_scope", "ACTIVE", "responsive_session", "later_close_confirmation_required"
        },
        "one_shot_blocked_handoff": {
            "one_shot_scope", "clear_incomplete_handoff", "no_cross_turn_persistence", "controllable_workers_closed", "no_close_question", "same_turn_deactivation", "OFF"
        },
        "no_auto_wake_continues_to_completion_candidate": {
            "result_notifications", "notification_presence_not_wake_proof", "no_notification_auto_wake", "native_completion_polling", "short_bounded_poll_interval", "disclosure_once", "main_turn_in_progress_disclosure", "message_may_wait_up_to_poll_interval", "process_newer_input_between_intervals", "process_delivered_results_between_intervals", "active_work_and_next_condition_required", "dependent_waves", "integration", "verification", "completion_candidate", "no_user_or_manual_wake_dependency", "no_shell_sleep", "no_long_blind_block", "no_poll_without_active_work_or_next_condition"
        },
        "auto_wake_dispatch_yields": {
            "result_notifications", "notification_auto_wake", "dispatch_nonblocking", "yield_main_turn", "resume_natively", "autonomous_synthesis_after_wake"
        },
        "native_polling_stop_conditions": {
            "stop_poll_for_result", "stop_poll_for_completion", "stop_poll_for_redirect", "stop_poll_for_stop", "stop_poll_for_one_off_pause_or_yield", "stop_poll_for_real_blocker", "process_before_next_interval", "poll_again_only_with_active_work", "no_poll_without_active_work_or_next_condition"
        },
        "explicit_pause_or_yield_is_one_off": {
            "ordinary_one_off_instruction", "one_off_yield_honored", "remain_ACTIVE", "no_mode", "no_option", "no_scope", "no_toggle", "no_persistent_policy", "automatic_progress_after_return"
        },
        "completion_candidate_stays_active": {
            "final_audit", "ask_close", "pending_close_confirmation", "remain_ACTIVE", "no_automatic_STOPPING"
        },
        "direct_close_confirmation": {
            "user_authored_later_turn", "current_audited_revision", "ACTIVE_to_STOPPING", "STOPPING_to_OFF"
        },
        "close_confirmation_not_unstable_acceptance": {
            "remain_STOPPING", "distinct_unstable_handback_question", "close_confirmation_not_reused", "later_user_risk_acceptance_before_OFF"
        },
        "new_work_cancels_pending_close": {"cancel_pending_close", "continue_ACTIVE", "route_new_work", "audit_before_reasking"},
        "non_direct_assent_does_not_close": {"no_closure_authorization", "remain_ACTIVE", "require_direct_pending_close_answer"},
        "ambiguous_conditional_or_mixed_close_reply": {
            "ambiguous_or_conditional_stays_ACTIVE", "mixed_new_work_cancels_pending_close", "fresh_audit_before_reasking"
        },
        "stale_close_confirmation": {"stale_confirmation_rejected", "no_closure_authorization", "remain_ACTIVE"},
        "close_confirmation_result_race": {
            "provisional_close_authorization", "drain_delivery_batch", "audit_result_before_transition", "cancel_pending_close", "no_premature_STOPPING"
        },
        "pending_close_persistence_fallback": {
            "session_token", "pending_close_and_audited_revision_in_token", "explicit_skill_resume", "remain_ACTIVE_while_waiting"
        },
        "persistence_capability_gate": {
            "check_each_capability", "separate_result_notification_and_auto_wake_checks", "explicit_skill_resume", "session_token"
        },
        "unexpected_lost_writer_handle": {
            "handle_lifecycle_unknown", "retain_exact_accounting", "tree_unstable", "freeze_repository_operations", "freeze_overlapping_writer_dispatch"
        },
        "overlapping_writers": {"pause_before_dispatch", "recommend_worktree_or_serialization", "no_silent_worktree"},
        "approved_worktrees": {"worktree_mode", "one_checkout_per_writer", "coordinator_integrates"},
        "sole_dispatcher": {"coordinator_only_dispatcher", "leaf_agents_do_not_spawn", "no_nested_orchestration"},
        "one_agent": {"requested_total_1", "responsive_session"},
        "fifteen_agents": {"requested_total_15", "no_skill_cap", "account_all"},
        "exact_total_ceiling": {"EXACT_2", "ask_for_count_delta", "no_third_handle"},
        "open_scheduler_addition": {"OPEN_count_mode", "scheduler_may_add"},
    }
    for case_id, expected in required_case_expectations.items():
        actual = case_expectations.get(case_id)
        if actual is None:
            fail(f"missing eval case: {case_id}")
        if not expected.issubset(actual):
            fail(f"eval case {case_id!r} is missing required expectations")

    transcripts = json.loads((ROOT / "evals" / "transcripts.json").read_text(encoding="utf-8"))
    if not isinstance(transcripts, list) or not transcripts:
        fail("transcripts.json must contain a non-empty list")
    transcript_ids: set[str] = set()
    capability_keys = {
        "skill_instructions_persist",
        "ledger_persists",
        "agent_handles_persist",
        "result_notifications",
        "notification_auto_wake",
    }
    states = {"ACTIVE", "STOPPING", "OFF"}
    events = {"user", "coordinator", "yield", "delivery_batch", "worker_result", "notification_wake", "wait_timeout"}
    event_kinds: set[str] = set()
    expectation_tokens: set[str] = set()

    for transcript in transcripts:
        required_keys = {"id", "scope", "capabilities", "initial_state", "steps", "final_state"}
        if set(transcript) != required_keys:
            fail(f"invalid transcript scenario keys: {transcript!r}")
        transcript_id = transcript["id"]
        if transcript_id in transcript_ids:
            fail(f"duplicate transcript id: {transcript_id}")
        transcript_ids.add(transcript_id)
        if transcript["scope"] not in {"live", "one_shot"}:
            fail(f"invalid transcript scope: {transcript_id}")
        capabilities = transcript["capabilities"]
        if set(capabilities) != capability_keys or not all(isinstance(value, bool) for value in capabilities.values()):
            fail(f"invalid transcript capabilities: {transcript_id}")
        if capabilities["notification_auto_wake"] and not capabilities["result_notifications"]:
            fail(f"auto-wake requires result notifications: {transcript_id}")
        if transcript["initial_state"] not in states or transcript["final_state"] not in states:
            fail(f"invalid transcript state: {transcript_id}")
        if not isinstance(transcript["steps"], list) or not transcript["steps"]:
            fail(f"transcript must have steps: {transcript_id}")

        previous_turn = 0
        for step in transcript["steps"]:
            required_step = {"turn", "event", "detail", "expect"}
            allowed_step = required_step | {"inputs"}
            if not required_step.issubset(step) or not set(step).issubset(allowed_step):
                fail(f"invalid transcript step: {step!r}")
            if not isinstance(step["turn"], int) or step["turn"] < previous_turn:
                fail(f"transcript turns must be ordered: {transcript_id}")
            previous_turn = step["turn"]
            if step["event"] not in events or not step["detail"]:
                fail(f"invalid transcript event: {transcript_id}")
            if not isinstance(step["expect"], list) or not step["expect"] or not all(isinstance(token, str) and token for token in step["expect"]):
                fail(f"transcript step lacks expectations: {step!r}")
            event_kinds.add(step["event"])
            if step["event"] == "delivery_batch":
                inputs = step.get("inputs")
                if not isinstance(inputs, list) or len(inputs) != 2 or {item.get("kind") for item in inputs} != {"user", "worker_result"}:
                    fail(f"delivery_batch must contain one user and one worker result: {transcript_id}")
            elif "inputs" in step:
                fail(f"inputs are only valid on delivery_batch: {transcript_id}")

        if transcript["scope"] == "one_shot":
            validate_one_shot(transcript, expectation_tokens)
            continue

        state = transcript["initial_state"]
        requirement_revision = 1 if state == "ACTIVE" else 0
        pending_close = False
        pending_close_revision: int | None = None
        pending_close_turn: int | None = None
        close_authorization: str | None = None
        cleared_close_seen = False
        ambiguous_reply_seen = False
        unstable_handback_pending = False
        unstable_question_turn: int | None = None
        unstable_handback_accepted = False
        completion_poll_count = 0
        poll_disclosure_count = 0

        for step in transcript["steps"]:
            tokens = set(step["expect"])
            expectation_tokens.update(tokens)
            event = step["event"]
            turn = step["turn"]

            authority_tokens = {"direct_close_confirmation", "stop_requested", "accept_unstable_handback"}
            if len(authority_tokens.intersection(tokens)) > 1:
                fail(f"one event cannot supply multiple authorizations: {transcript_id}")

            if "result_notifications" in tokens and not capabilities["result_notifications"]:
                fail(f"result notifications claimed without capability: {transcript_id}")
            if "notification_auto_wake" in tokens:
                if event != "coordinator" or not capabilities["notification_auto_wake"]:
                    fail(f"automatic wake claimed without capability: {transcript_id}")
            if "no_notification_auto_wake" in tokens:
                required = {
                    "result_notifications",
                    "notification_presence_not_wake_proof",
                    "native_completion_polling",
                }
                if event != "coordinator" or capabilities["notification_auto_wake"] or not required.issubset(tokens):
                    fail(f"queued notifications do not continue through native polling: {transcript_id}")
            if "dispatch" in tokens and capabilities["result_notifications"] and not capabilities["notification_auto_wake"]:
                required = {
                    "notification_presence_not_wake_proof",
                    "no_notification_auto_wake",
                    "native_completion_polling",
                }
                if event != "coordinator" or not required.issubset(tokens):
                    fail(f"live dispatch omits continuous native polling: {transcript_id}")
            if event == "notification_wake":
                required = {"auto_wake_started_coordinator_turn", "resume_natively", "worker_result_delivered"}
                if not capabilities["notification_auto_wake"] or not required.issubset(tokens):
                    fail(f"invalid notification-triggered wake: {transcript_id}")
            if "native_completion_polling" in tokens:
                required = {
                    "short_bounded_poll_interval",
                    "bounded_timeout",
                    "active_work_and_next_condition_required",
                    "no_shell_sleep",
                    "no_long_blind_block",
                    "no_poll_without_active_work_or_next_condition",
                }
                if (
                    event != "coordinator"
                    or state != "ACTIVE"
                    or capabilities["notification_auto_wake"]
                    or not required.issubset(tokens)
                ):
                    fail(f"invalid native completion poll: {transcript_id}")
                completion_poll_count += 1
                if "disclosure_once" in tokens:
                    disclosure_required = {
                        "main_turn_in_progress_disclosure",
                        "message_may_wait_up_to_poll_interval",
                    }
                    if not disclosure_required.issubset(tokens):
                        fail(f"native polling disclosure is incomplete: {transcript_id}")
                    poll_disclosure_count += 1
            if event == "wait_timeout":
                required = {
                    "short_poll_timeout",
                    "still_running_state_reported",
                    "check_newer_input_between_intervals",
                    "check_delivered_results_between_intervals",
                    "active_work_remains",
                    "specific_next_condition",
                    "repeat_bounded_poll",
                    "remain_ACTIVE",
                }
                if not completion_poll_count or not required.issubset(tokens):
                    fail(f"native poll timeout did not re-check active work: {transcript_id}")
            if "poll_cycle_stops" in tokens:
                required = {"result_available", "newer_input_checked_before_result", "worker_result_delivered"}
                if event not in {"worker_result", "delivery_batch"} or not required.issubset(tokens):
                    fail(f"native poll did not stop to process a result: {transcript_id}")

            if "session_token" in tokens:
                if event != "coordinator":
                    fail(f"session token must be coordinator-authored: {transcript_id}")
                if not capabilities["agent_handles_persist"] and "no_live_handle_at_yield" not in tokens:
                    fail(f"token yield may strand a live handle: {transcript_id}")
            if "OFF_to_ACTIVE" in tokens:
                if event != "user" or state != "OFF":
                    fail(f"invalid OFF to ACTIVE transition: {transcript_id}")
                state = "ACTIVE"
                requirement_revision = 1
            if "completion_candidate" in tokens:
                required = {"pending_close_confirmation", "close_question_ends_turn", "remain_ACTIVE"}
                if event != "coordinator" or state != "ACTIVE" or not required.issubset(tokens) or "ACTIVE_to_STOPPING" in tokens:
                    fail(f"completion candidate must remain ACTIVE: {transcript_id}")
            if "pending_close_confirmation" in tokens:
                required = {"final_audit", "ask_close", "close_question_revision_bound", "remain_ACTIVE"}
                if event != "coordinator" or state != "ACTIVE" or pending_close or not required.issubset(tokens):
                    fail(f"invalid close question: {transcript_id}")
                pending_close = True
                pending_close_revision = requirement_revision
                pending_close_turn = turn
                if not capabilities["skill_instructions_persist"] or not capabilities["ledger_persists"]:
                    fallback = {"session_token", "pending_close_and_audited_revision_in_token"}
                    if not fallback.issubset(tokens):
                        fail(f"pending close is not persisted: {transcript_id}")
            if "ambiguous_or_conditional_close_reply" in tokens:
                required = {"no_closure_authorization", "remain_ACTIVE"}
                if event != "user" or state != "ACTIVE" or not pending_close or turn <= pending_close_turn or not required.issubset(tokens):
                    fail(f"ambiguous close reply was accepted: {transcript_id}")
                close_authorization = None
                ambiguous_reply_seen = True
            if "replace_pending_close_question" in tokens:
                required = {"same_audited_revision", "remain_ACTIVE"}
                if event != "coordinator" or state != "ACTIVE" or not pending_close or not ambiguous_reply_seen or not required.issubset(tokens):
                    fail(f"invalid replacement close question: {transcript_id}")
                pending_close_turn = turn
                ambiguous_reply_seen = False
            if "provisional_close_authorization" in tokens:
                required = {
                    "drain_delivery_batch_before_STOPPING",
                    "audit_result_before_transition",
                    "material_result_invalidates_close",
                    "cancel_pending_close",
                    "no_closure_authorization",
                    "remain_ACTIVE",
                    "no_ACTIVE_to_STOPPING",
                }
                if event != "delivery_batch" or state != "ACTIVE" or not pending_close or turn <= pending_close_turn or not required.issubset(tokens):
                    fail(f"close/result race is not safely drained: {transcript_id}")
                close_authorization = "provisional"
            if "material_result_invalidates_close" in tokens and "provisional_close_authorization" not in tokens:
                required = {"cancel_pending_close", "no_closure_authorization", "remain_ACTIVE"}
                if event not in {"worker_result", "delivery_batch"} or state != "ACTIVE" or not pending_close or not required.issubset(tokens):
                    fail(f"material result did not invalidate pending close: {transcript_id}")
            if "mixed_assent_plus_new_work" in tokens:
                required = {"cancel_pending_close", "no_closure_authorization", "remain_ACTIVE"}
                if event != "user" or state != "ACTIVE" or not pending_close or turn <= pending_close_turn or not required.issubset(tokens):
                    fail(f"mixed assent closed the session: {transcript_id}")
            if "cancel_pending_close" in tokens:
                if state != "ACTIVE" or not pending_close:
                    fail(f"invalid close cancellation: {transcript_id}")
                pending_close = False
                pending_close_revision = None
                pending_close_turn = None
                close_authorization = None
                cleared_close_seen = True
            if "no_closure_authorization" in tokens:
                close_authorization = None
            if "revision_increment" in tokens:
                if event != "coordinator" or state != "ACTIVE" or pending_close or close_authorization:
                    fail(f"revision advanced without clearing close authorization: {transcript_id}")
                requirement_revision += 1
            if "direct_close_confirmation" in tokens:
                contradictory = {
                    "no_closure_authorization",
                    "cancel_pending_close",
                    "stale_close_confirmation",
                    "ambiguous_or_conditional_close_reply",
                    "mixed_assent_plus_new_work",
                    "material_result_invalidates_close",
                }
                if (
                    event != "user"
                    or state != "ACTIVE"
                    or not pending_close
                    or pending_close_revision != requirement_revision
                    or pending_close_turn is None
                    or turn <= pending_close_turn
                    or "close_confirmation_revision_match" not in tokens
                    or contradictory.intersection(tokens)
                ):
                    fail(f"close confirmation is not a direct current later-turn answer: {transcript_id}")
                close_authorization = "confirmation"
            if "stale_close_confirmation" in tokens:
                required = {"no_closure_authorization", "fresh_audit_and_question_required", "remain_ACTIVE"}
                if event != "user" or state != "ACTIVE" or pending_close or not cleared_close_seen or not required.issubset(tokens):
                    fail(f"stale close confirmation was accepted: {transcript_id}")
                close_authorization = None
            if "stop_requested" in tokens:
                if event != "user" or state != "ACTIVE" or "no_closure_authorization" in tokens:
                    fail(f"explicit stop must be user-authored while ACTIVE: {transcript_id}")
                pending_close = False
                pending_close_revision = None
                pending_close_turn = None
                close_authorization = "stop"
            if "ACTIVE_to_STOPPING" in tokens:
                if event != "coordinator" or state != "ACTIVE" or close_authorization not in {"confirmation", "stop"}:
                    fail(f"unauthorized ACTIVE to STOPPING transition: {transcript_id}")
                if close_authorization == "confirmation" and "confirmation_authorizes_STOPPING" not in tokens:
                    fail(f"close confirmation was not consumed explicitly: {transcript_id}")
                state = "STOPPING"
                pending_close = False
                pending_close_revision = None
                pending_close_turn = None
                close_authorization = None
            if "unstable_handback_required" in tokens:
                required = {"tree_unstable", "repository_operations_prohibited", "risk_disclosed", "remain_STOPPING"}
                if event != "coordinator" or state != "STOPPING" or not required.issubset(tokens):
                    fail(f"invalid unstable hand-back question: {transcript_id}")
                unstable_handback_pending = True
                unstable_question_turn = turn
                unstable_handback_accepted = False
            if "accept_unstable_handback" in tokens:
                if (
                    event != "user"
                    or state != "STOPPING"
                    or not unstable_handback_pending
                    or unstable_question_turn is None
                    or turn <= unstable_question_turn
                ):
                    fail(f"unstable hand-back acceptance is not a later user answer: {transcript_id}")
                unstable_handback_pending = False
                unstable_handback_accepted = True
            if "STOPPING_to_OFF" in tokens:
                writers_safe = "terminal_writers_confirmed" in tokens or (
                    unstable_handback_accepted and not unstable_handback_pending and "unstable_handoff" in tokens
                )
                if event != "coordinator" or state != "STOPPING" or "controllable_workers_closed" not in tokens or not writers_safe:
                    fail(f"unsafe STOPPING to OFF transition: {transcript_id}")
                state = "OFF"
            if ("remain_ACTIVE" in tokens or "ACTIVE" in tokens) and state != "ACTIVE":
                fail(f"ACTIVE assertion does not match state: {transcript_id}")
            if "remain_STOPPING" in tokens and state != "STOPPING":
                fail(f"STOPPING assertion does not match state: {transcript_id}")
            if "OFF" in tokens and state != "OFF":
                fail(f"OFF assertion does not match state: {transcript_id}")

        if completion_poll_count and poll_disclosure_count != 1:
            fail(f"native polling must disclose its responsiveness cost once: {transcript_id}")
        if state != transcript["final_state"]:
            fail(f"modeled final state does not match transcript: {transcript_id}")

    required_transcripts = {
        "no_auto_wake_continues_through_completion_candidate",
        "auto_wake_dispatch_resumes_coordinator",
        "explicit_pause_or_yield_is_one_off",
        "explicit_one_shot_bounded_completion",
        "one_shot_blocked_handoff",
        "stop_during_shared_write_and_late_result",
        "persistence_fallback_continuous_bounded_waves",
        "bare_explicit_invocation_defaults_live_and_requires_later_close",
        "new_work_cancels_pending_close",
        "close_confirmation_requires_separate_unstable_acceptance",
        "pending_close_confirmation_fallback",
        "fallback_approval_is_not_close_confirmation",
        "stale_close_confirmation_is_rejected",
        "close_confirmation_races_material_result",
        "ambiguous_and_mixed_replies_stay_active",
        "unexpected_lost_writer_handle_remains_significant",
    }
    if not required_transcripts.issubset(transcript_ids):
        fail("missing required transcript scenario")
    continuous = next(
        transcript for transcript in transcripts
        if transcript["id"] == "no_auto_wake_continues_through_completion_candidate"
    )
    continuous_tokens = {token for step in continuous["steps"] for token in step["expect"]}
    required_continuous = {
        "native_completion_polling",
        "repeat_bounded_poll",
        "user_delta_first",
        "poll_cycle_stops",
        "dispatch_dependent_implementation",
        "integrate_completed_work",
        "dispatch_verification_wave",
        "verification_completed",
        "completion_candidate",
        "pending_close_confirmation",
        "remain_ACTIVE",
    }
    if not required_continuous.issubset(continuous_tokens):
        fail("no-auto-wake transcript must continue through verification to an ACTIVE completion candidate")
    bare_live = next(
        transcript for transcript in transcripts
        if transcript["id"] == "bare_explicit_invocation_defaults_live_and_requires_later_close"
    )
    bare_live_tokens = {token for step in bare_live["steps"] for token in step["expect"]}
    required_bare_live = {
        "default_live_scope",
        "OFF_to_ACTIVE",
        "completion_candidate",
        "pending_close_confirmation",
        "remain_ACTIVE",
        "later_close_confirmation_required",
        "direct_close_confirmation",
        "close_confirmation_revision_match",
        "ACTIVE_to_STOPPING",
        "STOPPING_to_OFF",
    }
    if not required_bare_live.issubset(bare_live_tokens):
        fail("bare explicit invocation transcript must stay live until later direct close confirmation")
    for event in ("yield", "delivery_batch", "worker_result", "notification_wake", "wait_timeout"):
        if event not in event_kinds:
            fail(f"transcripts are missing {event!r} event")
    for token in (
        "one_shot_scope",
        "default_live_scope",
        "same_turn_deactivation",
        "no_close_question",
        "no_cross_turn_persistence",
        "single_native_bounded_wait",
        "one_shot_wait_opt_in_exception",
        "no_later_user_wake_dependency",
        "yield_main_turn",
        "result_notifications",
        "notification_presence_not_wake_proof",
        "no_notification_auto_wake",
        "native_completion_polling",
        "short_bounded_poll_interval",
        "disclosure_once",
        "message_may_wait_up_to_poll_interval",
        "process_newer_input_between_intervals",
        "process_delivered_results_between_intervals",
        "active_work_and_next_condition_required",
        "no_user_or_manual_wake_dependency",
        "no_long_blind_block",
        "no_poll_without_active_work_or_next_condition",
        "notification_auto_wake",
        "auto_wake_started_coordinator_turn",
        "resume_natively",
        "strict_dependency_wait",
        "bounded_timeout",
        "main_turn_in_progress_disclosure",
        "new_input_may_be_delayed",
        "no_shell_sleep",
        "no_busy_poll",
        "no_wait_loop",
        "no_repeated_wait",
        "short_poll_timeout",
        "still_running_state_reported",
        "check_newer_input_between_intervals",
        "check_delivered_results_between_intervals",
        "repeat_bounded_poll",
        "poll_cycle_stops",
        "dispatch_dependent_implementation",
        "integrate_completed_work",
        "dispatch_verification_wave",
        "verification_completed",
        "ordinary_one_off_instruction",
        "one_off_yield_honored",
        "no_mode",
        "no_option",
        "no_scope",
        "no_toggle",
        "no_persistent_policy",
        "automatic_progress_after_return",
        "queued_input",
        "HELD_to_QUEUED",
        "ACTIVE_to_STOPPING",
        "STOPPING_to_OFF",
        "controllable_workers_closed",
        "report_late_write",
        "session_token",
        "portable_resume_payload",
        "rehydrate",
        "explicit_skill_resume",
        "pending_close_confirmation",
        "close_question_revision_bound",
        "direct_close_confirmation",
        "close_confirmation_revision_match",
        "unstable_handback_required",
        "accept_unstable_handback",
        "cancel_pending_close",
        "fallback_authorization_question",
        "fallback_work_authorized",
        "non_close_answer",
        "no_closure_authorization",
        "close_question_ends_turn",
        "later_close_confirmation_required",
        "no_same_turn_shutdown",
        "stale_close_confirmation",
        "provisional_close_authorization",
        "material_result_invalidates_close",
        "ambiguous_or_conditional_close_reply",
        "mixed_assent_plus_new_work",
        "handle_lifecycle_unknown",
        "retain_exact_accounting",
    ):
        if token not in expectation_tokens:
            fail(f"transcripts are missing {token!r} expectation")

    for relative in ("scripts/install.py", "install.sh", "install.ps1", "tests/test_install.py"):
        if not (ROOT / relative).is_file():
            fail(f"missing repository file: {relative}")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Relay Orchestra validation passed.")
