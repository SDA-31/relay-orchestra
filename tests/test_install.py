from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
SHELL_INSTALLER = ROOT / "install.sh"


class InstallerTests(unittest.TestCase):
    def run_installer(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(INSTALLER), *args],
            cwd="/",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return result

    def test_default_open_standard_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = self.run_installer("--home", str(home), "--json")
            payload = json.loads(result.stdout)
            installed = home / ".agents" / "skills" / "relay-orchestra"
            self.assertTrue((installed / "SKILL.md").is_file())
            self.assertEqual(payload["destinations"][0]["target"], "agents")

    def test_codex_home_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            codex_home = base / "custom-codex"
            self.run_installer("--home", str(base / "home"), "--codex-home", str(codex_home), "--target", "codex")
            self.assertTrue((codex_home / "skills" / "relay-orchestra" / "SKILL.md").is_file())

    def test_project_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            project = base / "project"
            self.run_installer("--home", str(home), "--project", str(project))
            self.assertTrue((project / ".agents" / "skills" / "relay-orchestra" / "SKILL.md").is_file())
            self.assertFalse((home / ".agents").exists())

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = self.run_installer("--home", str(home), "--dry-run", "--json")
            self.assertEqual(json.loads(result.stdout)["destinations"][0]["status"], "dry-run")
            self.assertFalse((home / ".agents").exists())

    def test_existing_destination_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.run_installer("--home", str(home))
            self.run_installer("--home", str(home), expected=1)
            self.run_installer("--home", str(home), "--force")

    def test_link_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.run_installer("--home", str(home), "--link")
            installed = home / ".agents" / "skills" / "relay-orchestra"
            self.assertTrue(installed.is_symlink())
            self.assertEqual(installed.resolve(), (ROOT / "skills" / "relay-orchestra").resolve())

    def test_all_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = self.run_installer("--home", str(home), "--target", "all", "--json")
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload["destinations"]), 7)
            self.assertTrue((home / ".config" / "opencode" / "skills" / "relay-orchestra" / "SKILL.md").is_file())


class ShellInstallerTests(unittest.TestCase):
    def make_archive(self, base: Path) -> Path:
        package = base / "relay-orchestra-test"
        (package / "scripts").mkdir(parents=True)
        shutil.copy2(INSTALLER, package / "scripts" / "install.py")
        shutil.copytree(ROOT / "skills" / "relay-orchestra", package / "skills" / "relay-orchestra")
        archive = base / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(package, arcname=package.name)
        return archive

    def run_remote(
        self,
        archive: Path,
        cwd: Path,
        tmpdir: Path,
        *args: str,
        expected: int = 0,
        extra_env: dict[str, str] | None = None,
        shell: str = "bash",
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "RELAY_ORCHESTRA_TEST_ARCHIVE": str(archive),
                "TMPDIR": str(tmpdir),
            }
        )
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            [shell, "-s", "--", *args],
            cwd=cwd,
            env=env,
            input=SHELL_INSTALLER.read_text(encoding="utf-8"),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return result

    def test_local_checkout_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            result = subprocess.run(
                ["sh", str(SHELL_INSTALLER), "--home", str(home), "--json"],
                cwd="/",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".agents" / "skills" / "relay-orchestra" / "SKILL.md").is_file())

    def test_remote_install_from_unrelated_directory_and_forwards_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = self.make_archive(base)
            cwd = base / "unrelated working directory"
            tmpdir = base / "tmp"
            home = base / "home with spaces"
            (cwd / "scripts").mkdir(parents=True)
            (cwd / "scripts" / "install.py").write_text("raise SystemExit(99)\n", encoding="utf-8")
            tmpdir.mkdir()

            result = self.run_remote(
                archive,
                cwd,
                tmpdir,
                "--home",
                str(home),
                "--target",
                "codex",
                "--json",
            )
            payload = json.loads(result.stdout)
            installed = home / ".codex" / "skills" / "relay-orchestra"
            self.assertEqual(Path(payload["destinations"][0]["path"]), installed.resolve())
            self.assertTrue((installed / "SKILL.md").is_file())
            self.assertEqual(list(tmpdir.iterdir()), [])

    def test_remote_supports_posix_sh_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = self.make_archive(base)
            tmpdir = base / "tmp"
            tmpdir.mkdir()
            home = base / "home"
            result = self.run_remote(
                archive,
                base,
                tmpdir,
                "--home",
                str(home),
                "--dry-run",
                "--json",
                shell="sh",
            )
            self.assertEqual(json.loads(result.stdout)["destinations"][0]["status"], "dry-run")
            self.assertFalse((home / ".agents").exists())
            self.assertEqual(list(tmpdir.iterdir()), [])

    def test_remote_requires_force_and_rejects_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = self.make_archive(base)
            tmpdir = base / "tmp"
            tmpdir.mkdir()
            home = base / "home"
            self.run_remote(archive, base, tmpdir, "--home", str(home))
            self.run_remote(archive, base, tmpdir, "--home", str(home), expected=1)
            self.run_remote(archive, base, tmpdir, "--home", str(home), "--force")
            result = self.run_remote(archive, base, tmpdir, "--link", expected=1)
            self.assertIn("--link requires a local checkout", result.stderr)
            abbreviated = self.run_remote(archive, base, tmpdir, "--lin", expected=2)
            self.assertIn("unrecognized arguments: --lin", abbreviated.stderr)
            self.assertEqual(list(tmpdir.iterdir()), [])

    def test_remote_rejects_malformed_ref_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = self.make_archive(base)
            tmpdir = base / "tmp"
            tmpdir.mkdir()
            result = self.run_remote(
                archive,
                base,
                tmpdir,
                expected=1,
                extra_env={"RELAY_ORCHESTRA_REF": "../main"},
            )
            self.assertIn("invalid RELAY_ORCHESTRA_REF", result.stderr)
            self.assertEqual(list(tmpdir.iterdir()), [])

    def test_remote_rejects_unsafe_archive_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = base / "unsafe.tar.gz"
            payload = base / "payload"
            payload.write_text("unsafe", encoding="utf-8")
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(payload, arcname="../escaped")
            tmpdir = base / "tmp"
            tmpdir.mkdir()
            result = self.run_remote(archive, base, tmpdir, expected=1)
            self.assertIn("unsafe path", result.stderr)
            self.assertFalse((base.parent / "escaped").exists())
            self.assertEqual(list(tmpdir.iterdir()), [])

    def test_remote_rejects_archive_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            archive = base / "linked.tar.gz"
            link = tarfile.TarInfo("relay-orchestra-test/scripts/install.py")
            link.type = tarfile.SYMTYPE
            link.linkname = "/tmp/untrusted-installer"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.addfile(link)
            tmpdir = base / "tmp"
            tmpdir.mkdir()
            result = self.run_remote(archive, base, tmpdir, expected=1)
            self.assertIn("non-file entry", result.stderr)
            self.assertEqual(list(tmpdir.iterdir()), [])


class ReadmeInstallerContractTests(unittest.TestCase):
    def test_remote_install_commands_are_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        command = "curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.sh | bash"
        self.assertIn(command, readme)
        self.assertIn(f"{command} -s -- --target codex", readme)


if __name__ == "__main__":
    unittest.main()
