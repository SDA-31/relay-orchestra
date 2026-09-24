# Live Session Control Loop

Use this reference when the user changes requirements while agents are active, while close confirmation is pending, when capacity must be reallocated, or when several worker and user events arrive close together.

Auto is a separate chat preference, never part of this ledger or lifecycle. Full live takes precedence: while `ACTIVE`, route related deltas and bare reinvocation into this session instead of starting an Auto run. Starting or closing Full live does not change Auto. An `auto off` request disables only future automatic routing; keep the current run active unless the same message clearly stops it. Never put Auto or its filter in a resume token, transfer it to a child coordinator, or infer it in another chat.

Apply the core effort policy independently of Auto and lifecycle. Effort normally belongs to the current task; explicit future-use wording may retain a chat default only in host-preserved context. A task override leaves that default intact. Do not serialize effort preferences into tokens or configuration, infer them in another chat, or treat them as authority. Optional [effort and sizing examples](effort-and-sizing.md) cover ambiguous intent.

## Full One-Shot Versus Full Live

Full one-shot imports the capability, ownership, writer, integration, cancellation, settlement, and verification safeguards in this reference without opening an `ACTIVE` live session, persistent ledger, or close-confirmation handshake. Use it only when the promoted bounded objective can still finish in the originating response. After terminal work is audited and every controllable worker is settled, report completion or an honest blocked/partial result and finish `OFF` without a close question.

If a required approval, user decision, background dependency, material mid-run requirement change, or other unresolved lifecycle condition needs another turn, use full live instead. Before writer dispatch, a missing approval or decision keeps unsafe work blocked; do not create a worktree or writer first. If control of a dispatched writer unexpectedly becomes unavailable, enter the full live `STOPPING` containment path immediately: freeze new dispatch and repository operations, preserve exact handle accounting and continuity, audit delivered or partial writes, disclose the unstable-tree risk, and remain `STOPPING` until the writer is terminal or the user later accepts the separate hand-back risk. Never report that a bounded run reached `OFF` safely while an uncontrolled possible writer remains.

The close-confirmation rules below apply only to full live. They do not add a close question to full one-shot.

## Event Loop

1. Read the newest user message before processing older worker events.
2. Assign an internal requirement revision when intent, priority, ownership, or acceptance changes; describe the change in plain language to the user.
3. Compare the delta with every active and queued work item.
4. Preserve valid work, redirect invalid work, and record intentionally deferred ideas.
5. Dispatch newly unblocked work up to capacity.
6. Choose native auto-wake yield or continuous bounded native completion polling under the rules below.

An allocation adjustment within the same objective does not itself change requirements or require a lifecycle transition. Higher effort alone is such an adjustment; changed acceptance, scope, or other active requirements follow the existing routing rules. Preserve a valid active writer while redirecting future work or adding compatible read-only coverage. Update actual handle accounting whenever new work is dispatched.

Apply the lifecycle-neutral boundary rule in `SKILL.md` to host `final`, `final_answer`, and `task_complete` markers, compaction, summary replacement, resume, and notification wake. These boundaries may end a host turn, task, or retained context, but do not authorize a Relay lifecycle transition. Apply response mutations and replacement-token issuance first. Continue through verified native continuity, or require explicit activation with a structurally valid token from the planned non-`OFF` yield. Compare against newer surviving ledger state when available; otherwise accept the explicit token as supplied portable state and disclose that relative staleness cannot be independently proven. If explicit resume is already required, record later lifecycle-neutral host bookkeeping without execution and keep work frozen. Freeze only when neither continuity path is available or surviving state proves the token stale; never infer `OFF`.

Before any permitted yield, record whether skill instructions and the ledger persist and whether every nonterminal agent handle remains controllable; zero nonterminal handles satisfies the handle condition. Treat unverified persistence or controllability as unavailable. If skill or ledger state does not persist, use the explicit-resume fallback only when material unfinished state exists: active, queued, or held work; a nonterminal handle; or pending close confirmation. An empty session, a request for the next task, or an `ACTIVE` label alone does not qualify. Only the coordinator may emit a redeemable opaque handle, as one plain-text line rather than inline, fenced, or indented Markdown code. Never expose semicolon/key-value fields, JSON, YAML, XML, a raw ledger, or a tool payload. If the runtime cannot issue and later redeem an opaque handle, disclose the continuity limitation naturally and do not substitute internal serialization.

The internal state behind a valid handle has a monotonic ledger generation that covers every token-carried mutable field, including requirement and session state, pending close, handle accounting, tree stability, and queued/held work. Increment it on any such change and replace the handle before a later yield. Only after a yield that issued this handle or already required explicit resume must the next user turn request explicit skill activation plus `resume <token>:`; verified native continuity accepts an ordinary related user delta without reinvocation. A verified automatic wake may instead reload the skill and current state. If a newer comparator survives, compare and reject stale input. Otherwise accept a structurally valid explicit token as supplied portable state, without claiming comparison to lost state; relative staleness cannot be independently proven. If handles do not persist, settle every worker before yielding because the token cannot restore control. Treat an unexpectedly unavailable nonterminal handle as `unknown`, retain its exact count, and freeze repository operations and overlapping dispatch when it may still write.

