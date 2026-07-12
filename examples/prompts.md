# Prompt Examples

## One reviewer

```text
Use Relay Orchestra for this request only. Run one isolated read-only reviewer.
```

## Three lenses

```text
$relay-orchestra run three read-only agents: regressions, architecture, and tests.
```

## Fifteen agents

```text
Use Relay Orchestra for this request only. Run fifteen focused reviewers,
using capacity waves if the client cannot run all fifteen simultaneously.
```

## Disjoint implementation

```text
$relay-orchestra split this change among four writers with disjoint ownership.
Use the shared tree and show the ownership map first.
```

## Worktree opt-in

```text
Use Relay Orchestra. I approve one isolated worktree per concurrent writer.
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
