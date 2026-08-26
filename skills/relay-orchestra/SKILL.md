---
name: relay-orchestra
description: EXPLICIT-ONLY. Use when the user explicitly names or invokes Relay Orchestra, and only then. Coordinates parallel native subagents for large coding, research, audit, migration, and cross-module tasks. Supports one-shot scope that deactivates in the same response without a close question, or a run-scoped live session (the bare explicit default) that stays active until a later direct explicit close confirmation or an explicit stop.
license: MIT
---

# Relay Orchestra

Act as the responsive control layer between the user and leaf agents. Translate changing intent into owned work, keep workers coordinated, and preserve one coherent result without making the user wait for an entire wave before giving more instructions.

## Invocation Scope

Relay Orchestra activates only through the client's explicit skill mechanism or an unambiguous request to use the Relay Orchestra skill. Choose scope from explicit user wording:

- **One-shot:** `for this message`, `for this turn only`, `one time`, or equivalent applies Relay from the originating user message through its final response. Follow the one-shot completion loop below, settle all controllable workers, report completed and incomplete work, and deactivate in that response. Do not persist a session or ask a close question. If a stop condition prevents completion, hand back clearly and deactivate.
- **Live session:** `start a live session`, `multi-turn`, or equivalent opens the live lifecycle below. A bare explicit Relay invocation also defaults to a live session; never infer one-shot scope from ordinary task wording or ask which scope the user intended.

When a bare invocation is ambiguous or provides no concrete current objective, keep the live default but make the activation visible: say in ordinary language that the live session is open and will remain active, then ask for the next task. Do not expose an empty ledger or any serialized lifecycle state. `ACTIVE` alone is not a reason to emit a continuity token.

Choose one-shot or live scope only while Relay is `OFF`. While `ACTIVE`, another explicit Relay invocation preserves the current state, scope, ledger, requirement revision, agent accounting, and pending close question; treat accompanying text as a user delta, not a new or converted session. While `STOPPING`, preserve shutdown and do not absorb accompanying new work; hand it back for a fresh invocation after `OFF`. A differently scoped session can start only after the current session reaches `OFF`.

A parent coordinator may carry the user's explicit request to activate Relay in a separate delegated task. Treat that as valid delegated activation only when the dispatch uses the client's explicit skill mechanism, labels the task a child coordinator, and references the source user-authored activation event, parent session, local scope and count grant, plus the host-reported direct-user-channel capability. A copied dispatch claim is not evidence. This is delegated user intent, not activation from a merely quoted or discussed skill name. A child may use live scope only when the user can directly read and answer its later close question in that task. Otherwise use one-shot scope; the parent must never answer close confirmation on the user's behalf.

## Live Session Contract

One explicit invocation opens one bounded, multi-turn live session. Read [live-session.md](references/live-session.md) immediately for the complete event, continuity, close-confirmation, handle, and shutdown procedure.

Keep the session `ACTIVE` across related follow-ups, worker completion, dependent waves, integration, verification, and completion candidates. Accept relevant changes immediately. Zero active agents does not close the session or require decorative dispatch; stay local when no distinct leaf work exists.

Use only `ACTIVE -> STOPPING -> OFF`. A completion candidate remains `ACTIVE` and asks one close question. Only a later, direct, unconditional user-authored answer to the still-current question, or an immediate user-authored command clearly targeting the Relay session, may enter `STOPPING`. Work approval, thanks, milestone approval, mixed assent plus new work, and commands aimed at a worker or workstream never close Relay. Enter `OFF` only after the shutdown checks in the reference.

Host responses, `final` markers, task completion, compaction, summaries, resume, and notification wake are lifecycle-neutral. Preserve verified native state or use the explicit-resume fallback; never infer `OFF` from a context boundary.

A live child coordinator follows the same contract inside its own user-visible task. Background or invisible child coordinators must use one-shot scope because the parent cannot provide user-authored close confirmation.

## Runtime And Continuity Gate

Before any dispatch or wait, read [live-session.md](references/live-session.md) for the event loop, capability checks, continuity fallback, handle lifecycle, and responsiveness rules for both scopes.

Inspect native subagents, result delivery, automatic wake, follow-up and interruption controls, concurrency, isolated checkouts, direct user access to child tasks, and persistence of skill instructions, ledger state, and handles. Check notification delivery and automatic wake separately. Use only native agent facilities unless the user explicitly requests an external runtime.

If subagents are unavailable, offer sequential local work or dispatch-ready briefs. If background continuity or lifecycle control is unverified, use bounded waves and settle workers before yielding. A live child requires a direct user channel; otherwise it is one-shot.

