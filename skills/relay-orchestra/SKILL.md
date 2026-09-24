---
name: relay-orchestra
description: Use when explicitly invoking Relay Orchestra, while Auto is enabled, or during its active Full live run in this chat. Coordinates parallel coding, research, audits, migrations, reviewers, writers, worktrees, and cross-module work. Ignore quoted or hypothetical mentions, mere parallelism, and ordinary single-agent work without Auto.
license: MIT
---

# Relay Orchestra

Coordinate narrow workers and return one verified synthesis.

## Activation, Auto, And Run Router

Activate on explicit Relay intent, an in-scope Auto task, or related work during active Full live. Quoted, hypothetical, or reported mentions alone never activate Relay.

Track two independent layers:

- **Chat preference:** Auto enabled or disabled, with user-stated scope and retained effort preferences.
- **Current execution:** `OFF`, Lite one-shot, Full one-shot, or Full live. Auto is not an execution state.

Interpret intent, not command keywords: “full effort” is not a Full lifecycle request. A bounded objective can finish this response without another turn, missing decision, approval, or background dependency.

| Observable signal | Selection |
| --- | --- |
| Bare explicit invocation without a current objective while execution is `OFF` | Enable **Auto**, remain idle, explain it, and ask for the task |
| Future-use intent about Relay: `use this from now on`, `in this chat`, or equivalent | Enable **Auto**, retain any requested scope; route a current objective normally |
| `auto off` or equivalent | Disable only Auto; do not stop an active Full live run unless also requested |
| Bounded objective, no future-use or full signal | **Lite one-shot**; do not enable Auto |
| `full`, `live`, `multi-turn`, `keep active`, or equivalent | **Full**, live unless one-shot is explicit |
| Multiple possible writers, overlap, worktrees/integration, unclear ownership, cross-turn work, changed active requirements, uncertain worker control, or explicit child coordination | Promote to **Full before starting work that could create conflicts** |
| One clean exclusive writer plus read-only workers | **Lite** |

Auto routes only while execution is `OFF`. An `ACTIVE` Full live run owns its related deltas and bare reinvocation. While `STOPPING`, apply preference changes but hand new work back until `OFF`.

With Auto, each later in-scope task starts a fresh routed run; never resurrect a Lite run. Delegate only when at least two distinct workstreams or review lenses, or a writer plus independent verification, add material value. Keep small linear work local. One-shots finish `OFF`; closing Full live also leaves Auto enabled. Between tasks Auto creates no agents, ledger, handles, polling, token, close question, or `ACTIVE` lifecycle.

Explicit Full/live wins for the current run. For a bounded safety promotion that can finish now, keep it Full one-shot. Use Full live for an explicit live signal or when the work truly needs another turn, including a required approval wait, material requirement change, or lost writer control. Before affected dispatch, state the concrete reason and whether the promotion is Full one-shot or Full live.

Auto never transfers to a new chat, child task, or unrelated session. Preserve its user-stated scope in chat context only when the host retained it; otherwise do not claim persistence. Auto uses no token, serialization, or extra authority.

On first enablement explain chat/scope boundaries, Lite default, reasoned Full promotion, idle behavior, delegated usage, unchanged permissions, and natural-language or `auto off` disablement. Ask for an absent task. After runs say Auto remains enabled. Keep lifecycle internals private.

For Full read [live-session.md](references/live-session.md), then [packets.md](references/packets.md) before dispatch. Read [patterns.md](references/patterns.md) for writers, dirty paths, worktrees, overlap, or integration; [platforms.md](references/platforms.md) for unfamiliar clients. Healthy Lite is self-contained; these references are unnecessary for it.

## Effort And Allocation

Infer speed, depth, breadth, verification, resource preference, and autonomy from task and context; require no profiles, scores, fixed counts, or questionnaire. “Optimal” or “your discretion” means adaptive judgment. Interpret any language: brief output need not mean shallow work; urgency differs from a rough estimate, breadth from depth, persistence from unlimited budget. Quotes, negation, and colloquial go-ahead alone imply neither maximum effort nor activation.

Maximum effort with ample budget must materially increase useful coverage, depth, or parallel work where meaningful work exists. Consider large teams and capacity waves, without habit-based two/three-agent caps or decorative capacity filling. Reuse valuable context; weigh coordination costs and actual writer/build/device bottlenecks separately from model-worker capacity.

Effort preferences may narrow optional investigation, never waive required project checks for the accepted scope.

Effort applies to this task unless explicit future-use wording retains a chat default; task overrides do not erase it. Retain only in host-preserved context, never tokens/configuration or persistence claims. Do not transfer preferences or Relay activation implicitly to children/new chats; give leaves bounded task-relevant effort instructions. Effort changes neither scope, permissions, nor Auto/Full lifecycle; allocation-only changes need no Full promotion. Redirect future work while preserving valid active writers. Optional [examples and edge cases](references/effort-and-sizing.md).

