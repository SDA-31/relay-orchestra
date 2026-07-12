# Platform Capability Notes

Snapshot: 2026-07-12. Prefer runtime inspection because agent features and limits change.

## Portable Core

Relay Orchestra follows the open Agent Skills format: one `relay-orchestra` directory, a `SKILL.md` with name and description frontmatter, and optional references and product metadata.

The specification defines neither a universal subagent API nor a universal explicit-only switch. It also does not guarantee that loaded skill instructions, coordinator state, or agent handles survive a user-turn boundary. Relay Orchestra therefore applies a runtime capability gate and uses explicit activation for one bounded multi-turn session. Optional Codex metadata adds platform-level explicit-only policy.

## Capability Matrix

| Client | Agent Skills | Native subagents | Guidance |
| --- | --- | --- | --- |
| OpenAI Codex | Yes | Yes | Inspect current concurrency, cross-turn state, and handle controls; use native continuity when present. |
| Claude Code | Yes | Yes | Inspect background and cross-turn controls; keep Relay Orchestra's own workers leaf-only even if the client permits nesting. |
| Gemini CLI | Yes | Version dependent | Inspect installed subagent, concurrency, and persistence support. |
| Cursor | Yes | Yes | Inspect cross-turn controls; use native parallel agents and client-provided isolation when approved. |
| OpenCode | Yes | Client/version dependent | Inspect runtime concurrency, persistence, and lifecycle controls. |
| GitHub Copilot CLI | Yes | Yes | Inspect cross-turn controls; use native parallel agents or Fleet when appropriate. |
| goose | Skills available | Version dependent | Inspect current discovery, persistence, and parallel-agent behavior. |
| Other clients | Often | Unknown | Use the complete capability gate and honest fallback. |

## Explicit Session Invocation

Use the client's explicit skill mechanism once to open a bounded session. Related follow-ups remain in that session only when native continuity works or the user supplies the fallback token requested by the coordinator. The portable phrase is:

    Start a Relay Orchestra session for this work.

In Codex, mention `$relay-orchestra`. Milestone responses do not end the session. To stop:

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
