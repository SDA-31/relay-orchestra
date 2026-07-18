# Prompt Examples

## One reviewer

```text
Use Relay Orchestra for this message only. Run one isolated read-only reviewer.
```

## Three lenses

```text
Start a live $relay-orchestra session with three read-only agents: regressions,
architecture, and tests.
```

## Fifteen agents

```text
Start a live Relay Orchestra session with fifteen focused reviewers,
using capacity waves if the client cannot run all fifteen simultaneously.
```

## Disjoint implementation

```text
Start a live $relay-orchestra session and split this change among four writers.
Use the shared tree and show the ownership map first.
```

## Worktree opt-in

```text
Start a live Relay Orchestra session. I approve one isolated worktree per
concurrent writer.
```

## Controlled same-file work

```text
Start a live Relay Orchestra session. I approve one worktree per concurrent
writer. Let the authentication and retry writers edit src/client.ts in parallel,
then reconcile both patches and test the combined behavior.
```

## Stop

```text
Stop Relay Orchestra. Stop new waves, close active workers safely, report
partial changes, and do not apply these rules to later messages.
```

## Mid-run changes

```text
Move account security above preferences. Send this to the existing screen
implementer; do not restart the research agents.
```

```text
Keep the animation idea for the next iteration. Add an accessibility reviewer
as soon as the implementation agent finishes.
```
