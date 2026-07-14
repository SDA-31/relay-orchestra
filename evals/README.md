# Forward-Test Scenarios

`cases.json` is a portable scenario specification, not a deterministic LLM test suite. It records prompts and observable expectations for manual or client-provided agent eval runners.

## Transcript Rules

`transcripts.json` specifies ordered one-shot and multi-turn event traces. Runners should:

- preserve each delivery batch;
- distinguish result notification from automatic wake;
- verify user-event priority;
- assert scope, state transitions, continuity, bounded polling, and stop conditions after every step.

A one-shot interval timeout is a scheduling tick. Keep polling in the same turn while healthy or authorized dependent work remains. Finish with terminal synthesis, worker settlement, and `OFF`. A blocked one-shot also finishes `OFF` in its only turn. A bare explicit invocation uses live scope and needs a later direct close answer.

## Writer Dispatches

Writer-policy transcripts may include `writer_dispatches`. Each dispatch step lists exact `writer_ids`. Each matching record contains:

- `step`: the 1-based dispatch step;
- `owned_paths`: exact file paths;
- `interfaces_invariants`: non-empty shared contracts;
- `isolation`: `shared` or `worktree`;
- `after_terminal_and_audited`: writers that must finish first.

Every owned file uses one canonical repository-root-relative POSIX path. Reject absolute or worktree-specific paths, globs, directories, `.`/`..`, Windows-reserved names or characters, and components ending in a dot or space. Resolve Unicode, hardlink, symlink, and case aliases to one logical identity.

A worktree record also needs a globally unique `checkout_id` and `base_revision`; shared records omit `checkout_id`. User approval comes before worktree creation. Every dispatch continues through its scope's native mechanism: live automatic wake or polling, or one-shot polling.

For a dependency named `writer_api`, earlier steps must contain `writer_api_terminal` and then `writer_api_audited`. Concurrent writers use approved distinct worktrees. Same-path writers use terminal-and-audited ordering even when the prompt asks for simultaneous work and pre-approves worktrees.

## Dirty Paths and Integration

Each `dirty_conflicts` entry records `step`, `dirty_since_step`, `dirty_paths`, and `planned_owned_paths`.

- A shared writer fails if it was still active when an overlapping dirty change began, even if it started earlier.
- A writer already terminal before `dirty_since_step` is safe.
- An isolated writer may finish, but its overlapping integration stays blocked.
- `user_authorized_dirty_path_write` supplies `authorized_dirty_paths`.
- `dirty_changes_reconciled_for_integration` supplies `reconciled_dirty_paths`.
- Each resolution clears only its named canonical paths. Other overlaps stay protected.

Every integration operation supplies exactly one `integrated_writer_ids` entry, even when no dirty path exists. That isolated writer needs a terminal result and a later coordinator audit. Paths are checked per writer, so a clean stream can proceed while another stream remains blocked.

CI validates the package structure and required policy language. Before a release, invoke Relay Orchestra against representative cases with the target clients and record any platform-specific behavior separately.
