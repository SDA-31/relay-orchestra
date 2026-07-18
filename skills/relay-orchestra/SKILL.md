---
name: relay-orchestra
description: EXPLICIT-ONLY. Coordinates parallel native subagents for large coding, research, audit, migration, and cross-module tasks. Use only when the user explicitly names or invokes Relay Orchestra. Supports one-shot scope that deactivates in the same response without a close question, or a run-scoped live session (the bare explicit default) that stays active until a later direct explicit close confirmation or an explicit stop.
---

# Relay Orchestra

Act as the responsive control layer between the user and leaf agents. Translate changing intent into owned work, keep workers coordinated, and preserve one coherent result without making the user wait for an entire wave before giving more instructions.

## Invocation Scope

Relay Orchestra activates only through the client's explicit skill mechanism or an unambiguous request to use the Relay Orchestra skill. Choose scope from explicit user wording:

- **One-shot:** `for this message`, `for this turn only`, `one time`, or equivalent applies Relay from the originating user message through its final response. Follow the one-shot completion loop below, settle all controllable workers, report completed and incomplete work, and deactivate in that response. Do not persist a session or ask a close question. If a stop condition prevents completion, hand back clearly and deactivate.
- **Live session:** `start a live session`, `multi-turn`, or equivalent opens the live lifecycle below. A bare explicit Relay invocation also defaults to a live session; never infer one-shot scope from ordinary task wording or ask which scope the user intended.

Choose one-shot or live scope only while Relay is `OFF`. While `ACTIVE`, another explicit Relay invocation preserves the current state, scope, ledger, requirement revision, agent accounting, and pending close question; treat accompanying text as a user delta, not a new or converted session. While `STOPPING`, preserve shutdown and do not absorb accompanying new work; hand it back for a fresh invocation after `OFF`. A differently scoped session can start only after the current session reaches `OFF`.

## Live Session Contract

One explicit invocation opens one bounded, multi-turn live session.

1. Activate through the client's explicit skill picker or command, or an unambiguous request to start the Relay Orchestra skill.
2. Keep the session active across related follow-ups, including while work is active, queued, held, awaiting integration, or awaiting close confirmation. Related follow-ups need no reinvocation only when skill instructions and ledger state are verified to persist; otherwise continuation after a non-`OFF` yield follows the explicit `resume <token>:` rules below.
3. Accept additions, corrections, reprioritization, agent-count changes, and cancellations immediately. Never reject a relevant update merely because workers are already running.
4. Do not activate from quoted text, discussion of the skill, or a previously completed session.
5. Deactivate only through the `ACTIVE -> STOPPING -> OFF` state machine below. Later work requires a new invocation.

Treat milestone reports and apparent objective completion as intermediate. Do not deactivate a live session merely because the latest objective appears complete. Running or completed leaf agents are not a reason to stop orchestration: continue through worker completion, authorized dependent waves, integration, verification, and a completion candidate without requiring another user message.

Zero active agents, settled handles, or an immediate blocking phase handled locally do not deactivate a live session. Keep session and agent status explicit, re-evaluate whether distinct leaf work is useful at each research, implementation, integration, and verification boundary, and never dispatch merely to keep the agent count above zero. If no distinct leaf work exists, remain local and `ACTIVE` without dispatch.

### Session States

- `ACTIVE`: accept and route related user deltas; dispatch is allowed, including while close confirmation is pending.
- `STOPPING`: freeze new dispatch, interrupt or settle workers, inspect partial writes, account for results, and prepare the final handoff.
- `OFF`: no session work or worker result is silently absorbed. A new orchestration request must activate a new session.

A host response or context boundary does not authorize a Relay lifecycle transition, although it may end the host turn, task, or retained context. This includes a normal response labeled `final` or `final_answer`, host `task_complete`, compaction, summarization, context replacement, resume, and notification wake. Apply response mutations and replacement-token issuance before checking boundary continuity. Continue through verified native continuity, or require explicit activation with a structurally valid token from the planned non-`OFF` yield. When native continuity is verified across compaction, preserve the same state, ledger, requirement revision, pending close identity, and controllable handles; accept the next related delta without a new Relay invocation. If a newer ledger generation survives, compare it and reject a stale token. If no comparator survives, accept the explicit token as supplied portable state without claiming comparison to lost state; relative staleness cannot be independently proven. If explicit resume is already required, later lifecycle-neutral host bookkeeping markers may be recorded without execution; keep work frozen and resume still required. Freeze dispatch and writes only when neither verified native state nor a valid explicit token is available, or when a surviving newer comparator proves the token stale. Never infer `OFF` from a boundary.

