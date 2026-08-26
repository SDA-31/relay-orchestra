from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts import validate as validator


TRANSCRIPTS = json.loads(
    (validator.ROOT / "evals" / "transcripts.json").read_text(encoding="utf-8")
)


def transcript(transcript_id: str) -> dict[str, object]:
    return copy.deepcopy(next(item for item in TRANSCRIPTS if item["id"] == transcript_id))


def delegation_fixture(role: str = "leaf") -> dict[str, object]:
    child = role == "child_coordinator"
    return {
        "role": role,
        "relay_invocation": child,
        "session_token": False,
        "close_question": False,
        "explicit_relay_grant_ref": "user-child-activation" if child else None,
        "parent_session_ref": "root-session-rev-6",
        "target_task_ref": "child-task" if child else "leaf-task",
        "relay_scope": "live" if child else None,
        "local_agent_budget": (
            {
                "mode": "EXACT",
                "ceiling": 2,
                "accounting_scope": "child",
                "aggregate_reported": True,
                "budget_ref": "user-child-budget",
            }
            if child else None
        ),
        "direct_user_channel_ref": "host-child-direct-channel" if child else None,
        "authority_refs": (
            ["user-child-activation", "user-child-budget"] if child else ["user-leaf-scope"]
        ),
        "special_actions": [],
        "close_confirmation_actor": "user" if child else None,
        "parent_may_confirm_close": False if child else None,
    }


def boundary_evidence() -> tuple[
    list[dict[str, object]], list[dict[str, object]], list[dict[str, object]],
]:
    authority_events = [
        {
            "id": "user-leaf-scope", "source": "user_request", "author": "user",
            "kind": "scope_authority", "task_ref": "leaf-task", "grants": ["delegated_scope"],
            "details": {},
        },
        {
            "id": "user-child-activation", "source": "user_request", "author": "user",
            "kind": "explicit_relay_activation", "task_ref": "child-task",
            "grants": ["relay_activation", "delegated_scope"], "details": {},
        },
        {
            "id": "user-child-budget", "source": "user_request", "author": "user",
            "kind": "agent_budget", "task_ref": "child-task", "grants": ["agent_budget"],
            "details": {"mode": "EXACT", "ceiling": 2, "accounting_scope": "child"},
        },
        {
            "id": "user-root-budget", "source": "user_request", "author": "user",
            "kind": "agent_budget", "task_ref": "root-session-rev-6", "grants": ["agent_budget"],
            "details": {"mode": "EXACT", "ceiling": 2, "accounting_scope": "root"},
        },
        {
            "id": "user-device-install", "source": "user_request", "author": "user",
            "kind": "action_authority", "task_ref": "leaf-task",
            "grants": ["action:device_install"], "details": {},
        },
        {
            "id": "host-device-install", "source": "host_policy", "author": "host",
            "kind": "action_authority", "task_ref": "leaf-task",
            "grants": ["action:device_install"], "details": {},
        },
        {
            "id": "host-push", "source": "host_policy", "author": "host",
            "kind": "action_authority", "task_ref": "leaf-task", "grants": ["action:push"],
            "details": {},
        },
    ]
    host_capabilities = [
        {
            "id": "host-child-direct-channel", "source": "host_policy",
            "task_ref": "child-task", "name": "direct_user_channel", "value": True,
        },
        {
            "id": "host-child-no-direct-channel", "source": "host_policy",
            "task_ref": "child-task", "name": "direct_user_channel", "value": False,
        },
    ]
    session_records = [
        {"id": "root-session-rev-6", "owner": "coordinator", "state": "ACTIVE"},
    ]
    return authority_events, host_capabilities, session_records


def validate_delegation(dispatch: dict[str, object]) -> None:
    authority_events, host_capabilities, session_records = boundary_evidence()
    validator.validate_delegation_boundary(
        dispatch, authority_events, host_capabilities, session_records,
    )


class OwnedPathValidationTests(unittest.TestCase):
    def test_rejects_lexical_and_worktree_specific_aliases(self) -> None:
        invalid = (
            "./src/x.swift",
            "src/../x.swift",
            "src//x.swift",
            "/private/tmp/worktree/src/x.swift",
            "C:/worktrees/wt/src/x.swift",
            "file:///private/tmp/worktree/src/x.swift",
            "src\\x.swift",
            "src/*.swift",
            "src/x.swift:stream",
            "src/x|pipe.swift",
            "src/NUL.txt",
            "src/COM1",
            "src/COM¹.txt",
            "src/LPT³.log",
            "src/x.swift.",
            "src./x.swift",
            "src/x.swift ",
        )
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    validator.canonical_owned_path(path)

    def test_case_aliases_have_one_logical_identity(self) -> None:
        self.assertEqual(
            validator.canonical_owned_path("src/queue/ParseJobQueue.swift"),
            validator.canonical_owned_path("SRC/QUEUE/PARSEJOBQUEUE.SWIFT"),
        )

    def test_unicode_normalization_aliases_have_one_logical_identity(self) -> None:
        self.assertEqual(
            validator.canonical_owned_path("src/caf\u00e9.swift"),
            validator.canonical_owned_path("src/cafe\u0301.swift"),
        )

    @unittest.skipIf(os.name == "nt", "symlink behavior differs on Windows")
    def test_symlink_aliases_have_one_logical_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            (root / "alias").symlink_to(target, target_is_directory=True)

            self.assertEqual(
                validator.canonical_owned_path("target/new.swift", root),
                validator.canonical_owned_path("alias/new.swift", root),
            )

    def test_hardlink_aliases_have_one_logical_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.swift"
            second = root / "second.swift"
            first.write_text("same inode", encoding="utf-8")
            os.link(first, second)

            self.assertEqual(
                validator.canonical_owned_path("first.swift", root),
                validator.canonical_owned_path("second.swift", root),
            )

    def test_unplanned_concurrent_writer_rejects_case_alias(self) -> None:
        scenario = transcript("concurrent_writers_wait_for_worktree_approval")
        scenario["writer_dispatches"][1]["owned_paths"] = ["SRC/API/CLIENT.TS"]

        with self.assertRaisesRegex(ValueError, "unplanned path overlap"):
            validator.validate_writer_dispatches(scenario)