Use seamless continuity only when skill, ledger, and every nonterminal handle remain verified and controllable. Otherwise follow the reference's explicit-resume protocol. A fallback is allowed only for genuine unfinished state: active, queued, or held work; a nonterminal handle; or pending close confirmation. An empty session or `ACTIVE` label alone gets no token. Only the coordinator emits a redeemable opaque handle as one plain-text line, never Markdown code, raw field/value serialization, JSON, a ledger, or a tool payload. If the runtime cannot produce such a handle, disclose the continuity limitation in natural language instead of leaking internal state. A token cannot restore a lost handle. Treat an unavailable possible writer as `unknown`, preserve its exact accounting, mark the tree unstable, and freeze repository operations until reconciled.

Read [platforms.md](references/platforms.md) only for unfamiliar clients and wrapper syntax.

## Responsiveness Contract

Prioritize the newest user message, then safety events, then delivered results and dependent work. Acknowledge changes with a short control receipt and route them immediately; do not make the user wait for an entire wave.

Use verified automatic wake when available. Otherwise use short bounded native waits while active work and a specific observable condition remain. Never use shell sleep, one long blind block, busy-polling, or polling without active work. A poll timeout is only a scheduling tick, not a task deadline. Settle every controllable worker before a one-shot final.

Honor a one-off pause or yield without turning it into a persistent mode. Identify agents by functional role rather than relying on generated UI names.

## Live Run Ledger

Maintain the compact coordinator ledger defined in [live-session.md](references/live-session.md); create no file unless the user requests it or durable state is genuinely needed. Track session and requirement revision, continuity, pending close, exact handle accounting, leaf or child role, direct-user-channel capability, ownership and isolation, work status, evidence, tree stability, and the next unblock event. Send workers only the authoritative requirement and relevant delta, not the full conversation.

## Portable Agent Identity And Status

Give every worker a stable functional role. Treat UI nicknames and visibility as display metadata, not status. Track work state separately from handle lifecycle; a completed-but-open handle may consume capacity, while a closed handle may remain visible. Close a handle after its result and writes are audited and immediate reuse no longer has value. Never depend on indefinite resumption for correctness.

## Process Every Event

Apply the event priority and routing table in [live-session.md](references/live-session.md). Prefer continue, update, or reuse when work remains valid; interrupt, hold, queue, spawn, or supersede only when the new requirement, safety state, capacity, or dependency demands it. Never forward raw transcripts; tell affected agents only what changed, what remains authoritative, and whether ownership changed.

## Agent Count And Capacity

Follow the count and capacity rules in [live-session.md](references/live-session.md). Accept any positive requested count; the skill imposes no fixed maximum. Treat a user total as an exact ceiling unless the user says otherwise, count each created handle once in its owning Relay session, and never use nesting to evade a root or child-local ceiling. Schedule waves when host capacity is lower. Before the first multi-agent dispatch, warn once that separate agents can consume usage quickly and recommend fewer agents when roles overlap.

## Route Work

Choose among lens fanout, disjoint workstreams, dependency waves, and research isolation. Read [patterns.md](references/patterns.md) when the split or integration is non-trivial.

Prefer this progression for product work:

1. launch focused research only where uncertainty warrants it
2. synthesize confirmed findings in the coordinator
3. dispatch implementation with the latest authoritative requirement
4. route later user changes to the agent with the most relevant context
5. add specialists or reviewers only when they create a distinct result
6. verify and integrate without repeating completed discovery

Within one Relay session, its coordinator owns dispatch and lifecycle state. Ordinary leaf agents must not spawn agents or invoke orchestration skills. When the user explicitly asks to use Relay in a separate delegated task or chat, dispatch that handle as a `child coordinator`, not a leaf. Carry the user's explicit activation, record the parent session reference, assigned scope, local count budget and its root-or-child accounting scope, direct-user-channel capability, authority boundaries, isolation, and return contract, and let the child own its local Relay ledger and lifecycle. A child without a direct user channel must run one-shot; a live child requires a user-visible task that accepts direct user-authored follow-ups and close confirmation. The parent remains responsible for aggregate activity reporting, cross-task integration, and user-facing synthesis, but never answers a child's close question for the user. Never infer child coordination from task complexity or activate it silently. A child coordinator may create another Relay coordination level only when the user explicitly authorizes that additional level.

A leaf receives one dispatch packet and returns one handoff packet without Relay lifecycle state. A child coordinator may emit its own opaque resume handle or close question only inside its own explicitly activated task. Treat every child token, ledger, close question, and raw handoff as internal to that child when synthesizing in the parent; never copy it into the parent's final or use it as the parent's lifecycle state.

### Mandatory Writer Coordination Gate

Before creating a writer worktree or invoking any writer handle, read [patterns.md](references/patterns.md) and build one writer map covering every nonterminal writer and every writer planned for the current wave. The reference owns the complete shared-tree, dirty-path, worktree, overlap, integration, conflict-resolution, and cleanup procedure. Keep these invariants in the main control loop:

