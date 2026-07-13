from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import install as installer_module


INSTALLER = ROOT / "scripts" / "install.py"
SHELL_INSTALLER = ROOT / "install.sh"
POWERSHELL_INSTALLER = ROOT / "install.ps1"


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

    def test_explicit_targets_preflight_later_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            later = home / ".gemini" / "skills" / "relay-orchestra"
            later.mkdir(parents=True)
            marker = later / "existing.txt"
            marker.write_text("keep", encoding="utf-8")

            result = self.run_installer(
                "--home",
                str(home),
                "--target",
                "codex",
                "--target",
                "gemini",
                expected=1,
            )

            self.assertIn(f"destination already exists: {later.resolve()}", result.stderr)
            self.assertFalse((home / ".codex").exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_all_targets_preflight_later_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            later = home / ".config" / "opencode" / "skills" / "relay-orchestra"
            later.mkdir(parents=True)
            marker = later / "existing.txt"
            marker.write_text("keep", encoding="utf-8")

            result = self.run_installer(
                "--home",
                str(home),
                "--target",
                "all",
                expected=1,
            )

            self.assertIn(f"destination already exists: {later.resolve()}", result.stderr)
            for earlier_root in (".agents", ".codex", ".claude", ".gemini", ".cursor"):
                self.assertFalse((home / earlier_root).exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_interactive_menu_selects_environment(self) -> None:
        expected_targets = (
            ("codex", "Codex"),
            ("claude", "Claude Code"),
            ("gemini", "Gemini CLI"),
            ("cursor", "Cursor"),
            ("opencode", "OpenCode"),
            ("copilot", "GitHub Copilot"),
            ("agents", "Universal Agent Skills"),
            ("all", "All supported environments"),
        )
        self.assertEqual(installer_module.INTERACTIVE_TARGETS, expected_targets)

        output = io.StringIO()
        target = installer_module.choose_target(io.StringIO("2\n"), output)
        self.assertEqual(target, "claude")
        menu = output.getvalue()
        for index, (_, label) in enumerate(expected_targets, start=1):
            self.assertIn(f"  {index}) {label}", menu)

    def test_interactive_menu_retries_invalid_input(self) -> None:
        output = io.StringIO()
        target = installer_module.choose_target(io.StringIO("0\nunknown\n\u00b2\n9\n8\n"), output)
        self.assertEqual(target, "all")
        self.assertEqual(output.getvalue().count("Enter one of the numbers shown above."), 4)

    def test_interactive_menu_fails_on_end_of_input(self) -> None:
        with self.assertRaisesRegex(ValueError, r"pass --target <environment>"):
            installer_module.choose_target(io.StringIO(""), io.StringIO())

    def test_explicit_target_skips_interactive_prompt(self) -> None:
        with mock.patch.object(
            installer_module,
            "prompt_for_target",
            side_effect=AssertionError("explicit target prompted for input"),
        ):
            args = installer_module.parse_arguments(["--target", "gemini", "--dry-run"])
        self.assertEqual(args.target, ["gemini"])

    def test_no_arguments_use_interactive_selection(self) -> None:
        with mock.patch.object(installer_module, "prompt_for_target", return_value="cursor") as prompt:
            args = installer_module.parse_arguments([])
        prompt.assert_called_once_with()
        self.assertEqual(args.target, ["cursor"])

    @unittest.skipIf(os.name == "nt", "POSIX controlling-terminal behavior")
    def test_posix_prompt_uses_standard_streams_when_interactive(self) -> None:
        class TtyInput(io.StringIO):
            def isatty(self) -> bool:
                return True

        input_stream = TtyInput("3\n")
        output_stream = io.StringIO()
        with mock.patch.object(installer_module.sys, "stdin", input_stream):
            with mock.patch.object(installer_module.sys, "stdout", output_stream):
                with mock.patch("builtins.open", side_effect=AssertionError("/dev/tty should not be opened")):
                    target = installer_module.prompt_for_target()
        self.assertEqual(target, "gemini")
        self.assertIn("Gemini CLI", output_stream.getvalue())

    @unittest.skipIf(os.name == "nt", "POSIX controlling-terminal behavior")
    def test_posix_prompt_uses_controlling_terminal(self) -> None:
        class DuplexTerminal:
            def __init__(self) -> None:
                self.input = io.StringIO("1\n")
                self.output = io.StringIO()

            def __enter__(self) -> DuplexTerminal:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def write(self, value: str) -> int:
                return self.output.write(value)

            def flush(self) -> None:
                pass

            def readline(self) -> str:
                return self.input.readline()

        terminal = DuplexTerminal()
        with mock.patch.object(installer_module.sys.stdin, "isatty", return_value=False):
            with mock.patch("builtins.open", return_value=terminal) as open_terminal:
                target = installer_module.prompt_for_target()
        self.assertEqual(target, "codex")
        open_terminal.assert_called_once_with("/dev/tty", "r+", encoding="utf-8", buffering=1)

    def test_windows_prompt_uses_python_menu(self) -> None:
        class TtyInput(io.StringIO):
            def isatty(self) -> bool:
                return True

        input_stream = TtyInput("6\n")
        output_stream = io.StringIO()
        with mock.patch.object(installer_module.os, "name", "nt"):
            with mock.patch.object(installer_module.sys, "stdin", input_stream):
                with mock.patch.object(installer_module.sys, "stdout", output_stream):
                    target = installer_module.prompt_for_target()
        self.assertEqual(target, "copilot")
        self.assertIn("GitHub Copilot", output_stream.getvalue())

    def test_windows_noninteractive_input_fails_clearly(self) -> None:
        with mock.patch.object(installer_module.os, "name", "nt"):
            with mock.patch.object(installer_module.sys, "stdin", io.StringIO("")):
                with self.assertRaisesRegex(ValueError, r"pass --target <environment>"):
                    installer_module.prompt_for_target()

    @unittest.skipUnless(os.name == "posix", "requires POSIX session handling")
    def test_no_argument_noninteractive_process_fails_clearly(self) -> None:
        result = subprocess.run(
            [sys.executable, str(INSTALLER)],
            cwd="/",
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            check=False,
            start_new_session=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        self.assertEqual(result.stdout, "")
        self.assertIn("pass --target <environment>", result.stderr)


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
    def test_primary_skills_cli_install_is_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("npx skills add SDA-31/relay-orchestra", readme)
        self.assertEqual(readme.count("npx skills add SDA-31/relay-orchestra"), 1)
        self.assertIn("https://skills.sh/b/SDA-31/relay-orchestra", readme)
        self.assertIn("https://skills.sh/SDA-31/relay-orchestra", readme)
        self.assertIn("## When It Helps", readme)
        self.assertIn("market or competitor research", readme)
        self.assertIn("multi-module implementation", readme)
        self.assertIn("flowchart TD", readme)
        self.assertNotIn("flowchart LR", readme)
        self.assertNotIn("Python 3.7", readme)
        self.assertNotIn("curl -fsSL", readme)
        self.assertNotIn("irm https://", readme)
        self.assertNotIn("git clone --depth 1", readme)
        self.assertIn("`$relay-orchestra`", readme)
        self.assertNotRegex(readme, r"ACCEPTED R\d+")

    def test_standalone_install_commands_are_documented(self) -> None:
        installation = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        command = "curl -fsSL https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.sh | bash"
        windows_command = "irm https://raw.githubusercontent.com/SDA-31/relay-orchestra/main/install.ps1 | iex"
        self.assertIn(command, installation)
        self.assertIn(windows_command, installation)
        self.assertIn("npx skills update relay-orchestra", installation)
        self.assertIn("interactive menu", installation.lower())
        self.assertIn("`--target codex`", installation)
        self.assertIn("`bash -s -- --target codex`", installation)

    def test_powershell_remote_bootstrap_contract(self) -> None:
        script = POWERSHELL_INSTALLER.read_text(encoding="utf-8")
        self.assertIn('Invoke-WebRequest -UseBasicParsing -Uri $archiveUrl -OutFile $archive', script)
        self.assertIn('Invoke-RemoteInstall -Python $python -Arguments $InstallerArgs', script)
        self.assertIn('Stop-Install "--link requires a local checkout"', script)
        self.assertIn("RELAY_ORCHESTRA_TEST_ARCHIVE", script)


if __name__ == "__main__":
    unittest.main()
