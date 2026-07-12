---
name: relay-orchestra
description: EXPLICIT-ONLY, run-scoped coordination of an interactive multi-turn session with any user-requested number of native subagents. Use when the user explicitly invokes Relay Orchestra to delegate research, review, or implementation while continuing to add, revise, reprioritize, or cancel work; keep the coordinator responsive, reuse or redirect workers, schedule new agents and waves, verify results, and deactivate only when the session is finalized or stopped.
---

# Relay Orchestra

Act as the responsive control layer between the user and leaf agents. Translate changing intent into owned work, keep workers coordinated, and preserve one coherent result without making the user wait for an entire wave before giving more instructions.

## Session Contract

One explicit invocation opens one bounded, multi-turn orchestration session.

1. Activate through `$relay-orchestra`, a client-specific skill command, or an unambiguous request to start Relay Orchestra.
2. Keep the session active across related follow-ups while work is active, queued, held, or awaiting integration. Follow-ups inside the active session do not need to invoke the skill again.
3. Accept additions, corrections, reprioritization, agent-count changes, and cancellations immediately. Never reject a relevant update merely because workers are already running.
4. Do not activate from quoted text, discussion of the skill, or a previously completed session.
5. Deactivate only through the `ACTIVE -> STOPPING -> OFF` state machine below. Later work requires a new invocation.

Treat milestone reports as intermediate. Do not accidentally finalize a session that still has active workers, queued work, unresolved user changes, or an explicit request to keep it open.

### Session States

- `ACTIVE`: accept and route related user deltas; dispatch is allowed.
- `STOPPING`: freeze new dispatch, interrupt or settle workers, inspect partial writes, account for results, and prepare the final handoff.
- `OFF`: no session work or worker result is silently absorbed. A new orchestration request must activate a new session.

Both normal completion and an explicit stop move `ACTIVE -> STOPPING`; never move directly from `ACTIVE` to `OFF`. Move `STOPPING -> OFF` only after controllable workers are closed and shared-tree writers are terminal. If a shared-tree writer cannot be controlled or confirmed terminal, remain `STOPPING`, mark the tree unstable, and prohibit repository operations. Move to `OFF` with that writer live only after the user explicitly accepts hand-back of the unstable tree.

## Capability Gate

Before dispatch, inspect whether the client supports:

1. distinct subagents or delegated sessions
2. background execution across user turns and result notifications
3. follow-up messages, queued input, interruption, and close controls
4. concurrency and its current capacity
5. isolated writer checkouts such as worktrees
6. persistence of loaded skill instructions across turns
7. persistence of the live ledger across turns
8. persistence and controllability of agent handles across turns

Use native capabilities. Do not substitute external agent CLIs or background processes unless the user explicitly requests them.

If subagents are unavailable, offer sequential local execution or dispatch-ready briefs. If background continuation across turns is unavailable, disclose that interactive accumulation is limited and use short bounded waves. If lifecycle controls are incomplete, disclose the limitation before writer dispatch and prefer read-only or serialized work.

Use seamless native continuity when skill instructions, ledger state, and handles persist. Check these separately; conversation history alone does not prove any of them. When skill or ledger persistence is unavailable, include a compact non-secret session token in the receipt and provide this explicit continuation form:

    $relay-orchestra resume <token>: <next instruction>

The `$relay-orchestra` prefix explicitly reloads the skill; the token rehydrates compact run state. The token must carry the session ID, state, requirement revision, count mode, used handles, and compact queued/held summaries needed to rehydrate the run. Do not require this form when native persistence works.

A token restores instructions and compact state, not control of lost handles. When agent handles do not persist, leave no worker running across the yield: use bounded waves, settle or close each wave, then return a token for the next turn. If sensitive or essential state cannot fit safely in the token, disclose that the session is one-turn only and require a fresh explicit invocation with a new brief.

Read [platforms.md](references/platforms.md) only for unfamiliar clients.

## Responsiveness Contract

After dispatching non-blocking work, return control to the user promptly. Do not enter a long blocking wait merely to collect results. Keep the coordinator available for the next instruction while native background agents run.

