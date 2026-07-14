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

1. Build an ownership map across nonterminal and same-wave writers; assign exactly one possible active owner per exact path.
2. Record shared interfaces and invariants.
3. Identify coordinator-only files.
4. If two or more writers could run together, plan one worktree per writer and obtain explicit approval before creation; otherwise use the shared tree.
5. Define audit or integration order.

If two workstreams need the same file, do not create or dispatch the second writer concurrently. Serialize them or give the file to one owner while the other returns read-only recommendations. Treat this as a mandatory pre-dispatch gate even when the user requests simultaneous writers, specifies an exact agent count, or approves worktrees. Worktree isolation does not relax this rule.

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

### Before Dispatch

1. Record every owned file as one canonical repository-root-relative POSIX path plus expected interfaces and invariants.
2. Reject absolute or worktree-specific paths, globs, directories, `.`/`..`, Windows-reserved characters or device names, and path components ending in a dot or space.
3. Resolve Unicode, hardlink, symlink, and case aliases to one logical identity before comparison.
4. Build and audit the ownership map before creating a writer worktree or invoking its handle.
5. Keep one possible active owner per canonical path per wave, even with worktrees. If a path overlaps, hold the later writer until the current owner is terminal and audited.

### Integration

Worktrees isolate checked-out files, not semantic, API, schema, external-state, or integration conflicts.

1. Integrate exactly one isolated writer per operation after its terminal result and coordinator audit.
2. Record its writer ID, re-inspect shared-tree status, and compare that writer's canonical owned paths with the currently protected dirty paths.
3. Worktree approval alone never authorizes integration over dirty user paths. Block an overlapping stream, but allow an independent stream to integrate.
4. A user authorization or coordinator reconciliation clears only its exact named dirty paths; all other overlaps remain protected. Ownership narrowing is valid only before isolated work has produced changes on an overlapping path.
5. Validate recorded contracts and retain worktrees until integration or explicit abandonment. Remove task-created worktrees after verified integration when cleanup is authorized.

## Synthesis

Normalize results into confirmed consensus, meaningful disagreement, verified evidence, unresolved blockers, agent accounting, and the next action. Do not paste full reports.

## Anti-Patterns

- A fixed maximum agent count imposed by the skill
- Silently reducing the requested total
- Decorative agents without a lens, partition, or ownership
- Nested subagent trees
- Concurrent writers sharing overlapping paths
- Treating a branch in one checkout as isolation
- Worktree creation without approval
- Raw transcript forwarding
- Completion based only on worker summaries
- Implicit or always-on activation outside an explicitly opened live session