## Session States And Close Confirmation

- `ACTIVE`: accept and route related deltas; dispatch remains allowed even while a close question is pending.
- `STOPPING`: freeze new dispatch, settle or interrupt workers, audit partial writes, account for results, and prepare the handoff.
- `OFF`: absorb no later session work or worker result automatically; new orchestration needs a new activation.

Milestones and apparent completion stay `ACTIVE`. Authorization to perform work, approve a fallback or milestone, or answer a non-close question never authorizes closure. When the latest revision appears complete and no close question is pending, audit it, close handles that no longer add correction value, present one completion candidate, ask one concise question equivalent to `Everything looks complete. May I close Relay Orchestra?`, and record its audited revision, issued text, and turn. If a question is already pending, retain it without another candidate or question.

Treat semantic affirmation as provisional closure authorization only when it is user-authored on a later turn, directly answers the still-pending question, targets its current audited revision, and is wholly unconditional with no related work, correction, or doubt. Generic thanks, work approval, stale assent, ambiguous or conditional assent, and mixed assent plus new work do not authorize closure. Interpret meaning in the user's language rather than matching keywords.

An immediate user-authored command clearly targeting the current Relay session may enter `STOPPING` without a pending question. A command to stop, cancel, or pause a task, workstream, worker, action, or direction is only a work delta. Quoted, hypothetical, reported, future, and conditional stop text is not a session stop. If the target is unclear or continued work is also requested, remain `ACTIVE` and clarify.

Before consuming closure authorization, process newer user input and drain already-delivered safety events and material results. Clear pending authorization when the requirement revision changes or a related correction, doubt, refusal, or material result invalidates the audit. Re-audit before asking again. Move `STOPPING -> OFF` only after every controllable worker is closed and shared-tree writers are terminal. An uncontrollable writer keeps the tree unstable and repository operations frozen until the user later accepts the separately disclosed hand-back risk.

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
| Stop a task, workstream, worker, action, or direction | Interrupt only affected work | Continue `ACTIVE`; do not treat as a session stop |
| Explicit Relay invocation while `ACTIVE` | Preserve current handles and work | Preserve scope, ledger, revision, accounting, and pending close; route accompanying text as a delta |
| Explicit Relay invocation while `STOPPING` | Preserve shutdown work | Do not absorb accompanying new work; hand it back for a fresh invocation after `OFF` |
| Related work, correction, or doubt while close confirmation is pending | Preserve audited evidence | Clear pending close confirmation, revise, and continue ACTIVE |
| Stop session | Interrupt all controllable workers | Stop waves and begin safe shutdown |

Use queued input when the current task remains valid and the delta can be applied afterward. Use interruption only when continuing would waste work, create conflicting changes, or violate the newest requirement.

## Allocate Agents

Reuse an agent when its local context materially reduces rediscovery and its ownership remains compatible. Spawn a new agent when the work is independent, needs a different specialty, or would overload the current agent's scope. Queue when capacity is full. Hold when a dependency or user decision is missing.

Send ordinary leaf agents plain dispatch packets without Relay invocations or lifecycle state. When the user explicitly requests Relay in a separate delegated task, label that handle a child coordinator, pass the activation reference plus its stated local agent budget and accounting scope, and keep its ledger, token, and close lifecycle local to that task. Record whether the user can directly read and answer that child task. Permit live scope only with that direct user channel; otherwise use one-shot so the child settles without a later close answer. Child coordinators report descendant handle counts and a synthesized result to the parent; the parent does not copy their lifecycle artifacts into its own final or answer close confirmation for the user.

Give leaves bounded task-relevant effort instructions, not inherited chat settings. Child coordination still requires a positive bounded local agent budget and source user authority; an adaptive parent plan neither grants unlimited descendants nor changes the structured packet contract.

Assign a stable functional role or task label to each agent. Use that label in user-facing receipts across clients; include a generated nickname only as optional mapping metadata. Track work status separately from handle state so `completed`, `open`, `closed`, `visible`, and `archived` are never treated as synonyms.

Keep an agent open while it is running, while its result or writes still need capture or audit, or while an immediate compatible follow-up is likely and capacity is available. Once its useful context is synthesized and owned writes are audited, close it even if the session remains `ACTIVE`. Do not wait for confirmation of the entire parent task merely to preserve a completed handle. When the client supports resume, retain the handle ID and resume it for a later context-dependent follow-up; otherwise send compact retained context to a new agent.

Treat closing as a runtime-capacity transition, not as hiding, archiving, deleting, or removing the handle from `EXACT` accounting. A completed-but-open handle may still consume capacity; a closed handle may remain visible as history. For large workloads, dispatch bounded waves and close accounted agents before opening the next wave. Do not depend on indefinite resume availability for correctness.