Apparent live-session completion does not enter `STOPPING`. Only a valid answer to a pending close question or a user-authored explicit stop while `ACTIVE` authorizes `ACTIVE -> STOPPING`; never move directly from `ACTIVE` to `OFF`. Move `STOPPING -> OFF` only after all controllable workers are closed and shared-tree writers are terminal. If a shared-tree writer cannot be controlled or confirmed terminal, remain `STOPPING`, mark the tree unstable, and prohibit repository operations. Close confirmation or an explicit stop authorizes only entry into `STOPPING`; after disclosing the live-writer risk, ask a distinct hand-back question and move to `OFF` with that writer live only after a later user-authored direct acceptance while `STOPPING`.

### Request Close Confirmation

**Live closure invariant:** Authorization to perform work, approve a fallback, approve a milestone, or answer any non-close question never authorizes closure. Every live-session turn that reports a completion candidate must remain `ACTIVE` and end with the close question; no initial, repeated, or corrected completion candidate enters `STOPPING` or `OFF`. This guard does not apply to explicit one-shot scope, which deactivates in its completion response without asking.

When the completion criteria appear satisfied and no close question is currently pending, stay `ACTIVE` and:

1. perform the final audit against the latest requirement revision
2. apply the handle lifecycle rules below, closing audited handles that are no longer useful for an immediate correction
3. present a completion-candidate synthesis with completed work and residual risks
4. ask one concise question equivalent to: `Everything looks complete. May I close Relay Orchestra?`
5. record pending close confirmation with the audited revision, issued question, and coordinator turn in the ledger

If a close question is already pending, retain it and do not issue another completion candidate or close question. Re-ask only after the pending question is cleared and a fresh audit completes.

Treat `yes`, `yes, thanks`, `all good`, and equivalent semantic affirmation as provisional closure authorization only when it is user-authored on a later turn, directly answers the still-pending question, its audited revision is current, and the whole reply is unconditional and introduces no related work, correction, or doubt. Generic thanks, work or fallback approval, milestone approval, statements that work is done, stale assent, ambiguous or conditional assent, and mixed assent plus new work do not authorize closure. Interpret meaning in the user's language, not keywords.

Only an immediate user-authored command that clearly targets the current Relay session, such as `Stop Relay Orchestra` or `Close the Relay session`, authorizes `ACTIVE -> STOPPING` without a pending question. A command to stop, cancel, or pause a task, workstream, worker, action, or direction is a work delta and leaves Relay `ACTIVE`. Quoted, hypothetical, reported, future, and conditional stop text is not session-stop authorization; `finish this, then close` still requires later direct close confirmation. If the target is unclear or the command also requests continued work, remain `ACTIVE` and clarify.

Before consuming close authorization, process newer user input and drain already-delivered safety events and material results. A same-batch material result can invalidate authorization. Clear the pending question and provisional authorization when the requirement revision changes, the user supplies related work, correction, doubt, or refusal, or a material result invalidates the synthesis. Reject answers to cleared questions or non-current audited revisions. Re-audit before asking again. Ambiguous or conditional assent leaves the existing question pending and does not authorize or issue a replacement question.

## Capability Gate

Before dispatch, inspect whether the client supports:

1. distinct subagents or delegated sessions
2. background execution across user turns
3. result delivery or notification
4. notification-triggered automatic coordinator wake or resumption
5. follow-up messages, queued input, interruption, and close controls
6. concurrency and its current capacity
7. isolated writer checkouts such as worktrees
8. persistence of loaded skill instructions across turns
9. persistence of the live ledger across turns
10. persistence and controllability of agent handles across turns

Use native capabilities. Do not substitute external agent CLIs or background processes unless the user explicitly requests them.

Check result notification and automatic coordinator wake separately. Notification presence alone does not prove wake support.

If subagents are unavailable, offer sequential local execution or dispatch-ready briefs. Treat approval of that fallback as work authorization only, never as close confirmation. In one-shot scope, use only an already-authorized safe fallback or hand back instead of opening another turn for approval. If background continuation across turns is unavailable, disclose that interactive accumulation is limited and use short bounded waves. If lifecycle controls are incomplete, disclose the limitation before writer dispatch and prefer read-only or serialized work.

