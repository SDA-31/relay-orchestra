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
        "settle_controllable_workers_before_final_response",
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
        "workers_terminal",
        "synthesis_complete",
    }
    blocked = {"capability_or_authorization_blocked", "clear_incomplete_handoff"}
    if not completed.issubset(tokens) and not blocked.issubset(tokens):
        fail(f"one-shot transcript lacks completion or blocked handoff: {transcript_id}")

    if blocked.issubset(tokens):
        return

    completed_terminal = {"workers_terminal", "synthesis_complete", "stop_for_terminal_results_and_synthesis"}
    if not completed_terminal.issubset(terminal["expect"]):
        fail(f"one-shot final response precedes terminal synthesis: {transcript_id}")

    stop_policy = {
        "bound_to_originating_message_and_final_response",
        "no_arbitrary_poll_deadline",
        "stop_for_terminal_results_and_synthesis",
        "stop_for_user_cancel_or_redirect",
        "stop_for_user_specified_overall_limit",
        "stop_for_genuine_runtime_blocker",
    }
    if not stop_policy.issubset(tokens):
        fail(f"one-shot polling lacks its scope or stop policy: {transcript_id}")

    poll_indexes: list[int] = []
    disclosure_count = 0
    poll_guards = {
        "short_bounded_poll_interval",
        "one_shot_wait_opt_in_exception",
        "strict_dependency_wait",
        "bounded_timeout",
        "active_work_and_next_condition_required",
        "same_coordinator_turn",
        "no_shell_sleep",
        "no_long_blind_block",
        "no_busy_poll",
        "no_poll_without_active_work_or_next_condition",
    }
    for index, step in enumerate(steps):
        step_tokens = set(step["expect"])
        if "native_one_shot_completion_polling" in step_tokens:
            if step["event"] != "coordinator" or not poll_guards.issubset(step_tokens):
                fail(f"invalid one-shot completion poll: {transcript_id}")
            poll_indexes.append(index)
            disclosure_tokens = {
                "main_turn_in_progress_disclosure",
                "message_may_wait_up_to_poll_interval",
            }
            if "disclosure_once" in step_tokens:
                if not disclosure_tokens.issubset(step_tokens):
                    fail(f"one-shot polling disclosure is incomplete: {transcript_id}")
                disclosure_count += 1
            elif disclosure_tokens.intersection(step_tokens):
                fail(f"one-shot polling repeats its disclosure: {transcript_id}")

        if step["event"] == "wait_timeout":
            timeout_required = {
                "short_poll_timeout",
                "poll_timeout_is_scheduling_tick",
                "poll_timeout_not_task_deadline",
                "still_running_state_reported",
                "check_newer_input_between_intervals",
                "check_delivered_results_between_intervals",
                "process_newer_input_between_intervals",
                "process_delivered_results_between_intervals",
                "active_work_remains",
                "specific_next_condition",
                "healthy_workers_not_interrupted",
                "repeat_bounded_poll",
                "same_coordinator_turn",
                "no_deactivation_on_interval_timeout",
            }
            if not any(poll_index < index for poll_index in poll_indexes) or not timeout_required.issubset(step_tokens):
                fail(f"one-shot poll timeout was treated as terminal: {transcript_id}")
            if terminal_required.intersection(step_tokens):
                fail(f"one-shot poll timeout deactivates Relay: {transcript_id}")
            if index + 1 >= len(steps):
                fail(f"one-shot poll timeout did not schedule another interval: {transcript_id}")
            next_step = steps[index + 1]
            if next_step["event"] != "coordinator" or "native_one_shot_completion_polling" not in next_step["expect"]:
                fail(f"one-shot poll timeout did not schedule another interval: {transcript_id}")

        if "authorized_dependent_work_remains" in step_tokens:
            if index + 1 >= len(steps):
                fail(f"one-shot did not advance authorized dependent work: {transcript_id}")
            next_step = steps[index + 1]
            dependent_required = {"dispatch_authorized_dependent_work", "native_one_shot_completion_polling"}
            if next_step["event"] != "coordinator" or not dependent_required.issubset(next_step["expect"]):
                fail(f"one-shot did not dispatch and poll authorized dependent work: {transcript_id}")

    if len(poll_indexes) < 2:
        fail(f"one-shot completion must use repeated bounded polling: {transcript_id}")
    if disclosure_count != 1:
        fail(f"one-shot polling must disclose its responsiveness cost once: {transcript_id}")
    if not any(step["event"] == "wait_timeout" for step in steps):
        fail(f"one-shot completion lacks interval-timeout coverage: {transcript_id}")


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
        "While `ACTIVE`, another explicit Relay invocation preserves the current state, scope, ledger, requirement revision, agent accounting, and pending close question",
        "treat accompanying text as a user delta, not a new or converted session",
        "Do not persist a session or ask a close question",
        "Live closure invariant",
        "Every live-session turn that reports a completion candidate",
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
        "Zero active agents, settled handles, or an immediate blocking phase handled locally do not deactivate a live session",
        "re-evaluate whether distinct leaf work is useful",
        "If no distinct leaf work exists, remain local and `ACTIVE` without dispatch",
        "A host response or context boundary does not authorize a Relay lifecycle transition",
        "`final_answer`",
        "host `task_complete`",
        "compaction, summarization, context replacement, resume, and notification wake",
        "Treat unverified persistence or controllability as unavailable",
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
        "originating user message and its final response, not by an arbitrary poll timeout",
        "native short bounded completion polls repeatedly within the same coordinator turn",
        "healthy workers or authorized dependent work remain",
        "A normal interval timeout is a scheduling tick, not the one-shot task deadline",
        "Never interrupt healthy workers solely because one interval elapsed",
        "Complete normally only after all workers are terminal and synthesis is complete",
        "Stop earlier only when the user explicitly cancels or redirects",
        "a user-specified overall limit is reached",
        "a genuine host or runtime blocker prevents progress",
        "Settle all controllable workers before the one-shot final response",
        "no cross-turn persistence",
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
        "A command to stop, cancel, or pause a task, workstream, worker, action, or direction is a work delta and leaves Relay `ACTIVE`",
        "While `STOPPING`, preserve shutdown and do not absorb accompanying new work",
        "Apply response mutations and replacement-token issuance before checking boundary continuity",
        "every nonterminal handle remains controllable; zero nonterminal handles satisfies the handle condition",
        "When the completion criteria appear satisfied and no close question is currently pending",
        "does not authorize or issue a replacement question",
        "monotonic ledger generation",
        "Increment the generation whenever any token-carried mutable state changes",
        "When a newer surviving ledger or generation exists, compare it and reject a stale token",
        "Without a surviving comparator, relative staleness cannot be independently proven",
        "accept a structurally valid token through explicit activation as the caller-supplied portable state",
        "Freeze dispatch and writes only when neither verified native state nor a valid explicit token is available",
        "does not itself reload instructions or restore control of lost handles",
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
        "repeats short native completion polls in its originating turn",
        "treats an interval timeout as a scheduling tick",
        "settling every controllable worker before its final response",
        "not a mode, option, scope, toggle, or persistent policy",
        "an active task may retain the skill instructions it already loaded",
        "Start a new task or chat before relying on updated instructions",
        "If cached content remains, use the client's documented refresh or restart procedure",
        "> [!WARNING]",
        "Delegated agents perform separate model work",
        "tokens or credits can be consumed quickly",
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
        "host `final`, `final_answer`, and `task_complete` markers",
        "do not authorize a Relay lifecycle transition",
        "Apply response mutations and replacement-token issuance first",
        "zero nonterminal handles satisfies the handle condition",
        "monotonic ledger generation covers every token-carried mutable field",
        "Compare against newer surviving ledger state when available",
        "accept the explicit token as supplied portable state",
        "relative staleness cannot be independently proven",
        "Freeze only when neither continuity path is available or surviving state proves the token stale",
        "Treat unverified persistence or controllability as unavailable",
        "Stop a task, workstream, worker, action, or direction",
        "Explicit Relay invocation while `ACTIVE`",
        "Explicit Relay invocation while `STOPPING`",
        "Do not absorb accompanying new work",
        "If a question is pending, retain it without another completion candidate or close question",
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

    install_doc = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    for phrase in (
        "An active task may retain Relay instructions loaded before the update",
        "Start a new task or chat before relying on updated instructions",
        "If cached content remains, use the client's documented refresh or restart procedure",
        "An update does not hot-reload instructions already held by an active task",
        "Then confirm the printed destination is one the client scans",
    ):
        if phrase not in install_doc:
            fail(f"INSTALL.md is missing {phrase!r}")

    installer = (ROOT / "scripts" / "install.py").read_text(encoding="utf-8")
    for phrase in (
        "Active tasks may retain Relay instructions loaded before this install or update.",
        "Start a new task or chat before relying on updated instructions.",
        "If cached content remains, use the client's documented refresh or restart procedure.",
    ):
        if phrase not in installer:
            fail(f"scripts/install.py is missing {phrase!r}")

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
            "one_shot_scope", "bounded_wave", "native_one_shot_completion_polling", "short_bounded_poll_interval", "one_shot_wait_opt_in_exception", "strict_dependency_wait", "bounded_timeout", "disclosure_once", "main_turn_in_progress_disclosure", "message_may_wait_up_to_poll_interval", "same_coordinator_turn", "bound_to_originating_message_and_final_response", "no_arbitrary_poll_deadline", "short_poll_timeout", "poll_timeout_is_scheduling_tick", "poll_timeout_not_task_deadline", "check_newer_input_between_intervals", "check_delivered_results_between_intervals", "process_newer_input_between_intervals", "process_delivered_results_between_intervals", "healthy_workers_not_interrupted", "repeat_bounded_poll", "authorized_dependent_work_remains", "dispatch_authorized_dependent_work", "stop_for_terminal_results_and_synthesis", "stop_for_user_cancel_or_redirect", "stop_for_user_specified_overall_limit", "stop_for_genuine_runtime_blocker", "workers_terminal", "synthesis_complete", "no_shell_sleep", "no_long_blind_block", "no_busy_poll", "no_poll_without_active_work_or_next_condition", "no_later_user_wake_dependency", "no_cross_turn_persistence", "settle_controllable_workers_before_final_response", "controllable_workers_closed", "no_close_question", "same_turn_deactivation", "OFF"
        },
        "bare_explicit_invocation_defaults_to_live_session": {
            "default_live_scope", "ACTIVE", "responsive_session", "later_close_confirmation_required"
        },
        "one_shot_blocked_handoff": {
            "one_shot_scope", "clear_incomplete_handoff", "no_cross_turn_persistence", "settle_controllable_workers_before_final_response", "controllable_workers_closed", "no_close_question", "same_turn_deactivation", "OFF"
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
            "session_token", "pending_close_and_audited_revision_in_token", "explicit_skill_resume",
            "structurally_valid_session_token", "token_accepted_as_supplied_state", "remain_ACTIVE_while_waiting"
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
        "historical_normal_completion_does_not_self_close": {
            "historical_normal_completion", "no_self_close", "completion_candidate", "ask_close", "remain_ACTIVE"
        },
        "host_final_and_task_complete_are_lifecycle_neutral": {
            "final_answer_boundary", "task_complete_boundary", "lifecycle_neutral", "preserve_ACTIVE", "no_closure_authorization"
        },
        "compaction_while_active_preserves_session": {
            "compaction_boundary", "lifecycle_neutral", "treat_unverified_persistence_as_unavailable",
            "session_token", "explicit_skill_resume", "structurally_valid_session_token",
            "token_accepted_as_supplied_state", "relative_staleness_not_independently_proven",
            "freeze_dispatch_and_writes", "no_restoration_claim", "remain_ACTIVE"
        },
        "compaction_without_continuity_freezes_work": {
            "compaction_boundary", "lifecycle_neutral", "continuity_loss", "freeze_dispatch_and_writes",
            "continuity_loss_disclosed", "no_restoration_claim", "never_infer_OFF", "remain_ACTIVE"
        },
        "stale_token_after_revision_is_rejected": {
            "stale_session_token", "stale_token_rejected", "token_ledger_generation_mismatch",
            "newer_generation_comparator_survives", "freeze_dispatch_and_writes",
            "no_restoration_claim", "remain_ACTIVE"
        },
        "stale_token_after_ledger_generation_change": {
            "ledger_generation_increment", "handle_accounting_changed", "tree_stability_changed",
            "queued_or_held_work_changed", "stale_session_token", "token_ledger_generation_mismatch",
            "newer_generation_comparator_survives", "stale_token_rejected", "remain_ACTIVE"
        },
        "non_native_host_final_then_task_complete_resumes": {
            "post_response_boundary_freshness", "session_token", "ledger_generation_in_token",
            "continuation_requires_explicit_resume", "host_bookkeeping_only", "execution_frozen",
            "explicit_skill_resume", "structurally_valid_session_token", "token_accepted_as_supplied_state",
            "relative_staleness_not_independently_proven", "remain_ACTIVE"
        },
        "native_continuity_with_zero_handles": {
            "zero_nonterminal_handles", "handle_continuity_vacuously_satisfied",
            "native_continuity_verified", "no_session_token", "remain_ACTIVE"
        },
        "reinvocation_while_active_preserves_session": {
            "reinvoke_while_ACTIVE", "preserve_state_scope_ledger_accounting", "accompanying_text_is_delta",
            "no_new_activation", "remain_ACTIVE"
        },
        "reinvocation_while_stopping_preserves_shutdown": {
            "reinvoke_while_STOPPING", "preserve_shutdown", "no_new_work_absorbed", "hand_back_after_OFF",
            "remain_STOPPING"
        },
        "pending_close_question_is_not_duplicated": {
            "retain_pending_close_question", "pending_close_identity_preserved",
            "no_duplicate_completion_candidate", "no_duplicate_close_question", "remain_ACTIVE"
        },
        "workstream_stop_is_not_relay_stop": {
            "work_item_stop", "no_session_stop_authorization", "interrupt_affected_work", "remain_ACTIVE",
            "explicit_session_stop_still_supported"
        },
        "local_phase_rechecks_delegation": {
            "zero_active_agents", "local_blocking_work", "explicit_ACTIVE_status", "delegation_re_evaluated",
            "no_distinct_leaf_work", "remain_local", "no_dispatch", "no_mandatory_fanout", "remain_ACTIVE"
        },
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
    required_capability_keys = {
        "skill_instructions_persist",
        "ledger_persists",
        "agent_handles_persist",
        "result_notifications",
        "notification_auto_wake",
    }
    states = {"ACTIVE", "STOPPING", "OFF"}
    events = {
        "user", "coordinator", "yield", "delivery_batch", "worker_result", "notification_wake", "wait_timeout",
        "host_final", "task_complete", "compaction",
    }
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
        if (
            not required_capability_keys.issubset(capabilities)
            or set(capabilities) != required_capability_keys
            or not all(isinstance(value, bool) for value in capabilities.values())
        ):
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
        unstable_handback_pending = False
        unstable_question_turn: int | None = None
        unstable_handback_accepted = False
        completion_poll_count = 0
        poll_disclosure_count = 0
        ledger_generation = 1 if state != "OFF" else 0
        continuity_token_generation: int | None = None
        explicit_resume_required = False
        ledger_mutation_tokens = {
            "OFF_to_ACTIVE", "ACTIVE_to_STOPPING", "STOPPING_to_OFF", "revision_increment",
            "pending_close_confirmation", "cancel_pending_close", "stop_requested",
            "direct_close_confirmation", "nonterminal_handle_recorded", "exact_used_handle_accounting",
            "handle_lifecycle_unknown", "retain_exact_accounting", "controllable_workers_closed",
            "shared_writer_live", "tree_unstable", "terminal_writers_confirmed", "unstable_handoff",
            "queued_input", "HELD_to_QUEUED", "route_followup", "dispatch_or_queue",
            "dispatch", "dispatch_nonblocking", "dispatch_dependent_implementation",
            "dispatch_verification_wave", "delegate_after_local_phase", "bounded_wave",
            "ledger_generation_increment", "handle_accounting_changed", "tree_stability_changed",
            "queued_or_held_work_changed",
        }
        boundary_events = {"host_final", "task_complete", "compaction"}

        for step in transcript["steps"]:
            tokens = set(step["expect"])
            expectation_tokens.update(tokens)
            event = step["event"]
            turn = step["turn"]
            ledger_identity_before = (
                state, requirement_revision, pending_close, pending_close_revision,
                pending_close_turn, ledger_generation,
            )
            resume_required_at_start = explicit_resume_required
            issue_session_token = "session_token" in tokens
            generation_comparator_survives = capabilities["ledger_persists"]
            token_is_current = (
                generation_comparator_survives
                and continuity_token_generation is not None
                and continuity_token_generation == ledger_generation
            )
            handle_continuity = (
                capabilities["agent_handles_persist"]
                or "all_nonterminal_handles_controllable" in tokens
                or "zero_nonterminal_handles" in tokens
            )
            native_continuity = (
                capabilities["skill_instructions_persist"]
                and capabilities["ledger_persists"]
                and handle_continuity
            )

            if explicit_resume_required:
                explicit_resume = event == "user" and "explicit_skill_resume" in tokens
                bookkeeping_boundary = event in boundary_events and "host_bookkeeping_only" in tokens
                if not explicit_resume and not bookkeeping_boundary:
                    fail(f"continuation bypassed required explicit resume: {transcript_id}")

            authority_tokens = {"direct_close_confirmation", "stop_requested", "accept_unstable_handback"}
            if len(authority_tokens.intersection(tokens)) > 1:
                fail(f"one event cannot supply multiple authorizations: {transcript_id}")

            if "persistence_unverified" in tokens:
                required = {"treat_unverified_persistence_as_unavailable", "session_token"}
                if event != "coordinator" or not required.issubset(tokens):
                    fail(f"unverified persistence was treated as available: {transcript_id}")
            if "reinvoke_while_ACTIVE" in tokens:
                required = {
                    "preserve_state_scope_ledger_accounting", "accompanying_text_is_delta", "no_new_activation", "remain_ACTIVE"
                }
                forbidden = {"OFF_to_ACTIVE", "ACTIVE_to_STOPPING", "one_shot_scope", "same_turn_deactivation"}
                if event != "user" or state != "ACTIVE" or not required.issubset(tokens) or forbidden.intersection(tokens):
                    fail(f"re-invocation reset the active session: {transcript_id}")
            if "reinvoke_while_STOPPING" in tokens:
                required = {
                    "preserve_shutdown", "no_new_work_absorbed", "hand_back_after_OFF",
                    "no_new_activation", "remain_STOPPING",
                }
                forbidden = {"OFF_to_ACTIVE", "accompanying_text_is_delta", "dispatch", "ACTIVE_to_STOPPING"}
                if event != "user" or state != "STOPPING" or not required.issubset(tokens) or forbidden.intersection(tokens):
                    fail(f"re-invocation absorbed work during shutdown: {transcript_id}")
            if "work_item_stop" in tokens:
                required = {"no_session_stop_authorization", "no_closure_authorization", "remain_ACTIVE"}
                forbidden = {"stop_requested", "ACTIVE_to_STOPPING"}
                if event != "user" or state != "ACTIVE" or not required.issubset(tokens) or forbidden.intersection(tokens):
                    fail(f"work-item stop was treated as a Relay stop: {transcript_id}")
            if "zero_active_agents" in tokens:
                required = {"local_blocking_work", "explicit_ACTIVE_status", "no_deactivation", "remain_ACTIVE"}
                if event != "coordinator" or state != "ACTIVE" or not required.issubset(tokens):
                    fail(f"zero-agent local phase deactivated Relay: {transcript_id}")
            if "delegation_re_evaluated" in tokens:
                required = {"phase_boundary", "no_mandatory_fanout"}
                if event != "coordinator" or state != "ACTIVE" or not required.issubset(tokens):
                    fail(f"delegation was not re-evaluated at the phase boundary: {transcript_id}")
            if "no_distinct_leaf_work" in tokens:
                required = {"delegation_re_evaluated", "remain_local", "no_dispatch", "no_mandatory_fanout", "remain_ACTIVE"}
                if event != "coordinator" or state != "ACTIVE" or not required.issubset(tokens) or "dispatch" in tokens:
                    fail(f"no-leaf phase forced dispatch: {transcript_id}")
            if "zero_nonterminal_handles" in tokens:
                required = {"handle_continuity_vacuously_satisfied", "no_session_token"}
                if "nonterminal_handle_recorded" in tokens or issue_session_token or not required.issubset(tokens):
                    fail(f"zero-handle continuity was not treated vacuously: {transcript_id}")

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
                if event not in {"coordinator", "host_final"}:
                    fail(f"session token must be coordinator-authored: {transcript_id}")
                if not {"portable_resume_payload", "ledger_generation_in_token"}.issubset(tokens):
                    fail(f"session token lacks portable resume payload: {transcript_id}")
                if not capabilities["agent_handles_persist"] and "no_live_handle_at_yield" not in tokens:
                    fail(f"token yield may strand a live handle: {transcript_id}")
            if "explicit_skill_resume" in tokens:
                required = {"portable_resume_payload"}
                if event != "user" or state == "OFF" or not required.issubset(tokens):
                    fail(f"invalid explicit Relay resume: {transcript_id}")
                if "current_session_token" in tokens:
                    required = {"token_ledger_generation_match"}
                    if not token_is_current or not required.issubset(tokens) or "stale_session_token" in tokens:
                        fail(f"resume token is not current: {transcript_id}")
                    explicit_resume_required = False
                elif "stale_session_token" in tokens:
                    required = {
                        "token_ledger_generation_mismatch", "newer_generation_comparator_survives",
                        "stale_token_rejected",
                        "freeze_dispatch_and_writes", "no_restoration_claim", "remain_ACTIVE",
                    }
                    if (
                        not generation_comparator_survives
                        or continuity_token_generation is None
                        or token_is_current
                        or not required.issubset(tokens)
                    ):
                        fail(f"stale resume token was not rejected: {transcript_id}")
                elif "structurally_valid_session_token" in tokens:
                    required = {
                        "token_accepted_as_supplied_state", "relative_staleness_not_independently_proven",
                        "no_comparison_to_lost_state",
                    }
                    forbidden = {"current_session_token", "stale_session_token", "token_ledger_generation_match"}
                    if (
                        generation_comparator_survives
                        or continuity_token_generation is None
                        or not resume_required_at_start
                        or not required.issubset(tokens)
                        or forbidden.intersection(tokens)
                    ):
                        fail(f"portable token was not accepted strictly as supplied state: {transcript_id}")
                    explicit_resume_required = False
                else:
                    fail(f"explicit resume lacks token freshness result: {transcript_id}")
            if "OFF_to_ACTIVE" in tokens:
                if event != "user" or state != "OFF":
                    fail(f"invalid OFF to ACTIVE transition: {transcript_id}")
                state = "ACTIVE"
                requirement_revision = 1
            if "completion_candidate" in tokens:
                required = {"pending_close_confirmation", "close_question_ends_turn", "remain_ACTIVE"}
                if event not in {"coordinator", "host_final"} or state != "ACTIVE" or not required.issubset(tokens) or "ACTIVE_to_STOPPING" in tokens:
                    fail(f"completion candidate must remain ACTIVE: {transcript_id}")
            if "pending_close_confirmation" in tokens:
                required = {"final_audit", "ask_close", "close_question_revision_bound", "remain_ACTIVE"}
                if event not in {"coordinator", "host_final"} or state != "ACTIVE" or pending_close or not required.issubset(tokens):
                    fail(f"invalid close question: {transcript_id}")
                pending_close = True
                pending_close_revision = requirement_revision
                pending_close_turn = turn
                if not capabilities["skill_instructions_persist"] or not capabilities["ledger_persists"]:
                    fallback = {"session_token", "pending_close_and_audited_revision_in_token"}
                    if not fallback.issubset(tokens):
                        fail(f"pending close is not persisted: {transcript_id}")
            if "retain_pending_close_question" in tokens:
                required = {
                    "pending_close_identity_preserved", "no_duplicate_completion_candidate",
                    "no_duplicate_close_question", "remain_ACTIVE",
                }
                forbidden = {"completion_candidate", "ask_close", "pending_close_confirmation"}
                if event != "coordinator" or state != "ACTIVE" or not pending_close or not required.issubset(tokens) or forbidden.intersection(tokens):
                    fail(f"pending close question was duplicated or replaced: {transcript_id}")
            if "ambiguous_or_conditional_close_reply" in tokens:
                required = {"no_closure_authorization", "remain_ACTIVE"}
                if event != "user" or state != "ACTIVE" or not pending_close or turn <= pending_close_turn or not required.issubset(tokens):
                    fail(f"ambiguous close reply was accepted: {transcript_id}")
                close_authorization = None
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

            if "ledger_generation_increment" in tokens:
                required = {"handle_accounting_changed", "tree_stability_changed", "queued_or_held_work_changed"}
                if event != "coordinator" or not required.issubset(tokens):
                    fail(f"ledger generation increment lacks mutable-state coverage: {transcript_id}")
            if ledger_mutation_tokens.intersection(tokens):
                ledger_generation += 1
            if issue_session_token:
                continuity_token_generation = ledger_generation

            ledger_identity_after = (
                state, requirement_revision, pending_close, pending_close_revision,
                pending_close_turn, ledger_generation,
            )
            post_response_token_is_current = (
                generation_comparator_survives
                and continuity_token_generation is not None
                and continuity_token_generation == ledger_generation
            )
            post_response_token_matches_ledger = (
                continuity_token_generation is not None
                and continuity_token_generation == ledger_generation
            )

            if resume_required_at_start and event in boundary_events:
                required = {
                    "host_bookkeeping_only", "execution_frozen", "continuation_requires_explicit_resume",
                    "freeze_dispatch_and_writes", "no_restoration_claim",
                }
                forbidden = ledger_mutation_tokens | {
                    "session_token", "rehydrate", "dispatch", "ACTIVE_to_STOPPING", "STOPPING_to_OFF",
                }
                if (
                    ledger_identity_after != ledger_identity_before
                    or not required.issubset(tokens)
                    or forbidden.intersection(tokens)
                ):
                    fail(f"host bookkeeping executed while explicit resume was required: {transcript_id}")

            if event in boundary_events:
                if "lifecycle_neutral" not in tokens:
                    fail(f"host boundary is not lifecycle-neutral: {transcript_id}")
                if state != ledger_identity_before[0] or {"ACTIVE_to_STOPPING", "STOPPING_to_OFF", "OFF"}.intersection(tokens):
                    fail(f"host boundary changed Relay lifecycle: {transcript_id}")
                if state == "ACTIVE" and "remain_ACTIVE" not in tokens:
                    fail(f"host boundary lost ACTIVE state: {transcript_id}")
                if state == "STOPPING" and "remain_STOPPING" not in tokens:
                    fail(f"host boundary lost STOPPING state: {transcript_id}")
                if event == "host_final" and "final_answer_boundary" not in tokens:
                    fail(f"host final response lacks boundary accounting: {transcript_id}")
                if event == "task_complete" and "task_complete_boundary" not in tokens:
                    fail(f"task_complete lacks boundary accounting: {transcript_id}")
                if event == "compaction":
                    required = {"compaction_boundary", "never_infer_OFF"}
                    if not required.issubset(tokens):
                        fail(f"compaction inferred a lifecycle transition: {transcript_id}")
                if event == "host_final" and not native_continuity and (
                    issue_session_token or ledger_mutation_tokens.intersection(tokens)
                ) and "post_response_boundary_freshness" not in tokens:
                    fail(f"host final freshness was checked before response mutations: {transcript_id}")

                if native_continuity:
                    if "native_continuity_verified" not in tokens:
                        fail(f"host boundary lacks verified native continuity: {transcript_id}")
                elif (
                    generation_comparator_survives
                    and continuity_token_generation is not None
                    and not post_response_token_is_current
                ):
                    required = {"stale_token_rejected", "freeze_dispatch_and_writes", "no_restoration_claim"}
                    if not required.issubset(tokens):
                        fail(f"host boundary ignored a comparator-proven stale token: {transcript_id}")
                elif continuity_token_generation is not None:
                    required = {
                        "continuation_requires_explicit_resume", "freeze_dispatch_and_writes",
                        "no_restoration_claim",
                    }
                    if not required.issubset(tokens):
                        fail(f"host boundary used a token without explicit resume: {transcript_id}")
                    if event == "compaction" and "preserve_state_scope_ledger_accounting" not in tokens:
                        fail(f"compaction lost current token state: {transcript_id}")
                else:
                    required = {
                        "continuity_loss", "freeze_dispatch_and_writes", "continuity_loss_disclosed",
                        "no_restoration_claim",
                    }
                    if not required.issubset(tokens):
                        fail(f"host boundary claimed unavailable continuity: {transcript_id}")

            if event == "yield" and state != "OFF" and not (
                capabilities["skill_instructions_persist"] and capabilities["ledger_persists"]
            ):
                if not post_response_token_matches_ledger:
                    fail(f"non-OFF yield lacks a structurally current continuity token: {transcript_id}")
                explicit_resume_required = True
            if event in boundary_events and not native_continuity:
                explicit_resume_required = True
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
        "historical_normal_completion_remains_active",
        "host_final_and_task_complete_preserve_active",
        "compaction_preserves_active_session",
        "compaction_without_continuity_freezes_work",
        "stale_token_after_revision_is_rejected",
        "stale_token_after_ledger_generation_change",
        "non_native_host_final_then_task_complete_resumes",
        "native_continuity_with_zero_handles",
        "reinvocation_while_active_is_a_delta",
        "reinvocation_while_stopping_preserves_shutdown",
        "pending_close_question_is_not_duplicated",
        "workstream_stop_does_not_stop_relay",
        "local_phase_rechecks_delegation",
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
    for event in (
        "yield", "delivery_batch", "worker_result", "notification_wake", "wait_timeout",
        "host_final", "task_complete", "compaction",
    ):
        if event not in event_kinds:
            fail(f"transcripts are missing {event!r} event")
    for token in (
        "one_shot_scope",
        "default_live_scope",
        "same_turn_deactivation",
        "no_close_question",
        "no_cross_turn_persistence",
        "native_one_shot_completion_polling",
        "one_shot_wait_opt_in_exception",
        "same_coordinator_turn",
        "bound_to_originating_message_and_final_response",
        "no_arbitrary_poll_deadline",
        "poll_timeout_is_scheduling_tick",
        "poll_timeout_not_task_deadline",
        "healthy_workers_not_interrupted",
        "no_deactivation_on_interval_timeout",
        "authorized_dependent_work_remains",
        "dispatch_authorized_dependent_work",
        "stop_for_terminal_results_and_synthesis",
        "stop_for_user_cancel_or_redirect",
        "stop_for_user_specified_overall_limit",
        "stop_for_genuine_runtime_blocker",
        "workers_terminal",
        "synthesis_complete",
        "settle_controllable_workers_before_final_response",
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
        "no_shell_sleep",
        "no_busy_poll",
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
        "historical_normal_completion",
        "no_self_close",
        "final_answer_boundary",
        "task_complete_boundary",
        "lifecycle_neutral",
        "compaction_boundary",
        "preserve_state_scope_ledger_accounting",
        "native_continuity_verified",
        "continuation_requires_explicit_resume",
        "continuity_loss",
        "continuity_loss_disclosed",
        "freeze_dispatch_and_writes",
        "no_restoration_claim",
        "never_infer_OFF",
        "persistence_unverified",
        "treat_unverified_persistence_as_unavailable",
        "ledger_generation_in_token",
        "structurally_valid_session_token",
        "token_accepted_as_supplied_state",
        "relative_staleness_not_independently_proven",
        "no_comparison_to_lost_state",
        "stale_session_token",
        "token_ledger_generation_mismatch",
        "newer_generation_comparator_survives",
        "stale_token_rejected",
        "post_response_boundary_freshness",
        "host_bookkeeping_only",
        "execution_frozen",
        "zero_nonterminal_handles",
        "handle_continuity_vacuously_satisfied",
        "no_session_token",
        "ledger_generation_increment",
        "handle_accounting_changed",
        "tree_stability_changed",
        "queued_or_held_work_changed",
        "reinvoke_while_ACTIVE",
        "reinvoke_while_STOPPING",
        "accompanying_text_is_delta",
        "no_new_work_absorbed",
        "hand_back_after_OFF",
        "retain_pending_close_question",
        "pending_close_identity_preserved",
        "no_duplicate_completion_candidate",
        "no_duplicate_close_question",
        "work_item_stop",
        "no_session_stop_authorization",
        "explicit_session_stop_still_supported",
        "zero_active_agents",
        "local_blocking_work",
        "explicit_ACTIVE_status",
        "delegation_re_evaluated",
        "no_distinct_leaf_work",
        "remain_local",
        "no_dispatch",
        "no_mandatory_fanout",
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