## Agent Count And Capacity

Accept any positive requested count. The skill imposes no fixed maximum; honor one agent and large requests such as fifteen when the host can create them. Infer effort from task and user context without profiles or a questionnaire. Maximum effort with ample budget should materially expand useful depth, coverage, verification, or parallel work when meaningful work exists; large teams and capacity waves are valid. Reuse useful context, account for actual writer/build/device bottlenecks separately from model slots, and avoid decorative or duplicate work. Before the first multi-agent dispatch, disclose once that agents perform separate model work and can consume tokens, credits, quota, or billed usage quickly. Recommend fewer agents when roles overlap, without inventing a multiplier or price. Repeat the warning only if the requested count later increases.

Treat an unqualified user-specified total as `EXACT`: `EXACT N` is the target and cumulative hard ceiling for its stated scope. “Up to N” is a ceiling without a fill target; “at least N” is a floor without a ceiling. An estimate is a plan. With no exact total, use existing `OPEN` mode while enforcing every separately stated floor and ceiling; no new schema or mode is needed. Maximum effort never overrides a numeric cap. State whether the count means delegated workers or includes the coordinator; default to delegated workers and honor the user's explicit basis. Never silently reduce or exceed an exact count. When capacity is lower, use waves and report requested total, peak concurrency, active, queued, failed, completed, and unstarted slots.

A self-selected initial count is a coordinator plan, not a user ceiling. Revise it within the same objective as evidence warrants; announce the changed count, roles, and reason before affected dispatch, within user limits, actual capacity, permissions, and ownership. This also applies in Lite without asking for a count grant or promoting solely for count. Existing safety or active-requirement promotion rules still apply.

Count each distinct successfully created handle once in the Relay session whose coordinator created it, including failed or cancelled handles. Count a child task handle in its parent and descendants in the child's scope; report aggregate activity without double-counting one handle in two totals. Partition a root-wide ceiling across children, or keep explicitly child-local budgets separate. Never let nesting evade an applicable ceiling, capacity, or usage warning. Messages and reused handles add no count. A failed spawn before handle creation adds none; a replacement handle does. At a ceiling, reuse or queue and ask the user for a count delta before creating another handle in that scope.

Completion, closing, cancellation, and new waves never reset the cumulative total. Do not fabricate work to meet an exact target; explain any insufficient meaningful scope and account for unstarted slots honestly.

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

When the latest requirement revision appears complete and no close question is pending, audit the integrated outcome while the session remains `ACTIVE`, then apply the [close-confirmation rules](#session-states-and-close-confirmation). If a question is pending, retain it without another completion candidate or close question. Related work, doubt, a revision change, or a material result clears the pending question and requires a fresh audit before asking again. When continuity needs a fallback token, carry the pending question and its audited revision in that token. Settling leaf handles for a bounded wave does not close the Relay session.

## Stay Responsive

The coordinator is a control plane, not an extra background implementer. Check result delivery and notification-triggered auto-wake separately; a queued notification may not start a coordinator turn.

- With auto-wake, dispatch non-blocking work, yield, and resume natively when the notification wakes the coordinator.
- Without auto-wake, automatically use native completion waits or polling at short bounded intervals while active work remains and a specific completion or status condition can be observed. Disclose once that the coordinator remains `In Progress` and a message may wait up to one poll interval; do not require wait opt-in or another user or manual wake.
- Between intervals, process newer user input first and delivered results next, then advance dependent waves, integration, verification, and synthesis. A result to process, completed orchestration work, redirect, stop, one-off pause or yield request, or real blocker ends the polling cycle. Poll again after processing only while active work remains.
- Never use shell sleep, a single long blind block, blind busy-polling, or polling with no active work or next condition.
- Honor a request to pause or yield until the user returns once. Do not record a mode, option, scope, toggle, or persistent policy; automatic progress applies again without a fresh request.

When the user sends a new message, acknowledge what changed before reporting old progress. Never answer “wait for the agents” when the new instruction can be accepted, queued, or routed immediately.

## Stop And Late Results

Shutdown is `ACTIVE -> STOPPING -> OFF`. Enter `STOPPING` after an immediate user-authored command clearly targeting the current Relay session while `ACTIVE`, or a valid later-turn answer to the pending close question. A stop aimed at work rather than Relay leaves the session `ACTIVE`. In `STOPPING`, dispatch is frozen but results are still processed and shared-tree writes are audited. Close confirmation or stop does not accept an unstable hand-back. If an uncontrollable writer remains live, disclose the risk, ask a distinct question, prohibit repository operations, and stay `STOPPING` until a later user-authored direct acceptance. Move to `OFF` only after all controllable workers are closed.

After `OFF`, an ordinary late read-only result does not reopen the session. Report late writes, ownership conflicts, or material safety findings as exceptions; do not integrate or dispatch follow-up work without a new explicit activation.
