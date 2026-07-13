# Installing Relay Orchestra

The [README](README.md) contains the recommended installation path. This guide covers exact destinations, updates, reproducible installation, local development, installer behavior, and troubleshooting.

## Recommended Installation

Relay Orchestra has no runtime dependencies. The skills CLI uses Node.js and npm only during installation:

```sh
npx skills add SDA-31/relay-orchestra
```

The CLI discovers the `relay-orchestra` skill, detects supported agents, and installs it for the project in your current directory by default. Add `-g` for a user-level installation. Update it later with:

```sh
npx skills update relay-orchestra
```

See the [skills.sh listing](https://www.skills.sh/sda-31/relay-orchestra/relay-orchestra) for discovery. Start a new task or chat before relying on updated instructions. If cached content remains, use the client's documented refresh or restart procedure.

## Standalone Script Installation

Use the repository installers when Node.js is unavailable or when you need their explicit destination and linking controls.

Requirements:

- Python 3.7 or newer.
- macOS or Linux: a POSIX shell, `curl`, and standard temporary-file tools.
- Windows: PowerShell.

macOS and Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.ps1 | iex
```

Both commands execute code from the mutable `main` branch. Use them only if you trust this repository and GitHub's delivery path; inspect-first and pinned alternatives are documented below.

## Interactive Selection

Running either installer without arguments opens an interactive menu with these choices:

1. Codex
2. Claude Code
3. Gemini CLI
4. Cursor
5. OpenCode
6. GitHub Copilot
7. Universal Agent Skills
8. All supported environments

The installer does not infer a client from directories on disk. It installs only the selected target and prints the exact destination when it succeeds. For unattended use, pass an explicit target; run `./install.sh --help` or `.\install.ps1 --help` for the complete option syntax.

## Exact Target Paths

| Selection | Destination |
| --- | --- |
| Universal Agent Skills | `~/.agents/skills/relay-orchestra` |
| Codex | `$CODEX_HOME/skills/relay-orchestra`, or `~/.codex/skills/relay-orchestra` when `CODEX_HOME` is unset |
| Claude Code | `~/.claude/skills/relay-orchestra` |
| Gemini CLI | `~/.gemini/skills/relay-orchestra` |
| Cursor | `~/.cursor/skills/relay-orchestra` |
| OpenCode | `~/.config/opencode/skills/relay-orchestra` |
| GitHub Copilot | `~/.copilot/skills/relay-orchestra` |
| All supported environments | One separate copy in every user-level destination above |

A project installation goes to `<project>/.agents/skills/relay-orchestra`. A custom destination names the final `relay-orchestra` directory itself, not its parent.

## Standalone Installer Options

For remote macOS/Linux installation, pass options after `bash -s --` (for example, `bash -s -- --target codex`). PowerShell options use the script-block form shown in the updating section. Local Windows checkouts can append options to `.\install.ps1` directly.

| Flag | Purpose |
| --- | --- |
| `--target` | Skip every question and choose a user target directly. Examples: `--target codex`, `--target claude`, `--target gemini`. Repeatable; `all` installs separate copies. |
| `--project <project-path>` | Install under the specified project's `.agents/skills` directory. |
| `--destination` | Install to an exact skill directory; repeatable. |
| `--home` | Override the home directory used to resolve targets. |
| `--codex-home` | Override the Codex home directory. |
| `--source` | Use another source skill directory. |
| `--link` | Symlink from a local checkout instead of copying. |
| `--force` | Replace an existing destination using a staged replacement with rollback on failure. |
| `--dry-run` | Report destinations without writing. |
| `--json` | Emit machine-readable output. |

For example, from a local checkout:

```sh
./install.sh --project /path/to/project
```

## Updating Standalone Installations

An existing installation is never overwritten implicitly. Repeat the original installer with the same target and add `--force`:

```sh
curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.sh | bash -s -- --target <environment> --force
```

For Windows, run the remote installer as a script block so arguments are forwarded explicitly:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.ps1))) -InstallerArgs @("--target", "<environment>", "--force")
```

The installer uses a staged replacement beside the current destination, with rollback to the previous installation on failure.

An active task may retain Relay instructions loaded before the update. Start a new task or chat before relying on updated instructions. If cached content remains, use the client's documented refresh or restart procedure. An update does not hot-reload instructions already held by an active task.

## Inspect Before Running

The short macOS/Linux command executes `install.sh` from the mutable `main` branch. Download and inspect that entry point before running it when you do not want to pipe remote code directly into a shell:

```sh
curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.sh -o relay-orchestra-install.sh
less relay-orchestra-install.sh
sh relay-orchestra-install.sh
```

The reviewed entry point still downloads the repository archive that contains the skill and shared installer. Clone the repository when you want to inspect the complete payload before installation.

On Windows, inspect the PowerShell entry point before executing it:

```powershell
irm https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.ps1 -OutFile relay-orchestra-install.ps1
Get-Content .\relay-orchestra-install.ps1
.\relay-orchestra-install.ps1
```

## Pinned Installation

For a reproducible remote installation, use the same verified full commit SHA for both the entry point and payload:

```sh
curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/<full-commit-sha>/install.sh -o relay-orchestra-install.sh
less relay-orchestra-install.sh
RELAY_ORCHESTRA_REF=<full-commit-sha> sh relay-orchestra-install.sh
```

Do not review one revision and install another. A branch or tag can move; a full commit SHA cannot.

The equivalent pinned Windows flow is:

```powershell
$env:RELAY_ORCHESTRA_REF = "<full-commit-sha>"
try {
    $entryPoint = irm "https://raw.githubusercontent.com/SDA-31/relay-orchestra/$env:RELAY_ORCHESTRA_REF/install.ps1"
    & ([scriptblock]::Create($entryPoint))
} finally {
    Remove-Item Env:RELAY_ORCHESTRA_REF
}
```

## Local Checkout and Linking

Clone the repository to inspect or develop the skill locally:

```sh
git clone https://github.com/SDA-31/relay-orchestra.git
cd relay-orchestra
./install.sh --target codex --link
```

Link mode points the destination at `skills/relay-orchestra` in the checkout, so edits take effect without reinstalling. It is accepted only from a local checkout; the remote bootstrap rejects it.

Without link mode, a local checkout copies the skill just like the remote installer. Use `--source` only when testing a different source directory that contains a correctly named `SKILL.md`.

## Installer Architecture

- `install.sh` is the macOS/Linux entry point. From a local checkout it calls the shared Python installer directly. When fetched remotely, it downloads a temporary repository archive, validates and extracts it, calls the shared installer, and removes the temporary files.
- `install.ps1` is the Windows entry point. From a local checkout it forwards arguments to the shared Python installer. When fetched remotely, it downloads and validates a temporary repository archive first.
- `scripts/install.py` resolves destinations, validates the source skill, and performs copy, link, dry-run, replacement, and output handling.

Users should invoke an operating-system entry point rather than call the Python implementation directly.

## Security Model

Remote installation trusts this repository, GitHub's raw-file delivery, and GitHub's archive delivery. The bootstrap requires TLS, limits the archive download, extracts into a private temporary directory, rejects unsafe paths and non-file archive entries, caps member count and expanded size, and verifies that the expected installer and skill are present.

The installer validates that the source contains a `SKILL.md` named `relay-orchestra`. It refuses to overwrite an existing destination unless replacement is explicitly requested. Remote link mode is prohibited. These checks reduce common installation risks but do not replace source review or commit pinning.

Installing a skill does not grant it permissions beyond those provided by the host client. Review the skill and its references before using it for sensitive work.

## Troubleshooting

### Python is missing or too old

Install Python 3.7 or newer and ensure `python3` or `python` is available on macOS/Linux. On Windows, the wrapper checks `py -3`, `python3`, and `python` in that order.

### Interactive input is unavailable

The menu needs a terminal. In CI, scripts, or other non-interactive environments, pass an explicit target.

### The destination already exists

Update intentionally with the replacement option. The installer will not merge files into an existing skill directory.

### Codex installed somewhere unexpected

The Codex target honors `CODEX_HOME` when set. Otherwise it uses `~/.codex`. The installer prints the resolved destination so it can be checked directly.

### The client does not discover the skill

Start a new task or chat before relying on updated instructions. If cached content remains, use the client's documented refresh or restart procedure. Then confirm the printed destination is one the client scans. Consult the [platform capability notes](skills/relay-orchestra/references/platforms.md) because discovery behavior varies by client and version.

### Remote link mode fails

Linking requires a local checkout because its purpose is to reference local development files. Clone the repository and run the local entry point.
