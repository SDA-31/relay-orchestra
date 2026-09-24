# Platform Capability Notes

Snapshot: 2026-07-13. Prefer runtime inspection because agent features and limits change.

## Portable Core

Relay Orchestra follows the open Agent Skills format: one `relay-orchestra` directory, a `SKILL.md` with name and description frontmatter, and optional references and product metadata.

The specification defines neither a universal subagent API, invocation syntax, nor persistent chat preference. Relay Orchestra therefore applies two layers: optional chat-scoped Auto plus separate current execution. A bare invocation with a bounded objective defaults to Lite one-shot; without an objective it enables idle Auto, explains it, and asks for the task. It does not open Full live. Future-use wording also enables Auto while a current objective routes normally. Explicit `full`, `live`, or `multi-turn` selects Full. Codex metadata permits prompt-matched reload so a later task can honor previously enabled Auto or continue active Full live; the description rejects use without explicit activation or that surviving chat context.

Auto launches no agents and creates no lifecycle machinery while idle. It retains any user-stated filter, delegates only when materially distinct work exists, and otherwise keeps small linear work local. Auto routes only while execution is `OFF`; an active Full live session owns related deltas. Completed one-shots leave Auto enabled. Auto is not copied to new chats or child tasks. Natural-language `auto off` disables only the future preference, not active Full work. Compaction preserves Auto only when the host retained the preference and filter; no client-independent persistence is claimed.

Effort is inferred from task and natural language without named profiles, fixed team sizes, or a configuration questionnaire. Future-use wording about effort alone retains a chat preference only when context survives; it does not enable Auto. Current-task overrides preserve earlier chat defaults. Never encode these preferences in tokens/configuration or copy them implicitly into new chats or children. Ordinary leaves receive bounded task-relevant instructions. Higher effort alone changes neither activation, Full routing, nor permissions.

Keep host concurrent capacity separate from cumulative created-handle accounting and local writer/build/device constraints. Meaningful large teams and capacity waves are valid under maximum effort and ample budget, while user numeric ceilings remain binding across waves. A self-selected plan may be revised within the same objective in Lite without user permission or promotion solely for count; announce changed count, roles, and reason. State the count basis, normally delegated workers excluding the coordinator, and honor explicit user wording. Optional [effort and sizing examples](effort-and-sizing.md) cover interpretation and bounds.

When the user explicitly requests Relay in separate delegated tasks, the parent may carry that activation through each client's explicit skill mechanism. Treat those tasks as child coordinators with independent local lifecycles and stated count budgets, not as ordinary leaves. A live child also requires a user-visible task with direct user-authored follow-up and close confirmation; use one-shot for background or invisible child tasks. Never infer another coordination level merely because a client supports nested agents, and never let the parent impersonate the user for child closure.

## Capability Matrix

| Client | Agent Skills | Native subagents | Guidance |
| --- | --- | --- | --- |
| OpenAI Codex | Yes | Yes | Inspect notification delivery and coordinator auto-wake separately, plus current concurrency, cross-turn state, and handle controls. |
| Claude Code | Yes | Yes | Inspect background and cross-turn controls. Keep ordinary workers leaf-only; permit a separate child coordinator only after explicit user activation for that delegated task. |
| Gemini CLI | Yes | Version dependent | Inspect installed subagent, concurrency, and persistence support. |
| Cursor | Yes | Yes | Inspect cross-turn controls; use native parallel agents and client-provided isolation when approved. |
| OpenCode | Yes | Client/version dependent | Inspect runtime concurrency, persistence, and lifecycle controls. |
| GitHub Copilot CLI | Yes | Yes | Inspect background, concurrency, persistence, and lifecycle controls. |
| goose | Skills available | Version dependent | Inspect current discovery, persistence, and parallel-agent behavior. |
| Other clients | Often | Unknown | Use the complete capability gate and honest fallback. |

## Observed Codex Behavior

On 2026-07-13, the Codex app was observed queueing a completed-subagent notification without starting a new coordinator turn; the result became visible when the next user turn began. The app-server protocol also represents notifications separately from turn/start. Treat this as notification delivery without proven auto-wake unless the current runtime demonstrates otherwise. In that case, automatically use native completion waits or polling at short bounded intervals while active work remains and a specific completion or status condition can be observed. Disclose once that the coordinator remains `In Progress` and a message may wait up to one poll interval. Between intervals, process newer input and delivered results before advancing dependent waves, integration, verification, and synthesis; never use shell sleep, a single long blind block, or polling without active work or a next condition.

