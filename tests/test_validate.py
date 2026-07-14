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

    def test_concurrent_writer_rejects_case_alias(self) -> None:
        scenario = transcript("concurrent_writers_wait_for_worktree_approval")
        scenario["writer_dispatches"][1]["owned_paths"] = ["SRC/API/CLIENT.TS"]

        with self.assertRaisesRegex(ValueError, "share owned paths"):
            validator.validate_writer_dispatches(scenario)


class WriterStructureValidationTests(unittest.TestCase):
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

        with self.assertRaisesRegex(ValueError, "before terminal result and coordinator audit"):
            validator.validate_writer_integrations(scenario)

    def test_terminal_evidence_must_follow_writer_dispatch(self) -> None:
        scenario = transcript("no_auto_wake_continues_through_completion_candidate")
        actual_result = next(step for step in scenario["steps"] if "writer_implementation_terminal" in step["expect"])
        actual_result["expect"].remove("writer_implementation_terminal")
        earlier_result = next(step for step in scenario["steps"] if step["event"] == "delivery_batch")
        earlier_result["expect"].append("writer_implementation_terminal")

        with self.assertRaisesRegex(ValueError, "before terminal result and coordinator audit"):
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
                "expect": ["integrate_isolated_stream", "remain_ACTIVE"],
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
                {"event": "coordinator", "expect": ["writer_integration"], "integrated_writer_ids": ["writer_a"]},
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
                    "expect": ["writer_integration"],
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