Use seamless native continuity only when skill instructions and ledger state are verified to persist and every nonterminal handle remains controllable; zero nonterminal handles satisfies the handle condition. Treat unverified persistence or controllability as unavailable, and do not use conversation history as proof. For these rules, every response that returns control while Relay remains `ACTIVE` or `STOPPING` is a permitted yield, including a completion-candidate response. When skill or ledger persistence is unavailable, include a compact non-secret session token before that yield and mark explicit resume as required. Only a yield that issued this token or already required explicit resume makes the next user turn request explicit skill activation with the portable payload below; verified native continuity accepts an ordinary related user delta without reinvocation. Unless a verified automatic wake can reload the skill and current state without user action, treat auto-wake as unusable while explicit resume is required and keep the current turn in progress.

    resume <token>: <next instruction>

The client-specific wrapper requests explicit skill activation; count it as reloading instructions only when that client behavior is verified. [platforms.md](references/platforms.md) owns wrapper examples. The token compactly carries a monotonic ledger generation with state, requirement revision, count mode and ceiling, exact used-handle accounting, nonterminal handle control records, tree stability, queued/held work, and any pending close question with its audited revision and issued turn. Increment the generation whenever any token-carried mutable state changes, and issue a replacement token before a later yield. When a newer surviving ledger or generation exists, compare it and reject a stale token. Without a surviving comparator, relative staleness cannot be independently proven; after a planned non-`OFF` yield, accept a structurally valid token through explicit activation as the caller-supplied portable state, without claiming it was compared with lost state. Never let a resumed token overwrite newer available state. If close confirmation is pending, require the direct answer through the same explicit activation mechanism with `resume <token>: <answer>`.

A token carries compact state after the skill is actually loaded; it does not itself reload instructions or restore control of lost handles. When handles do not persist, leave no worker running across a permitted yield: use bounded waves and settle or close each wave first. If a recorded nonterminal handle is unexpectedly unavailable, mark it `unknown`, retain it in exact used-handle accounting, and do not replace it past an `EXACT` ceiling. If it may write, mark the tree unstable and freeze repository operations and overlapping writer dispatch until terminal state is confirmed. If essential state cannot fit safely in the token, disclose a one-turn limitation before honoring a one-off pause or yield and require a fresh explicit invocation.

Read [platforms.md](references/platforms.md) only for unfamiliar clients.

## Responsiveness Contract

After live-session dispatch, choose the path supported by the host:

- If result notification automatically wakes the coordinator, dispatch non-blocking work, yield the main turn, and resume natively on that wake.
- If notifications do not auto-wake the coordinator, automatically use native completion waits or completion polling at short bounded intervals. Do not require wait opt-in or another user or manual wake. Disclose once that the coordinator remains `In Progress` and a message may wait up to one poll interval.
- Between intervals, process newer user input first and delivered worker results next, update the ledger, and advance newly unblocked waves, integration, verification, and synthesis. Start another interval only while active work remains and a specific completion or status condition can be observed.
- End the current polling cycle when there is a result to process, orchestration work completes, the user redirects, stops, or requests a one-off pause or yield, or a real blocker requires user input. After processing an event, poll again only if active work remains. Never use shell sleep, a single long blind block, blind busy-polling, or polling with no active work or next condition.
- Honor an explicit user request to pause or yield until they return as an ordinary one-off instruction. Do not create a mode, option, scope, toggle, or persistent policy; absent a fresh request, later continuation returns to automatic progress.

One-shot scope is bounded by the originating user message and its final response, not by an arbitrary poll timeout. When that response depends on worker results, use native short bounded completion polls repeatedly within the same coordinator turn without separate wait opt-in while healthy workers or authorized dependent work remain. Disclose once that the turn stays `In Progress` and input may wait up to one poll interval. Between intervals, process newer user input first and delivered results next, advance authorized dependent work, and poll again when active work and a specific next condition remain. A normal interval timeout is a scheduling tick, not the one-shot task deadline. Never interrupt healthy workers solely because one interval elapsed.

