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

1. Assign one owner per path for the current wave.
2. Record shared interfaces and invariants.
3. Identify coordinator-only files.
4. Confirm shared mode or obtain approval for worktrees.
5. Define audit or integration order.

If two workstreams need the same file, serialize them or give the file to one owner while the other returns recommendations.

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

Default to the shared tree and announce that changes appear there immediately. Use isolated worktrees only after explicit user request or approval. Explain that Git objects are shared but checked-out files, local dependencies, and in-tree build outputs may consume additional disk space.

Recommend worktrees when paths may overlap, the main tree is dirty, independent builds are required, attribution is unreliable, or writers may run for a long time. Use one separate checkout per concurrent writer. A branch alone is not file isolation.

For shared writers, audit actual changes after each result. For isolated writers, compare paths before integration, integrate one stream at a time, resolve conflicts from confirmed intent, and retain worktrees until integration or explicit abandonment. Remove task-created worktrees after verified integration when cleanup is authorized.

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
- Permanent session activation

## Related Work

The design is informed by public projects including Dimillian Skills, addyosmani/agent-skills, obra/superpowers, ZypherHQ/agent-orchestration-skill, am-will/codex-skills, and howells/arc. Relay Orchestra keeps only the portable coordination layer and does not require a fixed reviewer set, external CLI, run ledger, plan format, or GUI.
