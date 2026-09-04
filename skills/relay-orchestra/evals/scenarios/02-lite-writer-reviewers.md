---
task: "Invoke Relay Orchestra for a one-shot bounded documentation change. One writer owns one exclusive file; two reviewers are read-only and review the result. Require coordinator verification and an explicit incomplete report if anything cannot be checked."
baseline_failure: "Full writer mechanics and repeated probes are disproportionate for one writer with read-only reviewers and a bounded scope."
runs: 3
assertions:
  - "Select lite one-shot with at most one writer and exclusive non-overlapping scope."
  - "Reviewers do not write, and every dispatch has the five required packet slots."
  - "Inspect and independently verify the writer artifact rather than trusting its summary."
  - "Do not use worktree/integration machinery, a ledger, a close handshake, or repeated polling."
  - "Do not report completion when verification or required work is incomplete."
---

The writer owns the file; reviewers return read-only findings to the coordinator.
