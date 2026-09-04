---
task: "Start a bounded Relay Orchestra review in lite, then add a material requirement while its agents are still active. Preserve already returned evidence and safely continue under the required mode."
baseline_failure: "A bounded coordinator may keep lite mechanics after the task becomes cross-turn or invalidate useful evidence during transition."
runs: 3
assertions:
  - "Promote from lite to full before routing the changed requirement to active work."
  - "Preserve valid returned evidence, exact agent accounting, ownership, and unresolved obligations."
  - "Do not silently demote back to lite during the invocation."
  - "Do not claim completion until the changed requirement is verified."
---

Promotion changes the control contract, not the truth status of already audited evidence.
