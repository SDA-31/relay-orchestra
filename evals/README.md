# Forward-Test Scenarios

`cases.json` is a portable scenario specification, not a deterministic LLM test suite. It records prompts and observable expectations for manual or client-provided agent eval runners.

`transcripts.json` specifies ordered one-shot and multi-turn event traces. Runners should preserve each delivery batch, distinguish result notification from automatic wake, verify user-event priority, and assert scope, state transitions, continuity, bounded completion polling, and stop conditions after every step. A one-shot interval timeout is a scheduling tick: runners must verify same-turn repolling while healthy or authorized dependent work remains, followed by terminal synthesis, worker settlement, and `OFF` in the final response. Blocked one-shots also finish `OFF` in their only turn; bare explicit invocations require a later direct close answer.

CI validates the package structure and required policy language. Before a release, invoke Relay Orchestra against representative cases with the target clients and record any platform-specific behavior separately.
