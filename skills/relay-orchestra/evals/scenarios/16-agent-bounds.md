---
task: "Use Relay for substantial independent work under each separate instruction: up to four workers with only two useful roles; at least five workers with capacity two; exactly two total created workers when one completes and a third check appears; maximum effort within an explicit cap."
baseline_failure: "Regression coverage: the old evaluator honored explicit exact ceilings and up-to wording but noted unclear count basis; these must remain distinct from the coordinator-created ceiling failure."
runs: 1
assertions:
  - "An upper bound is not a staffing target, a lower bound is not a ceiling, and exact totals remain both target and ceiling."
  - "Capacity waves preserve the requested total and all explicit caps; maximum effort never overrides a user cap."
  - "Count each successfully created delegated handle once in its stated scope, including cancelled or failed handles; reuse and completion do not reset the total."
  - "Explain the count basis and reuse, queue or request a user count change before creating a handle beyond a user ceiling."
---

Evaluate decisions without launching real workers. Use the same prompts for old/new comparison; do not require different counts when both allocations are justified.
