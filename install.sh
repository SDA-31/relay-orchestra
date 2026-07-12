#!/bin/sh
set -eu

REPOSITORY="SDA-31/relay-orchestra"

die() {
  printf '%s\n' "Relay Orchestra installation failed: $*" >&2
  exit 1
}

find_python() {
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
      "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 7))' >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

local_checkout() {
  case $0 in
    install.sh | */install.sh) ;;
    *) return 1 ;;
  esac

  script_dir=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd) || return 1
  [ -f "$script_dir/install.sh" ] || return 1
  [ -f "$script_dir/scripts/install.py" ] || return 1
  [ -f "$script_dir/skills/relay-orchestra/SKILL.md" ] || return 1
  printf '%s\n' "$script_dir"
}

validate_ref() {
  case $1 in
    '' | -* | *..* | *//* | */ | *[!ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/-]*)
      die "invalid RELAY_ORCHESTRA_REF: $1"
      ;;
  esac
}

extract_archive() {
  "$python" - "$archive" "$extract_dir" <<'PY'
import os
import posixpath
import sys
import tarfile

archive_path, destination = sys.argv[1:]
max_members = 1024
max_bytes = 20 * 1024 * 1024

with tarfile.open(archive_path, "r:gz") as bundle:
    members = bundle.getmembers()
    if not members or len(members) > max_members:
        raise SystemExit("archive has an invalid number of entries")

    roots = set()
    paths = set()
    total_size = 0
    checked = []

    for member in members:
        name = member.name
        normalized = posixpath.normpath(name)
        parts = normalized.split("/")
        if (
            not name
            or name.startswith("/")
            or normalized in ("", ".")
            or any(part in ("", ".", "..") for part in parts)
            or normalized in paths
        ):
            raise SystemExit(f"archive contains an unsafe path: {name!r}")
        if not (member.isdir() or member.isfile()):
            raise SystemExit(f"archive contains a non-file entry: {name!r}")
        roots.add(parts[0])
        paths.add(normalized)
        total_size += member.size
        if total_size > max_bytes:
            raise SystemExit("archive contents exceed the 20 MiB safety limit")
        checked.append((member, normalized))

    if len(roots) != 1:
        raise SystemExit("archive must contain exactly one repository root")

    for member, normalized in sorted(checked, key=lambda item: item[1].count("/")):
        output = os.path.join(destination, *normalized.split("/"))
        if member.isdir():
            os.makedirs(output, mode=0o755, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(output), mode=0o755, exist_ok=True)
        source = bundle.extractfile(member)
        if source is None:
            raise SystemExit(f"could not read archive entry: {member.name!r}")
        with source, open(output, "xb") as target:
            while True:
                chunk = source.read(64 * 1024)
                if not chunk:
                    break
                target.write(chunk)
        os.chmod(output, 0o755 if member.mode & 0o111 else 0o644)

root = os.path.join(destination, roots.pop())
required = (
    os.path.join(root, "scripts", "install.py"),
    os.path.join(root, "skills", "relay-orchestra", "SKILL.md"),
)
if not all(os.path.isfile(path) for path in required):
    raise SystemExit("archive does not contain the Relay Orchestra installer and skill")
print(root)
PY
}

remote_install() {
  for argument in "$@"; do
    [ "$argument" != "--link" ] || die "--link requires a local checkout"
  done

  ref=${RELAY_ORCHESTRA_REF:-main}
  validate_ref "$ref"
  command -v mktemp >/dev/null 2>&1 || die "mktemp is required"

  umask 077
  work_dir=$(mktemp -d "${TMPDIR:-/tmp}/relay-orchestra.XXXXXX") || die "could not create a temporary directory"
  archive="$work_dir/source.tar.gz"
  extract_dir="$work_dir/source"
  mkdir "$extract_dir"

  cleanup() {
    rm -rf "$work_dir" || :
  }
  trap cleanup 0
  trap 'exit 129' 1
  trap 'exit 130' 2
  trap 'exit 131' 3
  trap 'exit 143' 15

  if [ -n "${RELAY_ORCHESTRA_TEST_ARCHIVE:-}" ]; then
    [ -f "$RELAY_ORCHESTRA_TEST_ARCHIVE" ] || die "test archive does not exist"
    cp "$RELAY_ORCHESTRA_TEST_ARCHIVE" "$archive"
  else
    command -v curl >/dev/null 2>&1 || die "curl is required for remote installation"
    archive_url="https://codeload.github.com/$REPOSITORY/tar.gz/$ref"
    curl --proto '=https' --tlsv1.2 --max-filesize 52428800 -fsSL "$archive_url" -o "$archive"
  fi

  repository_root=$(extract_archive) || die "downloaded archive failed validation"
  if "$python" "$repository_root/scripts/install.py" "$@"; then
    status=0
  else
    status=$?
  fi
  exit "$status"
}

main() {
  python=$(find_python) || die "Python 3.7 or newer is required"
  if [ -z "${RELAY_ORCHESTRA_REF:-}" ] && checkout=$(local_checkout); then
    exec "$python" "$checkout/scripts/install.py" "$@"
  fi
  remote_install "$@"
}

main "$@"
