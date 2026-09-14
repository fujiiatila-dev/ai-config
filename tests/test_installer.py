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
        self.assertIn("referência do repo: 0.1.6", text)

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
        failed = mock.Mock(returncode=1)
        failed.communicate.return_value = ("", "unknown flag")
        succeeded = mock.Mock(returncode=0)
        succeeded.communicate.return_value = ("8.30.1\n", "")
        with mock.patch.object(
            AICONFIG.subprocess,
            "Popen",
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

    def test_managed_commands_use_catalog_versions_for_each_manager(self) -> None:
        with mock.patch.object(
            AICONFIG, "which", side_effect=lambda name: "/usr/bin/npm" if name == "npm" else None
        ):
            self.assertEqual(
                AICONFIG.tool_install_command("openspec"),
                [
                    "/usr/bin/npm",
                    "install",
                    "-g",
                    "--no-audit",
                    "--no-fund",
                    "--fetch-retries=0",
                    "--fetch-timeout=15000",
                    "@fission-ai/openspec@1.7.0",
                ],
            )

        self.assertEqual(
            AICONFIG.tool_install_command("semgrep"),
            [
                AICONFIG.sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                "--disable-pip-version-check",
                "--retries",
                "0",
                "--timeout",
                "15",
                "semgrep==1.172.0",
            ],
        )
        self.assertEqual(
            AICONFIG.tool_install_command("semgrep", upgrade=True),
            [
                AICONFIG.sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                "--disable-pip-version-check",
                "--retries",
                "0",
                "--timeout",
                "15",
                "--upgrade",
                "semgrep==1.172.0",
            ],
        )

        with mock.patch.object(
            AICONFIG, "which", side_effect=lambda name: "winget.exe" if name == "winget" else None
        ):
            self.assertEqual(
                AICONFIG.tool_install_command("gitleaks", upgrade=True),
                [
                    "winget.exe",
                    "upgrade",
                    "--id",
                    "Gitleaks.Gitleaks",
                    "--exact",
                    "--version",
                    "8.30.1",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--silent",
                ],
            )

        with mock.patch.object(
            AICONFIG, "which", side_effect=lambda name: "choco.exe" if name == "choco" else None
        ):
            self.assertEqual(
                AICONFIG.tool_install_command("trivy", upgrade=True),
                [
                    "choco.exe",
                    "upgrade",
                    "trivy",
                    "--version",
                    "0.72.0",
                    "-y",
                    "--no-progress",
                ],
            )

        with mock.patch.object(
            AICONFIG, "which", side_effect=lambda name: "brew" if name == "brew" else None
        ):
            self.assertEqual(
                AICONFIG.tool_install_command("gitleaks", upgrade=True),
                ["brew", "upgrade", "gitleaks"],
            )

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

    def test_standard_install_does_not_upgrade_existing_tools(self) -> None:
        with (
            mock.patch.object(AICONFIG, "which", return_value="installed"),
            mock.patch.object(AICONFIG, "tool_install_command") as command,
            mock.patch.object(AICONFIG.subprocess, "run") as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertTrue(AICONFIG.install_recommended_tools())

        command.assert_not_called()
        run.assert_not_called()

    def test_update_tools_requests_upgrade_for_existing_tools(self) -> None:
        completed = subprocess.CompletedProcess(["installer"], 0)
        with (
            mock.patch.object(AICONFIG, "which", return_value="installed"),
            mock.patch.object(
                AICONFIG,
                "tool_install_command",
                side_effect=lambda name, upgrade=False: ["installer", name, str(upgrade)],
            ) as command,
            mock.patch.object(AICONFIG.subprocess, "run", return_value=completed) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertTrue(AICONFIG.install_recommended_tools(update=True))

        self.assertEqual(command.call_count, 4)
        self.assertTrue(all(call.kwargs == {"upgrade": True} for call in command.call_args_list))
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
                        update_tools=True,
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

    def test_new_codex_config_uses_secure_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = SimpleNamespace(
                dry_run=False,
                prefer_repo=False,
                keep_existing=True,
                yes=True,
            )
            env = {"CLAUDE_CONFIG_DIR": str(root / "claude")}
            with mock.patch.dict(os.environ, env):
                ctx = AICONFIG.Ctx(args)
                AICONFIG.install_toml(
                    ROOT / "adapters/codex/config.toml.example",
                    root / "codex.toml",
                    ctx,
                    {
                        "PYTHON": "python",
                        "NODE": "node",
                        "CLAUDE_HOME": str(root / "claude"),
                        "HEADROOM_PORT": "48731",
                    },
                )

            text = (root / "codex.toml").read_text(encoding="utf-8")

        self.assertIn('sandbox_mode = "workspace-write"', text)
        self.assertIn('approval_policy = "on-request"', text)
        self.assertIn('approvals_reviewer = "user"', text)
        self.assertIn('sandbox = "unelevated"', text)

    def test_markdown_merge_accepts_backslashes_in_managed_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.md"
            destination = root / "destination.md"
            source.write_text("PowerShell: .\\install.ps1", encoding="utf-8")
            destination.write_text(f"{AICONFIG.BEGIN}\nold\n{AICONFIG.END}\n", encoding="utf-8")
            args = SimpleNamespace(
                dry_run=False,
                prefer_repo=False,
                keep_existing=True,
                yes=True,
            )
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(root / "claude")}):
                AICONFIG.install_markdown(source, destination, AICONFIG.Ctx(args))

            merged = destination.read_text(encoding="utf-8")

        self.assertIn("PowerShell: .\\install.ps1", merged)
        self.assertNotIn("old", merged)

    def test_configured_headroom_port_rejects_invalid_values(self) -> None:
        for raw in ("0", "65536", "not-a-port"):
            with self.subTest(raw=raw), mock.patch.dict(os.environ, {"HEADROOM_PORT": raw}):
                with self.assertRaises(ValueError):
                    AICONFIG.configured_headroom_port()

        with mock.patch.dict(os.environ, {"HEADROOM_PORT": "12345"}):
            self.assertEqual(AICONFIG.configured_headroom_port(), "12345")

    def test_doctor_probes_configured_headroom_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with (
                mock.patch.dict(
                    os.environ,
                    {"HEADROOM_PORT": "12345", "CODEX_HOME": str(Path(temp) / "codex")},
                ),
                mock.patch.object(AICONFIG, "doctor_checks", return_value=[]),
                mock.patch.object(AICONFIG, "which", return_value=None),
                mock.patch.object(AICONFIG, "proxy_status", return_value="fora") as probe,
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(AICONFIG.cmd_doctor(None), 0)

        probe.assert_called_once_with("12345")
        self.assertIn("HEADROOM_PORT = 12345", output.getvalue())

    def test_tool_version_stops_after_shared_deadline(self) -> None:
        process = mock.Mock(
            pid=123,
            returncode=-9,
            communicate=mock.Mock(
                side_effect=[subprocess.TimeoutExpired(["stuck"], 1.0), ("", "")]
            ),
        )
        with (
            mock.patch.object(AICONFIG, "VERSION_PROBE_TIMEOUT_SEC", 1.0),
            mock.patch.object(AICONFIG.time, "monotonic", side_effect=[0.0, 0.0, 2.0]),
            mock.patch.object(AICONFIG.subprocess, "run", return_value=None),
            mock.patch.object(AICONFIG.subprocess, "Popen", return_value=process) as run,
        ):
            self.assertIsNone(AICONFIG.tool_version("stuck"))

        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["creationflags"], AICONFIG.subprocess.CREATE_NEW_PROCESS_GROUP)

    def test_codex_doctor_detects_broad_trust_and_elevated_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "profile"
            home.mkdir()
            config = root / "config.toml"
            config.write_text(
                f'[windows]\nsandbox = "elevated"\n\n[projects."{home}"]\ntrust_level = "trusted"\n',
                encoding="utf-8",
            )
            with mock.patch.object(AICONFIG.Path, "home", return_value=home):
                findings = AICONFIG.codex_security_findings(config)

        self.assertTrue(any("windows.sandbox=elevated" in finding for finding in findings))
        self.assertTrue(any("raiz do perfil" in finding for finding in findings))
        self.assertTrue(any("approval_policy" in finding for finding in findings))

    def test_harden_codex_preserves_unknown_keys_and_removes_only_broad_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "profile"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            config = root / "config.toml"
            original = (
                'sandbox_mode = "danger-full-access"\n'
                'approval_policy = "never"\n'
                'custom_root = "keep"\n\n'
                '[windows]\n'
                'sandbox = "elevated"\n'
                'custom_windows = true\n\n'
                f'[projects."{home}"]\n'
                'trust_level = "trusted"\n\n'
                f'[projects."{project}"]\n'
                'trust_level = "trusted"\n'
                'custom_project = "keep"\n'
            )
            config.write_text(original, encoding="utf-8")
            args = SimpleNamespace(
                dry_run=False,
                prefer_repo=False,
                keep_existing=True,
                yes=True,
            )
            with (
                mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(root / "claude")}),
                mock.patch.object(AICONFIG.Path, "home", return_value=home),
            ):
                ctx = AICONFIG.Ctx(args)
                AICONFIG.harden_codex_config(config, ctx)

            updated = config.read_text(encoding="utf-8")
            backups = list((root / "claude" / "backups").glob("ai-config-*/**/config.toml"))
            backup_contents = backups[0].read_text(encoding="utf-8") if backups else None

        self.assertIn('sandbox_mode = "workspace-write"', updated)
        self.assertIn('approval_policy = "on-request"', updated)
        self.assertIn('approvals_reviewer = "user"', updated)
        self.assertIn('sandbox = "unelevated"', updated)
        self.assertIn('custom_root = "keep"', updated)
        self.assertIn('custom_windows = true', updated)
        self.assertNotIn(f'[projects."{home}"]', updated)
        self.assertIn(f'[projects."{project}"]', updated)
        self.assertIn('custom_project = "keep"', updated)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backup_contents, original)

    def test_harden_codex_keeps_broad_trust_section_with_other_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "profile"
            home.mkdir()
            config = root / "config.toml"
            config.write_text(
                'sandbox_mode = "workspace-write"\n\n'
                f'[projects."{home}"]\n'
                'trust_level = "trusted"\n'
                'other = true\n',
                encoding="utf-8",
            )
            args = SimpleNamespace(
                dry_run=False,
                prefer_repo=False,
                keep_existing=True,
                yes=True,
            )
            with (
                mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(root / "claude")}),
                mock.patch.object(AICONFIG.Path, "home", return_value=home),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                AICONFIG.harden_codex_config(config, AICONFIG.Ctx(args))

            updated = config.read_text(encoding="utf-8")

        self.assertIn(f'[projects."{home}"]', updated)
        self.assertIn('trust_level = "trusted"', updated)
        self.assertIn("other = true", updated)


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
