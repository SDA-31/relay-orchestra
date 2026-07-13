# Live Session Control Loop

Use this reference when the user changes requirements while agents are active, while close confirmation is pending, when capacity must be reallocated, or when several worker and user events arrive close together.

## Event Loop

1. Read the newest user message before processing older worker events.
2. Assign an internal requirement revision when intent, priority, ownership, or acceptance changes; describe the change in plain language to the user.
3. Compare the delta with every active and queued work item.
4. Preserve valid work, redirect invalid work, and record intentionally deferred ideas.
5. Dispatch newly unblocked work up to capacity.
6. Choose responsive yield, auto-wake yield, or one dependency wait under the rules below.

Before the first yield, record whether skill instructions, the ledger, and agent handles each persist across turns. Use native continuity when all three do. If skill or ledger state does not persist, emit the compact session token and require the client-specific explicit skill invocation plus the portable `resume <token>:` payload defined in `SKILL.md`; if handles do not persist, settle every worker before yielding because the token cannot restore control. On resume, reject older available token state. Treat an unexpectedly unavailable nonterminal handle as `unknown`, retain its exact count, and freeze repository operations and overlapping dispatch when it may still write.

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
| Related work, correction, or doubt while close confirmation is pending | Preserve audited evidence | Clear pending close confirmation, revise, and continue ACTIVE |
| Stop session | Interrupt all controllable workers | Stop waves and begin safe shutdown |

Use queued input when the current task remains valid and the delta can be applied afterward. Use interruption only when continuing would waste work, create conflicting changes, or violate the newest requirement.

## Allocate Agents

Reuse an agent when its local context materially reduces rediscovery and its ownership remains compatible. Spawn a new agent when the work is independent, needs a different specialty, or would overload the current agent's scope. Queue when capacity is full. Hold when a dependency or user decision is missing.

Assign a stable functional role or task label to each agent. Use that label in user-facing receipts across clients; include a generated nickname only as optional mapping metadata. Track work status separately from handle state so `completed`, `open`, `closed`, `visible`, and `archived` are never treated as synonyms.

Keep an agent open while it is running, while its result or writes still need capture or audit, or while an immediate compatible follow-up is likely and capacity is available. Once its useful context is synthesized and owned writes are audited, close it even if the session remains `ACTIVE`. Do not wait for confirmation of the entire parent task merely to preserve a completed handle. When the client supports resume, retain the handle ID and resume it for a later context-dependent follow-up; otherwise send compact retained context to a new agent.

Treat closing as a runtime-capacity transition, not as hiding, archiving, deleting, or removing the handle from `EXACT` accounting. A completed-but-open handle may still consume capacity; a closed handle may remain visible as history. For large workloads, dispatch bounded waves and close accounted agents before opening the next wave. Do not depend on indefinite resume availability for correctness.

## Handle Results

Before accepting a result:

1. Compare its requirement revision with the current revision.
2. Extract evidence that remains valid even if the requested output is superseded.
3. Audit actual changed paths and side effects.
4. Update the ledger and dependencies.
5. Dispatch the next wave only after applying newer user deltas.

When a user delta and worker result arrive together, route the user delta first. A result can then move dependent work from `HELD` to `QUEUED`, but it cannot erase the newer requirement or bypass an exact agent ceiling.

A direct answer to the close question is provisional authorization, not a requirement delta. If it arrives with worker results or safety events, defer `ACTIVE -> STOPPING` until the delivery batch is drained. A material event clears the pending question and authorization; remain `ACTIVE` and re-audit before asking again.

If research completes and the implementation direction is already authorized, synthesize it and launch the implementation wave without asking the user to repeat the request. Ask only for a genuinely missing product decision, authorization, or external dependency.

## Present A Completion Candidate

When the latest requirement revision appears complete, audit the integrated outcome while the session remains `ACTIVE`, then apply the [close-confirmation rules](../SKILL.md#request-close-confirmation). Related work, doubt, a revision change, or a material result clears the pending question and requires a fresh audit. When continuity needs a fallback token, carry the pending question and its audited revision in that token. Settling leaf handles for a bounded wave does not close the Relay session.

## Stay Responsive

The coordinator is a control plane, not an extra background implementer. Check result delivery and notification-triggered auto-wake separately; a queued notification may not start a coordinator turn.

- With auto-wake, dispatch non-blocking work and yield.
- Without auto-wake, normally yield and disclose once that synthesis resumes on the next user or manual wake.
- A request for a completion candidate without another user or manual wake does not authorize blocking. When worker results are a strict dependency, offer one native wait and invoke it only after the user explicitly opts in to that blocking wait. State the shortest practical bounded timeout and disclose that the main turn stays `In Progress` and may delay new input. Never use shell sleep, busy-poll, loop waits, or immediately re-wait after a timeout; report the still-running state, return control, and require fresh opt-in before another wait.

When the user sends a new message, acknowledge what changed before reporting old progress. Never answer “wait for the agents” when the new instruction can be accepted, queued, or routed immediately.

## Stop And Late Results

Shutdown is `ACTIVE -> STOPPING -> OFF`. Enter `STOPPING` after a user-authored direct explicit stop while `ACTIVE` or a valid later-turn answer to the pending close question. In `STOPPING`, dispatch is frozen but results are still processed and shared-tree writes are audited. Close confirmation or stop does not accept an unstable hand-back. If an uncontrollable writer remains live, disclose the risk, ask a distinct question, prohibit repository operations, and stay `STOPPING` until a later user-authored direct acceptance. Move to `OFF` only after all controllable workers are closed.

After `OFF`, an ordinary late read-only result does not reopen the session. Report late writes, ownership conflicts, or material safety findings as exceptions; do not integrate or dispatch follow-up work without a new explicit activation.
