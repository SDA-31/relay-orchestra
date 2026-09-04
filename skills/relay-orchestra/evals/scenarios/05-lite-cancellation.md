---
task: "Explicitly use Relay Orchestra for a bounded one-shot task with one writer and one read-only reviewer. Cancel after the bounded wait; audit partial writes and disclose any late writer result without integrating it automatically."
baseline_failure: "A false-completion path can treat worker summaries as success and ignore partial or late writes."
runs: 1
assertions:
  - "Keep the run lite unless cancellation handling reveals an actual capability ambiguity requiring promotion."
  - "Settle or interrupt controllable workers and audit partial writes."
  - "Disclose late writes and do not integrate them automatically."
  - "Report incomplete or blocked status when verification did not finish; never claim false completion."
  - "Ask no close question and do not leave lite active across turns."
---

Cancellation is a correctness gate, not a successful completion signal.
