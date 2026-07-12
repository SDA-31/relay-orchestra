# Live Session Control Loop

Use this reference when the user changes requirements while agents are active, when capacity must be reallocated, or when several worker and user events arrive close together.

## Event Loop

1. Read the newest user message before processing older worker events.
2. Assign a requirement revision when intent, priority, ownership, or acceptance changes.
3. Compare the delta with every active and queued work item.
4. Preserve valid work, redirect invalid work, and record intentionally deferred ideas.
5. Dispatch newly unblocked work up to capacity.
6. Return a compact receipt and yield control instead of blocking on completion.

Before the first yield, record whether skill instructions, the ledger, and agent handles each persist across turns. Use native continuity when all three do. If skill or ledger state does not persist, emit the compact session token and explicit `$relay-orchestra resume <token>:` continuation form defined in `SKILL.md`; if handles do not persist, settle every worker before yielding because the token cannot restore control.

## Route A User Delta

| Delta | Existing agent action | Scheduler action |
| --- | --- | --- |
| Clarification, same scope | Queue follow-up | Keep slot and ownership |
| Urgent correction, current output invalid | Interrupt with authoritative delta | Recalculate dependencies |
| New independent feature | Leave existing work intact | Spawn or queue a new workstream |
| New requirement depends on research | Update or reuse researcher | Hold implementation until evidence arrives |
| Reordering only | Update affected implementer | Preserve other work |
| Defer until later | Do not send yet | Put in HELD with unblock condition |
| Remove requirement | Interrupt if still active | Mark work SUPERSEDED; retain useful evidence |
| Stop session | Interrupt all controllable workers | Stop waves and begin safe shutdown |

Use queued input when the current task remains valid and the delta can be applied afterward. Use interruption only when continuing would waste work, create conflicting changes, or violate the newest requirement.

## Allocate Agents

Reuse an agent when its local context materially reduces rediscovery and its ownership remains compatible. Spawn a new agent when the work is independent, needs a different specialty, or would overload the current agent's scope. Queue when capacity is full. Hold when a dependency or user decision is missing.

Do not keep an idle agent merely to preserve trivial context. Close agents whose useful context has been synthesized and whose follow-up probability is low.

## Handle Results

Before accepting a result:

1. Compare its requirement revision with the current revision.
2. Extract evidence that remains valid even if the requested output is superseded.
3. Audit actual changed paths and side effects.
4. Update the ledger and dependencies.
5. Dispatch the next wave only after applying newer user deltas.

When a user delta and worker result arrive together, route the user delta first. A result can then move dependent work from `HELD` to `QUEUED`, but it cannot erase the newer requirement or bypass an exact agent ceiling.

If research completes and the implementation direction is already authorized, synthesize it and launch the implementation wave without asking the user to repeat the request. Ask only for a genuinely missing product decision, authorization, or external dependency.

## Stay Responsive

The coordinator is a control plane, not an extra background implementer. After dispatch, it should normally return control to the user with the current state. Avoid long waits, repeated polling, verbose status narration, and local work that duplicates or competes with delegated ownership.

When the user sends a new message, acknowledge what changed before reporting old progress. Never answer “wait for the agents” when the new instruction can be accepted, queued, or routed immediately.

## Stop And Late Results

Shutdown is `ACTIVE -> STOPPING -> OFF`. In `STOPPING`, dispatch is frozen but results are still processed for shutdown and shared-tree writes are audited. Stay `STOPPING` while an uncontrollable shared writer is live unless the user explicitly accepts hand-back with the tree marked unstable.

After `OFF`, an ordinary late read-only result does not reopen the session. Report late writes, ownership conflicts, or material safety findings as exceptions; do not integrate or dispatch follow-up work without a new explicit activation.