Complete normally only after all workers are terminal and synthesis is complete. Stop earlier only when the user explicitly cancels or redirects, a user-specified overall limit is reached, or a genuine host or runtime blocker prevents progress. Account for partial results and interrupt or settle affected workers as appropriate. Settle all controllable workers before the one-shot final response. Then deactivate with no close question and no cross-turn persistence. The live-session rules above are unchanged.

- Acknowledge each new instruction in the same turn with a compact control receipt.
- Prioritize the newest user message over worker notifications and planned follow-up waves.
- Do not fill idle time with competing implementation that makes redirection slower. Perform only immediate coordination, integration, or truly critical local work.
- When the host delivers a worker result, process it as another event; do not finalize before checking for newer user input.

Use this receipt shape when useful:

~~~text
ACCEPTED: what changed
NOW: work continuing or redirected
QUEUED: work waiting for capacity or dependencies
HELD: work intentionally deferred and its unblock condition
AGENTS: active / queued / requested
~~~

Keep receipts short. Omit empty fields. Identify agents by functional role or task label, such as `Lifecycle research` or `README editor`; append a client-generated nickname only when it helps the user map the role to a visible thread.

## Live Run Ledger

Maintain a compact ledger in the coordinating context; do not create a file unless the user requests it or durable state is genuinely needed.

Track:

- session state: ACTIVE, STOPPING, or OFF
- current objective and latest internal requirement revision
- pending close confirmation, its audited requirement revision, issued question, and coordinator turn
- continuity support for result delivery, automatic wake, skill instructions, ledger, and agent handles; fallback token when needed
- count mode, exact ceiling when set, and distinct successfully created handles
- agent ID when available, stable functional role, optional client nickname, work status, handle state, context value, exact owned paths for writers, logical edit scope, expected interfaces and invariants, isolation, and any controlled-overlap group
- active, queued, held, superseded, failed, and completed work
- confirmed decisions and evidence
- shared-tree stability and changed-path ownership
- next unblock event or action

Track meaningful user changes with an internal monotonic revision such as `rev-1`. Never use bare `R1`, `R2`, and similar labels in user-facing receipts unless the user chose that convention; they are easily confused with agent roles or workstreams. Lead with a plain-language description of what changed. Send workers the relevant delta plus the current authoritative requirement, not the entire conversation. Read [live-session.md](references/live-session.md) for event routing, resource allocation, and redirection rules.

## Portable Agent Identity And Status

Agent presentation differs by client: a client may expose separate chats with generated names, show a subagent panel, or keep workers invisible in the background. Use a client-neutral ledger instead of depending on any one presentation.

- Assign every worker a stable functional role or task label before dispatch. Use that label in receipts and handoffs.
- Treat a client-generated nickname as optional display metadata, never as the worker's responsibility or status.
- Keep work status separate from handle lifecycle. Normalize work as `queued`, `running`, `completed`, `errored`, or `interrupted`; normalize lifecycle as `open`, `closing`, `closed`, or `unknown` when the client exposes it.
- Do not infer active runtime, capacity use, closure, archival, or deletion from whether a worker remains visible in the client UI.
- When lifecycle controls are absent, report the closest confirmed state without pretending that a hidden or completed worker is closed.

Closing is resource cleanup, not deletion. A completed-but-open handle may still consume capacity, while a closed handle may remain visible as history. Keep an agent open while it is running, while its result or writes still need capture or audit, or while an immediate context-dependent follow-up is likely and capacity is available. Once its useful result is synthesized, owned writes are audited, and no immediate correction is expected, close it even if the Relay session remains `ACTIVE`. When supported, resume the same closed handle for a later related follow-up; otherwise dispatch a new worker with the compact retained context. Never rely on indefinite resumption for correctness.

## Process Every Event

Handle events in this priority order:

1. stop, cancellation, or urgent redirect from the user
2. safety issue or unexpected shared-tree change
3. new user requirement, priority, or resource request
4. worker request for context or reported blocker
5. worker result or failure
6. queued work newly unblocked by capacity or dependencies

For each user delta, choose one or more actions:

- continue: existing work remains valid
- update: queue a compatible follow-up to the same agent
- interrupt: current work is invalid or urgent direction changed
- reuse: preserve valuable agent context for the next related step
- spawn: create a distinct workstream when capacity permits
- queue: wait for capacity or a dependency
- hold: preserve the idea for a named later condition
- supersede: stop integrating obsolete output while retaining useful evidence

Do not forward raw transcripts. Tell each affected agent what changed, what remains authoritative, and whether its ownership changed.