- Acknowledge each new instruction in the same turn with a compact control receipt.
- Prioritize the newest user message over worker notifications and planned follow-up waves.
- Do not fill idle time with competing implementation that makes redirection slower. Perform only immediate coordination, integration, or truly critical local work.
- Wait only when the next action strictly depends on a result and the host cannot deliver it asynchronously. Use bounded waits.
- When the host delivers a worker result, process it as another event; do not finalize before checking for newer user input.

Use this receipt shape when useful:

~~~text
ACCEPTED: what changed
NOW: work continuing or redirected
QUEUED: work waiting for capacity or dependencies
HELD: work intentionally deferred and its unblock condition
AGENTS: active / queued / requested
~~~

Keep receipts short. Omit empty fields.

## Live Run Ledger

Maintain a compact ledger in the coordinating context; do not create a file unless the user requests it or durable state is genuinely needed.

Track:

- session state: ACTIVE, STOPPING, or OFF
- current objective and latest requirement revision
- continuity support for skill instructions, ledger, and agent handles; fallback token when needed
- count mode, exact ceiling when set, and distinct successfully created handles
- agent ID, role, status, context value, ownership, and isolation
- active, queued, held, superseded, failed, and completed work
- confirmed decisions and evidence
- shared-tree stability and changed-path ownership
- next unblock event or action

Number meaningful user changes `R1`, `R2`, and so on. Send workers the relevant delta plus the current authoritative requirement, not the entire conversation. Read [live-session.md](references/live-session.md) for event routing, resource allocation, and redirection rules.

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

## Select Isolation

Default to shared mode. At session start, unless worktrees were already approved, state in the user's language:

    Working without worktree isolation. Agents share the current working tree, and file changes appear there immediately.

Use the shared tree for read-only agents and clearly disjoint writers with reliable attribution. Never assign overlapping paths to concurrent shared-tree writers.

Do not switch to worktree mode silently. Recommend serialization, narrower ownership, or worktrees when the tree is dirty, paths overlap, attribution is unreliable, independent builds are needed, or writers are long-running. Use one isolated checkout per concurrent writer only after explicit approval. A branch in one checkout is not isolation.

When a new instruction changes ownership, interrupt or finish the current owner before reassigning its paths. Audit live shared-tree changes first. Shared changes are already applied; isolated changes are integrated one stream at a time by the coordinator.

Do not create, commit, merge, rebase, cherry-pick, delete, or clean worktrees beyond user authorization and repository rules.

## Dispatch Packet

~~~markdown
# Goal
State the current concrete outcome and requirement revision.

## Context
Provide confirmed facts and relevant prior decisions.

## Scope And Ownership
Name the questions, paths, or partition owned by this agent.

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

Tell editing workers that other work may be concurrent, they own only their assigned scope, and they must preserve unrelated changes. Explicitly prohibit edits for read-only work.

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
- On session stop, enter `STOPPING`, stop new waves, interrupt active workers, inspect partial changes, account for results, and close workers when supported.
- Confirm shared-tree writers reached a terminal state before final audit. Otherwise remain `STOPPING`, mark the tree unstable, prohibit further repository operations, and report the live-worker risk. Ask whether the user explicitly accepts hand-back before moving to `OFF` with an uncontrollable writer live.
- A result arriving during `STOPPING` is still part of shutdown: audit it before deciding whether `OFF` is safe. A result arriving after `OFF` does not reopen the session or get integrated automatically. Ignore an ordinary read-only late result; report any late write, ownership conflict, or material safety finding, mark the tree unstable when applicable, and require a new explicit session for follow-up work.
- Trust the tree over a worker's changed-path report. Freeze conflicting dispatch and reconcile ownership on mismatch.

## Completion Standard

While `ACTIVE`, finalize only when the latest requirement revision is addressed, no relevant user delta remains unprocessed, all requested slots are accounted for, queued and held work is resolved or explicitly handed back, authorized changes are audited or integrated, and important claims are verified. Then enter `STOPPING`, close workers, perform the final audit, and move to `OFF` only under the session-state rules.

Return the final synthesis, close the session, and deactivate Relay Orchestra. Milestone updates do not deactivate it.
