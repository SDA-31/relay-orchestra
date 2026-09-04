---
task: "While a Full live Relay session is active and Auto is enabled, ask in natural language to stop using Relay automatically for later tasks but keep the current live session running."
baseline_failure: "A single toggle can accidentally stop active work when the user intended only to disable future routing."
runs: 3
assertions:
  - "Disable only the chat-scoped Auto preference."
  - "Keep the current Full live lifecycle, handles, ledger, and work intact."
  - "Stop the live session only if the user separately and clearly targets that session."
  - "Acknowledge the preference change in plain language without raw state."
---

Preference control and live-session control are independent.