## Invocation Scope

Use the client's explicit skill mechanism. This phrase opens a full live session:

    Start a full live Relay Orchestra session for this work.

This bounded request defaults to Lite one-shot and deactivates with the response:

    Use Relay Orchestra to run two reviewers and synthesize their findings.

A bare explicit invocation with a bounded objective defaults to Lite one-shot and does not enable Auto unless future-use intent is present. Without an objective, while execution is `OFF`, it enables Auto and asks for the next task without lifecycle artifacts. While Full live is `ACTIVE`, related requests and bare reinvocation preserve that session; Auto cannot open a competing run. Explicit live sessions remain active until a later direct close answer or explicit stop. Promote Lite to Full before unsafe dispatch, naming the reason and whether the run is Full one-shot or Full live.

## Resume Wrappers

The portable fallback uses `resume <token>: <next instruction>`. Only the coordinator of that task may emit a redeemable opaque handle, as one plain-text line rather than Markdown code, raw field/value state, JSON, or a tool payload. It is allowed only for real unfinished work, a nonterminal handle, or pending close confirmation—not merely because the session is `ACTIVE`. Never put it in an ordinary leaf dispatch or handoff, and never copy a child coordinator's token into the parent's lifecycle. Wrap it in the client's explicit skill mechanism:

| Client | Example wrapper |
| --- | --- |
| OpenAI Codex | `$relay-orchestra resume <token>: <next instruction>` |
| Claude Code | `/relay-orchestra resume <token>: <next instruction>` |
| Generic Agent Skills client | `Use the Relay Orchestra skill to resume <token>: <next instruction>` |

Milestone responses and apparent objective completion do not end a live session. The coordinator audits the outcome, presents a completion candidate, and asks before closing. To stop directly:

    Stop Relay Orchestra, close active workers safely, and return partial results.

## Installation Locations

Prefer open-standard paths:

- project: `.agents/skills/relay-orchestra`
- user: `~/.agents/skills/relay-orchestra`

Known alternatives include `.claude/skills`, `.gemini/skills`, `.cursor/skills`, `.opencode/skills`, `.github/skills`, and `~/.codex/skills`. Use symlinks during development to keep one canonical copy.

## Worktree Notes

Worktree support is not part of the Agent Skills standard.

- Shared mode remains the default for read-only agents and at most one active writer only when writes are safely attributable. Treat pre-existing or unattributed dirty paths as user-owned; narrow ownership or offer an approved worktree before overlapping them.
- For two or more possible concurrent writers, plan one isolated checkout per writer by default, but create none before explicit user approval. If worktrees are unavailable or declined, serialize writers.
- Before creating any writer handle, compare canonical repository-relative paths and logical edit scopes across the wave. Shared-tree overlap must serialize; approved isolated writers may use a recorded controlled-overlap group from one confirmed base revision.
- Integrate exactly one terminal, audited writer per operation. Apply each controlled-overlap result as a patch from its recorded base; for later writers, three-way reconcile against the updated integration state instead of overwriting the file.
- Keep the combined requirement authoritative, use a coordinator or context-rich resolver for ordinary conflicts, and verify the combined diff even when Git reports a clean merge.
- Block only overlapping streams, and clear protection only for exact paths authorized by the user or explicitly reconciled.
- Keep integration in the coordinating context, and never treat a branch alone as isolation.

## Primary Documentation

- Agent Skills specification: https://agentskills.io/specification
- Codex skills: https://learn.chatgpt.com/docs/build-skills
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Gemini CLI subagents: https://geminicli.com/docs/core/subagents/
- Gemini CLI skills: https://geminicli.com/docs/cli/using-agent-skills/
- Cursor subagents and skills: https://cursor.com/changelog/2-4
- OpenCode skills: https://opencode.ai/docs/skills
- OpenCode agents: https://opencode.ai/docs/agents/
- GitHub Copilot Fleet: https://docs.github.com/en/copilot/concepts/agents/copilot-cli/fleet
- GitHub Copilot skills: https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills
- goose: https://goose-docs.ai/
