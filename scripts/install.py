#!/usr/bin/env python3
"""Install Relay Orchestra into user, project, or client-specific skill roots."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


SKILL_NAME = "relay-orchestra"
CLIENTS = ("agents", "codex", "claude", "gemini", "cursor", "opencode", "copilot")


@dataclass(frozen=True)
class Destination:
    target: str
    path: Path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Install Relay Orchestra without guessing a client's home directory.",
        allow_abbrev=False,
    )
    result.add_argument(
        "--target",
        action="append",
        choices=(*CLIENTS, "all"),
        help="User-level target; repeat for several clients. Defaults to the open Agent Skills path.",
    )
    result.add_argument("--home", type=Path, help="Override the user home used for target paths.")
    result.add_argument("--codex-home", type=Path, help="Override CODEX_HOME for the Codex target.")
    result.add_argument("--project", type=Path, help="Install into <project>/.agents/skills.")
    result.add_argument(
        "--destination",
        action="append",
        type=Path,
        help="Install to an exact skill directory; repeat for multiple custom locations.",
    )
    result.add_argument("--source", type=Path, help="Override the source skill directory.")
    result.add_argument("--link", action="store_true", help="Create symlinks instead of copying files.")
    result.add_argument("--force", action="store_true", help="Replace an existing destination atomically.")
    result.add_argument("--dry-run", action="store_true", help="Show destinations without writing files.")
    result.add_argument("--json", action="store_true", help="Emit machine-readable output.")
    return result


def default_source() -> Path:
    return Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME


def validate_source(source: Path) -> Path:
    source = source.expanduser().resolve()
    skill_file = source / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"source does not contain SKILL.md: {source}")
    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match or not re.search(rf"(?m)^name:\s*{re.escape(SKILL_NAME)}\s*$", match.group(1)):
        raise ValueError(f"source SKILL.md is not named {SKILL_NAME}")
    return source


def target_path(target: str, home: Path, codex_home: Path) -> Path:
    roots = {
        "agents": home / ".agents" / "skills",
        "codex": codex_home / "skills",
        "claude": home / ".claude" / "skills",
        "gemini": home / ".gemini" / "skills",
        "cursor": home / ".cursor" / "skills",
        "opencode": home / ".config" / "opencode" / "skills",
        "copilot": home / ".copilot" / "skills",
    }
    return roots[target] / SKILL_NAME


def destinations(args: argparse.Namespace) -> list[Destination]:
    explicit_home = args.home is not None
    home = (args.home or Path.home()).expanduser().resolve()
    if args.codex_home:
        codex_home = args.codex_home.expanduser().resolve()
    elif not explicit_home and os.environ.get("CODEX_HOME"):
        codex_home = Path(os.environ["CODEX_HOME"]).expanduser().resolve()
    else:
        codex_home = home / ".codex"

    targets = args.target or ([] if args.project or args.destination else ["agents"])
    if "all" in targets:
        targets = list(CLIENTS)

    items = [Destination(target, target_path(target, home, codex_home)) for target in targets]
    if args.project:
        project = args.project.expanduser().resolve()
        items.append(Destination("project", project / ".agents" / "skills" / SKILL_NAME))
    for path in args.destination or []:
        items.append(Destination("custom", path.expanduser().resolve()))

    unique: list[Destination] = []
    seen: set[Path] = set()
    for item in items:
        if item.path not in seen:
            seen.add(item.path)
            unique.append(item)
    return unique


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def install_one(source: Path, destination: Destination, args: argparse.Namespace) -> dict[str, str]:
    path = destination.path
    mode = "link" if args.link else "copy"
    if args.dry_run:
        return {"target": destination.target, "path": str(path), "status": "dry-run", "mode": mode}

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() and args.link and path.resolve() == source:
        return {"target": destination.target, "path": str(path), "status": "unchanged", "mode": mode}
    if (path.exists() or path.is_symlink()) and not args.force:
        raise ValueError(f"destination already exists: {path} (use --force to replace it)")

    suffix = uuid.uuid4().hex
    staged = path.parent / f".{SKILL_NAME}.install-{suffix}"
    backup = path.parent / f".{SKILL_NAME}.backup-{suffix}"
    try:
        if args.link:
            staged.symlink_to(source, target_is_directory=True)
        else:
            shutil.copytree(source, staged)
        if path.exists() or path.is_symlink():
            path.rename(backup)
        staged.rename(path)
        remove_path(backup)
    except Exception:
        remove_path(staged)
        if backup.exists() or backup.is_symlink():
            if not path.exists() and not path.is_symlink():
                backup.rename(path)
        raise
    return {"target": destination.target, "path": str(path), "status": "installed", "mode": mode}


def emit(results: list[dict[str, str]], args: argparse.Namespace) -> None:
    payload = {"skill": SKILL_NAME, "dry_run": args.dry_run, "destinations": results}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    heading = "Relay Orchestra installation plan:" if args.dry_run else "Relay Orchestra installed:"
    print(heading)
    for result in results:
        print(f"- {result['target']}: {result['path']} ({result['status']}, {result['mode']})")
    if not args.dry_run:
        print("Start a new task or chat if your client caches its skill catalog.")


def main() -> int:
    args = parser().parse_args()
    try:
        source = validate_source(args.source or default_source())
        selected = destinations(args)
        if not selected:
            raise ValueError("no installation destination selected")
        results = [install_one(source, item, args) for item in selected]
    except (OSError, ValueError) as error:
        if args.json:
            print(json.dumps({"skill": SKILL_NAME, "error": str(error)}, indent=2), file=sys.stderr)
        else:
            print(f"Installation failed: {error}", file=sys.stderr)
        return 1
    emit(results, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
