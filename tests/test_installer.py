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
            write_executable(fake_bin / "python3", "exit 23")
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

    def test_homebrew_installs_gitleaks_and_trivy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fake_bin = Path(temp) / "bin"
            fake_bin.mkdir()
            log = Path(temp) / "brew.log"
            write_executable(fake_bin / "python3", "exit 0")
            write_executable(fake_bin / "openspec", "exit 0")
            write_executable(fake_bin / "semgrep", "exit 0")
            write_executable(
                fake_bin / "brew",
                'printf "%s\\n" "$*" >> "$BREW_LOG"\nexit 0',
            )
            env = os.environ.copy()
            env["BREW_LOG"] = str(log)
            env["PATH"] = f"{fake_bin}:/usr/bin:/bin"

            result = subprocess.run(
                ["/bin/bash", str(ROOT / "install.sh"), "--yes"],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )

            calls = log.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["install gitleaks", "install trivy"])
        self.assertIn("gitleaks instalado via brew", result.stdout)
        self.assertIn("trivy instalado via brew", result.stdout)
