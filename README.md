# Relay Orchestra

Move work faster with parallel agents while keeping control of the conversation.

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2563EB)](https://agentskills.io/specification)
![Distribution](https://img.shields.io/badge/distribution-install%20scripts-0F766E)
[![License: MIT](https://img.shields.io/badge/license-MIT-374151)](LICENSE)

Relay Orchestra coordinates your client's built-in agents across a live multi-turn session, so parallel research, review, and implementation can move faster while you keep steering. Clients without live parallel support fall back honestly to bounded waves, sequential work, or dispatch-ready briefs.

It stays active only for the current task. It does not silently apply itself to later work.

## Quick Start

Relay Orchestra requires Python 3.7 or newer. Windows installation also requires Git.

With no arguments, the installer opens an interactive menu for Codex, Claude Code, Gemini CLI, Cursor, OpenCode, GitHub Copilot, universal Agent Skills, or all supported environments. It prints the exact destination after installation. Start a new task or chat afterward if your client caches its skill catalog.

### macOS and Linux

```sh
curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.sh | bash
```

This executes code from the mutable `main` branch. Use it only if you trust this repository and GitHub's delivery path; see [Installation](INSTALL.md) for inspect-first and pinned alternatives.

### Windows PowerShell

```powershell
git clone --depth 1 https://github.com/SDA-31/relay-orchestra.git
Set-Location relay-orchestra
.\install.ps1
```

### Invoke It

Use your client's explicit skill picker or command when available (`$relay-orchestra` in Codex), or use this portable request:

```text
Use the Relay Orchestra skill for this request only. Run three read-only agents
to review the current changes, then verify and synthesize their findings.
```

> **Usage warning:** Each parallel agent performs separate model work. Running several agents can consume tokens or credits much faster than a single-agent run, even when they share one objective. Start with the fewest agents that provide distinct value, and check your client's usage or billing controls.

On clients with full live support, a successful start returns a short receipt while work continues; other clients disclose their bounded-wave fallback:

```text
NOW: three reviewers active
QUEUED: verification and synthesis after their reports
AGENTS: 3 active / 0 queued / 3 requested
```

## What It Does

- **Keeps the conversation live.** Dispatch returns promptly so you can keep steering.
- **Accepts changes mid-run.** Add, revise, reprioritize, hold, or cancel work while agents are active.
- **Uses native agents.** Relay Orchestra delegates through the host client instead of launching external agent CLIs.
- **Schedules to capacity.** Request any positive number of agents; the coordinator uses waves when the client has fewer slots.
- **Coordinates and verifies.** It assigns ownership, tracks dependencies, and checks worker reports before finalizing.

## How a Live Session Works

```mermaid
flowchart LR
    U["You: start or change the task"] --> C["Relay Orchestra"]
    C -->|dispatch| A["Native agents"]
    C -->|prompt receipt| U
    A -->|results and blockers| C
    C -->|reuse, redirect, spawn, queue, or hold| A
```

You remain the source of truth. New instructions take priority over planned follow-up work and incoming results.

## Realistic Multi-Turn Example

```text
You: Use Relay Orchestra for this request only. Improve the recipe import flow.
Start two researchers, then have one implementer use their findings.

Relay Orchestra: Working without worktree isolation. Agents share the current
working tree, and file changes appear there immediately.
NOW: two researchers active
QUEUED: implementation after research synthesis
AGENTS: 2 active / 1 queued / 3 requested

You: Support CSV first. Hold spreadsheet import for a later release, and keep
the current researcher who already mapped the data model.

Relay Orchestra: ACCEPTED: CSV is authoritative; spreadsheet import held.
NOW: data-model researcher reused; format research redirected to CSV
QUEUED: implementation brief updated

You: Add an accessibility reviewer after implementation. Do not delay the CSV
work if there is no free agent slot.

Relay Orchestra: ACCEPTED: accessibility review added.
NOW: research continues
QUEUED: implementation, then accessibility review as capacity becomes available
AGENTS: 2 active / 2 queued / 4 requested

You: Drop the animated preview. Reuse the format researcher to draft concise
error messages instead.

Relay Orchestra: ACCEPTED: animation superseded; copy task sent to the
context-rich researcher. CSV scope and accessibility review remain unchanged.
```

## Safety and Working Trees

Relay Orchestra uses the shared working tree by default and says so when a run starts. Concurrent writers must own separate paths; overlapping edits should be narrowed, serialized, or isolated.

Worktrees are opt-in. Relay Orchestra does not create or use one without explicit approval, and a branch alone is not treated as isolation. It does not bypass host permissions, make overlapping edits safe, or claim that a worker stopped when that cannot be confirmed.

## Compatibility and Limitations

Relay Orchestra follows the [Agent Skills specification](https://agentskills.io/specification), but the standard does not define subagents or background work. Full live behavior depends on runtime capabilities.

| Capability | Behavior |
| --- | --- |
| Agent Skills | Required for normal discovery and invocation. |
| Native subagents | Enables parallel delegation; otherwise Relay Orchestra offers sequential work or dispatch-ready briefs. |
| Background work across turns | Enables a continuous live session; otherwise work runs in short, disclosed waves. |
| Lifecycle controls | Follow-up, interruption, and closure vary by client and version. |
| Concurrency | The host sets practical limits; Relay Orchestra schedules within them. |
| Worktrees | Never assumed and always require explicit approval. |

See the dated [platform capability notes](skills/relay-orchestra/references/platforms.md). Relay Orchestra is a run-scoped coordinator, not an always-on automation framework.

## Installer Options

All options use the same installer entry point shown above. For remote macOS/Linux installation, pass them after `bash -s --` (for example, `bash -s -- --target codex`); on Windows, append them to `.\install.ps1`. See [Installation](INSTALL.md) for exact paths and detailed workflows.

| Flag | Purpose |
| --- | --- |
| `--target` | Skip every question and choose a user target directly. Examples: `--target codex`, `--target claude`, `--target gemini`. Repeatable; `all` installs separate copies. |
| `--project` | Install under a project's `.agents/skills` directory. |
| `--destination` | Install to an exact skill directory; repeatable. |
| `--home` | Override the home directory used to resolve targets. |
| `--codex-home` | Override the Codex home directory. |
| `--source` | Use another source skill directory. |
| `--link` | Symlink from a local checkout instead of copying. |
| `--force` | Replace an existing destination using a staged replacement with rollback on failure. |
| `--dry-run` | Report destinations without writing. |
| `--json` | Emit machine-readable output. |

## Documentation

- [Installation, updates, paths, and security](INSTALL.md)
- [Live-session control](skills/relay-orchestra/references/live-session.md)
- [Coordination patterns](skills/relay-orchestra/references/patterns.md)
- [Prompt examples](examples/prompts.md)
- [Contributing](CONTRIBUTING.md)

## Related Work

The design draws from public work by [Dimillian](https://github.com/Dimillian/Skills), [addyosmani](https://github.com/addyosmani/agent-skills), [obra/superpowers](https://github.com/obra/superpowers), [ZypherHQ](https://github.com/ZypherHQ/agent-orchestration-skill), [am-will](https://github.com/am-will/codex-skills), and [howells/arc](https://github.com/howells/arc).

## License

[MIT](LICENSE)