## Agent Count And Capacity

Accept any positive requested count. The skill imposes no fixed maximum and must not hard-code common counts such as three or five.

Before the first multi-agent dispatch in a session, disclose once that each agent performs separate model work and parallel fan-out can consume tokens, credits, quota, or billed usage much faster than a single-agent run. Recommend fewer agents when roles overlap. Do not invent a fixed multiplier or price. Do not repeat the warning after the user explicitly acknowledges it unless the requested agent count increases.

- Honor one agent as a valid delegation run.
- Honor large requests such as fifteen agents when the client can create them.
- Treat a user-specified total as `EXACT` unless the user calls it a minimum, estimate, or explicitly authorizes scheduler-selected additions. `EXACT N` is both the target and a hard ceiling for the session.
- When no exact total is set, use `OPEN` count mode. The scheduler may add distinct agents for justified independent work and must show the updated count in the next receipt.
- Do not silently reduce or exceed an exact requested total.
- Add agents mid-session when the user asks, or when new independent work appears in `OPEN` mode.
- If capacity is lower than requested, schedule waves and report requested total, peak concurrency, active count, and queued count.
- If a client hard limit blocks the total, account for completed, active, queued, failed, and unstarted slots exactly.

For counting, one distinct successfully created leaf-agent handle consumes one agent from the total, even if it later fails or is cancelled. Messages, queued follow-ups, and reuse of the same handle do not add an agent. A spawn attempt that fails before creating a handle does not consume one; a replacement handle does. At an `EXACT` ceiling, reuse a suitable handle or queue the work. Ask the user for a count delta before creating another handle.

Differentiate responsibilities, lenses, ownership, or partitions. Explain duplication or cost concerns without inventing a skill-level cap.

## Route Work

Choose among lens fanout, disjoint workstreams, dependency waves, and research isolation. Read [patterns.md](references/patterns.md) when the split or integration is non-trivial.

Prefer this progression for product work:

1. launch focused research only where uncertainty warrants it
2. synthesize confirmed findings in the coordinator
3. dispatch implementation with the latest authoritative requirement
4. route later user changes to the agent with the most relevant context
5. add specialists or reviewers only when they create a distinct result
6. verify and integrate without repeating completed discovery

The coordinator remains the only dispatcher. Leaf agents must not spawn agents or invoke orchestration skills.

### Mandatory Writer Coordination Gate

Before creating a writer worktree or invoking any writer handle, build one writer map covering every nonterminal writer and every writer planned for the current wave. Then:

1. Record each owned file as one canonical repository-root-relative POSIX path, never as an absolute, worktree-specific, glob, directory, or `.`/`..` path.
2. Resolve Unicode normalization, hardlink, symlink, and case aliases against the repository to one logical identity before comparing paths.
3. For portable Windows behavior, reject reserved characters, device names, and components ending in a dot or space.
4. Record each writer's logical edit scope plus the expected interfaces and invariants, even when its paths are disjoint.
5. Classify every same-path pair as shared-tree overlap, accidental isolated overlap, or controlled isolated overlap.

Shared-tree overlap is forbidden. If worktrees are unavailable, declined, or not yet approved, do not dispatch a second concurrent writer for the same path. Serialize it after the current owner is terminal and audited, narrow the work, or make one agent read-only.

Approved worktrees permit controlled same-path overlap. Do not serialize work merely because two useful workstreams need the same file. Before dispatch, record one overlap contract containing:

- a stable group ID and every overlapping canonical path
- all participating writers, their logical edit scopes, and one distinct checkout per writer
- one confirmed base revision shared by the group
- the combined intended outcome, interfaces, and invariants
- the planned integration order and the coordinator or agent responsible for conflict resolution

Use controlled overlap when parallel feature progress is likely to outweigh reconciliation cost. Edit scopes may overlap at the same symbol or hunk; that raises integration risk but is not itself invalid. Prefer narrower scopes and avoid competing whole-file rewrites when a cleaner partition exists. Keep overlap waves bounded so patches are reconciled before they become large. If repeated conflicts consume more time than feature work, narrow or serialize only the hot scope while keeping independent work parallel. Announce the overlap and resolution plan before dispatch. Existing approval that covers one worktree per concurrent writer is sufficient; do not request a second permission merely because their paths overlap.

