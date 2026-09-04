# Prompt Examples

## Enable Auto For This Chat

```text
$relay-orchestra
```

```text
Use Relay Orchestra for suitable work from now on in this chat. I do not have a
concrete task yet.
```

Both enable an idle chat preference. They do not open a Full live session or launch agents.

## Run Now And Keep Auto Enabled

```text
$relay-orchestra Review the current diff with two read-only reviewers and
synthesize once. Keep using Relay for suitable later tasks in this chat.
```

The bounded review runs as a fresh Lite one-shot; Auto remains enabled afterward.

## Scope Auto

```text
Use Relay Orchestra automatically for code reviews in this chat, but never for implementation.
```

Later review tasks may use Relay when delegation adds value. Implementation stays outside this Auto scope unless Relay is explicitly invoked for it.

## One reviewer

```text
Use Relay Orchestra for this message only. Run one isolated read-only reviewer.
```

## Three lenses

```text
Start a live $relay-orchestra session with three read-only agents: regressions,
architecture, and tests.
```

## Disable Auto

```text
Stop using Relay for later tasks in this chat, but leave the current live session alone.
```

`auto off` is a shorter equivalent. Neither stops an active Full live session unless the request also targets that session.

## Keep Active Full In Charge

```text
The live Relay session is still active. Add one accessibility reviewer to the current work.
```

This joins the related work to the existing Full live session. Auto never opens a competing run.

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
