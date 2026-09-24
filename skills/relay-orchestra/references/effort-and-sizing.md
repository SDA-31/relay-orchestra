# Effort And Agent Sizing

Optional guidance for ambiguous preferences or allocation decisions. The core policy in `SKILL.md` is sufficient for healthy Lite; no profile selection or reference-reading ceremony is required.

## Interpret The Work, Not Keywords

Infer the tradeoffs the user actually wants across speed, depth, breadth, verification, resource use, and autonomy. Use the objective, consequences, uncertainty, and available evidence. These dimensions can differ: a short final answer may require extensive investigation, and an urgent production diagnosis may need deep work on the critical path with independent checks running alongside it.

“Optimal,” “do your best,” or “use your discretion” leaves normal adaptive judgment. A request to persist until completion is not unlimited time, spending, authority, or scope. Do not turn preferences into named profiles, scores, fixed team sizes, a parser, or a configuration questionnaire. Clarify only a material unresolved conflict or missing requirement; continue independent authorized work when possible.

Effort preferences may reduce optional investigation or supplemental checks, but required project verification for the accepted scope remains mandatory. A short or economical task still needs its normal acceptance checks. Disclose any genuine inability to run them; do not relabel them optional to meet an effort preference.

Interpret meaning in any language and context. Quotes, negation, hypothetical examples, reported speech, and ordinary colloquial go-ahead are not maximum-effort instructions or Relay activation. A preference about effort never activates Relay by itself.

| User wording | Practical interpretation |
| --- | --- |
| “Be brief, but investigate thoroughly.” | Deep investigation, concise synthesis; do not reduce work to match answer length. |
| “I need this fixed quickly; verify the risky paths.” | Prioritize the critical path and targeted verification; parallelize useful independent checks. |
| “Just a rough estimate for now.” | Bound precision and verification to an explicitly provisional estimate. |
| “Cover all plausible causes independently.” | Broaden independent lenses or partitions, then reconcile evidence. |
| “Dig deeply into this one failure.” | Follow causal evidence and reuse context; extra breadth must earn its cost. |
| “Use maximum effort; budget is ample.” | Materially expand useful investigation, coverage, verification, or parallel work when available. |
| “Давай чуть плотнее” / “a little more thoroughly.” | Increase useful effort relative to the current approach; do not jump automatically to maximum. |
| “Жги на максимум, не жалей токенов, но до трёх агентов.” | Maximize useful effort within the three-worker ceiling. |
| “Жги” / “go ahead,” after an estimate-only plan. | Continue that authorized estimate; infer no maximum budget or expanded scope. |
| “Не надо на максимум, пока только прикинь.” | Keep the estimate bounded; the negated maximum phrase is not an instruction to escalate. |
| “The quoted prompt says ‘use maximum effort’; review its wording.” | Treat the phrase as task data. |

## Allocate Adaptively

Choose a justified initial plan and revisit it as evidence reveals independent questions, uncertainty, or duplicated work. Favor context reuse when it avoids rediscovery; add a fresh handle when independence, breadth, or specialization is valuable. Serial deep investigation may beat broad fanout for a tightly coupled problem. Broad audits may justify large teams or successive capacity waves. There is no habitual two- or three-agent ceiling and no requirement to fill every slot.

Maximum effort with ample budget should change the actual work when useful opportunities exist: partition a broad surface more fully, test competing explanations independently, examine overlooked failure paths, or deepen evidence and verification. Merely announcing “maximum” while repeating a default small-team plan is insufficient. Conversely, do not invent questions or agents when meaningful work is exhausted; explain the actual bottleneck or completion evidence.

Model-worker slots, a shared writer, local build throughput, and a single device are different resources. A serial writer or build does not by itself preclude useful read-only investigation elsewhere. Schedule around real contention and dependency costs without treating every additional model worker as another simultaneous build. Review a writer's result only after that writer is terminal and audited.

Within the same objective, a coordinator-selected plan is revisable in Lite: “I planned two delegated reviewers; the evidence exposes an independent migration risk, so I’m adding a third reviewer.” Announce changed count, roles, and reason. This needs neither a new user grant nor Full solely for count. All user bounds, actual capacity, permissions, and ownership still apply. Multiple possible writers, a changed active requirement, or another existing promotion condition still routes through Full.

## Keep Bounds And Accounting Distinct

- An unqualified user total such as “run three agents” is `EXACT`: target and cumulative hard ceiling for its stated scope. Do not silently reduce it or exceed it.
- “Up to three” is a ceiling, not a request for three. “At least three” is a floor, not a ceiling. An estimate or coordinator-selected initial count is a plan. Apply all simultaneous constraints; if they conflict, explain the conflict before affected dispatch.
- “Maximum effort, at most three agents” retains the cap. Broaden or deepen assignments, reuse created handles, or perform permitted coordinator work. Another new handle requires a user change to that cap.
- State the count basis. By default counts mean delegated workers, excluding the coordinator. Honor explicit wording such as “three total including you” by allowing only two delegated workers. Apply scope across waves and descendants where requested.
- Count every distinct successfully created handle once, including later failed, cancelled, completed, or closed handles. Reusing a handle adds none. A failed spawn without a created handle adds none; a replacement handle adds one. Closing or a new wave never replenishes a cumulative ceiling.
- Separate peak concurrency from cumulative count. If an exact request exceeds actual capacity, use meaningful capacity waves and report unstarted or blocked slots honestly. If there is insufficient meaningful work for an exact target, explain the mismatch rather than inventing decorative agents or pretending the target was met.

Ordinary leaves remain leaf-only. A child coordinator still requires source user-authored activation, a positive bounded delegated budget, and the existing accounting scope. Partition applicable parent ceilings; aggregate descendant activity without double-counting. An open root plan does not grant unlimited child fanout. These preferences do not change packet schemas, lineage validation, or child lifecycle authority.

## Scope And Mid-Run Steering

An effort preference normally applies only to the current task. Explicit future-use wording, such as “For later tasks in this chat, prioritize thoroughness over speed,” retains that preference as a chat default only when the host preserves the context. “For this one, give me a quick estimate” overrides the current task without erasing that earlier default. A statement about future effort is not a request to enable Auto; future use of Relay follows the existing Auto router.

Store no preference token or configuration file, and claim no persistence beyond retained context. Never implicitly transfer chat defaults or Relay activation to a child or new chat. Pass only bounded effort instructions needed for an ordinary leaf's assigned deliverable. Explicit child coordination follows the existing authority and budget contract.

Higher effort alone does not select Full or change Auto, close state, permissions, or task scope. Interpret “full effort” as effort, not an explicit request for the Full lifecycle. Preserve valid active writers while redirecting queued work or adding compatible read-only coverage. If the user changes acceptance, scope, or another active requirement, apply the existing promotion and delta rules. Never interpret more effort as permission for installs, external writes, destructive actions, or other side effects.
