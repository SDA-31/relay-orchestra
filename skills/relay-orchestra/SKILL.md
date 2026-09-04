---
name: relay-orchestra
description: Use when explicitly invoking Relay Orchestra, while Auto is enabled, or during its active Full live run in this chat. Coordinates parallel coding, research, audits, migrations, reviewers, writers, worktrees, and cross-module work. Ignore quoted or hypothetical mentions, mere parallelism, and ordinary single-agent work without Auto.
license: MIT
---

# Relay Orchestra

Act as coordinator. Keep workers leaf-only; return one verified synthesis, not raw handoffs.

## Activation, Auto, And Run Router

Activate after explicit invocation, an unambiguous Relay request, a later in-scope Auto task, or a related task during active Full live. Quoted, hypothetical, or reported mentions without Auto are not activation.

Track two independent layers:

- **Chat preference:** Auto is enabled or disabled for this chat, with any user-stated scope.
- **Current execution:** `OFF`, Lite one-shot, Full one-shot, or Full live. Auto is not an execution state.

Natural-language intent is primary; commands are examples. A bounded objective can finish now without planned steering, background dependency, missing decision or approval, or another turn.

Apply preference changes separately from current-task routing:

| Observable signal | Selection |
| --- | --- |
| Bare explicit invocation without a current objective while execution is `OFF` | Enable **Auto**, remain idle, explain it, and ask for the task |
| `use this from now on`, `for later tasks`, `in this chat`, or equivalent | Enable **Auto**, retain any requested scope; route a current objective normally |
| `auto off`, `stop using this for later tasks here`, or equivalent | Disable only Auto; do not stop an active Full live run unless the user also targets that run |
| Bounded objective, no future-use or full signal | Fresh **Lite one-shot**; do not enable Auto |
| `full`, `live`, `multi-turn`, `keep active`, or equivalent | **Full** for the current run; use live unless one-shot is explicit |
| Multiple possible writers, overlap, worktrees/integration, unclear ownership, cross-turn work, changed active requirements, uncertain worker control, or explicit child coordination | Promote to **Full before starting work that could create conflicts** |
| One clean exclusive writer plus read-only workers | **Lite** |

Auto routes only while execution is `OFF`. An `ACTIVE` Full live run owns its related deltas; a bare invocation preserves that run, and Auto never starts a competing execution. While `STOPPING`, apply explicit preference changes but hand new work back until `OFF`.

With Auto enabled, each later in-scope task starts a fresh routed run; never resurrect a Lite run. Delegate only when at least two distinct workstreams or review lenses, or a writer plus independent verification, add material value. Keep small linear work local. Lite and Full one-shot finish `OFF` while Auto remains enabled; closing Full live also leaves it enabled. Between tasks Auto creates no agents, ledger, handles, polling, token, close question, or `ACTIVE` lifecycle.

Lite is always one-shot. Full may be one-shot or live. Explicit Full/live wins for the current run; a real safety requirement may still promote Lite. If a bounded task switches to full mode only for writer, ownership, isolation, integration, or capability safety and can still finish in the current response, keep it Full one-shot. Use Full live for an explicit live signal or when the work truly needs another turn, including a required approval wait, a material requirement change during active work, or unexpected loss of writer control. Before affected dispatch, state the concrete reason and whether the promotion is Full one-shot or Full live.

Auto never transfers to a new chat, child task, or unrelated session. Preserve its user-stated scope in chat context, including after compaction only when the host retained it; otherwise do not claim persistence. Auto uses no token, serialization, or extra authority.

On first enablement, state its chat/scope boundary, Lite default, reasoned Full promotion, idle behavior, delegated usage, unchanged permissions, and natural-language or `auto off` disablement. Ask for the task when absent. After a run, say compactly that Auto remains enabled. Never expose raw state, a ledger, JSON, or lifecycle tokens.

When Full is selected, read [live-session.md](references/live-session.md). Before Full dispatch, read [packets.md](references/packets.md). Also read [patterns.md](references/patterns.md) for a writer, dirty path, worktree, overlap, or integration; read [platforms.md](references/platforms.md) only for an unfamiliar client. Healthy Lite is self-contained: do not load these Full references.

## Process: Lite One-Shot Loop

Use this complete loop only when the router selects lite:

