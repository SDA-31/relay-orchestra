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

## Let Relay Choose The Plan

```text
$relay-orchestra Review the current changes and verify the important findings.
```

No effort label or agent count is required. Relay chooses useful roles from the task and context, keeps small linear work local, and may revise its own allocation as evidence develops. This bounded invocation does not enable Auto for later tasks.

## Steer Effort In Ordinary Language

Once Auto is enabled for the relevant work, later requests can be as short as these. Without Auto, explicitly invoke Relay with the task.

| Wording | Intended direction |
| --- | --- |
| “Use your judgment.” | Normal adaptive planning; no special effort tier. |
| “Give this a more thorough pass, without going all-out.” | Increase useful effort relative to the current approach. |
| “Keep this one lean; focus on the evidence that changes the decision.” | Reduce optional exploration while retaining required checks. |
| “This is urgent. Investigate thoroughly and give me two lines.” | Prioritize speed and depth; keep the answer short. |
| “Use maximum effort on this audit; don't economize on tokens.” | Expand useful coverage, depth, verification, or parallel work, including large teams and capacity waves when justified. |
| “Keep going until the agreed work is finished.” | Persist within the accepted scope and permissions. |

These are examples, not commands or named modes. Equivalent wording in another language works too: “чуть плотнее, но без фанатизма” asks for a relative increase; “жги на максимум, не жалей токенов” signals maximum useful effort. A quoted or negated phrase does not request that behavior. “Жги” after an estimate-only plan means continue that estimate.

Required project checks stay in place at every effort level. Maximum effort does not select the Full lifecycle, grant new permissions, or require filling every available worker slot.

## Set A Chat Default And Override One Task

After enabling Auto:

```text
For later tasks in this chat, keep the work economical.
```

Then, for one task:

```text
For this audit, use maximum effort, but no more than three workers.
```

The next ordinary task returns to the economical default. The three-worker ceiling applies to this audit. Effort preferences alone do not enable Auto or transfer to another chat or a child task; retention depends on the client preserving the context.

## State Numeric Bounds When They Matter

| Request | Meaning |
| --- | --- |
| “Run exactly three workers for this audit.” | Three is both the target and the cumulative ceiling. |
| “Use up to three workers for this audit.” | Three is a ceiling; fewer may be appropriate. |
| “Use at least five workers for these independent reviews.” | Five is a floor; use capacity waves if needed. |
| “Use three agents total, including yourself.” | Allow two delegated workers plus the coordinator. |

Unqualified counts normally mean delegated workers, excluding the coordinator. Completing, closing, cancelling, or replacing a created worker does not replenish a cumulative ceiling; a replacement counts as another handle. Reusing an existing handle adds no count. Relay explains insufficient useful work instead of inventing assignments just to fill an exact target.

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