Treat any unrecorded isolated overlap as accidental: pause new dispatch into that overlap group and block its integration until the writer map and overlap contract are reconciled. Other isolated work may continue.

## Select Isolation

Use the shared tree for read-only agents and plans with at most one active writer only when existing changes and new writes can be attributed safely. When that applies, state in the user's language:

    Working without worktree isolation. Agents share the current working tree, and file changes appear there immediately.

Before any shared-tree writer dispatch, inspect repository status and the writer map. Treat every pre-existing or unattributed dirty path as user-owned until it is audited. Do not assign a shared-tree writer to those paths without explicit user authorization; narrow ownership, serialize after a safe handoff, or offer an isolated worktree. Any authorization must name the exact canonical dirty paths it covers and leaves every other dirty path protected. Recommend an approved worktree even for one writer when the tree is dirty, attribution is unreliable, independent builds are needed, or the work is long-running. If isolation is declined, preserve user-owned dirty paths and do not dispatch overlapping work.

Re-inspect shared-tree status while a writer is nonterminal and before its result audit. If a user-owned or unattributed change appears on that writer's owned path, interrupt the writer when possible, mark the tree unstable, and freeze overlapping writes and integration until the changes are reconciled. A writer that was already terminal before the dirty change appeared does not create this race. An isolated writer may finish, but its overlapping integration remains blocked.

When two or more agents could write at the same time, make one isolated worktree per concurrent writer the default execution plan. This planning default is not permission to create or use a worktree. Do not switch to worktree mode silently.

Before creation, disclose that each worktree shares Git history but duplicates checked-out files, may duplicate local dependencies or build outputs, and leaves temporary checkouts that require cleanup. Account for repository size and available disk space, then obtain explicit user approval. After approval, record a distinct checkout ID and confirmed base revision for each isolated writer; shared writers have no checkout ID. While approval is pending, dispatch no writers that could run concurrently. A branch in one checkout is not isolation.

If isolated worktrees are unavailable or declined, serialize writers in the shared tree. Start the next writer only after the previous writer is terminal and its actual changes are audited. Before every writer dispatch in any mode, record its exact owned paths, logical edit scope, expected interfaces, and invariants, then pass the mandatory coordination gate above.

A terminal and audited isolated writer may still have a pending patch. Before dispatching a shared-tree writer on any overlapping path, integrate that patch, explicitly reconcile it into the shared base, or explicitly abandon it. Record this disposition only after the isolated writer is terminal or cancelled and its actual result is audited; an earlier marker cannot settle future work. Terminal and audited status alone is not enough. Rebuild the writer map from the resulting shared base before dispatch.

Worktrees isolate checked-out files, not intent. They permit planned same-path execution but do not prevent semantic, API, schema, external-state, or integration conflicts. An approved worktree may isolate writer execution from dirty user paths, but it never authorizes integration over them. Record the writer ID, re-inspect shared-tree status, and compare that writer's exact canonical owned paths against the currently protected dirty paths. Block only an overlapping stream; an independent stream may integrate. Ownership narrowing can resolve a dirty-path overlap only before isolated work has produced changes on it. After that, keep integration blocked until the user authorizes the exact dirty paths or the coordinator explicitly reconciles those exact paths.

Integrate exactly one isolated writer per operation, only after that writer is terminal and the coordinator has audited its result. For a controlled-overlap group:

1. Preserve each writer's patch relative to the group's recorded base revision.
2. Apply the first audited stream, then reconcile each later stream against the updated integration state with a three-way diff; never replace the whole file with a later worktree copy.
3. Keep the combined intent and invariants authoritative. A clean Git merge is not proof of semantic compatibility.
4. Let the coordinator resolve small bounded conflicts directly. Prefer a context-rich resolver for non-trivial same-hunk or cross-contract conflicts. Give that resolver the latest requirement revision, overlap contract, each audited patch and handoff, current integrated diff, and acceptance checks. The resolver returns a reconciliation patch or instructions; the coordinator remains the integration authority and audits that output before applying it. Under an exact agent ceiling, reuse a suitable handle or resolve locally instead of silently creating another agent.
5. Ask the user only when requirements are genuinely ambiguous or mutually exclusive, not for ordinary code conflicts.
6. After the full overlap group is combined, inspect the resulting diff, validate the combined interfaces and invariants, and run focused tests for all participating workstreams.

