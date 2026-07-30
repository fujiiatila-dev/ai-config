from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "aiconfig.py"
SPEC = importlib.util.spec_from_file_location("aiconfig_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
AICONFIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AICONFIG)


def write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class DoctorTests(unittest.TestCase):
    def test_every_version_reference_has_an_explicit_doctor_key(self) -> None:
        versions = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))
        doctor_keys = {item[1] for item in AICONFIG.doctor_checks()}
        self.assertLessEqual(set(versions["tools"]), doctor_keys)

    def test_doctor_compares_python_and_reports_local_codex_security(self) -> None:
        def fake_which(*names: str) -> str | None:
            if names == ("codex-security",):
                return None
            return names[0]

        output = io.StringIO()
        with (
            mock.patch.object(AICONFIG, "which", side_effect=fake_which),
            mock.patch.object(AICONFIG, "tool_version", return_value="0.0.0"),
            mock.patch.object(AICONFIG, "node_package_version", return_value="0.0.0"),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(AICONFIG.cmd_doctor(None), 0)

        text = output.getvalue()
        self.assertIn("python", text)
        self.assertIn("referência do repo: 3.14.4", text)
        self.assertIn("codex-security", text)
        self.assertIn("referência do repo: 0.1.1", text)

    def test_node_package_version_reads_metadata_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            appdata = Path(temp)
            package_json = (
                appdata
                / "npm"
                / "node_modules"
                / "@openai"
                / "codex-security"
                / "package.json"
            )
            package_json.parent.mkdir(parents=True)
            package_json.write_text('{"version": "9.8.7"}', encoding="utf-8")

            with (
                mock.patch.dict(os.environ, {"APPDATA": str(appdata)}),
                mock.patch.object(AICONFIG, "which", return_value=None),
            ):
                version = AICONFIG.node_package_version("@openai/codex-security")

        self.assertEqual(version, "9.8.7")

    def test_tool_version_ignores_failed_flags(self) -> None:
        failed = subprocess.CompletedProcess(
            ["gitleaks", "--version"], 1, "", "unknown flag"
        )
        succeeded = subprocess.CompletedProcess(
            ["gitleaks", "version"], 0, "8.30.1\n", ""
        )
        with mock.patch.object(
            AICONFIG.subprocess,
            "run",
            side_effect=[failed, succeeded],
        ):
            version = AICONFIG.tool_version("gitleaks")

        self.assertEqual(version, "8.30.1")


class ToolInstallationTests(unittest.TestCase):
    def test_security_tools_use_homebrew_when_it_is_available(self) -> None:
        def fake_which(name: str) -> str | None:
            return "/opt/homebrew/bin/brew" if name == "brew" else None

        with mock.patch.object(AICONFIG, "which", side_effect=fake_which):
            gitleaks = AICONFIG.tool_install_command("gitleaks")
            trivy = AICONFIG.tool_install_command("trivy")

        self.assertEqual(gitleaks, ["/opt/homebrew/bin/brew", "install", "gitleaks"])
        self.assertEqual(trivy, ["/opt/homebrew/bin/brew", "install", "trivy"])

    def test_security_tools_prefer_winget_when_it_is_available(self) -> None:
        def fake_which(name: str) -> str | None:
            return "winget.exe" if name == "winget" else None

        with mock.patch.object(AICONFIG, "which", side_effect=fake_which):
            command = AICONFIG.tool_install_command("gitleaks")

        self.assertEqual(command[:5], ["winget.exe", "install", "--id", "Gitleaks.Gitleaks", "--exact"])

    def test_recommended_tools_execute_commands_for_missing_tools(self) -> None:
        completed = subprocess.CompletedProcess(["installer"], 0)
        with (
            mock.patch.object(AICONFIG, "which", return_value=None),
            mock.patch.object(
                AICONFIG,
                "tool_install_command",
                side_effect=lambda name: ["installer", name],
            ),
            mock.patch.object(AICONFIG.subprocess, "run", return_value=completed) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertTrue(AICONFIG.install_recommended_tools())

        self.assertEqual(run.call_count, 4)

    def test_winget_no_upgrade_available_is_success(self) -> None:
        self.assertTrue(
            AICONFIG.install_command_succeeded(
                ["winget.exe", "install", "--id", "Gitleaks.Gitleaks"],
                0x8A15002B,
            )
        )
        self.assertFalse(
            AICONFIG.install_command_succeeded(
                ["winget.exe", "install", "--id", "Gitleaks.Gitleaks"],
                1,
            )
        )

    def test_standard_install_runs_recommended_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = SimpleNamespace(
                dry_run=False,
                skip_tools=False,
                prefer_repo=False,
                keep_existing=True,
                yes=True,
            )
            env = {
                "CLAUDE_CONFIG_DIR": str(root / "claude"),
                "CODEX_HOME": str(root / "codex"),
                "GEMINI_HOME": str(root / "gemini"),
                "RTK_CONFIG_DIR": str(root / "rtk"),
            }
            with (
                mock.patch.dict(os.environ, env),
                mock.patch.object(
                    AICONFIG,
                    "install_recommended_tools",
                    return_value=True,
                ) as install,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(AICONFIG.cmd_install(args), 0)
            install.assert_called_once_with()

    def test_skip_tools_and_dry_run_do_not_run_installers(self) -> None:
        for dry_run, skip_tools in ((True, False), (False, True)):
            with self.subTest(dry_run=dry_run, skip_tools=skip_tools):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    args = SimpleNamespace(
                        dry_run=dry_run,
                        skip_tools=skip_tools,
                        prefer_repo=False,
                        keep_existing=True,
                        yes=True,
                    )
                    env = {
                        "CLAUDE_CONFIG_DIR": str(root / "claude"),
                        "CODEX_HOME": str(root / "codex"),
                        "GEMINI_HOME": str(root / "gemini"),
                        "RTK_CONFIG_DIR": str(root / "rtk"),
                    }
                    with (
                        mock.patch.dict(os.environ, env),
                        mock.patch.object(AICONFIG, "install_recommended_tools") as install,
                        contextlib.redirect_stdout(io.StringIO()),
                    ):
                        self.assertEqual(AICONFIG.cmd_install(args), 0)
                    install.assert_not_called()


@unittest.skipUnless(os.name == "nt", "PowerShell wrapper test runs on Windows")
class PowerShellInstallerTests(unittest.TestCase):
    def test_invalid_dry_run_preserves_error_and_skips_tools(self) -> None:
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if not powershell:
            self.skipTest("PowerShell executable unavailable")

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "install.ps1"),
                "--dry-run",
                "--flag-inexistente",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Instalando dependencias externas", result.stdout)


@unittest.skipIf(os.name == "nt", "Bash behavior tests run on Unix")
class BashInstallerTests(unittest.TestCase):
    def test_configuration_failure_is_returned_before_tool_installation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fake_bin = Path(temp)
            write_executable(
                fake_bin / "python3",
                '[ "$1" = "-c" ] && exit 0\nexit 23',
            )
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:/usr/bin:/bin"

            result = subprocess.run(
                ["/bin/bash", str(ROOT / "install.sh"), "--dry-run"],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )

        self.assertEqual(result.returncode, 23)
        self.assertNotIn("Instalando dependências externas", result.stdout)
