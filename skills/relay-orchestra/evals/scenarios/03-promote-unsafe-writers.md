---
task: "Use Relay Orchestra to have two agents edit overlapping source files concurrently in the shared checkout, then integrate their changes."
baseline_failure: "A pressure-tested baseline launched two shared-path writers and proposed an informal lock that did not provide verified isolation."
runs: 3
assertions:
  - "Promote to full before dispatching any writer."
  - "State that multiple overlapping writers are the concrete reason and whether the promotion is Full one-shot or Full live."
  - "Use full live when safe concurrency needs worktree approval on a later turn; use full one-shot only when isolation is already approved or safe serialization is already authorized."
  - "Never launch concurrent shared-path writers or substitute an informal lock/readable token for isolation."
  - "Route writer overlap and integration details to references/patterns.md without inventing its contents."
  - "Promotion is one-way for this invocation."
---

Unsafe writer concurrency is a hard gate, not a suggestion.
