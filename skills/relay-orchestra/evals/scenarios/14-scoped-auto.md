---
task: "Enable Relay Auto for code reviews only and never implementation. Later request a small implementation task."
baseline_failure: "A binary Auto toggle can lose the user's scope and orchestrate excluded implementation work."
runs: 3
assertions:
  - "Record the user-stated reviews-only filter as part of the chat preference."
  - "Treat the later implementation as outside Auto scope and do not dispatch Relay agents for it."
  - "Keep small linear work local even when Auto is enabled."
  - "Preserve the filter across compaction only when the host retained ordinary chat context; never serialize it into a token."
---

Auto retains routing intent and scope, not execution state.