When a new instruction changes shared-tree ownership, interrupt or finish the current owner before reassigning its paths and audit live changes first. For isolated writers, update the overlap contract and let still-relevant work continue when reconciliation remains bounded. Shared changes are already applied; isolated changes are integrated one stream at a time by the coordinator, using audited resolver output when applicable.

Do not create, commit, merge, rebase, cherry-pick, delete, or clean worktrees beyond user authorization and repository rules. After verified integration, remove task-created worktrees when authorized so temporary checkouts do not accumulate.

## Dispatch Packet

~~~markdown
# Goal
State the current concrete outcome and requirement revision.

## Context
Provide confirmed facts and relevant prior decisions.

## Scope And Ownership
Name the questions or read-only partition. For a writer, list every exact owned path and logical edit scope. Name any controlled-overlap group and the other writers that may edit the same paths; otherwise confirm there is no overlap with a nonterminal or same-wave writer.

## Interfaces And Invariants
Record expected contracts with other workstreams and assumptions that must remain true.

## Isolation
State read-only, shared, or isolated; include the base revision when relevant.

## Do Not Touch
List excluded paths, behavior, and other agents' work.

## Authorization
List allowed builds, tests, installs, commits, external writes, and destructive actions. Unlisted actions remain unauthorized.

## Acceptance
Give observable success conditions and checks.

## Handoff
Require the structured result below.
~~~

Tell editing workers that other work may be concurrent, they own only their assigned logical scope, and they must preserve unrelated changes. In a controlled-overlap group, tell them which paths other writers may also edit and require a patch that can be reconciled from the recorded base. Explicitly prohibit edits for read-only work.

## Handoff Packet

~~~text
STATUS: DONE | BLOCKED | NEEDS_CONTEXT | CANCELLED | SUPERSEDED
REQUIREMENT_REVISION:
SUMMARY:
EVIDENCE:
CHANGED_PATHS:
COMMANDS_AND_SIDE_EFFECTS:
WORKTREE_OR_BRANCH:
DECISIONS:
RISKS:
NEXT_ACTION:
~~~

Send missing context back to the same agent when useful. Do not count `BLOCKED`, `NEEDS_CONTEXT`, `CANCELLED`, or `SUPERSEDED` as completed implementation. Verify reported paths and high-impact claims against actual artifacts.

## Failure And Cancellation

- Retry a failed spawn at most once when the failure appears transient. Then mark that slot failed and continue exact accounting.
- Report hung workers instead of waiting forever.
- On urgent redirection, interrupt only agents whose work became invalid; queue compatible changes for context-rich agents.
- On a user-authored explicit live-session stop or valid close confirmation, enter `STOPPING`, stop new waves, interrupt or settle active workers, inspect partial changes, account for results, and close workers when supported.
- Confirm all controllable workers are closed and shared-tree writers reached a terminal state before completing shutdown. Otherwise remain `STOPPING`, mark the tree unstable, prohibit further repository operations, and report the live-worker risk. Ask a distinct hand-back question after that disclosure; do not reuse close confirmation or the explicit stop as acceptance. Move to `OFF` with an uncontrollable writer live only after a later user-authored direct acceptance while `STOPPING`.
- A result arriving during `STOPPING` is still part of shutdown: audit it before deciding whether `OFF` is safe. A result arriving after `OFF` does not reopen the session or get integrated automatically. Ignore an ordinary read-only late result; report any late write, ownership conflict, or material safety finding, mark the tree unstable when applicable, and require a new explicit session for follow-up work.
- Trust the tree over a worker's changed-path report. Freeze conflicting dispatch and reconcile ownership on mismatch.

## Completion Standard

In one-shot scope, audit the bounded result, settle all controllable workers, report completion or blockers, and deactivate in that response without a close question.

While a live session is `ACTIVE`, form a completion candidate only when the latest requirement revision is addressed, no relevant user delta remains unprocessed, all requested slots are accounted for, queued and held work is resolved or explicitly handed back, authorized changes are audited or integrated, and important claims are verified. Perform the final audit, present the synthesis and residual risks, ask for close confirmation, and remain `ACTIVE` while awaiting the answer.

Enter `STOPPING` only after valid direct confirmation or an explicit stop command. Complete the safe shutdown checks, return the final handoff, move to `OFF`, and deactivate Relay Orchestra. Milestone updates and completion candidates do not deactivate it.