1. **Bound the result.** State the concrete outcome, in-scope files or questions, exclusions, and finish condition. Treat a user-specified agent total as an exact ceiling. Otherwise choose the smallest justified exact total before dispatch. Never exceed it; use waves when host capacity is lower.
2. **Assign narrow leaves.** Give every dispatch five explicit slots: objective/scope, owner/role, deliverable, verification, and stop/cancellation condition. Prohibit nested agents. Mark every non-writer read-only. Tell workers to preserve unrelated changes and return concise evidence, not lifecycle state.
3. **Protect writes.** Lite permits at most one writer. Record its repository-relative owned paths and the behavior it may change. Inspect current changes before dispatch. Paths that belong to the user, have an unknown author, overlap, or remain uncertain switch the run to full. More than one possible writer also switches the run to full, even when their planned paths look separate.
4. **Dispatch economically.** Use known native primitives without speculative probes. If dispatch, cancellation, or handle control fails or stays ambiguous, stop unsafe work and promote. Send one compact start receipt; add progress only for a wait timeout, blocker, or user delta. Include exact count, roles, and one-time usage warning.
5. **Wait only for active work.** Use bounded native waits while a necessary wave remains active. If a wait times out with healthy work, report compact progress and wait again; never create a polling state machine or wait without active work. Process new input before results. Active requirement change switches to Full; cancellation follows safe shutdown. Never use shell sleep, a persistent ledger, resume state, or a close handshake in Lite.
6. **Audit and verify.** Inspect actual artifacts and important claims rather than trusting worker summaries. Audit changed paths, scope, ownership, deliverables, and side effects; run the coordinator's permitted focused checks. Reviewers of a writer's result run only after that writer is finished and its changes are audited. Resolve read-only disagreement in the synthesis; writer conflicts require full.
7. **Stop workers and report.** Stop or close every worker Relay can control. If cancelled, interrupt affected workers, inspect partial writes, and report incomplete scope. Disclose unexpected late writes and never integrate them automatically. Call the task complete only when the requested result and verification succeeded; otherwise report the blocker, cancellation, partial result, or unverifiable claim. Lite asks no close question and ends `OFF` in the same response.

If cancellation or writer control unexpectedly becomes unsafe after dispatch, enter the full `STOPPING` procedure: freeze new dispatch and repository operations, preserve exact accounting and continuity, disclose the risk, and wait until the writer is safely finished or the user accepts the separate hand-back risk. Do not claim that the one-shot ended safely.

Authority comes from the user request, repository instructions, and host policy. Relay may narrow it, never expand it. Do not re-ask for ordinary in-scope local work already allowed, and do not infer permission for installs, device actions, commits, pushes, deployments, destructive actions, or external writes.

The final response contains the verified outcome, concise evidence and checks, changed paths when relevant, residual risks, and the next action. Delegation wrappers, tool payloads, ledgers, raw handoffs, and child lifecycle artifacts stay internal.

## Full Handoff

Once full is selected, follow the routed references and preserve their lifecycle, capability, ownership, isolation, integration, continuity, authority, and verification rules. Fewer messages never justify omitting a required safety rule. Existing full sessions remain full across related follow-ups until their defined shutdown reaches `OFF`.

Host `final`, task-complete, compaction, summary, resume, and notification boundaries do not change a Full live lifecycle; follow the continuity rules in `live-session.md`.

Ordinary leaf agents must not spawn agents or invoke orchestration skills. When the user explicitly asks to use Relay in a separate delegated task or chat, dispatch that handle as a `child coordinator`, not a leaf. The full dispatch packet references the source user-authored activation event. A copied dispatch claim is not evidence. A child coordinator may emit its own opaque resume handle—a token used to continue unfinished work—only inside its task and contract.

## Verification / Success Criteria

- [ ] Route from observable signals; promote before unsafe dispatch.
- [ ] Account for agent ceilings, ownership, artifacts, deliverables, and partial or late work; inspect evidence and run permitted checks.
- [ ] Settle controllable workers; return one clean synthesis; end Lite `OFF` or preserve Full exactly.

## Anti-Patterns

- Using Full mechanics for a healthy bounded fanout, or keeping Lite active across turns.
- Dispatching a second, overlapping, or dirty-path writer in Lite.
- Treating an informal lock, branch, or readable token as verified isolation.
- Claiming success from summaries or hiding cancelled, partial, late, or unverifiable work.

## Extension Points

Add promotion predicates only from observed failures; keep client-specific mechanics in the routed references.
