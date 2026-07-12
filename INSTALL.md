# Installing Relay Orchestra

The [README](README.md) contains the recommended installation path. This guide covers exact destinations, updates, reproducible installation, local development, installer behavior, and troubleshooting.

## Requirements

- Python 3.7 or newer.
- macOS or Linux: a POSIX shell, `curl`, and standard temporary-file tools.
- Windows: PowerShell.

After installation, start a new task or chat if the client caches its skill catalog.

## Interactive Selection

Running either installer without arguments opens a menu with these choices:

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

## Updating

An existing installation is never overwritten implicitly. Repeat the original installer with the same target and add `--force`:

```sh
curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.sh | bash -s -- --target <environment> --force
```

For Windows, run the remote installer as a script block so arguments are forwarded explicitly:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.ps1))) -InstallerArgs @("--target", "<environment>", "--force")
```

The installer uses a staged replacement beside the current destination, with rollback to the previous installation on failure.

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

Start a new task or chat, then confirm the printed destination is one the client scans. Consult the [platform capability notes](skills/relay-orchestra/references/platforms.md) because discovery behavior varies by client and version.

### Remote link mode fails

Linking requires a local checkout because its purpose is to reference local development files. Clone the repository and run the local entry point.
