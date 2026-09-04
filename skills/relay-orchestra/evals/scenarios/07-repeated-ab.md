---
task: "Run each bounded and unsafe Relay Orchestra scenario against the new lite/full router and the aa4e907 baseline in fresh contexts, three times per scenario, and compare correctness and mandatory context/actions."
baseline_failure: "The baseline pays full mechanics on simple tasks and has an unsafe shared-path writer branch."
runs: 3
assertions:
  - "New and baseline variants tie or win on correctness for every scenario."
  - "The lite variant materially reduces mandatory instruction files, probes, waits, state creation, and close questions on simple scenarios."
  - "Multiple writers, overlap/worktrees, lifecycle, and unstable-capability cases retain full guarantees."
  - "Record selected mode, context/actions, verification outcome, and false-completion count per run."
---

Use the same prompts and measurement fields for both variants; do not give either variant the intended answer.