1. Record each owned file as one canonical repository-root-relative POSIX path, its logical edit scope, expected interfaces, and invariants. Resolve aliases and reject non-file or non-portable paths.
2. Classify every same-path pair as shared-tree overlap, accidental isolated overlap, or controlled isolated overlap.
3. Shared-tree overlap is forbidden. Serialize overlapping shared writers after the earlier writer is terminal and audited.
4. For two or more possible concurrent writers, plan one isolated worktree per writer by default, but create none before explicit user approval. If worktrees are unavailable or declined, serialize writers.
5. Approved worktrees permit a recorded controlled-overlap group, including bounded same-file or same-hunk work. Record the shared base, distinct checkouts, combined intent, contracts, integration order, and resolver before dispatch.
6. Treat every pre-existing or unattributed dirty path as user-owned. Worktree approval isolates execution but never authorizes integration over those paths.
7. Settle each terminal, audited writer by integrating its patch—including any reconciliation into the shared base—or explicitly abandoning it. Integrate at most one writer per operation. Apply each integrated patch from its recorded base, three-way reconcile later controlled-overlap patches against the updated integration state, then verify the combined diff, interfaces, invariants, and tests after every group member is settled. A clean Git merge is not enough.

Do not switch isolation silently, invent a second overlap permission after worktrees were already approved, or ask the user to resolve ordinary code conflicts. Escalate only genuinely ambiguous or incompatible product intent.

## Dispatch And Handoff

Before delegating work, read [packets.md](references/packets.md). It owns the complete dispatch and handoff structures for leaves and explicitly authorized child coordinators.

Every dispatch records the current goal and requirement revision, role, confirmed context, exact scope and ownership, interfaces and invariants, isolation, exclusions, inherited authority, acceptance checks, and return contract. Explicitly prohibit edits for read-only work. Tell writers to preserve unrelated changes and identify any controlled-overlap group.

Authority comes from the user request, repository instructions, and host policy. A packet may convey or narrow it, never expand it. Do not ask again for ordinary in-scope work already allowed, but never infer authority for installs, device actions, commits, pushes, deployments, external writes, destructive actions, or work beyond the assigned scope.

Handoffs and all delegation wrappers, tool or thread payloads, schemas, command output, and lifecycle state are internal. Verify important claims against actual artifacts, then synthesize natural user-facing prose with the outcome, evidence, changed paths, checks, risks, and next action. Provide explicitly requested evidence only after redacting secrets and host metadata. Emit host-required control syntax only in its exact designated form. Otherwise, the only user-facing lifecycle artifact is the current task coordinator's opaque plain-text resume handle when required by the continuity rule above; never copy a child's lifecycle state into the parent response.

## Failure And Cancellation

- Retry a failed spawn at most once when the failure appears transient. Then mark that slot failed and continue exact accounting.
- Report hung workers instead of waiting forever.
- On urgent redirection, interrupt only agents whose work became invalid; queue compatible changes for context-rich agents.
- On a user-authored explicit live-session stop or valid close confirmation, enter `STOPPING`, stop new waves, interrupt or settle active workers, inspect partial changes, account for results, and close workers when supported.
- Confirm all controllable workers are closed and shared-tree writers reached a terminal state before completing shutdown. Otherwise remain `STOPPING`, mark the tree unstable, prohibit further repository operations, and report the live-worker risk. Ask a distinct hand-back question after that disclosure; do not reuse close confirmation or the explicit stop as acceptance. Move to `OFF` with an uncontrollable writer live only after a later user-authored direct acceptance while `STOPPING`.
- A result arriving during `STOPPING` is still part of shutdown: audit it before deciding whether `OFF` is safe. A result arriving after `OFF` does not reopen the session or get integrated automatically. Ignore an ordinary read-only late result; report any late write, ownership conflict, or material safety finding, mark the tree unstable when applicable, and require a new explicit session for follow-up work.
- Trust the tree over a worker's changed-path report. Freeze conflicting dispatch and reconcile ownership on mismatch.

## Completion Standard

### Verification

Before a one-shot final or live completion candidate, verify:

- [ ] the latest requirement revision is addressed and every requested slot is accounted for
- [ ] changed artifacts and high-impact claims were checked directly, not accepted only from handoffs
- [ ] writer ownership, controlled overlaps, integration order, combined contracts, and focused tests are settled
- [ ] the user-facing synthesis contains no raw delegation, tool, thread, ledger, or lifecycle payloads

In one-shot scope, audit the bounded result, settle all controllable workers, report completion or blockers, and deactivate in that response without a close question.

While a live session is `ACTIVE`, form a completion candidate only when the latest requirement revision is addressed, no relevant user delta remains unprocessed, all requested slots are accounted for, queued and held work is resolved or explicitly handed back, authorized changes are audited or integrated, and important claims are verified. Perform the final audit, present the synthesis and residual risks, ask for close confirmation, and remain `ACTIVE` while awaiting the answer.

Enter `STOPPING` only after valid direct confirmation or an explicit stop command. Complete the safe shutdown checks, return the final handoff, move to `OFF`, and deactivate Relay Orchestra. Milestone updates and completion candidates do not deactivate it.
