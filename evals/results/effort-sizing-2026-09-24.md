# Effort and agent sizing evaluation — 2026-09-24

The repository skill now interprets natural-language effort and task context without requiring profiles or fixed team sizes. A coordinator's own staffing estimate is revisable; user exact totals, floors, and ceilings retain their distinct meanings. Required project verification remains mandatory.

## Observed behavioral change

The old version treated a coordinator-announced two-worker plan as a hard ceiling even when the user imposed none. Its recorded decision was: “Do not create a third handle under the current plan.” The candidate adds the useful third specialist within the same objective, announces the reason and revised count, and requires neither a new user grant nor Full promotion solely for that revision.

A fresh judge compared shuffled, unlabeled decisions for eight matched cases: **one candidate win, seven ties, no regressions**. The broad-audit case tied: twelve specialists in waves and four reused specialists were both defensible. More handles did not count as an improvement by itself.

The candidate also classified all twenty supplied trigger queries as expected: eleven positives, two held-out positives, and seven near misses.

## Verification and limits

- Project validator and all **140 unit tests** passed.
- SkillForge structure and documentation safety checks passed; **35/35 static checks** passed.
- Root skill body: **1,487 words**.
- Fresh adversarial review found no supported introduced blocker or should-fix issue. Its evidence limitations are retained below.

These were hypothetical decision probes, batched in one fresh context per version, followed by a separate blind judge. They were not independent repeated executions per scenario. Trigger groups were visible to the classifier; no full-roster selection experiment was run. This is a bounded adaptation of SkillForge's evaluation workflow, not completion of its full repeated execution protocol. The newly stored floor/capacity fixture was statically validated but was not one of the eight matched probes.

No claim is made about measured latency, token savings, or actual research quality. Those require representative real workloads. The supported conclusion is narrower: the observed self-imposed ceiling failure is fixed, and the sampled decisions did not regress.

Raw decisions, prompts, criteria, shuffled mapping, judgments, source hashes, trigger classifications, and review disposition are retained in [the evidence record](effort-sizing-2026-09-24.json). The old source is reproducible from commit `2e9e47bee39890be136a85e6deb2c88bfdb59795`.

This change updates repository source only. Installed Codex and Claude copies were not updated.
