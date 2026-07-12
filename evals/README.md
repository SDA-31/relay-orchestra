# Forward-Test Scenarios

`cases.json` is a portable scenario specification, not a deterministic LLM test suite. It records prompts and observable expectations for manual or client-provided agent eval runners.

`transcripts.json` specifies ordered multi-turn event traces. Runners should preserve each delivery batch, verify user-event priority, and assert state transitions and continuity behavior after every step.

CI validates the package structure and required policy language. Before a release, invoke Relay Orchestra against representative cases with the target clients and record any platform-specific behavior separately.
