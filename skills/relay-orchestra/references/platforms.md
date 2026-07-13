# Platform Capability Notes

Snapshot: 2026-07-13. Prefer runtime inspection because agent features and limits change.

## Portable Core

Relay Orchestra follows the open Agent Skills format: one `relay-orchestra` directory, a `SKILL.md` with name and description frontmatter, and optional references and product metadata.

The specification defines neither a universal subagent API, a universal invocation syntax, nor a universal explicit-only switch. Relay Orchestra therefore applies a runtime capability gate and explicit scope. One-shot work is bounded to the current user message and its response; bare explicit invocation defaults to a live session. Optional Codex metadata adds platform-level explicit-only policy.

## Capability Matrix

| Client | Agent Skills | Native subagents | Guidance |
| --- | --- | --- | --- |
| OpenAI Codex | Yes | Yes | Inspect notification delivery and coordinator auto-wake separately, plus current concurrency, cross-turn state, and handle controls. |
| Claude Code | Yes | Yes | Inspect background and cross-turn controls; keep Relay Orchestra's own workers leaf-only even if the client permits nesting. |
| Gemini CLI | Yes | Version dependent | Inspect installed subagent, concurrency, and persistence support. |
| Cursor | Yes | Yes | Inspect cross-turn controls; use native parallel agents and client-provided isolation when approved. |
| OpenCode | Yes | Client/version dependent | Inspect runtime concurrency, persistence, and lifecycle controls. |
| GitHub Copilot CLI | Yes | Yes | Inspect background, concurrency, persistence, and lifecycle controls. |
| goose | Skills available | Version dependent | Inspect current discovery, persistence, and parallel-agent behavior. |
| Other clients | Often | Unknown | Use the complete capability gate and honest fallback. |

## Observed Codex Behavior

On 2026-07-13, the Codex app was observed queueing a completed-subagent notification without starting a new coordinator turn; the result became visible when the next user turn began. The app-server protocol also represents notifications separately from turn/start. Treat this as notification delivery without proven auto-wake unless the current runtime demonstrates otherwise. In that case, automatically use native completion waits or polling at short bounded intervals while active work remains and a specific completion or status condition can be observed. Disclose once that the coordinator remains `In Progress` and a message may wait up to one poll interval. Between intervals, process newer input and delivered results before advancing dependent waves, integration, verification, and synthesis; never use shell sleep, a single long blind block, or polling without active work or a next condition.

## Invocation Scope

Use the client's explicit skill mechanism. This phrase opens a bounded live session:

    Start a Relay Orchestra session for this work.

This phrase applies Relay once and deactivates with the response:

    Use Relay Orchestra for this message only.

A bare explicit invocation defaults to live-session scope. Live sessions span related follow-ups and remain active after a completion candidate until a later direct close answer or explicit stop.

## Resume Wrappers

The portable fallback payload is `resume <token>: <next instruction>`. Wrap it in the client's explicit skill mechanism:

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

Worktree support is not part of the Agent Skills standard. Shared mode remains the default. Enable one isolated checkout per concurrent writer only after explicit user approval, keep integration in the coordinating context, and never treat a branch alone as isolation.

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
