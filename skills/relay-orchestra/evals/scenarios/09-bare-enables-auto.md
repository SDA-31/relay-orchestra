---
task: "Invoke $relay-orchestra with no objective, then wait for the coordinator's response."
baseline_failure: "The baseline opened a Full live ACTIVE session even though there was no current task."
runs: 3
assertions:
  - "Enable Auto only for the current chat and keep current execution idle."
  - "Launch no agents and create no ledger, handle, polling loop, resume token, close question, or active lifecycle."
  - "Explain Lite/Full routing, idle behavior, delegated-agent usage, unchanged permissions, and natural-language or auto off disablement."
  - "Ask for the task in plain language without raw JSON, state, or lifecycle tokens."
---

This is an idle preference transition, not an empty session.
