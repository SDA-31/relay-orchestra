---
task: "Explicitly use Relay Orchestra for a bounded task: ask two narrow read-only researchers to inspect supplied API docs from different angles, then synthesize a recommendation with citations in one shot."
baseline_failure: "Full orchestration adds repeated capability probes, polling, persistent state, and a close question to a simple read-only fanout."
runs: 3
assertions:
  - "Select lite one-shot and keep one coordinator responsible for synthesis and final verification."
  - "Use narrow non-overlapping roles and all five packet slots: scope, owner, deliverable, verification, and stop/cancellation."
  - "Do not create a persistent ledger/state machine or perform speculative capability probes."
  - "Wait only while a necessary wave is active; a healthy timeout may produce compact progress and another bounded wait, but no polling state machine."
  - "Base the final recommendation on inspected evidence, not worker summaries alone."
---

The run must report a verified one-shot result or an explicit blocker/incomplete state.
