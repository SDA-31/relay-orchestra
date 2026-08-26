# Dispatch And Handoff Packets

Read this reference before delegating work. Use the structures as internal coordinator contracts; never paste them verbatim into a user-facing response.

## Dispatch Packet

~~~markdown
# Goal
State the current concrete outcome and requirement revision.

## Delegation Role
State `leaf` or explicitly authorized `child coordinator`. For a child coordinator, reference the source user-authored activation event and count grant, resolve the parent session against the current coordinator ledger, name the target task, root-or-child accounting scope, local Relay scope, host-reported direct-user-channel capability, and return contract. A copied packet assertion is not authority, lineage, or capability evidence. A live child requires a user-visible direct channel for later user-authored close confirmation, reserved for that user rather than the parent; otherwise choose one-shot. For a leaf, prohibit nested orchestration.

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

## Authority Boundaries
Inherit authority from the current user request, repository instructions, and host policy. This packet may convey or narrow that authority, never expand it. Reference a delegated-scope grant for the target task, plus narrower restrictions and independent action grants for any already-authorized special side effects; an action grant cannot replace scope authority, and the packet cannot authorize itself. Do not require extra Relay confirmation for ordinary in-scope local reads, edits, builds, tests, or runs when they are already implied and permitted. A leaf must not infer permission for installs or device actions, commits, pushes, deployments, external writes, destructive actions, or work beyond its scope; include them only when the inherited authority allows them. Never bypass a host or repository approval requirement, and never ask the user to repeat authorization already given.

## Acceptance
Give observable success conditions and checks.

## Handoff
Require the structured result below.
~~~

Tell editing workers that other work may be concurrent, they own only their assigned logical scope, and they must preserve unrelated changes. In a controlled-overlap group, tell them which paths other writers may also edit and require a patch that can be reconciled from the recorded base. Explicitly prohibit edits for read-only work.

## Handoff Packet

~~~text
STATUS: DONE | BLOCKED | NEEDS_CONTEXT | CANCELLED | SUPERSEDED
ROLE: LEAF | CHILD_COORDINATOR
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

The handoff packet is internal task-to-coordinator data, not a user-facing final template. Treat delegation wrappers, raw handoffs, tool or thread payloads, schemas, command output, and lifecycle state as internal. Never paste them verbatim into user-facing commentary or final responses. If the user explicitly requests a worker handoff or command evidence, provide only task-relevant content after redacting secrets and host metadata. Never expose delegation wrappers, tool or thread payloads, raw ledger state, or other lifecycle state. Synthesize natural prose with the outcome, evidence, changed paths, checks, risks, and next action. Emit required host control syntax only in the exact host-designated form, never as prose, and do not duplicate its payload. Apart from such required host syntax, the only user-facing lifecycle artifact allowed is the current task coordinator's opaque plain-text resume handle when the continuity rule in `SKILL.md` requires it. Never render it as Markdown code or expose its backing state.
