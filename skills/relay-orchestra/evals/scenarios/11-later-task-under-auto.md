---
task: "Assume Relay Auto was enabled earlier in this chat and the previous Lite run ended. Now give Relay a new suitable bounded comparison task."
baseline_failure: "A persistent preference can be confused with a still-running Lite session and resurrect old execution state."
runs: 3
assertions:
  - "Start a fresh Lite one-shot run without resurrecting prior agents, handles, evidence, or lifecycle state."
  - "Apply the ordinary safety router and promote only for a concrete current reason."
  - "End the bounded run and leave Auto enabled for the next suitable task."
  - "Keep the completion receipt compact and free of raw preference or lifecycle serialization."
---

Auto remembers routing intent, not a previous run.
