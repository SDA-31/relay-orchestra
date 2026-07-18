# Coordination Patterns

Read this reference when a run has dependencies, concurrent writers, overlapping paths, many requested agents, or a non-trivial integration step.

## Decision Matrix

| Question | Decision |
| --- | --- |
| One artifact, several independent perspectives? | Lens fanout |
| Independent modules or paths can change separately? | Workstream fanout |
| Some tasks consume outputs from other tasks? | Dependency waves |
| One investigation would consume excessive context? | Research isolation |
| Work is tiny, tightly coupled, or immediately blocking? | Keep it local unless the user explicitly requested an agent |

## Lens Fanout

Give every agent the same artifact and intent, but a different lens or partition. Keep lenses read-only. Remove duplicates, reject unsupported claims, and preserve well-evidenced minority findings.

For large counts, partition by module, user journey, risk class, time range, or evidence source. Record every requested slot even when multiple agents use the same broader lens.

## Workstream Fanout

Split by module, user flow, package, or explicit path ownership. Before dispatch:

1. Build a writer map across nonterminal and same-wave writers; classify every path overlap as shared, accidental isolated, or controlled isolated.
2. Record shared interfaces and invariants.
3. Identify coordinator-only files.
4. If two or more writers could run together, plan one worktree per writer and obtain explicit approval before creation; otherwise use the shared tree.
5. Define audit or integration order.

Treat the first step as exclusive ownership only in the shared tree. With approved worktrees, two useful workstreams may intentionally own the same path through a controlled-overlap group. Record each writer's logical edit scope, a shared base revision, the combined intended outcome, integration order, and resolution owner. Prefer disjoint files or symbols when that preserves useful parallelism, but do not serialize automatically when a bounded same-file overlap is the fastest coherent plan.

## Dependency And Capacity Waves

Use waves both for dependencies and client concurrency limits:

1. Give every task or agent slot a stable ID.
2. Record direct dependencies.
3. Dispatch all unblocked slots up to current capacity.
4. Gather and verify the wave.
5. Pass only confirmed outputs to dependent slots.
6. Continue until every requested slot is complete, failed, cancelled, or explicitly unstarted.

Reject dependency cycles. Do not create a graph for a small cohesive task.

## Worktree Strategy

### Shared Tree

Default to the shared tree for read-only agents and at most one active writer only when existing changes and new writes can be attributed safely. Before a shared writer starts, inspect repository status and treat every pre-existing or unattributed dirty path as user-owned until audited. Block overlapping ownership unless the user explicitly authorizes it; narrow the writer's paths or offer an isolated worktree. Recommend an approved worktree even for one writer when the tree is dirty, attribution is unreliable, independent builds are needed, or work is long-running.

Recheck status while a shared writer is nonterminal and before auditing its result. If a new user-owned or unattributed change overlaps its owned paths, interrupt it when possible, mark the tree unstable, and freeze overlapping operations until reconciliation. A worktree writer can finish in isolation, but its overlapping integration stays blocked.

### Concurrent Writers

If two or more agents could write at the same time, make one isolated worktree per writer the default plan. The plan is not creation authorization: explain that Git objects are shared while checked-out files, local dependencies, build outputs, and temporary-checkout cleanup add cost, then obtain explicit approval. Record a globally distinct checkout ID and confirmed base revision for each isolated writer; shared writers have no checkout ID.

Do not dispatch concurrent writers while approval is pending. If worktrees are unavailable or declined, serialize writers in the shared tree; start the next only after the previous writer is terminal and its changes are audited. A branch alone is not file isolation.

When switching an overlapping path from an isolated writer to a shared-tree writer, settle the isolated patch first: integrate it, reconcile it into the shared base, or abandon it explicitly. Record that disposition only after the isolated writer is terminal or cancelled and its actual result is audited. Terminal and audited status without patch disposition is insufficient.

### Before Dispatch

1. Record every owned file as one canonical repository-root-relative POSIX path plus expected interfaces and invariants.
2. Reject absolute or worktree-specific paths, globs, directories, `.`/`..`, Windows-reserved characters or device names, and path components ending in a dot or space.
3. Resolve Unicode, hardlink, symlink, and case aliases to one logical identity before comparison.
4. Build and audit the writer map before creating a writer worktree or invoking its handle.
5. Keep one possible active owner per canonical path in the shared tree.
6. For isolated writers, reject accidental overlaps but permit a recorded controlled-overlap group. Give every participant a distinct worktree from the same confirmed base and record its logical edit scope, combined intent, contracts, integration order, and resolver.
7. Allow even same-hunk work when its parallel value justifies the merge cost. Keep waves and the conflict surface bounded, avoid competing whole-file rewrites, and serialize only a repeatedly hot scope when reconciliation starts consuming more time than feature work.

### Integration

Worktrees isolate checked-out files, not semantic, API, schema, external-state, or integration conflicts.

1. Integrate exactly one isolated writer per operation after its terminal result and coordinator audit.
2. Record its writer ID, re-inspect shared-tree status, and compare that writer's canonical owned paths with the currently protected dirty paths.
3. Worktree approval alone never authorizes integration over dirty user paths. Block an overlapping stream, but allow an independent stream to integrate.
4. A user authorization or coordinator reconciliation clears only its exact named dirty paths; all other overlaps remain protected. Ownership narrowing is valid only before isolated work has produced changes on an overlapping path.
5. For a controlled-overlap group, preserve patches relative to the shared base. Apply the first stream, then three-way reconcile later patches against the updated integration state; never copy a later worktree's whole file over earlier work.
6. Resolve small ordinary conflicts in the coordinator. Prefer the recorded context-rich resolver for non-trivial same-hunk or cross-contract conflicts, but keep integration coordinator-authored: audit the resolver's patch or instructions before applying them. Ask the user only for ambiguous or incompatible product intent.
7. Treat a clean merge as insufficient evidence. Audit the combined diff, validate the combined interfaces and invariants, and test every participating workstream after the group is assembled.
8. Validate recorded contracts and retain worktrees until integration or explicit abandonment. Remove task-created worktrees after verified integration when cleanup is authorized.

## Synthesis

Normalize results into confirmed consensus, meaningful disagreement, verified evidence, unresolved blockers, agent accounting, and the next action. Do not paste full reports.

## Anti-Patterns

- A fixed maximum agent count imposed by the skill
- Silently reducing the requested total
- Decorative agents without a lens, partition, or ownership
- Nested subagent trees
- Unrecorded or shared-tree writers sharing overlapping paths
- Blindly overwriting an integrated file with a later worktree copy
- Treating a branch in one checkout as isolation
- Worktree creation without approval
- Raw transcript forwarding
- Completion based only on worker summaries
- Implicit or always-on activation outside an explicitly opened live session
