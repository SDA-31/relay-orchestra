---
task: "Use Relay Orchestra for a background multi-turn migration that remains active overnight; during execution, requirements may change and the resume handle/cancellation primitive may be unknown."
baseline_failure: "Simple work was kept ACTIVE with a close question, while unstable handles and changing requirements create continuity obligations."
runs: 3
assertions:
  - "Select full before unsafe dispatch because long-running, cross-turn, changing-requirement, and unstable-capability signals are present."
  - "State the concrete cross-turn or capability reason and that the current run is Full live."
  - "Do not silently demote to lite."
  - "Route lifecycle/continuity to references/live-session.md and unknown clients or capabilities to references/platforms.md when applicable."
  - "Do not guess an opaque resume handle or cancellation primitive."
---

The explicit live lifecycle and uncertainty signals must override the lite default.
