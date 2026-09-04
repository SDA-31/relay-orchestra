# Forward-Test Scenarios

`cases.json` is a portable scenario specification, not a deterministic LLM test suite. It records prompts and observable expectations for manual or client-provided agent eval runners.

## Transcript Rules

`transcripts.json` specifies ordered one-shot and multi-turn event traces. Runners should:

- preserve each delivery batch;
- distinguish result notification from automatic wake;
- verify user-event priority;
- assert scope, state transitions, continuity, bounded polling, and stop conditions after every step.

A full one-shot interval timeout is a scheduling tick. Keep polling in the same turn while healthy or authorized dependent work remains. Finish with terminal synthesis, worker settlement, and `OFF`. A blocked full one-shot also finishes `OFF` in its only turn. Lite uses bounded native waits only while a necessary wave remains active; a healthy timeout may produce compact progress and another wait without creating a polling state machine. A bare invocation without a current objective enables idle chat-scoped Auto, gives the complete notice, asks for the task, and launches no lifecycle machinery.

`mode-transitions.json` isolates Auto from current execution, including active-Full precedence and scoped routing filters. The project validator checks each transition, state shape, required guarantees, and contradictory tokens. SkillForge fixtures ship under `skills/relay-orchestra/evals/`; Auto scenario assertions are exact regression contracts. Recorded baseline, GREEN, and blind A/B evidence lives under `evals/results/`.

## Delegation And Output Boundaries

`boundaries.json` contains deterministic fixtures for ordinary leaves, explicitly authorized child coordinators, and clean user-facing synthesis. Dispatch claims must reference separate authority-event, parent-session, and host-capability records; copying the same claim into two dispatch fields is not evidence. A child coordinator needs a user-authored activation and delegated-scope event, verified parent and target task references, a matching user-authored agent-budget record whose positive exact ceiling and root-or-child accounting scope are included in aggregate reporting, and a host-recorded direct-user-channel capability. Both visible and background child fixtures use positive exact ceilings; live children reserve close confirmation for the user through their channel, while background children use one-shot. Special actions reference separate action grants and cannot replace scope authority. Ordinary leaves cannot activate Relay silently. The text checks reject common raw JSON, XML, handoff, tool/thread, raw ledger, and lifecycle-token signatures; they are regression guards, not a claim that arbitrary prose can be perfectly classified. A resume handle must be runtime-issued, redeemable, opaque, and plain text; it is allowed only for genuine unfinished state and must belong to the task that emits it, so a parent cannot reuse or copy a child's handle.

## Writer Dispatches

Writer-policy transcripts may include `writer_dispatches`. Each dispatch step lists exact `writer_ids`. Each matching record contains:

- `step`: the 1-based dispatch step;
- `owned_paths`: exact file paths;
- `edit_scope`: the writer's logical change inside those files;
- `interfaces_invariants`: non-empty shared contracts;
- `isolation`: `shared` or `worktree`;
- `after_terminal_and_audited`: writers that must finish first.

Every owned file uses one canonical repository-root-relative POSIX path. Reject absolute or worktree-specific paths, globs, directories, `.`/`..`, Windows-reserved names or characters, and components ending in a dot or space. Resolve Unicode, hardlink, symlink, and case aliases to one logical identity.

A worktree record also needs a globally unique `checkout_id` and `base_revision`; shared records omit `checkout_id`. User approval comes before worktree creation. Every dispatch continues through its scope's native mechanism: live automatic wake or polling, or one-shot polling.

For a dependency named `writer_api`, earlier steps must contain `writer_api_terminal` and then `writer_api_audited`. Concurrent writers use approved distinct worktrees. Shared-tree same-path writers use terminal-and-audited ordering.

Approved worktree writers may share paths only through `overlap_group`. The matching top-level `overlap_groups` record contains the group ID, participating writers, canonical overlapping paths, shared base revision, combined intent, combined interfaces and invariants, integration order, and resolver. The resolver is `coordinator` or a registered writer ID. Every participant has a distinct checkout, a logical edit scope, and the same recorded base. Unrecorded concurrent overlap is invalid.

## Dirty Paths and Integration

Each `dirty_conflicts` entry records `step`, `dirty_since_step`, `dirty_paths`, and `planned_owned_paths`.

- A shared writer fails if it was still active when an overlapping dirty change began, even if it started earlier.
- A writer already terminal before `dirty_since_step` is safe.
- An isolated writer may finish, but its overlapping integration stays blocked.
- `user_authorized_dirty_path_write` supplies `authorized_dirty_paths`.
- `dirty_changes_reconciled_for_integration` supplies `reconciled_dirty_paths`.
- Each resolution clears only its named canonical paths. Other overlaps stay protected.

Every integration operation supplies exactly one `integrated_writer_ids` entry, even when no dirty path exists. That isolated writer needs a terminal result and a later coordinator audit. Paths are checked per writer, so a clean stream can proceed while another stream remains blocked.

Controlled-overlap members settle in their recorded workflow: each terminal, audited patch is integrated, reconciled into the shared base, or explicitly abandoned. Integrated members preserve their recorded relative order. Every integrated patch is applied from its recorded base without whole-file overwrite; every integrated patch after the first also requires three-way reconciliation against the updated integration state plus combined-intent and combined-contract preservation. Once every member is settled and at least one patch was integrated, the coordinator-authored transcript must name the group and record a combined diff audit, combined-contract validation, and focused tests. A resolver may prepare reconciliation instructions, but the coordinator audits and settles the result.

CI validates the package structure and required policy language. Before a release, invoke Relay Orchestra against representative cases with the target clients and record any platform-specific behavior separately.