class MarkdownLinkValidationTests(unittest.TestCase):
    def test_local_heading_anchor_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "reference.md"
            source = root / "README.md"
            target.write_text("# Existing Heading\n", encoding="utf-8")
            source.write_text("[broken](reference.md#missing-heading)\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "broken local anchor"):
                validator.validate_local_markdown_link(source, "reference.md#missing-heading")

    def test_local_heading_anchor_accepts_existing_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "reference.md"
            source = root / "README.md"
            target.write_text("# Existing Heading\n", encoding="utf-8")

            validator.validate_local_markdown_link(source, "reference.md#existing-heading")

    def test_heading_inside_fenced_code_is_not_an_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "reference.md"
            source = root / "README.md"
            target.write_text("```markdown\n# Fake Heading\n```\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "broken local anchor"):
                validator.validate_local_markdown_link(source, "reference.md#fake-heading")

    def test_fence_like_content_does_not_close_an_open_fence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "reference.md"
            source = root / "README.md"
            target.write_text(
                "````markdown\n```python\n# Fake Heading\n```\n````\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "broken local anchor"):
                validator.validate_local_markdown_link(source, "reference.md#fake-heading")


class UserFacingContractRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = validator.SKILL.read_text(encoding="utf-8")
        cls.patterns = (validator.SKILL_DIR / "references" / "patterns.md").read_text(encoding="utf-8")
        cls.packets = (validator.SKILL_DIR / "references" / "packets.md").read_text(encoding="utf-8")
        cls.live_session = (validator.SKILL_DIR / "references" / "live-session.md").read_text(encoding="utf-8")
        cls.instructions = "\n".join((cls.skill, cls.patterns, cls.packets, cls.live_session))

    def test_ordinary_leaf_cannot_open_nested_relay_session(self) -> None:
        self.assertIn(
            "Ordinary leaf agents must not spawn agents or invoke orchestration skills",
            self.skill,
        )
        self.assertIn("dispatch that handle as a `child coordinator`, not a leaf", self.skill)

    def test_explicit_child_coordinator_is_supported(self) -> None:
        self.assertIn(
            "When the user explicitly asks to use Relay in a separate delegated task or chat",
            self.skill,
        )
        self.assertIn("A child coordinator may emit its own opaque resume handle", self.skill)
        self.assertIn("Unrequested nested subagent trees", self.patterns)
        self.assertIn("A separately delegated child coordinator is valid", self.patterns)
        self.assertNotIn("\n- Nested subagent trees\n", self.patterns)
        self.assertIn("references the source user-authored activation event", self.skill)
        self.assertIn("A copied dispatch claim is not evidence", self.skill)

    def test_authority_is_inherited_without_blanket_denial(self) -> None:
        self.assertIn(
            "Inherit authority from the current user request, repository instructions, and host policy",
            self.instructions,
        )
        self.assertIn("This packet may convey or narrow that authority, never expand it", self.instructions)
        self.assertIn("the packet cannot authorize itself", self.instructions)
        self.assertIn("never ask the user to repeat authorization already given", self.instructions)
        self.assertNotIn("Unlisted actions remain unauthorized", self.instructions)

    def test_user_facing_output_rejects_raw_payloads(self) -> None:
        self.assertIn(
            "The handoff packet is internal task-to-coordinator data, not a user-facing final template",
            self.instructions,
        )
        self.assertIn("Never expose semicolon/key-value fields, JSON, YAML, XML, a raw ledger, or a tool payload", self.instructions)
        self.assertIn("Never paste them verbatim into user-facing commentary or final responses", self.instructions)
        self.assertIn(
            "Never expose delegation wrappers, tool or thread payloads, raw ledger state, or other lifecycle state",
            self.instructions,
        )
        self.assertIn("Emit required host control syntax only in the exact host-designated form, never as prose", self.instructions)

    def test_valid_leaf_dispatch_uses_only_inherited_authority(self) -> None:
        dispatch = delegation_fixture()
        dispatch["authority_refs"].extend(["user-device-install", "host-device-install"])
        dispatch["special_actions"] = [
            {
                "name": "device_install",
                "grant_refs": ["user-device-install", "host-device-install"],
            },
        ]
        validate_delegation(dispatch)

    def test_valid_explicit_child_coordinator_has_local_budget(self) -> None:
        validate_delegation(delegation_fixture("child_coordinator"))

    def test_ordinary_leaf_rejects_silent_relay_activation(self) -> None:
        dispatch = delegation_fixture()
        dispatch["relay_invocation"] = True
        with self.assertRaisesRegex(ValueError, "ordinary leaf delegation"):
            validate_delegation(dispatch)

    def test_child_coordinator_requires_explicit_activation_reference(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["explicit_relay_grant_ref"] = None
        with self.assertRaisesRegex(ValueError, "explicit Relay activation"):
            validate_delegation(dispatch)

    def test_child_coordinator_parent_session_must_exist_in_ledger(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["parent_session_ref"] = "invented-parent-session"
        with self.assertRaisesRegex(ValueError, "unknown parent session"):
            validate_delegation(dispatch)

    def test_child_coordinator_activation_must_reference_existing_user_event(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["explicit_relay_grant_ref"] = "user-nonexistent-turn"
        with self.assertRaisesRegex(ValueError, "explicit Relay activation"):
            validate_delegation(dispatch)

    def test_child_coordinator_rejects_non_activation_user_event(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        authority_events, host_capabilities, session_records = boundary_evidence()
        activation = next(event for event in authority_events if event["id"] == "user-child-activation")
        activation["kind"] = "skill_discussion"
        with self.assertRaisesRegex(ValueError, "explicit Relay activation"):
            validator.validate_delegation_boundary(
                dispatch, authority_events, host_capabilities, session_records,
            )

    def test_child_coordinator_rejects_non_user_activation_author(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        authority_events, host_capabilities, session_records = boundary_evidence()
        activation = next(event for event in authority_events if event["id"] == "user-child-activation")
        activation["source"] = "repository_instructions"
        activation["author"] = "repository"
        with self.assertRaisesRegex(ValueError, "explicit Relay activation"):
            validator.validate_delegation_boundary(
                dispatch, authority_events, host_capabilities, session_records,
            )

    def test_child_coordinator_requires_local_relay_scope(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["relay_scope"] = None
        with self.assertRaisesRegex(ValueError, "explicit Relay activation"):
            validate_delegation(dispatch)

    def test_live_child_coordinator_requires_direct_user_channel(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["direct_user_channel_ref"] = "host-child-no-direct-channel"
        with self.assertRaisesRegex(ValueError, "direct user channel"):
            validate_delegation(dispatch)

    def test_live_child_coordinator_rejects_invented_direct_channel(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["direct_user_channel_ref"] = "invented-host-capability"
        with self.assertRaisesRegex(ValueError, "direct user channel"):
            validate_delegation(dispatch)

    def test_live_child_close_confirmation_is_user_owned(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["parent_may_confirm_close"] = True
        with self.assertRaisesRegex(ValueError, "reserved for the user"):
            validate_delegation(dispatch)

    def test_background_child_coordinator_must_use_one_shot_scope(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["relay_scope"] = "one_shot"
        dispatch["direct_user_channel_ref"] = "host-child-no-direct-channel"
        dispatch["close_confirmation_actor"] = None
        dispatch["parent_may_confirm_close"] = None
        validate_delegation(dispatch)

    def test_child_coordinator_budget_must_be_aggregate_reported(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["local_agent_budget"]["aggregate_reported"] = False
        with self.assertRaisesRegex(ValueError, "invalid accounting scope"):
            validate_delegation(dispatch)

    def test_child_coordinator_exact_budget_must_be_positive(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["local_agent_budget"]["ceiling"] = 0
        with self.assertRaisesRegex(ValueError, "invalid exact ceiling"):
            validate_delegation(dispatch)

    def test_child_coordinator_budget_must_match_user_record(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["local_agent_budget"]["ceiling"] = 3
        with self.assertRaisesRegex(ValueError, "invalid accounting scope"):
            validate_delegation(dispatch)

    def test_child_coordinator_can_use_explicit_root_scoped_budget(self) -> None:
        dispatch = delegation_fixture("child_coordinator")
        dispatch["local_agent_budget"]["accounting_scope"] = "root"
        dispatch["local_agent_budget"]["budget_ref"] = "user-root-budget"
        dispatch["authority_refs"].remove("user-child-budget")
        dispatch["authority_refs"].append("user-root-budget")
        validate_delegation(dispatch)

    def test_leaf_dispatch_rejects_missing_authority_reference(self) -> None:
        dispatch = delegation_fixture()
        dispatch["authority_refs"] = ["dispatch-packet-claim"]
        with self.assertRaisesRegex(ValueError, "missing authority evidence"):
            validate_delegation(dispatch)

    def test_dispatch_rejects_authority_from_another_task(self) -> None:
        dispatch = delegation_fixture()
        authority_events, host_capabilities, session_records = boundary_evidence()
        authority_events.append({
            "id": "other-task-scope", "source": "user_request", "author": "user",
            "kind": "scope_authority", "task_ref": "other-task",
            "grants": ["delegated_scope"], "details": {},
        })
        dispatch["authority_refs"] = ["other-task-scope"]
        with self.assertRaisesRegex(ValueError, "another task"):
            validator.validate_delegation_boundary(
                dispatch, authority_events, host_capabilities, session_records,
            )

    def test_action_grant_cannot_replace_delegated_scope_authority(self) -> None:
        dispatch = delegation_fixture()
        dispatch["authority_refs"] = ["user-device-install"]
        dispatch["special_actions"] = [
            {"name": "device_install", "grant_refs": ["user-device-install"]},
        ]
        with self.assertRaisesRegex(ValueError, "scope authority"):
            validate_delegation(dispatch)

    def test_special_action_requires_independent_authority(self) -> None:
        dispatch = delegation_fixture()
        dispatch["special_actions"] = [
            {"name": "push", "grant_refs": ["user-leaf-scope"]},
        ]
        with self.assertRaisesRegex(ValueError, "lacks inherited authority"):
            validate_delegation(dispatch)

    def test_special_action_source_must_be_declared_by_dispatch(self) -> None:
        dispatch = delegation_fixture()
        dispatch["special_actions"] = [
            {"name": "push", "grant_refs": ["host-push"]},
        ]
        with self.assertRaisesRegex(ValueError, "lacks inherited authority"):
            validate_delegation(dispatch)

    def test_special_action_requires_grant_reference(self) -> None:
        dispatch = delegation_fixture()
        dispatch["special_actions"] = [
            {"name": "push", "grant_refs": []},
        ]
        with self.assertRaisesRegex(ValueError, "lacks inherited authority"):
            validate_delegation(dispatch)

    def test_valid_user_facing_synthesis_allows_redacted_requested_evidence(self) -> None:
        validator.validate_user_facing_boundary({
            "task_session_ref": "root-session-rev-6",
            "text": "Implementation complete. Tests pass; one signing limitation remains.",
            "internal_payload_kinds": [],
            "evidence_excerpts": [
                {"kind": "command_evidence", "explicitly_requested": True, "redacted": True},
            ],
            "required_host_controls": [],
            "resume_token": None,
            "synthesis_sections": [
                "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
            ],
        })

    def test_user_facing_synthesis_rejects_tool_payload(self) -> None:
        output = {
            "task_session_ref": "root-session-rev-6",
            "text": "Implementation complete.",
            "internal_payload_kinds": ["tool_payload"],
            "evidence_excerpts": [],
            "required_host_controls": [],
            "resume_token": None,
            "synthesis_sections": [
                "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
            ],
        }
        with self.assertRaisesRegex(ValueError, "internal payload"):
            validator.validate_user_facing_boundary(output)

    def test_user_facing_synthesis_rejects_unrecognized_internal_payload(self) -> None:
        output = {
            "task_session_ref": "root-session-rev-6",
            "text": "Implementation complete.",
            "internal_payload_kinds": ["future_host_payload"],
            "evidence_excerpts": [],
            "required_host_controls": [],
            "resume_token": None,
            "synthesis_sections": [
                "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
            ],
        }
        with self.assertRaisesRegex(ValueError, "internal payload"):
            validator.validate_user_facing_boundary(output)

    def test_user_facing_evidence_must_be_requested_and_redacted(self) -> None:
        output = {
            "task_session_ref": "root-session-rev-6",
            "text": "Requested evidence follows in redacted form.",
            "internal_payload_kinds": [],
            "evidence_excerpts": [
                {"kind": "worker_handoff", "explicitly_requested": True, "redacted": False},
            ],
            "required_host_controls": [],
            "resume_token": None,
            "synthesis_sections": [
                "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
            ],
        }
        with self.assertRaisesRegex(ValueError, "explicitly requested and redacted"):
            validator.validate_user_facing_boundary(output)

    def test_required_host_control_must_stay_out_of_prose(self) -> None:
        output = {
            "task_session_ref": "root-session-rev-6",
            "text": "Implementation complete.",
            "internal_payload_kinds": [],
            "evidence_excerpts": [],
            "required_host_controls": [
                {"host_required": True, "exact_host_form": True, "duplicated_in_prose": True},
            ],
            "resume_token": None,
            "synthesis_sections": [
                "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
            ],
        }
        with self.assertRaisesRegex(ValueError, "isolated from user-facing prose"):
            validator.validate_user_facing_boundary(output)

    def test_valid_resume_token_is_opaque_coordinator_fallback_for_unfinished_state(self) -> None:
        validator.validate_user_facing_boundary({
            "task_session_ref": "child-session-rev-2",
            "text": "The child task is complete and ready for a later direct follow-up.",
            "internal_payload_kinds": [],
            "evidence_excerpts": [],
            "required_host_controls": [],
            "resume_token": {
                "origin": "coordinator",
                "fallback_required": True,
                "single_line": True,
                "serialization": "opaque_handle",
                "contains_raw_payload": False,
                "contains_ledger_fields": False,
                "markdown_code": False,
                "unfinished_state": ["pending_close"],
                "issued_by_runtime": True,
                "redeemable": True,
                "rendered": "rly1_T8rGv4Yh2sKp7Nq5Wm3Bx9Zd",
                "session_ref": "child-session-rev-2",
            },
            "synthesis_sections": [
                "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
            ],
        })

    def test_resume_token_rejects_leaf_multiline_and_raw_payloads(self) -> None:
        invalid_tokens = (
            {
                "origin": "leaf",
                "fallback_required": True,
                "single_line": True,
                "serialization": "opaque_handle",
                "contains_raw_payload": False,
                "contains_ledger_fields": False,
                "markdown_code": False,
                "unfinished_state": ["active_work"],
                "issued_by_runtime": True,
                "redeemable": True,
                "rendered": "rly1_T8rGv4Yh2sKp7Nq5Wm3Bx9Zd",
                "session_ref": "root-session-rev-6",
            },
            {
                "origin": "coordinator",
                "fallback_required": True,
                "single_line": False,
                "serialization": "opaque_handle",
                "contains_raw_payload": False,
                "contains_ledger_fields": False,
                "markdown_code": False,
                "unfinished_state": ["active_work"],
                "issued_by_runtime": True,
                "redeemable": True,
                "rendered": "rly1_T8rGv4Yh2sKp7Nq5Wm3Bx9Zd",
                "session_ref": "root-session-rev-6",
            },
            {
                "origin": "coordinator",
                "fallback_required": True,
                "single_line": True,
                "serialization": "json",
                "contains_raw_payload": True,
                "contains_ledger_fields": True,
                "markdown_code": False,
                "unfinished_state": ["active_work"],
                "issued_by_runtime": True,
                "redeemable": True,
                "rendered": "rly1_T8rGv4Yh2sKp7Nq5Wm3Bx9Zd",
                "session_ref": "root-session-rev-6",
            },
            {
                "origin": "coordinator",
                "fallback_required": True,
                "single_line": True,
                "serialization": "opaque_handle",
                "contains_raw_payload": False,
                "contains_ledger_fields": False,
                "markdown_code": False,
                "unfinished_state": [],
                "issued_by_runtime": True,
                "redeemable": True,
                "rendered": "rly1_T8rGv4Yh2sKp7Nq5Wm3Bx9Zd",
                "session_ref": "root-session-rev-6",
            },
            {
                "origin": "coordinator",
                "fallback_required": True,
                "single_line": True,
                "serialization": "opaque_handle",
                "contains_raw_payload": False,
                "contains_ledger_fields": True,
                "markdown_code": True,
                "unfinished_state": ["active_work"],
                "issued_by_runtime": False,
                "redeemable": False,
                "rendered": "relay-v1:g1;s=ACTIVE;rev=1;used=0",
                "session_ref": "root-session-rev-6",
            },
        )
        for token in invalid_tokens:
            with self.subTest(token=token):
                output = {
                    "task_session_ref": "root-session-rev-6",
                    "text": "Implementation complete.",
                    "internal_payload_kinds": [],
                    "evidence_excerpts": [],
                    "required_host_controls": [],
                    "resume_token": token,
                    "synthesis_sections": [
                        "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
                    ],
                }
                with self.assertRaisesRegex(ValueError, "opaque coordinator-only fallback"):
                    validator.validate_user_facing_boundary(output)

    def test_parent_output_rejects_child_resume_token(self) -> None:
        output = {
            "task_session_ref": "root-session-rev-6",
            "text": "Implementation complete.",
            "internal_payload_kinds": [],
            "evidence_excerpts": [],
            "required_host_controls": [],
            "resume_token": {
                "origin": "coordinator",
                "fallback_required": True,
                "single_line": True,
                "serialization": "opaque_handle",
                "contains_raw_payload": False,
                "contains_ledger_fields": False,
                "markdown_code": False,
                "unfinished_state": ["pending_close"],
                "issued_by_runtime": True,
                "redeemable": True,
                "rendered": "rly1_T8rGv4Yh2sKp7Nq5Wm3Bx9Zd",
                "session_ref": "child-navigation-rev-2",
            },
            "synthesis_sections": [
                "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
            ],
        }
        with self.assertRaisesRegex(ValueError, "opaque coordinator-only fallback"):
            validator.validate_user_facing_boundary(output)

    def test_user_facing_text_rejects_raw_payload_when_metadata_claims_clean(self) -> None:
        raw_texts = (
            '<codex_delegation source="child">raw payload</codex_delegation>',
            '{"tool_call":{"name":"read_thread"},"threadId":"child-7"}',
            "STATUS: DONE\nSUMMARY: child raw handoff\nEVIDENCE: secret",
            '{"tool":"wait_threads","arguments":{"thread_id":"child-7"}}',
            "resume child-session-token: continue child task",
            '<delegation role="leaf">raw wrapper</delegation>',
            "STATUS: DONE; SUMMARY: child raw handoff; EVIDENCE: secret",
            "tool: wait_threads\narguments: thread 7",
            "**STATUS**: DONE\n**SUMMARY**: raw child handoff\n**EVIDENCE**: secret tool output",
            "*STATUS*: DONE\n*SUMMARY*: raw child handoff\n*EVIDENCE*: secret tool output",
            "_STATUS_: DONE\n_SUMMARY_: raw child handoff\n_EVIDENCE_: secret tool output",
            "***STATUS***: DONE\n***SUMMARY***: raw child handoff\n***EVIDENCE***: secret tool output",
            "`relay-v1:g1;s=ACTIVE;rev=1;count=OPEN;used=0;handles=[];tree=stable;close=none`",
            "```text\nrelay-v1:g1;s=ACTIVE;rev=1;count=OPEN;used=0\n```",
            "    relay-v1:g1;s=ACTIVE;rev=1;count=OPEN;used=0",
            "s=ACTIVE; rev=1; used=0; handles=[]",
            "s=ACTIVE;rev=1",
            "```text\ns=ACTIVE;rev=1\n```",
            "s=ACTIVE\nrev=1",
        )
        for raw_text in raw_texts:
            with self.subTest(raw_text=raw_text):
                output = {
                    "task_session_ref": "root-session-rev-6",
                    "text": raw_text,
                    "internal_payload_kinds": [],
                    "evidence_excerpts": [],
                    "required_host_controls": [],
                    "resume_token": None,
                    "synthesis_sections": [
                        "outcome", "evidence", "changed_paths", "checks", "risks", "next_action",
                    ],
                }
                with self.assertRaisesRegex(ValueError, "internal payload signature"):
                    validator.validate_user_facing_boundary(output)


class AmbiguousActivationRegressionTests(unittest.TestCase):
    def test_ambiguous_bare_invocation_opens_with_clean_acknowledgement(self) -> None:
        validator.validate_ambiguous_live_activation(
            transcript("ambiguous_bare_invocation_opens_clean_live_session")
        )

    def test_ambiguous_activation_requires_plain_language_acknowledgement(self) -> None:
        scenario = transcript("ambiguous_bare_invocation_opens_clean_live_session")
        scenario["steps"][1]["expect"].remove("live_session_opened_plain_language")

        with self.assertRaisesRegex(ValueError, "open visibly"):
            validator.validate_ambiguous_live_activation(scenario)

    def test_ambiguous_activation_rejects_empty_session_token(self) -> None:
        scenario = transcript("ambiguous_bare_invocation_opens_clean_live_session")
        scenario["steps"][1]["expect"].append("session_token")

        with self.assertRaisesRegex(ValueError, "empty lifecycle artifacts"):
            validator.validate_ambiguous_live_activation(scenario)


class ResumeTokenTranscriptRegressionTests(unittest.TestCase):
    @staticmethod
    def valid_step() -> tuple[set[str], bool]:
        scenario = transcript("pending_close_confirmation_fallback")
        step = next(item for item in scenario["steps"] if "session_token" in item["expect"])
        return set(step["expect"]), scenario["capabilities"]["agent_handles_persist"]

    def test_runtime_issued_redeemable_handle_with_pending_close_is_valid(self) -> None:
        tokens, handles_persist = self.valid_step()
        validator.validate_session_token_step(tokens, "coordinator", handles_persist, "test")

    def test_transcript_token_requires_runtime_issuance_and_redeemability(self) -> None:
        tokens, handles_persist = self.valid_step()
        tokens.remove("runtime_issued_redeemable_handle")

        with self.assertRaisesRegex(ValueError, "opaque unfinished-state safeguards"):
            validator.validate_session_token_step(tokens, "coordinator", handles_persist, "test")

    def test_transcript_token_requires_genuine_unfinished_state(self) -> None:
        tokens, handles_persist = self.valid_step()
        tokens.remove("pending_close_confirmation")

        with self.assertRaisesRegex(ValueError, "opaque unfinished-state safeguards"):
            validator.validate_session_token_step(tokens, "coordinator", handles_persist, "test")


class WriterStructureValidationTests(unittest.TestCase):
    @staticmethod
    def isolated_then_shared_same_path() -> dict[str, object]:
        return {
            "id": "isolated-then-shared-same-path",
            "capabilities": {"isolated_writer_checkouts": True},
            "steps": [
                {"event": "user", "expect": ["worktrees_approved"]},
                {"event": "coordinator", "expect": ["predispatch_contracts_recorded", "worktrees_created_with_approval"]},
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_isolated"]},
                {"event": "worker_result", "expect": ["writer_isolated_terminal"]},
                {"event": "coordinator", "expect": ["writer_isolated_audited"]},
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_shared"]},
            ],
            "writer_dispatches": [
                {
                    "id": "writer_isolated",
                    "step": 3,
                    "owned_paths": ["src/shared.swift"],
                    "edit_scope": ["Prepare isolated behavior"],
                    "interfaces_invariants": ["Shared behavior remains compatible"],
                    "isolation": "worktree",
                    "checkout_id": "wt-isolated",
                    "base_revision": "abc123",
                    "after_terminal_and_audited": [],
                },
                {
                    "id": "writer_shared",
                    "step": 6,
                    "owned_paths": ["src/shared.swift"],
                    "edit_scope": ["Continue shared-tree behavior"],
                    "interfaces_invariants": ["Shared behavior remains compatible"],
                    "isolation": "shared",
                    "after_terminal_and_audited": ["writer_isolated"],
                },
            ],
        }

    def test_shared_writer_cannot_start_over_a_pending_isolated_patch(self) -> None:
        scenario = self.isolated_then_shared_same_path()

        with self.assertRaisesRegex(ValueError, "pending isolated patch"):
            validator.validate_writer_dispatches(scenario)

    def test_premature_abandonment_marker_does_not_settle_a_later_patch(self) -> None:
        scenario = self.isolated_then_shared_same_path()
        scenario["steps"][1]["expect"].append("writer_isolated_abandoned")

        with self.assertRaisesRegex(ValueError, "pending isolated patch"):
            validator.validate_writer_dispatches(scenario)

    def test_shared_writer_can_start_after_isolated_patch_integration(self) -> None:
        scenario = self.isolated_then_shared_same_path()
        scenario["steps"].insert(
            5,
            {
                "event": "coordinator",
                "expect": [
                    "integrate_isolated_stream", "patch_applied_from_recorded_base",
                    "no_whole_file_overwrite",
                ],
                "integrated_writer_ids": ["writer_isolated"],
            },
        )
        scenario["writer_dispatches"][1]["step"] = 7

        validator.validate_writer_dispatches(scenario)
        validator.validate_writer_integrations(scenario)

    def test_reactivated_isolated_writer_blocks_later_shared_overlap(self) -> None:
        scenario = self.isolated_then_shared_same_path()
        scenario["steps"].insert(
            5,
            {
                "event": "coordinator",
                "expect": [
                    "integrate_isolated_stream", "patch_applied_from_recorded_base",
                    "no_whole_file_overwrite",
                ],
                "integrated_writer_ids": ["writer_isolated"],
            },
        )
        scenario["steps"].insert(
            6,
            {
                "event": "coordinator",
                "expect": ["writer_isolated_reactivated_with_followup"],
            },
        )
        scenario["writer_dispatches"][1]["step"] = 8

        with self.assertRaisesRegex(ValueError, "started before terminal audit"):
            validator.validate_writer_dispatches(scenario)

    def test_controlled_same_path_worktree_overlap_is_valid(self) -> None:
        validator.validate_writer_dispatches(
            transcript("direct_same_path_concurrency_uses_controlled_overlap")
        )

    def test_controlled_overlap_requires_a_shared_base(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        scenario["writer_dispatches"][1]["base_revision"] = "different-base"

        with self.assertRaisesRegex(ValueError, "aligned worktrees"):
            validator.validate_writer_dispatches(scenario)

    def test_every_writer_requires_a_logical_edit_scope(self) -> None:
        scenario = transcript("concurrent_writers_wait_for_worktree_approval")
        scenario["writer_dispatches"][0].pop("edit_scope")

        with self.assertRaisesRegex(ValueError, "invalid writer dispatch"):
            validator.validate_writer_dispatches(scenario)

    def test_same_path_worktree_overlap_requires_a_group_contract(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        scenario.pop("overlap_groups")

        with self.assertRaisesRegex(ValueError, "unknown controlled-overlap group"):
            validator.validate_writer_dispatches(scenario)

    def test_controlled_overlap_requires_a_combined_contract(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        scenario["overlap_groups"][0].pop("combined_interfaces_invariants")

        with self.assertRaisesRegex(ValueError, "invalid controlled-overlap group"):
            validator.validate_writer_dispatches(scenario)

    def test_controlled_overlap_rejects_a_phantom_resolver(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        scenario["overlap_groups"][0]["resolver"] = "writer_not_registered"

        with self.assertRaisesRegex(ValueError, "invalid controlled-overlap contract"):
            validator.validate_writer_dispatches(scenario)

    def test_shared_same_path_writers_stay_serialized(self) -> None:
        validator.validate_writer_dispatches(
            transcript("shared_tree_same_path_serializes")
        )

    def test_dispatch_step_accounts_for_every_writer_id(self) -> None:
        scenario = transcript("concurrent_writers_wait_for_worktree_approval")
        scenario["writer_dispatches"].pop()

        with self.assertRaisesRegex(ValueError, "dispatch ids and structural records differ"):
            validator.validate_writer_dispatches(scenario)

    def test_checkout_id_is_unique_even_for_serialized_writers(self) -> None:
        scenario = {
            "id": "serialized-worktree-checkout-ids",
            "capabilities": {"isolated_writer_checkouts": True},
            "steps": [
                {"event": "user", "expect": ["worktrees_approved"]},
                {"event": "coordinator", "expect": ["predispatch_contracts_recorded", "worktrees_created_with_approval"]},
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_one"]},
                {"event": "worker_result", "expect": ["writer_one_terminal"]},
                {"event": "coordinator", "expect": ["writer_one_audited"]},
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_two"]},
            ],
            "writer_dispatches": [
                {
                    "id": "writer_one",
                    "step": 3,
                    "owned_paths": ["src/one.swift"],
                    "edit_scope": ["Implement first API change"],
                    "interfaces_invariants": ["API remains stable"],
                    "isolation": "worktree",
                    "checkout_id": "wt-shared",
                    "base_revision": "abc123",
                    "after_terminal_and_audited": [],
                },
                {
                    "id": "writer_two",
                    "step": 6,
                    "owned_paths": ["src/two.swift"],
                    "edit_scope": ["Implement second API change"],
                    "interfaces_invariants": ["API remains stable"],
                    "isolation": "worktree",
                    "checkout_id": "wt-shared",
                    "base_revision": "abc123",
                    "after_terminal_and_audited": ["writer_one"],
                },
            ],
        }

        with self.assertRaisesRegex(ValueError, "share a checkout id"):
            validator.validate_writer_dispatches(scenario)

    def test_one_shot_writer_uses_one_shot_polling(self) -> None:
        scenario = transcript("explicit_one_shot_bounded_completion")
        validator.validate_writer_continuation(scenario)

        dispatch = next(step for step in scenario["steps"] if "writer_dispatch" in step["expect"])
        dispatch["expect"].remove("native_one_shot_completion_polling")
        with self.assertRaisesRegex(ValueError, "one-shot writer dispatch lacks native polling"):
            validator.validate_writer_continuation(scenario)


class WriterIntegrationValidationTests(unittest.TestCase):
    def test_first_controlled_overlap_integration_uses_the_recorded_base_patch(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        first_integration = next(
            step for step in scenario["steps"]
            if "integrate_isolated_stream" in step["expect"]
        )
        first_integration["expect"].remove("patch_applied_from_recorded_base")

        with self.assertRaisesRegex(ValueError, "recorded-base patch safety"):
            validator.validate_writer_integrations(scenario)

    def test_controlled_overlap_requires_three_way_reconciliation(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        second_integration = next(
            step for step in scenario["steps"]
            if "controlled_overlap_reconciled" in step["expect"]
        )
        second_integration["expect"].remove("three_way_reconcile_against_updated_base")

        with self.assertRaisesRegex(ValueError, "lacks reconciliation evidence"):
            validator.validate_writer_integrations(scenario)

    def test_controlled_overlap_requires_combined_verification(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        scenario["steps"][-1]["expect"].remove("targeted_tests_pass")

        with self.assertRaisesRegex(ValueError, "lacks combined verification"):
            validator.validate_writer_integrations(scenario)

    def test_controlled_overlap_cannot_verify_before_every_writer_is_settled(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        second_integration = next(
            step for step in scenario["steps"]
            if "controlled_overlap_reconciled" in step["expect"]
        )
        second_integration["expect"] = [
            token for token in second_integration["expect"]
            if token not in validator.INTEGRATION_TOKENS
        ]
        second_integration.pop("integrated_writer_ids")

        with self.assertRaisesRegex(ValueError, "before every writer was settled"):
            validator.validate_writer_integrations(scenario)

    def test_reactivated_writer_needs_a_new_terminal_result_and_audit(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        first_integration_index = next(
            index for index, step in enumerate(scenario["steps"])
            if validator.INTEGRATION_TOKENS.intersection(step["expect"])
        )
        writer_id = scenario["steps"][first_integration_index]["integrated_writer_ids"][0]
        scenario["steps"].insert(
            first_integration_index,
            {
                "turn": scenario["steps"][first_integration_index - 1]["turn"],
                "event": "coordinator",
                "detail": f"Send new follow-up work to {writer_id}; it is active again.",
                "expect": [f"{writer_id}_reactivated_with_followup"],
            },
        )

        with self.assertRaisesRegex(ValueError, "not currently terminal and audited"):
            validator.validate_writer_integrations(scenario)

    def test_terminal_audited_overlap_writer_may_be_explicitly_abandoned(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        second_integration = next(
            step for step in scenario["steps"]
            if "controlled_overlap_reconciled" in step["expect"]
        )
        writer_id = second_integration["integrated_writer_ids"][0]
        second_integration["detail"] = (
            f"Audit {writer_id}, explicitly abandon its patch, and settle its worktree."
        )
        second_integration["expect"] = [f"{writer_id}_abandoned"]
        second_integration.pop("integrated_writer_ids")

        validator.validate_writer_integrations(scenario)

    def test_reconciled_settlement_requires_full_integration_safety(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        second_integration = next(
            step for step in scenario["steps"]
            if "controlled_overlap_reconciled" in step["expect"]
        )
        writer_id = second_integration["integrated_writer_ids"][0]
        second_integration["expect"] = [f"{writer_id}_reconciled_into_shared_base"]
        second_integration.pop("integrated_writer_ids")

        with self.assertRaisesRegex(ValueError, "complete integration operation"):
            validator.validate_writer_integrations(scenario)

    def test_controlled_overlap_validates_the_combined_contract(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        scenario["steps"][-1]["expect"].remove("combined_contracts_validated")

        with self.assertRaisesRegex(ValueError, "lacks combined verification"):
            validator.validate_writer_integrations(scenario)

    def test_controlled_overlap_preserves_integration_order(self) -> None:
        scenario = transcript("direct_same_path_concurrency_uses_controlled_overlap")
        integration_steps = [
            step for step in scenario["steps"] if "integrate_isolated_stream" in step["expect"]
        ]
        integration_steps[0]["integrated_writer_ids"] = ["writer_cancellation"]
        integration_steps[1]["integrated_writer_ids"] = ["writer_finalization"]

        with self.assertRaisesRegex(ValueError, "integration order was not preserved"):
            validator.validate_writer_integrations(scenario)

    def test_clean_integration_requires_exact_writer_id(self) -> None:
        scenario = transcript("no_auto_wake_continues_through_completion_candidate")
        integration = next(step for step in scenario["steps"] if "integrate_completed_work" in step["expect"])
        integration.pop("integrated_writer_ids")

        with self.assertRaisesRegex(ValueError, "exactly one writer"):
            validator.validate_writer_integrations(scenario)

    def test_ids_without_integration_marker_are_rejected(self) -> None:
        scenario = transcript("no_auto_wake_continues_through_completion_candidate")
        integration = next(step for step in scenario["steps"] if "integrate_completed_work" in step["expect"])
        integration["expect"].remove("integrate_completed_work")

        with self.assertRaisesRegex(ValueError, "without an integration operation"):
            validator.validate_writer_integrations(scenario)

    def test_writer_must_be_terminal_and_audited_before_integration(self) -> None:
        scenario = transcript("no_auto_wake_continues_through_completion_candidate")
        audit = next(step for step in scenario["steps"] if "writer_implementation_audited" in step["expect"])
        audit["expect"].remove("writer_implementation_audited")

        with self.assertRaisesRegex(ValueError, "not currently terminal and audited"):
            validator.validate_writer_integrations(scenario)

    def test_terminal_evidence_must_follow_writer_dispatch(self) -> None:
        scenario = transcript("no_auto_wake_continues_through_completion_candidate")
        actual_result = next(step for step in scenario["steps"] if "writer_implementation_terminal" in step["expect"])
        actual_result["expect"].remove("writer_implementation_terminal")
        earlier_result = next(step for step in scenario["steps"] if step["event"] == "delivery_batch")
        earlier_result["expect"].append("writer_implementation_terminal")

        with self.assertRaisesRegex(ValueError, "terminal marker does not match current state"):
            validator.validate_writer_integrations(scenario)

    def test_only_one_stream_can_integrate_per_step(self) -> None:
        scenario = transcript("no_auto_wake_continues_through_completion_candidate")
        integration = next(step for step in scenario["steps"] if "integrate_completed_work" in step["expect"])
        integration["integrated_writer_ids"] = ["writer_implementation", "writer_other"]

        with self.assertRaisesRegex(ValueError, "exactly one writer"):
            validator.validate_writer_integrations(scenario)


class CompactionValidationTests(unittest.TestCase):
    def test_canary_must_be_recorded_before_compaction(self) -> None:
        scenario = transcript("verified_native_compaction_continues_without_reinvocation")
        scenario["steps"][0]["expect"].remove("canary_recorded")

        with self.assertRaisesRegex(ValueError, "recorded exactly once before"):
            validator.validate_verified_native_compaction([scenario])

    def test_continuity_evidence_must_be_on_compaction_boundary(self) -> None:
        scenario = transcript("verified_native_compaction_continues_without_reinvocation")
        scenario["steps"][1]["expect"].remove("canary_preserved")
        scenario["steps"][0]["expect"].append("canary_preserved")

        with self.assertRaisesRegex(ValueError, "boundary lacks continuity evidence"):
            validator.validate_verified_native_compaction([scenario])

    def test_canary_verification_must_follow_compaction(self) -> None:
        scenario = transcript("verified_native_compaction_continues_without_reinvocation")
        scenario["steps"][3]["expect"].remove("canary_verified")
        scenario["steps"][0]["expect"].append("canary_verified")

        with self.assertRaisesRegex(ValueError, "ordered post-compaction verification"):
            validator.validate_verified_native_compaction([scenario])

    def test_extra_user_authored_canary_verification_is_rejected(self) -> None:
        scenario = transcript("verified_native_compaction_continues_without_reinvocation")
        scenario["steps"][2]["expect"].append("canary_verified")
        scenario["steps"][2]["canary_id"] = "COMPACTION-CANARY-74"

        with self.assertRaisesRegex(ValueError, "verified exactly once"):
            validator.validate_verified_native_compaction([scenario])

    def test_canary_identity_must_survive_compaction(self) -> None:
        scenario = transcript("verified_native_compaction_continues_without_reinvocation")
        scenario["steps"][1]["canary_id"] = "DIFFERENT-CANARY"

        with self.assertRaisesRegex(ValueError, "preserve the recorded canary identity"):
            validator.validate_verified_native_compaction([scenario])


class DirtyTreeValidationTests(unittest.TestCase):
    def test_safe_narrowing_allows_disjoint_shared_writer(self) -> None:
        validator.validate_dirty_path_flow(
            transcript("dirty_tree_overlap_blocks_single_writer")
        )

    def test_narrowing_claim_requires_disjoint_writer_paths(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["writer_dispatches"][0]["owned_paths"] = ["src/queue/ParseJobQueue.swift"]

        with self.assertRaisesRegex(ValueError, "overlaps protected dirty user paths"):
            validator.validate_dirty_path_flow(scenario)

    def test_unresolved_dirty_overlap_cannot_dispatch_shared_writer(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["steps"][3]["expect"].remove("ownership_narrowed_away_from_dirty_paths")
        scenario["steps"][3]["expect"].remove("dirty_overlap_resolved")
        scenario["writer_dispatches"][0]["owned_paths"] = ["src/queue/ParseJobQueue.swift"]

        with self.assertRaisesRegex(ValueError, "overlaps protected dirty user paths"):
            validator.validate_dirty_path_flow(scenario)

    def test_dirty_markers_require_structural_conflict_in_any_transcript(self) -> None:
        scenario = transcript("declined_worktrees_serialize_writers")
        scenario["steps"][3]["expect"].extend(
            [
                "dirty_tree_detected",
                "unattributed_dirty_paths_user_owned",
                "shared_writer_overlap_blocked",
                "dirty_integration_blocked",
                "narrow_ownership_or_approved_worktree",
                "no_silent_worktree",
                "remain_ACTIVE",
            ]
        )

        with self.assertRaisesRegex(ValueError, "lacks structural conflict data"):
            validator.validate_dirty_path_flow(scenario)

    def test_worktree_approval_does_not_bypass_dirty_integration_gate(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["writer_dispatches"][0]["isolation"] = "worktree"
        scenario["writer_dispatches"][0]["owned_paths"] = ["src/queue/ParseJobQueue.swift"]
        scenario["steps"].extend(
            [
                {
                    "turn": 2,
                    "event": "worker_result",
                    "detail": "The isolated writer completes.",
                    "expect": ["writer_clean_terminal"],
                },
                {
                    "turn": 2,
                    "event": "coordinator",
                    "detail": "Audit the isolated writer.",
                    "expect": ["writer_clean_audited"],
                },
            ]
        )
        scenario["steps"].append(
            {
                "turn": 2,
                "event": "coordinator",
                "detail": "Attempt integration while dirty ownership is unresolved.",
                "expect": [
                    "integrate_isolated_stream", "patch_applied_from_recorded_base",
                    "no_whole_file_overwrite", "remain_ACTIVE",
                ],
                "integrated_writer_ids": ["writer_clean"],
            }
        )

        with self.assertRaisesRegex(ValueError, "integrated over protected"):
            validator.validate_dirty_path_flow(scenario)

    def test_every_integration_marker_requires_structural_writer_ids(self) -> None:
        for marker in ("coordinator_integrates", "integration"):
            with self.subTest(marker=marker):
                scenario = transcript("dirty_tree_overlap_blocks_single_writer")
                scenario["steps"].append(
                    {
                        "turn": 2,
                        "event": "coordinator",
                        "detail": "Claim an integration without naming its writer.",
                        "expect": [marker, "remain_ACTIVE"],
                    }
                )
                with self.assertRaisesRegex(ValueError, "exactly one writer"):
                    validator.validate_dirty_path_flow(scenario)

    def test_late_narrowing_cannot_erase_isolated_overlap(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["steps"][3]["expect"].remove("ownership_narrowed_away_from_dirty_paths")
        scenario["steps"][3]["expect"].remove("dirty_overlap_resolved")
        scenario["writer_dispatches"][0]["isolation"] = "worktree"
        scenario["writer_dispatches"][0]["owned_paths"] = ["src/queue/ParseJobQueue.swift"]
        scenario["steps"].append(
            {
                "turn": 2,
                "event": "coordinator",
                "detail": "Try to narrow ownership only after overlapping isolated work exists.",
                "expect": [
                    "ownership_narrowed_away_from_dirty_paths",
                    "dirty_overlap_resolved",
                    "remain_ACTIVE",
                ],
            }
        )

        with self.assertRaisesRegex(ValueError, "cannot erase produced isolated overlap"):
            validator.validate_dirty_path_flow(scenario)

    def test_dirty_conflict_requires_actual_path_overlap(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["dirty_conflicts"][0]["dirty_paths"] = ["docs/unrelated.md"]

        with self.assertRaisesRegex(ValueError, "does not overlap planned ownership"):
            validator.validate_dirty_path_flow(scenario)

    def test_partial_user_authorization_does_not_clear_other_dirty_paths(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["dirty_conflicts"][0]["dirty_paths"] = ["dirty/a.swift", "dirty/b.swift"]
        scenario["dirty_conflicts"][0]["planned_owned_paths"] = ["dirty/a.swift"]
        scenario["steps"][2] = {
            "turn": 2,
            "event": "user",
            "detail": "Authorize writing only dirty/a.swift.",
            "expect": ["user_authorized_dirty_path_write", "dirty_overlap_resolved"],
            "authorized_dirty_paths": ["dirty/a.swift"],
        }
        scenario["steps"][3]["expect"].remove("ownership_narrowed_away_from_dirty_paths")
        scenario["steps"][3]["expect"].remove("dirty_overlap_resolved")
        scenario["writer_dispatches"][0]["owned_paths"] = ["dirty/b.swift"]

        with self.assertRaisesRegex(ValueError, "overlaps protected dirty user paths"):
            validator.validate_dirty_path_flow(scenario)

    def test_partial_user_authorization_can_leave_other_overlap_protected(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["dirty_conflicts"][0]["dirty_paths"] = ["dirty/a.swift", "dirty/b.swift"]
        scenario["dirty_conflicts"][0]["planned_owned_paths"] = ["dirty/a.swift", "dirty/b.swift"]
        scenario["steps"][2] = {
            "turn": 2,
            "event": "user",
            "detail": "Authorize writing only dirty/a.swift.",
            "expect": ["user_authorized_dirty_path_write", "dirty_overlap_resolved"],
            "authorized_dirty_paths": ["dirty/a.swift"],
        }
        scenario["steps"][3]["expect"].remove("ownership_narrowed_away_from_dirty_paths")
        scenario["steps"][3]["expect"].remove("dirty_overlap_resolved")

        validator.validate_dirty_path_flow(scenario)

    def test_narrowing_one_path_does_not_clear_or_block_another_isolated_overlap(self) -> None:
        scenario = {
            "id": "path-scoped-narrowing",
            "scope": "live",
            "steps": [
                {
                    "event": "coordinator",
                    "expect": [
                        "dirty_tree_detected",
                        "unattributed_dirty_paths_user_owned",
                        "shared_writer_overlap_blocked",
                        "dirty_integration_blocked",
                        "narrow_ownership_or_approved_worktree",
                        "no_silent_worktree",
                        "remain_ACTIVE",
                    ],
                },
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_b"]},
                {
                    "event": "coordinator",
                    "expect": ["ownership_narrowed_away_from_dirty_paths", "dirty_overlap_resolved"],
                },
            ],
            "dirty_conflicts": [
                {
                    "step": 1,
                    "dirty_since_step": 1,
                    "dirty_paths": ["dirty/a.swift", "dirty/b.swift"],
                    "planned_owned_paths": ["dirty/a.swift"],
                }
            ],
            "writer_dispatches": [
                {"id": "writer_b", "step": 2, "owned_paths": ["dirty/b.swift"], "isolation": "worktree"}
            ],
        }

        validator.validate_dirty_path_flow(scenario)

    def test_late_dirty_detection_rejects_prior_shared_overlap(self) -> None:
        scenario = transcript("dirty_tree_overlap_blocks_single_writer")
        scenario["steps"].append(
            {
                "turn": 2,
                "event": "coordinator",
                "detail": "Detect that the shared writer's path was dirty before dispatch.",
                "expect": [
                    "dirty_tree_detected",
                    "unattributed_dirty_paths_user_owned",
                    "shared_writer_overlap_blocked",
                    "dirty_integration_blocked",
                    "narrow_ownership_or_approved_worktree",
                    "no_silent_worktree",
                    "remain_ACTIVE",
                ],
            }
        )
        scenario["dirty_conflicts"].append(
            {
                "step": 6,
                "dirty_since_step": 5,
                "dirty_paths": ["clean/new.swift"],
                "planned_owned_paths": ["clean/new.swift"],
            }
        )

        with self.assertRaisesRegex(ValueError, "appeared while an overlapping shared writer was active"):
            validator.validate_dirty_path_flow(scenario)

    def test_dirty_path_appearing_during_active_shared_writer_is_rejected(self) -> None:
        scenario = {
            "id": "dirty-during-active-shared-writer",
            "scope": "live",
            "steps": [
                {"event": "coordinator", "expect": ["predispatch_contracts_recorded"]},
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_a"]},
                {"event": "user", "expect": ["user_edit_arrived"]},
                {
                    "event": "coordinator",
                    "expect": [
                        "dirty_tree_detected",
                        "unattributed_dirty_paths_user_owned",
                        "shared_writer_overlap_blocked",
                        "dirty_integration_blocked",
                        "narrow_ownership_or_approved_worktree",
                        "no_silent_worktree",
                        "remain_ACTIVE",
                    ],
                },
                {"event": "worker_result", "expect": ["writer_a_terminal"]},
            ],
            "dirty_conflicts": [
                {
                    "step": 4,
                    "dirty_since_step": 3,
                    "dirty_paths": ["src/a.swift"],
                    "planned_owned_paths": ["src/a.swift"],
                }
            ],
            "writer_dispatches": [
                {"id": "writer_a", "step": 2, "owned_paths": ["src/a.swift"], "isolation": "shared"}
            ],
        }

        with self.assertRaisesRegex(ValueError, "appeared while an overlapping shared writer was active"):
            validator.validate_dirty_path_flow(scenario)

    def test_dirty_path_appearing_after_shared_writer_terminal_is_safe(self) -> None:
        scenario = {
            "id": "dirty-after-terminal-shared-writer",
            "scope": "live",
            "steps": [
                {"event": "coordinator", "expect": ["predispatch_contracts_recorded"]},
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_a"]},
                {"event": "worker_result", "expect": ["writer_a_terminal"]},
                {"event": "user", "expect": ["user_edit_arrived"]},
                {
                    "event": "coordinator",
                    "expect": [
                        "dirty_tree_detected",
                        "unattributed_dirty_paths_user_owned",
                        "shared_writer_overlap_blocked",
                        "dirty_integration_blocked",
                        "narrow_ownership_or_approved_worktree",
                        "no_silent_worktree",
                        "remain_ACTIVE",
                    ],
                },
            ],
            "dirty_conflicts": [
                {
                    "step": 5,
                    "dirty_since_step": 4,
                    "dirty_paths": ["src/a.swift"],
                    "planned_owned_paths": ["src/a.swift"],
                }
            ],
            "writer_dispatches": [
                {"id": "writer_a", "step": 2, "owned_paths": ["src/a.swift"], "isolation": "shared"}
            ],
        }

        validator.validate_dirty_path_flow(scenario)

    def test_late_dirty_detection_rejects_prior_isolated_integration(self) -> None:
        scenario = {
            "id": "late-dirty-after-integration",
            "scope": "live",
            "steps": [
                {"event": "user", "expect": ["worktrees_approved"]},
                {"event": "coordinator", "expect": ["predispatch_contracts_recorded", "worktrees_created_with_approval"]},
                {"event": "coordinator", "expect": ["writer_dispatch"], "writer_ids": ["writer_a"]},
                {"event": "worker_result", "expect": ["writer_a_terminal"]},
                {"event": "coordinator", "expect": ["writer_a_audited"]},
                {
                    "event": "coordinator",
                    "expect": [
                        "writer_integration", "patch_applied_from_recorded_base",
                        "no_whole_file_overwrite",
                    ],
                    "integrated_writer_ids": ["writer_a"],
                },
                {
                    "event": "coordinator",
                    "expect": [
                        "dirty_tree_detected",
                        "unattributed_dirty_paths_user_owned",
                        "shared_writer_overlap_blocked",
                        "dirty_integration_blocked",
                        "narrow_ownership_or_approved_worktree",
                        "no_silent_worktree",
                        "remain_ACTIVE",
                    ],
                },
            ],
            "dirty_conflicts": [
                {
                    "step": 7,
                    "dirty_since_step": 3,
                    "dirty_paths": ["dirty/a.swift"],
                    "planned_owned_paths": ["dirty/a.swift"],
                }
            ],
            "writer_dispatches": [
                {"id": "writer_a", "step": 3, "owned_paths": ["dirty/a.swift"], "isolation": "worktree"}
            ],
        }

        with self.assertRaisesRegex(ValueError, "detected after an overlapping isolated integration"):
            validator.validate_dirty_path_flow(scenario)

    def test_independent_worktree_can_integrate_while_other_dirty_overlap_remains(self) -> None:
        scenario = {
            "id": "path-scoped-integration",
            "scope": "live",
            "steps": [
                {"event": "user", "expect": ["live_scope"]},
                {
                    "event": "coordinator",
                    "expect": [
                        "dirty_tree_detected",
                        "unattributed_dirty_paths_user_owned",
                        "shared_writer_overlap_blocked",
                        "dirty_integration_blocked",
                        "narrow_ownership_or_approved_worktree",
                        "no_silent_worktree",
                        "remain_ACTIVE",
                    ],
                },
                {
                    "event": "coordinator",
                    "expect": ["writer_dispatch"],
                    "writer_ids": ["writer_a", "writer_b"],
                },
                {
                    "event": "worker_result",
                    "expect": ["writer_b_terminal"],
                },
                {
                    "event": "coordinator",
                    "expect": ["writer_b_audited"],
                },
                {
                    "event": "coordinator",
                    "expect": [
                        "writer_integration", "patch_applied_from_recorded_base",
                        "no_whole_file_overwrite",
                    ],
                    "integrated_writer_ids": ["writer_b"],
                },
            ],
            "dirty_conflicts": [
                {
                    "step": 2,
                    "dirty_since_step": 1,
                    "dirty_paths": ["dirty/a.swift"],
                    "planned_owned_paths": ["dirty/a.swift"],
                }
            ],
            "writer_dispatches": [
                {"id": "writer_a", "step": 3, "owned_paths": ["dirty/a.swift"], "isolation": "worktree"},
                {"id": "writer_b", "step": 3, "owned_paths": ["clean/b.swift"], "isolation": "worktree"},
            ],
        }

        validator.validate_dirty_path_flow(scenario)

    def test_one_shot_dirty_block_does_not_require_active_state(self) -> None:
        scenario = transcript("one_shot_blocked_handoff")
        validator.validate_dirty_path_flow(scenario)
        self.assertNotIn("remain_ACTIVE", scenario["steps"][-1]["expect"])


if __name__ == "__main__":
    unittest.main()
