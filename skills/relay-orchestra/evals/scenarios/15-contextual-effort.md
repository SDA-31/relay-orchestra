---
task: "With Relay Auto enabled, interpret a chat-wide economical preference followed by a maximum-effort override for this task only, then a later ordinary task. Also distinguish urgent thorough work with a short answer from a preliminary estimate, and reject quoted or negated maximum language."
baseline_failure: "Regression coverage: the old evaluator inferred these scopes correctly but had no explicit effort policy; preserve those decisions while fixing the observed coordinator-plan ceiling failure."
runs: 1
assertions:
  - "Infer effort from intent and context without requiring profile names or a priority questionnaire."
  - "Apply the task override only to its task, then restore the chat preference; do not transfer chat settings or activation to children or new chats."
  - "Distinguish urgency, depth, breadth, verification, autonomy, budget and answer length; preserve ordinary authorized checks."
  - "Quoted, negated or hypothetical maximum language and a colloquial go-ahead do not expand effort, authority or task scope."
---

Evaluate decisions without launching real workers. Use the same prompts for old/new comparison; do not require different counts when both allocations are justified.