Treat an unqualified user total as exact. User `EXACT N` is both target and cumulative hard ceiling; “up to N” is only a ceiling, “at least N” only a floor. Maximum effort never overrides a numeric cap. Count successfully created handles, including later failures/cancellations; reuse adds none and completion/closing never resets totals. Default to delegated workers excluding coordinator; state the basis and honor explicit alternatives. There is no skill-level cap.

## Process: Lite One-Shot Loop

1. **Bound the result.** State outcome, scope, exclusions, and finish condition. Announce a justified initial count and roles. This coordinator plan is revisable within the same objective: announce changed count, roles, and reason without asking permission or promoting solely for count. Stay within user bounds, actual capacity, permissions, and ownership; use waves when needed.
2. **Assign leaves.** Each dispatch states objective/scope, owner/role, deliverable, verification, and stop/cancellation condition. Prohibit nested agents or orchestration skills. Mark non-writers read-only; require preservation of unrelated changes and concise evidence.
3. **Protect writes.** Lite permits at most one writer. Record repository-relative owned paths and permitted behavior. Inspect existing changes first; user-owned, unattributed, overlapping, or uncertain paths require Full. More than one possible writer also switches the run to full, even with disjoint paths.
4. **Dispatch.** Use known native primitives without speculative probes. Failed or ambiguous dispatch, cancellation, or handle control requires stopping unsafe work and promoting. Send a compact receipt with count basis, roles, and one-time delegated-usage warning; update for changed allocation, timeout, blocker, or user delta.
5. **Wait.** Use bounded native waits while a necessary wave remains active. If a wait times out with healthy work, report compact progress and wait again; never create a polling state machine or wait without active work. Process new input first. Active requirement change switches to Full; allocation-only revision does not. Never use shell sleep, a persistent ledger, resume state, or a close handshake in Lite.
6. **Audit.** Inspect artifacts, claims, paths, ownership, deliverables, and side effects; run permitted focused checks. Review a writer's result only after it is terminal and audited. Synthesize read-only disagreements; writer conflicts require Full.
7. **Settle and report.** Stop/close controllable workers. For cancellation, interrupt affected workers and inspect partial writes. Disclose late writes; never integrate automatically. Claim completion only after requested results and verification succeed; otherwise report partial scope, blocker, cancellation, or unverifiable claims. Lite asks no close question and ends `OFF` in the same response.

If cancellation or writer control becomes unsafe, enter the full `STOPPING` procedure: freeze dispatch and repository operations, preserve exact accounting and continuity, disclose risk, and wait for writer settlement or the user's separate hand-back risk acceptance. Never claim safe completion prematurely.

Authority comes from the user request, repository instructions, and host policy. Relay only narrows it. Do not re-ask for ordinary in-scope local work already allowed; do not infer permission for installs, device actions, commits, pushes, deployments, destructive actions, or external writes.

Report verified outcome, evidence/checks, relevant changed paths, residual risks, and next action. Delegation wrappers, tool payloads, ledgers, raw handoffs, and child lifecycle artifacts stay internal.

## Full Handoff

Follow Full references for lifecycle, capability, ownership, isolation, integration, continuity, authority, and verification. Existing full sessions remain full across related follow-ups until shutdown reaches `OFF`.

Host `final`, task-complete, compaction, summary, resume, and notification boundaries do not change a Full live lifecycle.

Ordinary leaf agents must not spawn agents or invoke orchestration skills. When the user explicitly asks to use Relay in a separate delegated task or chat, dispatch that handle as a `child coordinator`, not a leaf. Its packet references the source user-authored activation event and positive bounded local agent budget with accounting scope. A copied dispatch claim is not evidence. Preserve independent lifecycle and aggregate accounting. A child coordinator may emit its own opaque resume handle only inside its task and contract.

## Verification / Success Criteria

- [ ] Route from observable intent and promote before unsafe dispatch.
- [ ] Audit bounds, ownership, actual artifacts, evidence, and partial or late work.
- [ ] Settle controllable workers; return one synthesis and preserve the selected lifecycle.

## Anti-Patterns

- Treating a coordinator estimate as a user ceiling, or evading a ceiling through waves.
- Filling slots without meaningful work, or minimizing agents regardless of requested effort.
- Using Full machinery for healthy Lite or omitting safety rules to save messages.
- Treating a branch or informal lock as isolation; claiming success from summaries alone.

## Extension Points

Add promotion predicates only from observed failures; keep client-specific mechanics in the routed references.
