---
task: "Assume Relay Auto is enabled and a Full live migration is ACTIVE. Add a related test reviewer without explicitly starting another session."
baseline_failure: "Auto and Full live can both claim the follow-up, creating a competing run and duplicate accounting."
runs: 3
assertions:
  - "Route the related request into the existing Full live session; do not start a fresh Auto run."
  - "Preserve its handles, ledger, ownership, and agent accounting."
  - "A bare reinvocation while ACTIVE also preserves that Full live session."
  - "Auto remains a separate preference for after the live session closes."
---

Active Full live execution takes precedence over future Auto routing.
