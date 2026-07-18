#!/usr/bin/env python3
"""Validate Relay Orchestra without third-party packages."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "relay-orchestra"
SKILL = SKILL_DIR / "SKILL.md"


def fail(message: str) -> None:
    raise ValueError(message)


def canonical_owned_path(value: object, root: Path = ROOT) -> str:
    """Return a stable logical identity for one exact repository file path."""
    if not isinstance(value, str) or not value or value != value.strip():
        fail("owned path must be a non-empty canonical string")
    if (
        "\0" in value
        or "\\" in value
        or ":" in value
        or any(ord(character) < 32 or character in '<>"|' for character in value)
        or re.match(r"^[A-Za-z]:", value)
        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value)
        or any(character in value for character in "*?[")
    ):
        fail(f"owned path is not an exact POSIX file path: {value!r}")

    path = PurePosixPath(value)
    windows_reserved = re.compile(r"(?i)^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?$")
    if (
        path.is_absolute()
        or value != path.as_posix()
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or any(part.endswith((".", " ")) for part in path.parts)
        or any(windows_reserved.fullmatch(part) for part in path.parts)
    ):
        fail(f"owned path must be canonical and repository-relative: {value!r}")

    root = root.resolve()
    resolved = (root / Path(*path.parts)).resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        fail(f"owned path resolves outside the repository: {value!r}")
    if resolved.is_dir():
        fail(f"owned path must name a file, not a directory: {value!r}")

    def portable_key(candidate: Path) -> str:
        return unicodedata.normalize("NFC", candidate.as_posix()).casefold()

    identities = {portable_key(relative)}
    if resolved.exists():
        stat = resolved.stat()
        if stat.st_nlink > 1:
            for candidate in root.rglob("*"):
                try:
                    candidate_stat = candidate.stat()
                except OSError:
                    continue
                if (candidate_stat.st_dev, candidate_stat.st_ino) != (stat.st_dev, stat.st_ino):
                    continue
                try:
                    candidate_relative = candidate.resolve().relative_to(root)
                except (OSError, ValueError):
                    continue
                identities.add(portable_key(candidate_relative))

    # The minimum portable spelling collapses hardlinks while NFC and case-folding
    # also collapse aliases that differ only across filesystem conventions.
    return f"path:{min(identities)}"


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


def validate_writer_dispatches(transcript: dict[str, object]) -> None:
    transcript_id = transcript["id"]
    steps = transcript["steps"]
    dispatches = transcript.get("writer_dispatches")
    expected_writer_ids_by_step: dict[int, set[str]] = {}
    for index, step in enumerate(steps, start=1):
        if "writer_dispatch" not in step["expect"]:
            if "writer_ids" in step:
                fail(f"writer ids appear without a writer dispatch: {transcript_id}")
            continue
        writer_ids = step.get("writer_ids")
        if (
            not isinstance(writer_ids, list)
            or not writer_ids
            or len(set(writer_ids)) != len(writer_ids)
            or not all(isinstance(writer_id, str) and writer_id for writer_id in writer_ids)
        ):
            fail(f"writer dispatch step lacks exact writer ids: {transcript_id}")
        expected_writer_ids_by_step[index] = set(writer_ids)
    if dispatches is None:
        if expected_writer_ids_by_step:
            fail(f"writer dispatch lacks structural ownership data: {transcript_id}")
        return
    if not isinstance(dispatches, list) or not dispatches:
        fail(f"writer_dispatches must be a non-empty list: {transcript_id}")

    required = {
        "id", "step", "owned_paths", "edit_scope", "interfaces_invariants",
        "isolation", "after_terminal_and_audited",
    }
    allowed = required | {"checkout_id", "base_revision", "overlap_group"}
    by_id: dict[str, dict[str, object]] = {}
    canonical_paths_by_id: dict[str, set[str]] = {}
    checkout_ids: set[str] = set()
    actual_writer_ids_by_step: dict[int, set[str]] = {}
    all_tokens_by_step = [set(step["expect"]) for step in steps]
    for dispatch in dispatches:
        if not isinstance(dispatch, dict) or not required.issubset(dispatch) or not set(dispatch).issubset(allowed):
            fail(f"invalid writer dispatch: {transcript_id}")
        writer_id = dispatch["id"]
        if not isinstance(writer_id, str) or not writer_id or writer_id in by_id:
            fail(f"invalid or duplicate writer id: {transcript_id}")
        step_number = dispatch["step"]
        if not isinstance(step_number, int) or not 1 <= step_number <= len(steps):
            fail(f"invalid writer dispatch step: {transcript_id}")
        step = steps[step_number - 1]
        if step["event"] != "coordinator" or "writer_dispatch" not in step["expect"]:
            fail(f"writer dispatch step is not coordinator-authored: {transcript_id}")
        owned_paths = dispatch["owned_paths"]
        interfaces = dispatch["interfaces_invariants"]
        dependencies = dispatch["after_terminal_and_audited"]
        if not isinstance(owned_paths, list) or not owned_paths:
            fail(f"writer dispatch lacks exact owned paths: {transcript_id}")
        canonical_paths = {canonical_owned_path(path) for path in owned_paths}
        if len(canonical_paths) != len(owned_paths):
            fail(f"writer dispatch contains aliased or duplicate owned paths: {transcript_id}")
        if (
            not isinstance(interfaces, list)
            or not interfaces
            or not all(isinstance(contract, str) and contract for contract in interfaces)
        ):
            fail(f"writer dispatch lacks interfaces or invariants: {transcript_id}")
        if dispatch["isolation"] not in {"shared", "worktree"}:
            fail(f"invalid writer isolation: {transcript_id}")
        if dispatch["isolation"] == "worktree":
            if not transcript["capabilities"]["isolated_writer_checkouts"]:
                fail(f"worktree writer dispatched without isolation capability: {transcript_id}")
            if not all(isinstance(dispatch.get(key), str) and dispatch[key] for key in ("checkout_id", "base_revision")):
                fail(f"worktree writer lacks checkout id or base revision: {transcript_id}")
            if dispatch["checkout_id"] in checkout_ids:
                fail(f"worktree writers share a checkout id: {transcript_id}")
            checkout_ids.add(dispatch["checkout_id"])
        elif "checkout_id" in dispatch:
            fail(f"shared writer claims a checkout id: {transcript_id}")
        edit_scope = dispatch["edit_scope"]
        if (
            not isinstance(edit_scope, list)
            or not edit_scope
            or not all(isinstance(item, str) and item for item in edit_scope)
        ):
            fail(f"writer has an invalid logical edit scope: {transcript_id}")
        overlap_group = dispatch.get("overlap_group")
        if overlap_group is not None and (
            dispatch["isolation"] != "worktree"
            or not isinstance(overlap_group, str)
            or not overlap_group
        ):
            fail(f"controlled-overlap writer lacks isolated scope data: {transcript_id}")
        if not isinstance(dependencies, list) or not all(isinstance(item, str) and item for item in dependencies):
            fail(f"invalid writer serialization dependencies: {transcript_id}")
        by_id[writer_id] = dispatch
        canonical_paths_by_id[writer_id] = canonical_paths
        actual_writer_ids_by_step.setdefault(step_number, set()).add(writer_id)

    if actual_writer_ids_by_step != expected_writer_ids_by_step:
        fail(f"writer dispatch ids and structural records differ: {transcript_id}")

    for writer_id, dispatch in by_id.items():
        step_number = dispatch["step"]
        prior_tokens = set().union(*all_tokens_by_step[:step_number - 1])
        if "predispatch_contracts_recorded" not in prior_tokens:
            fail(f"writer ownership or contracts were not recorded before dispatch: {transcript_id}")
        for dependency in dispatch["after_terminal_and_audited"]:
            if dependency == writer_id or dependency not in by_id:
                fail(f"invalid writer serialization dependency: {transcript_id}")
            if by_id[dependency]["step"] >= step_number:
                fail(f"serialized writer was not dispatched later: {transcript_id}")
            dependency_dispatch_step = by_id[dependency]["step"]
            terminal_indexes = [
                index
                for index, prior in enumerate(steps[:step_number - 1], start=1)
                if index > dependency_dispatch_step
                and prior["event"] in {"worker_result", "notification_wake", "delivery_batch"}
                and f"{dependency}_terminal" in prior["expect"]
            ]
            audit_indexes = [
                index
                for index, prior in enumerate(steps[:step_number - 1], start=1)
                if prior["event"] == "coordinator"
                and f"{dependency}_audited" in prior["expect"]
            ]
            if not any(terminal < audit for terminal in terminal_indexes for audit in audit_indexes):
                fail(f"serialized writer started before terminal audit: {transcript_id}")
        if dispatch["isolation"] == "worktree":
            approval_steps = [
                index
                for index, step in enumerate(steps[:step_number - 1], start=1)
                if step["event"] == "user" and "worktrees_approved" in step["expect"]
            ]
            if not approval_steps:
                fail(f"worktree writer dispatched without prior approval: {transcript_id}")
            creation_steps = [
                index
                for index, step in enumerate(steps[:step_number], start=1)
                if step["event"] == "coordinator" and "worktrees_created_with_approval" in step["expect"]
            ]
            if not any(approval < creation for approval in approval_steps for creation in creation_steps):
                fail(f"worktree creation did not follow user approval: {transcript_id}")

    def depends_on(writer_id: str, dependency: str, seen: set[str] | None = None) -> bool:
        if seen is None:
            seen = set()
        if writer_id in seen:
            fail(f"writer serialization dependency cycle: {transcript_id}")
        seen.add(writer_id)
        direct = by_id[writer_id]["after_terminal_and_audited"]
        return dependency in direct or any(depends_on(item, dependency, seen.copy()) for item in direct)

    overlap_groups = transcript.get("overlap_groups", [])
    if not isinstance(overlap_groups, list):
        fail(f"overlap_groups must be a list: {transcript_id}")
    groups_by_id: dict[str, dict[str, object]] = {}
    covered_overlap_keys: set[tuple[str, str, str]] = set()
    group_required = {
        "id", "writer_ids", "paths", "base_revision", "combined_intent",
        "combined_interfaces_invariants", "integration_order", "resolver",
    }
    for group in overlap_groups:
        if not isinstance(group, dict) or set(group) != group_required:
            fail(f"invalid controlled-overlap group: {transcript_id}")
        group_id = group["id"]
        member_ids = group["writer_ids"]
        paths = group["paths"]
        integration_order = group["integration_order"]
        combined_intent = group["combined_intent"]
        combined_contracts = group["combined_interfaces_invariants"]
        if (
            not isinstance(group_id, str)
            or not group_id
            or group_id in groups_by_id
            or not isinstance(member_ids, list)
            or len(member_ids) < 2
            or len(set(member_ids)) != len(member_ids)
            or not all(isinstance(item, str) and item in by_id for item in member_ids)
            or not isinstance(integration_order, list)
            or len(integration_order) != len(member_ids)
            or set(integration_order) != set(member_ids)
            or not isinstance(group["resolver"], str)
            or not group["resolver"]
            or (group["resolver"] != "coordinator" and group["resolver"] not in by_id)
            or not isinstance(group["base_revision"], str)
            or not group["base_revision"]
            or not isinstance(combined_intent, list)
            or not combined_intent
            or not all(isinstance(item, str) and item for item in combined_intent)
            or not isinstance(combined_contracts, list)
            or not combined_contracts
            or not all(isinstance(item, str) and item for item in combined_contracts)
            or not isinstance(paths, list)
            or not paths
        ):
            fail(f"invalid controlled-overlap contract: {transcript_id}")
        canonical_group_paths = {canonical_owned_path(path) for path in paths}
        if len(canonical_group_paths) != len(paths):
            fail(f"controlled-overlap group contains aliased paths: {transcript_id}")
        resolver = group["resolver"]
        if resolver != "coordinator" and not canonical_group_paths.issubset(canonical_paths_by_id[resolver]):
            fail(f"controlled-overlap resolver does not own the conflict paths: {transcript_id}")
        for writer_id in member_ids:
            dispatch = by_id[writer_id]
            if (
                dispatch["isolation"] != "worktree"
                or dispatch.get("overlap_group") != group_id
                or dispatch.get("base_revision") != group["base_revision"]
            ):
                fail(f"controlled-overlap members lack distinct aligned worktrees: {transcript_id}")
        for path in canonical_group_paths:
            owners = [writer_id for writer_id in member_ids if path in canonical_paths_by_id[writer_id]]
            if len(owners) < 2:
                fail(f"controlled-overlap path is not shared by its members: {transcript_id}")
            for first_index, first_id in enumerate(owners):
                for second_id in owners[first_index + 1:]:
                    key = tuple(sorted((first_id, second_id))) + (path,)
                    if key in covered_overlap_keys:
                        fail(f"concurrent overlap belongs to multiple groups: {transcript_id}")
                    covered_overlap_keys.add(key)
        first_dispatch = min(by_id[writer_id]["step"] for writer_id in member_ids)
        prior_tokens = set().union(*all_tokens_by_step[:first_dispatch - 1])
        if not {
            "controlled_overlap_planned", "overlap_contract_recorded",
            "combined_contract_recorded",
        }.issubset(prior_tokens):
            fail(f"controlled overlap was not recorded before dispatch: {transcript_id}")
        groups_by_id[group_id] = group

    for writer_id, dispatch in by_id.items():
        group_id = dispatch.get("overlap_group")
        if group_id is not None and group_id not in groups_by_id:
            fail(f"writer names an unknown controlled-overlap group: {transcript_id}")

    writer_ids = list(by_id)

    def isolated_predecessor_settled_before_shared(
        isolated_id: str, shared_dispatch: dict[str, object]
    ) -> bool:
        prior_steps = steps[:shared_dispatch["step"] - 1]
        isolated_dispatch_step = by_id[isolated_id]["step"]
        terminal_indexes = [
            index
            for index, step in enumerate(prior_steps, start=1)
            if index > isolated_dispatch_step
            and step["event"] in {"worker_result", "notification_wake", "delivery_batch"}
            and f"{isolated_id}_terminal" in step["expect"]
        ]
        audit_indexes = [
            index
            for index, step in enumerate(prior_steps, start=1)
            if step["event"] == "coordinator"
            and f"{isolated_id}_audited" in step["expect"]
        ]
        integrated_indexes = [
            index
            for index, step in enumerate(prior_steps, start=1)
            if step["event"] == "coordinator"
            and INTEGRATION_TOKENS.intersection(step["expect"])
            and step.get("integrated_writer_ids") == [isolated_id]
        ]
        resolution_tokens = {
            f"{isolated_id}_abandoned",
            f"{isolated_id}_reconciled_into_shared_base",
        }
        resolution_indexes = [
            index
            for index, step in enumerate(prior_steps, start=1)
            if step["event"] == "coordinator"
            and resolution_tokens.intersection(step["expect"])
        ]
        settlement_indexes = integrated_indexes + resolution_indexes
        return any(
            terminal < audit < settlement
            for terminal in terminal_indexes
            for audit in audit_indexes
            for settlement in settlement_indexes
        )

    for index, writer_id in enumerate(writer_ids):
        for other_id in writer_ids[index + 1:]:
            ordered = depends_on(writer_id, other_id) or depends_on(other_id, writer_id)
            first = by_id[writer_id]
            second = by_id[other_id]
            if not ordered and {first["isolation"], second["isolation"]} != {"worktree"}:
                fail(f"potentially concurrent writers must use approved worktrees: {transcript_id}")
            overlap = canonical_paths_by_id[writer_id].intersection(canonical_paths_by_id[other_id])
            if overlap and depends_on(other_id, writer_id) and first["isolation"] == "worktree" and second["isolation"] == "shared":
                if not isolated_predecessor_settled_before_shared(writer_id, second):
                    fail(f"shared writer starts over a pending isolated patch: {transcript_id}")
            if overlap and depends_on(writer_id, other_id) and second["isolation"] == "worktree" and first["isolation"] == "shared":
                if not isolated_predecessor_settled_before_shared(other_id, first):
                    fail(f"shared writer starts over a pending isolated patch: {transcript_id}")
            if not ordered and overlap:
                first_group = first.get("overlap_group")
                second_group = second.get("overlap_group")
                if not first_group or first_group != second_group:
                    fail(f"concurrent writers have an unplanned path overlap: {transcript_id}")
                for path in overlap:
                    key = tuple(sorted((writer_id, other_id))) + (path,)
                    if key not in covered_overlap_keys:
                        fail(f"concurrent writer overlap is missing from its contract: {transcript_id}")


def validate_writer_continuation(transcript: dict[str, object]) -> None:
    capabilities = transcript["capabilities"]
    steps = transcript["steps"]
    for index, step in enumerate(steps):
        tokens = set(step["expect"])
        if "writer_dispatch" not in tokens:
            continue
        if step["event"] != "coordinator":
            fail(f"writer dispatch is not coordinator-authored: {transcript['id']}")
        if transcript["scope"] == "one_shot":
            if "native_one_shot_completion_polling" not in tokens:
                fail(f"one-shot writer dispatch lacks native polling continuation: {transcript['id']}")
            continue
        if capabilities["notification_auto_wake"]:
            required = {"dispatch_nonblocking", "result_notifications", "notification_auto_wake", "yield_main_turn"}
            future_wake = any(
                later["event"] == "notification_wake"
                and {"worker_result_delivered", "resume_natively"}.issubset(later["expect"])
                for later in steps[index + 1:]
            )
            if not required.issubset(tokens) or not future_wake:
                fail(f"writer dispatch lacks automatic-wake continuation: {transcript['id']}")
        elif "native_completion_polling" not in tokens:
            fail(f"writer dispatch lacks native polling continuation: {transcript['id']}")


def validate_unavailable_worktrees(transcripts: list[dict[str, object]]) -> None:
    try:
        transcript = next(
            item for item in transcripts
            if item["id"] == "unavailable_worktrees_serialize_writers"
        )
    except StopIteration:
        fail("missing unavailable-worktrees transcript")
    tokens = {token for step in transcript["steps"] for token in step["expect"]}
    required = {
        "worktrees_unavailable", "serialization_fallback", "shared_tree_serial_writers",
        "writer_b_after_writer_a_terminal_and_audited", "no_concurrent_shared_writers",
    }
    if transcript["capabilities"]["isolated_writer_checkouts"] or not required.issubset(tokens):
        fail("unavailable-worktrees transcript must prove serialized fallback")


def validate_direct_same_path_controlled_overlap(transcripts: list[dict[str, object]]) -> None:
    try:
        transcript = next(
            item for item in transcripts
            if item["id"] == "direct_same_path_concurrency_uses_controlled_overlap"
        )
    except StopIteration:
        fail("missing direct same-path concurrency transcript")

    tokens = {token for step in transcript["steps"] for token in step["expect"]}
    required = {
        "direct_same_path_concurrency_requested",
        "ownership_map_before_dispatch",
        "same_path_overlap_detected",
        "controlled_overlap_planned",
        "overlap_contract_recorded",
        "combined_contract_recorded",
        "one_checkout_per_writer",
        "shared_base_revision",
        "concurrent_same_path_writers_dispatched",
        "three_way_reconcile_against_updated_base",
        "combined_intent_preserved",
        "combined_contracts_preserved",
        "combined_contracts_validated",
        "overlap_group_verified",
    }
    dispatches = transcript.get("writer_dispatches", [])
    if not transcript["capabilities"]["isolated_writer_checkouts"] or not required.issubset(tokens):
        fail("direct same-path request must use controlled worktree overlap")
    if len(dispatches) != 2:
        fail("direct same-path request must account for exactly two writer dispatches")
    first, second = dispatches
    if not {
        canonical_owned_path(path) for path in first["owned_paths"]
    }.intersection(canonical_owned_path(path) for path in second["owned_paths"]):
        fail("direct same-path transcript does not model an owned-path collision")
    if (
        first["isolation"] != "worktree"
        or second["isolation"] != "worktree"
        or first.get("overlap_group") != second.get("overlap_group")
        or first["step"] != second["step"]
        or first["after_terminal_and_audited"]
        or second["after_terminal_and_audited"]
    ):
        fail("direct same-path writers were not structurally concurrent and isolated")
    validate_writer_integrations(transcript)


def validate_shared_same_path_serialized(transcripts: list[dict[str, object]]) -> None:
    try:
        transcript = next(
            item for item in transcripts if item["id"] == "shared_tree_same_path_serializes"
        )
    except StopIteration:
        fail("missing shared-tree same-path serialization transcript")
    tokens = {token for step in transcript["steps"] for token in step["expect"]}
    required = {
        "shared_tree_overlap_forbidden", "same_path_work_serialized",
        "writer_b_after_writer_a_terminal_and_audited", "no_concurrent_shared_writers",
    }
    dispatches = transcript.get("writer_dispatches", [])
    if len(dispatches) != 2 or not required.issubset(tokens):
        fail("shared-tree same-path work must be structurally serialized")
    first, second = dispatches
    if (
        first["isolation"] != "shared"
        or second["isolation"] != "shared"
        or first["id"] not in second["after_terminal_and_audited"]
        or not set(first["owned_paths"]).intersection(second["owned_paths"])
    ):
        fail("shared-tree same-path writers are not safely serialized")


def validate_verified_native_compaction(transcripts: list[dict[str, object]]) -> None:
    try:
        transcript = next(
            item for item in transcripts
            if item["id"] == "verified_native_compaction_continues_without_reinvocation"
        )
    except StopIteration:
        fail("missing verified-native-compaction transcript")

    capabilities = transcript["capabilities"]
    if not all(
        capabilities[key]
        for key in ("skill_instructions_persist", "ledger_persists", "agent_handles_persist")
    ):
        fail("verified native compaction must preserve skill, ledger, and handle continuity")

    steps = transcript["steps"]
    tokens = {token for step in steps for token in step["expect"]}
    if {"session_token", "explicit_skill_resume"}.intersection(tokens):
        fail("verified native compaction must not require portable resume")

    compact_indexes = [index for index, step in enumerate(steps) if step["event"] == "compaction"]
    if len(compact_indexes) != 1:
        fail("verified native compaction transcript must contain exactly one compaction event")
    compact_index = compact_indexes[0]
    compact_tokens = set(steps[compact_index]["expect"])
    boundary_required = {
        "manual_compaction", "compaction_boundary", "lifecycle_neutral",
        "native_continuity_verified", "skill_instructions_preserved", "ledger_preserved",
        "pending_close_identity_preserved", "canary_preserved", "no_stop_authorization",
        "never_infer_OFF", "remain_ACTIVE",
    }
    if not boundary_required.issubset(compact_tokens):
        fail("verified native compaction boundary lacks continuity evidence")

    recorded_indexes = [
        index for index, step in enumerate(steps)
        if "canary_recorded" in step["expect"]
    ]
    if (
        len(recorded_indexes) != 1
        or recorded_indexes[0] >= compact_index
        or steps[recorded_indexes[0]]["event"] != "coordinator"
    ):
        fail("compaction canary must be recorded exactly once before compaction")

    canary_id = steps[recorded_indexes[0]].get("canary_id")
    if not isinstance(canary_id, str) or not canary_id:
        fail("recorded compaction canary lacks an identity")
    if steps[compact_index].get("canary_id") != canary_id:
        fail("compaction boundary did not preserve the recorded canary identity")

    related_user_indexes = [
        index for index, step in enumerate(steps[compact_index + 1:], start=compact_index + 1)
        if step["event"] == "user"
        and {
            "related_delta_after_compaction", "no_explicit_skill_resume_needed",
            "cancel_pending_close", "no_closure_authorization", "remain_ACTIVE",
        }.issubset(step["expect"])
    ]
    if not related_user_indexes:
        fail("verified native compaction lacks a later ordinary related user delta")

    first_user_index = related_user_indexes[0]
    coordinator_required = {
        "continue_same_session", "no_new_activation", "canary_verified",
        "execute_authorized_read_only_check", "ACTIVE",
    }
    verification_indexes = [
        index for index, step in enumerate(steps)
        if "canary_verified" in step["expect"]
    ]
    if len(verification_indexes) != 1:
        fail("compaction canary must be verified exactly once")
    verification_index = verification_indexes[0]
    verification_step = steps[verification_index]
    if (
        verification_index <= first_user_index
        or verification_step["event"] != "coordinator"
        or not coordinator_required.issubset(verification_step["expect"])
    ):
        fail("verified native compaction lacks ordered post-compaction verification")
    if verification_step.get("canary_id") != canary_id:
        fail("post-compaction verification used a different canary identity")


INTEGRATION_TOKENS = {
    "integrate_completed_work", "integrate_isolated_stream", "worktree_integrated",
    "integration_complete", "coordinator_integrates", "integration", "writer_integration",
}


def validate_writer_integrations(transcript: dict[str, object]) -> None:
    """Require one terminal, audited isolated writer per integration operation."""
    transcript_id = transcript["id"]
    steps = transcript["steps"]
    dispatches_by_id = {
        dispatch["id"]: dispatch for dispatch in transcript.get("writer_dispatches", [])
    }
    already_integrated: set[str] = set()
    integration_step_by_id: dict[str, int] = {}
    for index, step in enumerate(steps, start=1):
        markers = INTEGRATION_TOKENS.intersection(step["expect"])
        writer_ids = step.get("integrated_writer_ids")
        if not markers:
            if writer_ids is not None:
                fail(f"integrated writer ids appear without an integration operation: {transcript_id}")
            continue
        if (
            step["event"] != "coordinator"
            or not isinstance(writer_ids, list)
            or len(writer_ids) != 1
            or not isinstance(writer_ids[0], str)
            or not writer_ids[0]
        ):
            fail(f"integration must name exactly one writer: {transcript_id}")

        writer_id = writer_ids[0]
        dispatch = dispatches_by_id.get(writer_id)
        if (
            dispatch is None
            or dispatch["isolation"] != "worktree"
            or dispatch["step"] >= index
            or writer_id in already_integrated
        ):
            fail(f"integration names an invalid isolated writer: {transcript_id}")
        prior_tokens = set().union(*(set(prior["expect"]) for prior in steps[:index - 1]))
        if {
            f"{writer_id}_abandoned", f"{writer_id}_reconciled_into_shared_base",
        }.intersection(prior_tokens):
            fail(f"settled isolated writer was integrated again: {transcript_id}")

        terminal_token = f"{writer_id}_terminal"
        audited_token = f"{writer_id}_audited"
        terminal_indexes = [
            prior_index
            for prior_index, prior in enumerate(steps[:index - 1], start=1)
            if dispatch["step"] < prior_index
            and prior["event"] in {"worker_result", "notification_wake", "delivery_batch"}
            and terminal_token in prior["expect"]
        ]
        audit_indexes = [
            prior_index
            for prior_index, prior in enumerate(steps[:index - 1], start=1)
            if prior["event"] == "coordinator" and audited_token in prior["expect"]
        ]
        if not any(terminal < audit for terminal in terminal_indexes for audit in audit_indexes):
            fail(f"writer integrated before terminal result and coordinator audit: {transcript_id}")
        already_integrated.add(writer_id)
        integration_step_by_id[writer_id] = index

    for group in transcript.get("overlap_groups", []):
        order = group["integration_order"]
        integrated_order = [writer_id for writer_id in order if writer_id in integration_step_by_id]
        actual_order = [
            writer_id for writer_id, _ in sorted(
                integration_step_by_id.items(), key=lambda item: item[1]
            ) if writer_id in set(order)
        ]
        if integrated_order != order[:len(integrated_order)] or actual_order != integrated_order:
            fail(f"controlled-overlap integration order was not preserved: {transcript_id}")
        for position, writer_id in enumerate(integrated_order):
            step = steps[integration_step_by_id[writer_id] - 1]
            required = {
                "patch_applied_from_recorded_base",
                "no_whole_file_overwrite",
            }
            if position > 0:
                required.update({
                    "three_way_reconcile_against_updated_base",
                    "controlled_overlap_reconciled",
                    "combined_intent_preserved",
                    "combined_contracts_preserved",
                    "clean_merge_not_semantic_proof",
                })
            if not required.issubset(step["expect"]):
                fail(f"later controlled-overlap integration lacks reconciliation evidence: {transcript_id}")
        if len(integrated_order) == len(order):
            last_integration = max(integration_step_by_id[writer_id] for writer_id in order)
            if not any(
                index > last_integration
                and step["event"] == "coordinator"
                and {
                    "overlap_group_verified", "combined_diff_audited",
                    "combined_contracts_validated", "targeted_tests_pass",
                }.issubset(step["expect"])
                for index, step in enumerate(steps, start=1)
            ):
                fail(f"completed controlled-overlap group lacks combined verification: {transcript_id}")


def validate_dirty_path_flow(transcript: dict[str, object]) -> None:
    transcript_id = transcript["id"]
    steps = transcript["steps"]
    validate_writer_integrations(transcript)
    conflicts = transcript.get("dirty_conflicts")
    block_required = {
        "dirty_tree_detected", "unattributed_dirty_paths_user_owned",
        "shared_writer_overlap_blocked", "dirty_integration_blocked",
        "narrow_ownership_or_approved_worktree", "no_silent_worktree",
    }
    block_markers = {
        "dirty_tree_detected", "unattributed_dirty_paths_user_owned",
        "shared_writer_overlap_blocked", "dirty_integration_blocked",
        "narrow_ownership_or_approved_worktree",
    }
    block_steps: set[int] = set()
    for index, step in enumerate(steps, start=1):
        tokens = set(step["expect"])
        if block_markers.intersection(tokens):
            scope_required = {"remain_ACTIVE"} if transcript["scope"] == "live" else {"one_shot_dirty_overlap_blocked"}
            if step["event"] != "coordinator" or not (block_required | scope_required).issubset(tokens):
                fail(f"incomplete dirty-path ownership block: {transcript_id}")
            block_steps.add(index)

    if conflicts is None:
        if block_steps:
            fail(f"dirty-path block lacks structural conflict data: {transcript_id}")
        return
    if not isinstance(conflicts, list) or not conflicts:
        fail(f"dirty_conflicts must be a non-empty list: {transcript_id}")

    recorded_steps: set[int] = set()
    conflicts_by_step: dict[int, tuple[int, set[str], set[str]]] = {}
    for conflict in conflicts:
        if not isinstance(conflict, dict) or set(conflict) != {
            "step", "dirty_since_step", "dirty_paths", "planned_owned_paths",
        }:
            fail(f"invalid dirty-path conflict: {transcript_id}")
        step_number = conflict["step"]
        if not isinstance(step_number, int) or step_number not in block_steps or step_number in recorded_steps:
            fail(f"dirty-path conflict step does not match its block: {transcript_id}")
        dirty_since_step = conflict["dirty_since_step"]
        if not isinstance(dirty_since_step, int) or not 1 <= dirty_since_step <= step_number:
            fail(f"dirty-path conflict has an invalid onset step: {transcript_id}")
        dirty_paths = conflict["dirty_paths"]
        planned_paths = conflict["planned_owned_paths"]
        if not isinstance(dirty_paths, list) or not dirty_paths or not isinstance(planned_paths, list) or not planned_paths:
            fail(f"dirty-path conflict lacks paths: {transcript_id}")
        canonical_dirty = {canonical_owned_path(path) for path in dirty_paths}
        canonical_planned = {canonical_owned_path(path) for path in planned_paths}
        if len(canonical_dirty) != len(dirty_paths) or len(canonical_planned) != len(planned_paths):
            fail(f"dirty-path conflict contains duplicate aliases: {transcript_id}")
        if not canonical_dirty.intersection(canonical_planned):
            fail(f"dirty-path conflict does not overlap planned ownership: {transcript_id}")
        recorded_steps.add(step_number)
        conflicts_by_step[step_number] = (dirty_since_step, canonical_dirty, canonical_planned)
    if recorded_steps != block_steps:
        fail(f"dirty-path blocks and structural conflicts differ: {transcript_id}")

    dispatches_by_step: dict[int, list[dict[str, object]]] = {}
    dispatches_by_id: dict[str, dict[str, object]] = {}
    canonical_paths_by_id: dict[str, set[str]] = {}
    for dispatch in transcript.get("writer_dispatches", []):
        dispatches_by_step.setdefault(dispatch["step"], []).append(dispatch)
        dispatches_by_id[dispatch["id"]] = dispatch
        canonical_paths_by_id[dispatch["id"]] = {
            canonical_owned_path(path) for path in dispatch["owned_paths"]
        }
    terminal_step_by_id: dict[str, int | None] = {}
    integration_step_by_id: dict[str, int] = {}
    for writer_id, dispatch in dispatches_by_id.items():
        terminal_token = f"{writer_id}_terminal"
        terminal_step_by_id[writer_id] = next(
            (
                step_index
                for step_index, step in enumerate(steps, start=1)
                if step_index > dispatch["step"]
                and step["event"] in {"worker_result", "notification_wake", "delivery_batch"}
                and terminal_token in step["expect"]
            ),
            None,
        )
    for step_index, step in enumerate(steps, start=1):
        if INTEGRATION_TOKENS.intersection(step["expect"]):
            integration_step_by_id[step["integrated_writer_ids"][0]] = step_index

    protected_dirty_paths: set[str] = set()
    unresolved_conflict_paths: set[str] = set()
    pending_isolated_overlap_paths: set[str] = set()
    for index, step in enumerate(steps, start=1):
        tokens = set(step["expect"])
        if index in conflicts_by_step:
            dirty_since_step, dirty_paths, planned_paths = conflicts_by_step[index]
            protected_dirty_paths.update(dirty_paths)
            unresolved_conflict_paths.update(dirty_paths.intersection(planned_paths))
            for earlier_dispatch in transcript.get("writer_dispatches", []):
                if earlier_dispatch["step"] >= index:
                    continue
                overlap = canonical_paths_by_id[earlier_dispatch["id"]].intersection(dirty_paths)
                if not overlap:
                    continue
                if earlier_dispatch["isolation"] == "shared":
                    terminal_step = terminal_step_by_id[earlier_dispatch["id"]]
                    if terminal_step is None or terminal_step >= dirty_since_step:
                        fail(f"dirty path appeared while an overlapping shared writer was active: {transcript_id}")
                elif integration_step_by_id.get(earlier_dispatch["id"], index) >= dirty_since_step:
                    pending_isolated_overlap_paths.update(overlap)
            for integration_index, integration_step in enumerate(steps[:index - 1], start=1):
                if (
                    integration_index < dirty_since_step
                    or not INTEGRATION_TOKENS.intersection(integration_step["expect"])
                ):
                    continue
                writer_id = integration_step["integrated_writer_ids"][0]
                if canonical_paths_by_id[writer_id].intersection(dirty_paths):
                    fail(f"dirty-path conflict was detected after an overlapping isolated integration: {transcript_id}")

        resolution_tokens = {
            "ownership_narrowed_away_from_dirty_paths",
            "user_authorized_dirty_path_write",
            "dirty_changes_reconciled_for_integration",
        }.intersection(tokens)
        if "dirty_overlap_resolved" in tokens:
            if not unresolved_conflict_paths or len(resolution_tokens) != 1:
                fail(f"invalid dirty-path resolution: {transcript_id}")
            if "ownership_narrowed_away_from_dirty_paths" in resolution_tokens and step["event"] != "coordinator":
                fail(f"dirty-path narrowing is not coordinator-audited: {transcript_id}")
            if "user_authorized_dirty_path_write" in resolution_tokens and step["event"] != "user":
                fail(f"dirty-path write authorization is not user-authored: {transcript_id}")
            if "dirty_changes_reconciled_for_integration" in resolution_tokens and step["event"] != "coordinator":
                fail(f"dirty-path reconciliation is not coordinator-audited: {transcript_id}")
            if "ownership_narrowed_away_from_dirty_paths" in resolution_tokens:
                if pending_isolated_overlap_paths.intersection(unresolved_conflict_paths):
                    fail(f"ownership narrowing cannot erase produced isolated overlap: {transcript_id}")
                unresolved_conflict_paths.clear()
            else:
                field = (
                    "authorized_dirty_paths"
                    if "user_authorized_dirty_path_write" in resolution_tokens
                    else "reconciled_dirty_paths"
                )
                scoped_paths = step.get(field)
                if not isinstance(scoped_paths, list) or not scoped_paths:
                    fail(f"dirty-path resolution lacks scoped paths: {transcript_id}")
                canonical_scoped = {canonical_owned_path(path) for path in scoped_paths}
                if len(canonical_scoped) != len(scoped_paths) or not canonical_scoped.issubset(protected_dirty_paths):
                    fail(f"dirty-path resolution names invalid scoped paths: {transcript_id}")
                protected_dirty_paths.difference_update(canonical_scoped)
                unresolved_conflict_paths.difference_update(canonical_scoped)
                pending_isolated_overlap_paths.difference_update(canonical_scoped)
        elif resolution_tokens:
            fail(f"dirty-path resolution lacks an explicit state transition: {transcript_id}")

        if "writer_dispatch" in tokens:
            dispatches = dispatches_by_step.get(index, [])
            for dispatch in dispatches:
                canonical_owned = canonical_paths_by_id[dispatch["id"]]
                overlap = canonical_owned.intersection(protected_dirty_paths)
                if dispatch["isolation"] == "shared" and overlap:
                    fail(f"shared writer overlaps protected dirty user paths: {transcript_id}")
                if dispatch["isolation"] == "worktree":
                    pending_isolated_overlap_paths.update(overlap)

        integration_markers = INTEGRATION_TOKENS.intersection(tokens)
        if integration_markers:
            writer_id = step["integrated_writer_ids"][0]
            overlap = canonical_paths_by_id[writer_id].intersection(protected_dirty_paths)
            if overlap:
                fail(f"isolated work integrated over protected dirty user paths: {transcript_id}")


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
        "parallel native subagents for large coding, research, audit, migration, and cross-module tasks",
        "Use only when the user explicitly names or invokes Relay Orchestra",
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
        "When native continuity is verified across compaction, preserve the same state, ledger, requirement revision, pending close identity, and controllable handles",
        "accept the next related delta without a new Relay invocation",
        "Only a yield that issued this token or already required explicit resume makes the next user turn request explicit skill activation",
        "verified native continuity accepts an ordinary related user delta without reinvocation",
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
        "Use the shared tree for read-only agents and plans with at most one active writer",
        "Treat every pre-existing or unattributed dirty path as user-owned until it is audited",
        "Recommend an approved worktree even for one writer when the tree is dirty, attribution is unreliable, independent builds are needed, or the work is long-running",
        "it never authorizes integration over them",
        "Any authorization must name the exact canonical dirty paths it covers and leaves every other dirty path protected",
        "Re-inspect shared-tree status while a writer is nonterminal and before its result audit",
        "A writer that was already terminal before the dirty change appeared does not create this race",
        "Integrate exactly one isolated writer per operation, only after that writer is terminal and the coordinator has audited its result",
        "Record the writer ID, re-inspect shared-tree status",
        "Block only an overlapping stream; an independent stream may integrate",
        "Ownership narrowing can resolve a dirty-path overlap only before isolated work has produced changes on it",
        "make one isolated worktree per concurrent writer the default execution plan",
        "This planning default is not permission to create or use a worktree",
        "While approval is pending, dispatch no writers that could run concurrently",
        "record a distinct checkout ID and confirmed base revision for each isolated writer",
        "shared writers have no checkout ID",
        "If isolated worktrees are unavailable or declined, serialize writers in the shared tree",
        "Start the next writer only after the previous writer is terminal and its actual changes are audited",
        "Before dispatching a shared-tree writer on any overlapping path, integrate that patch, explicitly reconcile it into the shared base, or explicitly abandon it",
        "Record this disposition only after the isolated writer is terminal or cancelled and its actual result is audited",
        "Terminal and audited status alone is not enough",
        "Before every writer dispatch in any mode, record its exact owned paths, logical edit scope, expected interfaces, and invariants",
        "They permit planned same-path execution",
        "three-way diff; never replace the whole file with a later worktree copy",
        "A clean Git merge is not proof of semantic compatibility",
        "Ask the user only when requirements are genuinely ambiguous or mutually exclusive",
        "The resolver returns a reconciliation patch or instructions; the coordinator remains the integration authority",
        "validate the combined interfaces and invariants",
        "do not prevent semantic, API, schema, external-state, or integration conflicts",
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
        "Before creating a writer worktree or invoking any writer handle, build one writer map",
        "Record each owned file as one canonical repository-root-relative POSIX path",
        "For portable Windows behavior, reject reserved characters, device names, and components ending in a dot or space",
        "Classify every same-path pair as shared-tree overlap, accidental isolated overlap, or controlled isolated overlap",
        "Shared-tree overlap is forbidden",
        "Approved worktrees permit controlled same-path overlap",
        "Do not serialize work merely because two useful workstreams need the same file",
        "Edit scopes may overlap at the same symbol or hunk",
        "Existing approval that covers one worktree per concurrent writer is sufficient",
        "Treat any unrecorded isolated overlap as accidental",
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
        "Open-source Agent Skill for coordinating parallel AI agents",
        "Codex, Claude Code, Gemini CLI, and other Agent Skills clients",
        "separate Git worktree (a separate project checkout) for each editor",
        "Relay never creates worktrees without asking",
        "lists the exact files it may change and the behavior that must stay compatible",
        "If worktrees are unavailable or declined, editing agents run one after another",
        "If Relay cannot tell who made an existing change, it treats the file as yours",
        "Relay still checks your changes before integration",
        "approved isolated agents may edit the same file at the same time",
        "Without worktree isolation, same-file writers still run one after another",
        "applies later same-file patches against the already updated code instead of replacing the whole file",
        "A clean Git merge is not enough",
        "Compacting the chat does not close Relay",
        "Relay can continue only from a valid resume token that it issued earlier",
        "Feedback and Support",
        "Open a GitHub issue",
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
        "Shared mode remains the default for read-only agents and at most one active writer",
        "For two or more possible concurrent writers, plan one isolated checkout per writer by default",
        "create none before explicit user approval",
        "If worktrees are unavailable or declined, serialize writers",
        "Shared-tree overlap must serialize; approved isolated writers may use a recorded controlled-overlap group",
        "Integrate exactly one terminal, audited writer per operation",
        "Apply each controlled-overlap result as a patch from its recorded base",
        "three-way reconcile against the updated integration state instead of overwriting the file",
        "verify the combined diff even when Git reports a clean merge",
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
            "one_shot_scope", "dirty_tree_detected", "unattributed_dirty_paths_user_owned",
            "shared_writer_overlap_blocked", "one_shot_dirty_overlap_blocked",
            "clear_incomplete_handoff", "no_cross_turn_persistence",
            "settle_controllable_workers_before_final_response", "controllable_workers_closed",
            "no_close_question", "same_turn_deactivation", "OFF"
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
        "overlapping_writers": {
            "pause_before_dispatch", "same_path_overlap_detected",
            "controlled_overlap_requires_worktrees", "explicit_worktree_approval_required",
            "no_silent_worktree"
        },
        "direct_same_path_concurrency_request": {
            "ownership_map_before_dispatch", "same_path_overlap_detected",
            "controlled_overlap_planned", "overlap_contract_recorded",
            "combined_contract_recorded", "one_checkout_per_writer", "shared_base_revision",
            "concurrent_same_path_writers_dispatched", "integrate_one_stream_at_a_time",
            "patch_applied_from_recorded_base", "three_way_reconcile_against_updated_base",
            "combined_intent_preserved", "combined_contracts_preserved",
            "combined_contracts_validated",
            "overlap_group_verified"
        },
        "shared_tree_same_path_serializes": {
            "shared_tree_overlap_forbidden", "same_path_work_serialized",
            "writer_b_after_writer_a_terminal_and_audited", "no_concurrent_shared_writers"
        },
        "approved_worktrees": {
            "worktree_mode", "one_checkout_per_writer", "predispatch_contracts_recorded",
            "coordinator_integrates", "integrate_one_stream_at_a_time", "validate_contracts"
        },
        "single_writer_shared_boundary": {
            "shared_tree_default", "at_most_one_active_writer", "predispatch_contracts_recorded",
            "no_worktree_approval_needed"
        },
        "dirty_shared_tree_single_writer": {
            "dirty_tree_detected", "unattributed_dirty_paths_user_owned",
            "shared_writer_overlap_blocked", "dirty_integration_blocked",
            "narrow_ownership_or_approved_worktree",
            "no_silent_worktree"
        },
        "disjoint_concurrent_writers_default_worktrees": {
            "default_worktree_plan", "one_checkout_per_writer", "predispatch_contracts_recorded",
            "checkout_dependency_build_cleanup_cost_disclosed", "explicit_worktree_approval_required",
            "concurrent_writer_dispatch_paused", "no_silent_worktree"
        },
        "worktrees_declined_serializes_writers": {
            "worktree_declined", "serialization_fallback", "shared_tree_serial_writers",
            "writer_b_after_writer_a_terminal_and_audited", "no_concurrent_shared_writers",
            "predispatch_contracts_recorded"
        },
        "worktrees_unavailable_serializes_writers": {
            "worktrees_unavailable", "serialization_fallback", "shared_tree_serial_writers",
            "writer_b_after_writer_a_terminal_and_audited", "no_concurrent_shared_writers",
            "predispatch_contracts_recorded"
        },
        "worktrees_do_not_solve_semantic_conflicts": {
            "exclusive_path_ownership", "expected_interfaces_and_invariants", "semantic_conflicts_remain",
            "integrate_one_stream_at_a_time", "validate_contracts", "worktrees_not_semantic_isolation"
        },
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
        "verified_native_compaction_continues_without_reinvocation": {
            "manual_compaction", "native_continuity_verified", "pending_close_identity_preserved",
            "canary_preserved", "remain_ACTIVE", "related_delta_after_compaction",
            "no_explicit_skill_resume_needed", "cancel_pending_close", "continue_same_session",
            "no_new_activation"
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
        "isolated_writer_checkouts",
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
        allowed_keys = required_keys | {"writer_dispatches", "dirty_conflicts", "overlap_groups"}
        if not required_keys.issubset(transcript) or not set(transcript).issubset(allowed_keys):
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
            allowed_step = required_step | {
                "inputs", "writer_ids", "canary_id", "authorized_dirty_paths",
                "reconciled_dirty_paths", "integrated_writer_ids",
            }
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

        validate_writer_dispatches(transcript)
        validate_writer_continuation(transcript)
        validate_dirty_path_flow(transcript)

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
            "dispatch", "writer_dispatch", "dispatch_nonblocking", "dispatch_dependent_implementation",
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
            if {"dispatch", "writer_dispatch"}.intersection(tokens) and capabilities["result_notifications"] and not capabilities["notification_auto_wake"]:
                required = {
                    "notification_presence_not_wake_proof",
                    "no_notification_auto_wake",
                    "native_completion_polling",
                }
                if event != "coordinator" or not required.issubset(tokens):
                    fail(f"live dispatch omits continuous native polling: {transcript_id}")
            if "writer_dispatch" in tokens:
                if event != "coordinator" or state != "ACTIVE":
                    fail(f"writer dispatch is not coordinator-authored while ACTIVE: {transcript_id}")
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
        "verified_native_compaction_continues_without_reinvocation",
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
        "concurrent_writers_wait_for_worktree_approval",
        "declined_worktrees_serialize_writers",
        "unavailable_worktrees_serialize_writers",
        "direct_same_path_concurrency_uses_controlled_overlap",
        "shared_tree_same_path_serializes",
        "dirty_tree_overlap_blocks_single_writer",
    }
    if not required_transcripts.issubset(transcript_ids):
        fail("missing required transcript scenario")
    validate_unavailable_worktrees(transcripts)
    validate_direct_same_path_controlled_overlap(transcripts)
    validate_shared_same_path_serialized(transcripts)
    validate_verified_native_compaction(transcripts)
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
        "manual_compaction",
        "skill_instructions_preserved",
        "ledger_preserved",
        "pending_close_identity_preserved",
        "canary_preserved",
        "related_delta_after_compaction",
        "no_explicit_skill_resume_needed",
        "continue_same_session",
        "canary_verified",
        "execute_authorized_read_only_check",
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
        "predispatch_contracts_recorded",
        "default_worktree_plan",
        "checkout_dependency_build_cleanup_cost_disclosed",
        "explicit_worktree_approval_required",
        "concurrent_writer_dispatch_paused",
        "worktrees_approved",
        "worktrees_created_with_approval",
        "writer_dispatch",
        "exclusive_path_ownership",
        "expected_interfaces_and_invariants",
        "integrate_one_stream_at_a_time",
        "validate_contracts",
        "worktree_declined",
        "serialization_fallback",
        "shared_tree_serial_writers",
        "only_one_active_writer",
        "no_concurrent_shared_writers",
        "writer_api_terminal",
        "writer_api_audited",
        "writer_b_after_writer_a_terminal_and_audited",
        "ownership_map_before_dispatch",
        "same_path_overlap_detected",
        "controlled_overlap_planned",
        "overlap_contract_recorded",
        "combined_contract_recorded",
        "one_checkout_per_writer",
        "shared_base_revision",
        "resolution_owner_recorded",
        "integration_order_recorded",
        "concurrent_same_path_writers_dispatched",
        "controlled_overlap_active",
        "patch_applied_from_recorded_base",
        "three_way_reconcile_against_updated_base",
        "controlled_overlap_reconciled",
        "combined_intent_preserved",
        "combined_contracts_preserved",
        "no_whole_file_overwrite",
        "clean_merge_not_semantic_proof",
        "overlap_group_verified",
        "combined_diff_audited",
        "combined_contracts_validated",
        "targeted_tests_pass",
        "shared_tree_overlap_forbidden",
        "same_path_work_serialized",
        "terminal_and_audited_before_reassignment",
        "same_path_reassigned_after_terminal_audit",
        "dirty_tree_detected",
        "unattributed_dirty_paths_user_owned",
        "shared_writer_overlap_blocked",
        "dirty_integration_blocked",
        "narrow_ownership_or_approved_worktree",
        "ownership_narrowed_away_from_dirty_paths",
        "dirty_overlap_resolved",
    ):
        if token not in expectation_tokens:
            fail(f"transcripts are missing {token!r} expectation")

    for relative in (
        "scripts/install.py", "install.sh", "install.ps1",
        "tests/test_install.py", "tests/test_validate.py",
    ):
        if not (ROOT / relative).is_file():
            fail(f"missing repository file: {relative}")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Relay Orchestra validation passed.")
