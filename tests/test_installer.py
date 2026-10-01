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


def setUpModule() -> None:
    # O doctor abre um handshake TLS real; a suíte roda offline e determinística.
    os.environ["AICONFIG_DOCTOR_OFFLINE"] = "1"


def write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def validation_fixture(parent: str | Path) -> Path:
    root = Path(parent) / "repo"
    files = (
        ".env.example",
        "README.md",
        "CONFIGURATION_MAP.md",
        "HEADROOM.md",
        "TOOLS.md",
        "install.sh",
        "install.ps1",
        "shared/WORKFLOW.md",
        "claude/settings.json",
        "claude/CLAUDE.md",
        "claude/RTK.md",
        "claude/statusline.py",
        "adapters/codex/AGENTS.md",
        "adapters/codex/config.toml.example",
        "adapters/codex/headroom.config.toml.example",
        "adapters/codex/hooks.json",
        "adapters/codex/hooks.impeccable.json",
        "adapters/codex/windows.config.toml.example",
        "adapters/gemini/GEMINI.md",
        "adapters/gemini/antigravity-rule.md",
        "adapters/rtk/filters.toml",
        "tools/recover_codex_sessions.py",
        "versions.json",
    )
    for relative in files:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    (root / "claude/agents").mkdir(parents=True, exist_ok=True)
    (root / "claude/skills").mkdir(parents=True, exist_ok=True)
    for skill in (ROOT / "claude/skills").iterdir():
        (root / "claude/skills" / skill.name).mkdir(exist_ok=True)
    return root


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

        refs = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))["tools"]
        text = output.getvalue()
        self.assertIn("python", text)
        self.assertIn(f"referência do repo: {refs['python']}", text)
        self.assertIn("codex-security", text)
        self.assertIn(f"referência do repo: {refs['codex_security']}", text)

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


class ValidationTests(unittest.TestCase):
    def test_valid_repository_report_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }

            report = AICONFIG.validate_repository(root)
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }

        self.assertTrue(report.ok)
        self.assertEqual(before, after)
        self.assertEqual(report.as_dict()["schema_version"], 1)

    def test_missing_source_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            (root / "shared/WORKFLOW.md").unlink()
            report = AICONFIG.validate_repository(root)

        self.assertFalse(report.ok)
        self.assertIn("missing-source", {item["code"] for item in report.errors})

    def test_invalid_json_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            (root / "claude/settings.json").write_text("{broken", encoding="utf-8")
            report = AICONFIG.validate_repository(root)

        self.assertIn("invalid-json", {item["code"] for item in report.errors})

    def test_unknown_placeholder_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            path = root / "adapters/codex/headroom.config.toml.example"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "{{HEADROOM_PORT}}", "{{UNKNOWN}}"
                ),
                encoding="utf-8",
            )
            report = AICONFIG.validate_repository(root)

        self.assertIn("unknown-placeholder", {item["code"] for item in report.errors})

    def test_security_findings_redact_values_and_allow_loopback_examples(self) -> None:
        secret = "sk-" + "A" * 24
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            env = root / ".env.example"
            env.write_text(env.read_text(encoding="utf-8") + f"\nEXAMPLE={secret}\n", encoding="utf-8")
            report = AICONFIG.validate_repository(root)
            payload = json.dumps(report.as_dict(), ensure_ascii=False)

        self.assertIn("credential-pattern", {item["code"] for item in report.errors})
        self.assertNotIn(secret, payload)
        self.assertNotIn("non-loopback-endpoint", {item["code"] for item in report.errors})

    def test_absolute_path_and_external_endpoint_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            config = root / "adapters/codex/headroom.config.toml.example"
            text = config.read_text(encoding="utf-8")
            text = text.replace("http://127.0.0.1:{{HEADROOM_PORT}}/v1", "https://service.example/v1")
            config.write_text(text + "\nlocal = 'C:\\Users\\alice\\config'\n", encoding="utf-8")
            report = AICONFIG.validate_repository(root)

        codes = {item["code"] for item in report.errors}
        self.assertIn("non-loopback-endpoint", codes)
        self.assertIn("machine-absolute-path", codes)

    def test_json_output_is_single_document(self) -> None:
        report = AICONFIG.ValidationReport()
        output = io.StringIO()
        with (
            mock.patch.object(AICONFIG, "validate_repository", return_value=report),
            contextlib.redirect_stdout(output),
        ):
            result = AICONFIG.cmd_validate(SimpleNamespace(json=True))

        data = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(data["status"], "passed")
        self.assertEqual(data["schema_version"], 1)

    def test_install_stops_before_context_when_preflight_fails(self) -> None:
        report = AICONFIG.ValidationReport()
        report.error("invalid-json", "claude/settings.json", "invalid", "fix")
        args = SimpleNamespace(
            dry_run=False,
            skip_tools=False,
            update_tools=False,
            prefer_repo=False,
            keep_existing=True,
            yes=True,
        )
        with mock.patch.object(AICONFIG, "validate_repository", return_value=report), mock.patch.object(AICONFIG, "Ctx") as ctx:
            result = AICONFIG.cmd_install(args)

        self.assertEqual(result, 2)
        ctx.assert_not_called()

    def test_validate_does_not_start_tools_or_headroom(self) -> None:
        report = AICONFIG.ValidationReport()
        with (
            mock.patch.object(AICONFIG, "validate_repository", return_value=report),
            mock.patch.object(AICONFIG, "install_recommended_tools") as install,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(AICONFIG.cmd_validate(SimpleNamespace(json=False)), 0)

        install.assert_not_called()


class HeadroomConfigurationTests(unittest.TestCase):
    def test_default_agent_configs_do_not_require_headroom(self) -> None:
        settings = json.loads((ROOT / "claude" / "settings.json").read_text(encoding="utf-8"))
        codex = (ROOT / "adapters" / "codex" / "config.toml.example").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ANTHROPIC_BASE_URL", settings.get("env", {}))
        self.assertNotIn('model_provider = "headroom"', codex)
        for source in ("hooks.json", "hooks.impeccable.json"):
            codex_hooks = (ROOT / "adapters" / "codex" / source).read_text(encoding="utf-8")
            self.assertNotIn("headroom", codex_hooks.lower())
        self.assertFalse((ROOT / "tools" / "headroom_healthcheck.py").exists())

    def test_codex_headroom_profile_is_explicit_and_disables_websockets(self) -> None:
        profile = (
            ROOT / "adapters" / "codex" / "headroom.config.toml.example"
        ).read_text(encoding="utf-8")
        self.assertIn('model_provider = "headroom"', profile)
        self.assertIn('base_url = "http://127.0.0.1:{{HEADROOM_PORT}}/v1"', profile)
        self.assertIn("supports_websockets = false", profile)
        self.assertIn('wire_api = "responses"', profile)
        self.assertIn("[mcp_servers.headroom]", profile)
        self.assertIn('command = "{{HEADROOM}}"', profile)

    def test_preflight_rejects_persistent_headroom_routing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            settings_path = root / "claude/settings.json"
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            settings.setdefault("env", {})["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:48731"
            settings_path.write_text(json.dumps(settings), encoding="utf-8")
            config = root / "adapters/codex/config.toml.example"
            config_text = config.read_text(encoding="utf-8")
            config.write_text(
                config_text.replace(
                    "[windows]", 'model_provider = "headroom"\n\n[windows]', 1
                ),
                encoding="utf-8",
            )
            report = AICONFIG.validate_repository(root)

        codes = [item["code"] for item in report.errors]
        self.assertGreaterEqual(codes.count("persistent-headroom-route"), 2)


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
        versions = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))["tools"]

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
                    f"@fission-ai/openspec@{versions['openspec']}",
                ],
            )

        with mock.patch.object(AICONFIG, "pip_needs_truststore_flag", return_value=False):
            semgrep_install = AICONFIG.tool_install_command("semgrep")
            semgrep_upgrade = AICONFIG.tool_install_command("semgrep", upgrade=True)
        self.assertEqual(
            semgrep_install,
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
                f"semgrep=={versions['semgrep']}",
            ],
        )
        self.assertEqual(
            semgrep_upgrade,
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
                f"semgrep=={versions['semgrep']}",
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
                    "--source",
                    "winget",
                    "--version",
                    versions["gitleaks"],
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
                    versions["trivy"],
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
                    AICONFIG, "validate_repository", return_value=AICONFIG.ValidationReport()
                ),
                mock.patch.object(
                    AICONFIG,
                    "install_recommended_tools",
                    return_value=True,
                ) as install,
                mock.patch.object(AICONFIG.subprocess, "run") as run,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(AICONFIG.cmd_install(args), 0)
            install.assert_called_once_with()
            run.assert_not_called()
            self.assertTrue((root / "codex" / "headroom.config.toml").exists())
            self.assertNotIn(
                'model_provider = "headroom"',
                (root / "codex" / "config.toml").read_text(encoding="utf-8"),
            )

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
                        mock.patch.object(
                            AICONFIG,
                            "validate_repository",
                            return_value=AICONFIG.ValidationReport(),
                        ),
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

    def test_doctor_reports_persistent_claude_route_without_exposing_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            claude = root / "claude"
            claude.mkdir()
            (claude / "settings.json").write_text(
                json.dumps({"env": {"ANTHROPIC_BASE_URL": "http://127.0.0.1:8787"}}),
                encoding="utf-8",
            )
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "HEADROOM_PORT": "12345",
                        "CLAUDE_CONFIG_DIR": str(claude),
                        "CODEX_HOME": str(root / "codex"),
                        "ANTHROPIC_BASE_URL": "http://127.0.0.1:8787",
                        "OPENAI_BASE_URL": "",
                    },
                    clear=False,
                ),
                mock.patch.object(AICONFIG, "doctor_checks", return_value=[]),
                mock.patch.object(AICONFIG, "which", return_value=None),
                mock.patch.object(AICONFIG, "proxy_status", return_value="ok"),
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(AICONFIG.cmd_doctor(None), 0)

        text = output.getvalue()
        self.assertIn("Roteamento Headroom persistente", text)
        self.assertIn("settings.json persiste ANTHROPIC_BASE_URL", text)
        self.assertIn("risco de ConnectionRefused", text)
        self.assertNotIn("http://127.0.0.1:8787", text)

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
            # PID falso: no Unix, nunca sinalizar um grupo de processos real.
            mock.patch.object(AICONFIG.os, "getpgid", create=True, return_value=123),
            mock.patch.object(AICONFIG.os, "killpg", create=True) as killpg,
        ):
            self.assertIsNone(AICONFIG.tool_version("stuck"))

        run.assert_called_once()
        if os.name == "nt":
            self.assertEqual(
                run.call_args.kwargs["creationflags"], AICONFIG.subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            self.assertTrue(run.call_args.kwargs["start_new_session"])
            killpg.assert_called_once()

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


class ToolInteropTests(unittest.TestCase):
    def _claude_home(self, temp: str, settings: dict) -> Path:
        home = Path(temp) / "claude"
        home.mkdir()
        (home / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
        return home

    def test_store_alias_is_detected_with_either_separator(self) -> None:
        self.assertTrue(AICONFIG.is_store_alias(r"C:\Users\u\AppData\Local\Microsoft\WindowsApps\python3.EXE"))
        self.assertTrue(AICONFIG.is_store_alias("C:/Users/u/AppData/Local/Microsoft/WindowsApps/python3.EXE"))
        self.assertFalse(AICONFIG.is_store_alias(r"C:\Python311\python.exe"))

    def test_python_placeholder_skips_store_alias(self) -> None:
        alias = r"C:\Users\u\AppData\Local\Microsoft\WindowsApps\python3.exe"
        with (
            mock.patch.object(AICONFIG.sys, "executable", alias),
            mock.patch.object(
                AICONFIG,
                "which",
                side_effect=lambda name: alias if name == "python3" else r"C:\Python311\python.exe",
            ),
        ):
            self.assertEqual(AICONFIG.resolve_python(), r"C:\Python311\python.exe")

    def test_python_placeholder_prefers_running_interpreter(self) -> None:
        with mock.patch.object(AICONFIG, "which", return_value="/other/python3"):
            self.assertEqual(AICONFIG.resolve_python(), AICONFIG.sys.executable)

    def test_version_probe_disables_semgrep_network_check(self) -> None:
        process = mock.Mock(returncode=0)
        process.communicate.return_value = ("1.178.0\n", "")
        with mock.patch.object(AICONFIG.subprocess, "Popen", return_value=process) as popen:
            self.assertEqual(AICONFIG.tool_version("semgrep", 20.0), "1.178.0")
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["SEMGREP_ENABLE_VERSION_CHECK"], "0")

    def test_slow_python_tools_get_longer_probe_budget(self) -> None:
        self.assertGreater(AICONFIG.VERSION_PROBE_TIMEOUTS["semgrep"], AICONFIG.VERSION_PROBE_TIMEOUT_SEC)
        self.assertGreater(AICONFIG.VERSION_PROBE_TIMEOUTS["headroom"], AICONFIG.VERSION_PROBE_TIMEOUT_SEC)

    def test_pip_truststore_flag_only_where_it_is_opt_in(self) -> None:
        for installed, expected in (("21.3", False), ("22.2", True), ("24.0", True), ("24.2", False), ("25.1", False)):
            with mock.patch("importlib.metadata.version", return_value=installed):
                self.assertEqual(AICONFIG.pip_needs_truststore_flag(), expected, installed)

    def test_semgrep_command_adds_truststore_when_needed(self) -> None:
        with mock.patch.object(AICONFIG, "pip_needs_truststore_flag", return_value=True):
            command = AICONFIG.tool_install_command("semgrep")
        self.assertIn("--use-feature=truststore", command)

    def test_local_findings_flag_store_alias_missing_hook_and_broad_rules(self) -> None:
        settings = {
            "statusLine": {
                "type": "command",
                "command": '"C:/Users/u/AppData/Local/Microsoft/WindowsApps/python3.EXE" "x/statusline.py"',
            },
            "hooks": {"PreToolUse": []},
            "permissions": {"allow": ["Bash(rtk:*)", "Bash(git status:*)", "Bash(headroom:*)"]},
        }
        with tempfile.TemporaryDirectory() as temp:
            findings = AICONFIG.claude_local_findings(self._claude_home(temp, settings))

        text = "\n".join(findings)
        self.assertIn("WindowsApps", text)
        self.assertIn("hook RTK ausente", text)
        self.assertIn("Bash(rtk:*)", text)
        self.assertIn("Bash(headroom:*)", text)
        self.assertNotIn("Bash(git status:*)", text)

    def test_repo_settings_have_no_local_findings(self) -> None:
        settings = json.loads((ROOT / "claude/settings.json").read_text(encoding="utf-8"))
        settings["statusLine"]["command"] = f'"{AICONFIG.sys.executable}" "statusline.py"'
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(AICONFIG.claude_local_findings(self._claude_home(temp, settings)), [])

    def test_repo_permissions_are_not_broad(self) -> None:
        allow = json.loads((ROOT / "claude/settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
        self.assertFalse(set(allow) & set(AICONFIG.BROAD_TOOL_PERMISSIONS))
        self.assertIn("Bash(rtk gain:*)", allow)

    def test_tls_probe_is_skipped_offline(self) -> None:
        with (
            mock.patch.dict(os.environ, {"AICONFIG_DOCTOR_OFFLINE": "1"}),
            mock.patch.object(AICONFIG, "_tls_handshake") as handshake,
        ):
            self.assertEqual(AICONFIG.tls_inspection_status(), ("ignorado", None))
        handshake.assert_not_called()

    def test_tls_probe_reports_intercepting_issuer(self) -> None:
        intercepted = {"issuer": ((("commonName", "AVG Web/Mail Shield Root"),),)}
        with (
            mock.patch.dict(os.environ, {"AICONFIG_DOCTOR_OFFLINE": ""}),
            mock.patch.object(AICONFIG, "mozilla_ca_file", return_value="certifi.pem"),
            mock.patch.object(AICONFIG.ssl, "create_default_context"),
            mock.patch.object(
                AICONFIG,
                "_tls_handshake",
                side_effect=[AICONFIG.ssl.SSLCertVerificationError("unknown issuer"), intercepted],
            ),
        ):
            status = AICONFIG.tls_inspection_status()
        self.assertEqual(status, ("inspecionado", "AVG Web/Mail Shield Root"))

    def test_tls_probe_without_network_is_not_an_error(self) -> None:
        with (
            mock.patch.dict(os.environ, {"AICONFIG_DOCTOR_OFFLINE": ""}),
            mock.patch.object(AICONFIG, "mozilla_ca_file", return_value="certifi.pem"),
            mock.patch.object(AICONFIG.ssl, "create_default_context"),
            mock.patch.object(AICONFIG, "_tls_handshake", side_effect=OSError("offline")),
        ):
            self.assertEqual(AICONFIG.tls_inspection_status(), ("ignorado", None))

    def test_ca_bundle_combines_certifi_and_system_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            certifi = Path(temp) / "certifi.pem"
            certifi.write_text("MOZILLA\n", encoding="ascii")
            with (
                mock.patch.object(AICONFIG, "mozilla_ca_file", return_value=str(certifi)),
                mock.patch.object(AICONFIG, "windows_trusted_roots", return_value=["LOCAL-ROOT\n"]),
            ):
                content, count = AICONFIG.build_ca_bundle()
        self.assertEqual(count, 1)
        self.assertTrue(content.startswith("MOZILLA\n"))
        self.assertIn("LOCAL-ROOT", content)

    def test_windows_roots_keep_only_server_auth_certificates(self) -> None:
        entries = [
            (b"a", "x509_asn", True),
            (b"b", "x509_asn", {AICONFIG.SERVER_AUTH_OID}),
            (b"c", "x509_asn", {"1.3.6.1.5.5.7.3.3"}),
            (b"a", "x509_asn", True),
            (b"d", "pkcs_7_asn", True),
        ]
        with (
            mock.patch.object(AICONFIG.ssl, "enum_certificates", create=True, side_effect=[entries, []]),
            mock.patch.object(AICONFIG.ssl, "DER_cert_to_PEM_cert", side_effect=lambda der: der.decode()),
        ):
            self.assertEqual(AICONFIG.windows_trusted_roots(), ["a", "b"])

    @unittest.skipUnless(os.name == "nt", "o bundle só é gerado no Windows")
    def test_ca_bundle_command_writes_only_the_requested_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "sub" / "bundle.pem"
            with (
                mock.patch.object(AICONFIG, "build_ca_bundle", return_value=("PEM\n", 3)),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                code = AICONFIG.cmd_ca_bundle(SimpleNamespace(output=str(dest), dry_run=False))
            self.assertEqual(code, 0)
            self.assertEqual(dest.read_text(encoding="ascii"), "PEM\n")

            dry = Path(temp) / "dry.pem"
            with (
                mock.patch.object(AICONFIG, "build_ca_bundle", return_value=("PEM\n", 3)),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                AICONFIG.cmd_ca_bundle(SimpleNamespace(output=str(dry), dry_run=True))
            self.assertFalse(dry.exists())

    def test_wrappers_expose_ca_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            wrapper = root / "install.ps1"
            wrapper.write_text(
                wrapper.read_text(encoding="utf-8").replace("--ca-bundle", "--ca"), encoding="utf-8"
            )
            report = AICONFIG.validate_repository(root)
        codes = [item["code"] for item in report.as_dict()["errors"]]
        self.assertIn("wrapper-command-missing", codes)


class CodexAndAntigravityTests(unittest.TestCase):
    def _ctx(self, policy: str = "repo", dry_run: bool = False):
        return AICONFIG.Ctx(
            SimpleNamespace(
                dry_run=dry_run,
                prefer_repo=policy == "repo",
                keep_existing=policy == "local",
                yes=True,
            )
        )

    def test_includes_are_expanded_from_the_repository(self) -> None:
        body = AICONFIG.expand_includes("antes\n<!-- ai-config:include shared/WORKFLOW.md -->\ndepois")
        workflow = (ROOT / "shared/WORKFLOW.md").read_text(encoding="utf-8").strip()
        self.assertIn(workflow, body)
        self.assertNotIn("ai-config:include", body)

    def test_adapters_do_not_rely_on_at_imports(self) -> None:
        for relative in AICONFIG.ADAPTER_INSTRUCTION_FILES:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^@\S+", relative)
            self.assertIn("<!-- ai-config:include shared/WORKFLOW.md -->", text, relative)

    def test_preflight_rejects_at_import_and_missing_include(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = validation_fixture(temp)
            agents = root / "adapters/codex/AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8")
                + "\n@WORKFLOW.md\n<!-- ai-config:include nao/existe.md -->\n",
                encoding="utf-8",
            )
            codes = [e["code"] for e in AICONFIG.validate_repository(root).as_dict()["errors"]]
        self.assertIn("adapter-import-unsupported", codes)
        self.assertIn("adapter-include-missing", codes)

    def test_markdown_preamble_is_written_once_and_block_updates(self) -> None:
        preamble = "---\ntrigger: always_on\n---\n\n"
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / "src.md"
            dest = Path(temp) / "rules" / "ai-config.md"
            src.write_text("versão 1", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                AICONFIG.install_markdown(src, dest, self._ctx(), preamble=preamble)
                src.write_text("versão 2", encoding="utf-8")
                AICONFIG.install_markdown(src, dest, self._ctx(), preamble=preamble)
            text = dest.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\ntrigger: always_on\n---"))
        self.assertEqual(text.count("trigger: always_on"), 1)
        self.assertIn("versão 2", text)
        self.assertNotIn("versão 1", text)

    def test_legacy_codex_hooks_are_detected(self) -> None:
        legacy_windows = 'if exist "a.cmd" ("a.cmd" hook & exit /b)'
        self.assertIsNotNone(AICONFIG._codex_legacy_hook({"command": "rtk hook claude"}))
        self.assertIsNotNone(AICONFIG._codex_legacy_hook({"command": "x", "commandWindows": legacy_windows}))
        self.assertIsNone(AICONFIG._codex_legacy_hook({"command": "rtk hook codex"}))

    def _legacy_codex_hooks(self) -> dict:
        launcher = "C:\\u\\.agents\\skills\\impeccable\\scripts\\impeccable"
        return {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash|PowerShell", "hooks": [{"type": "command", "command": "rtk hook claude"}]}
                ],
                "PostToolUse": [
                    {
                        "matcher": "Edit|Write|apply_patch",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"[ ! -f '{launcher}' ] || '{launcher}' hook",
                                "commandWindows": f'if exist "{launcher}.cmd" ("{launcher}.cmd" hook & exit /b)',
                            }
                        ],
                    }
                ],
                "Custom": [{"hooks": [{"type": "command", "command": "meu-hook"}]}],
            }
        }

    def _install_codex_hooks(self, policy: str) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "hooks.json"
            dest.write_text(json.dumps(self._legacy_codex_hooks()), encoding="utf-8")
            subst = {"AGENTS_HOME": "C:/u/.agents", "AGENTS_HOME_WIN": "C:\\u\\.agents"}
            with contextlib.redirect_stdout(io.StringIO()):
                for source in ("hooks.json", "hooks.impeccable.json"):
                    AICONFIG.install_json(
                        ROOT / "adapters/codex" / source,
                        dest,
                        self._ctx(policy),
                        subst,
                        legacy=AICONFIG._codex_legacy_hook,
                    )
            return json.loads(dest.read_text(encoding="utf-8"))

    def test_prefer_repo_replaces_broken_codex_hooks_without_duplicates(self) -> None:
        hooks = self._install_codex_hooks("repo")["hooks"]
        commands = [h.get("command") for e in hooks["PreToolUse"] for h in e["hooks"]]
        self.assertEqual(commands, ["rtk hook codex"])
        windows = [h.get("commandWindows", "") for e in hooks["PostToolUse"] for h in e["hooks"]]
        self.assertEqual(windows, ["C:\\u\\.agents\\skills\\impeccable\\scripts\\impeccable.cmd hook"])
        self.assertEqual(hooks["Custom"][0]["hooks"][0]["command"], "meu-hook")

    def test_keep_existing_never_removes_legacy_hooks(self) -> None:
        hooks = self._install_codex_hooks("local")["hooks"]
        commands = [h.get("command") for e in hooks["PreToolUse"] for h in e["hooks"]]
        self.assertIn("rtk hook claude", commands)

    def test_codex_windows_hook_command_needs_no_quotes(self) -> None:
        hooks = json.loads((ROOT / "adapters/codex/hooks.impeccable.json").read_text(encoding="utf-8"))["hooks"]
        for event in ("PostToolUse", "Stop"):
            windows = hooks[event][0]["hooks"][0]["commandWindows"]
            self.assertNotIn('"', windows)
            self.assertTrue(windows.startswith("{{AGENTS_HOME_WIN}}"))

    def test_windows_fragment_disables_daemon_auto_start(self) -> None:
        text = (ROOT / "adapters/codex/windows.config.toml.example").read_text(encoding="utf-8")
        keys = AICONFIG._toml_keys(AICONFIG._toml_sections(text)["[features]"])
        self.assertEqual(keys["daemon_auto_start"], "false")

    def test_short_path_keeps_paths_without_spaces(self) -> None:
        self.assertEqual(AICONFIG.windows_short_path(Path("C:/u/.agents")), "C:\\u\\.agents")

    def _codex_profile(self, temp: str, *, daemon, legacy: bool, at_import: bool) -> tuple[Path, Path]:
        codex = Path(temp) / "codex"
        agents = Path(temp) / "agents"
        codex.mkdir()
        features = "[features]\nhooks = true\n" + (f"daemon_auto_start = {daemon}\n" if daemon else "")
        (codex / "config.toml").write_text(features, encoding="utf-8")
        clean = {
            "hooks": {
                "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook codex"}]}]
            }
        }
        hooks = self._legacy_codex_hooks() if legacy else clean
        (codex / "hooks.json").write_text(json.dumps(hooks), encoding="utf-8")
        (codex / "AGENTS.md").write_text("@WORKFLOW.md\n" if at_import else "texto\n", encoding="utf-8")
        return codex, agents

    def test_codex_findings_explain_windows_and_missing_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            codex, agents = self._codex_profile(temp, daemon=None, legacy=True, at_import=True)
            text = "\n".join(AICONFIG.codex_local_findings(codex, agents, windows=True))
        self.assertIn("daemon_auto_start", text)
        self.assertIn("rtk hook codex", text)
        self.assertIn("PowerShell", text)
        self.assertIn("@WORKFLOW.md", text)
        self.assertIn("skills ausentes", text)

    def test_codex_findings_are_empty_for_a_clean_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            codex, agents = self._codex_profile(temp, daemon="false", legacy=False, at_import=False)
            shutil.copytree(ROOT / "claude/skills", agents / "skills")
            self.assertEqual(AICONFIG.codex_local_findings(codex, agents, windows=True), [])

    def test_daemon_check_only_applies_on_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            codex, agents = self._codex_profile(temp, daemon=None, legacy=False, at_import=False)
            shutil.copytree(ROOT / "claude/skills", agents / "skills")
            self.assertEqual(AICONFIG.codex_local_findings(codex, agents, windows=False), [])

    def test_antigravity_findings_report_rule_and_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            gemini = Path(temp) / "gemini"
            gemini.mkdir()
            text = "\n".join(AICONFIG.antigravity_local_findings(gemini))
            self.assertIn("config/rules/ai-config.md", text)
            self.assertIn("skills ausentes", text)
            (gemini / "config" / "rules").mkdir(parents=True)
            (gemini / "config" / "rules" / "ai-config.md").write_text("x", encoding="utf-8")
            shutil.copytree(ROOT / "claude/skills", gemini / "config" / "skills")
            self.assertEqual(AICONFIG.antigravity_local_findings(gemini), [])

    def test_headroom_env_uses_bundle_without_overriding_the_user(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "ca.pem"
            bundle.write_text("PEM", encoding="ascii")
            with mock.patch.object(AICONFIG, "default_ca_bundle_path", return_value=bundle):
                env, notes = AICONFIG.headroom_session_env({})
                own, _ = AICONFIG.headroom_session_env({"SSL_CERT_FILE": "meu.pem"})
        self.assertEqual(env["HEADROOM_DISABLE_KOMPRESS"], "1")
        self.assertEqual(env["SSL_CERT_FILE"], str(bundle))
        self.assertEqual(env["REQUESTS_CA_BUNDLE"], str(bundle))
        self.assertTrue(notes)
        self.assertEqual(own["SSL_CERT_FILE"], "meu.pem")

    def test_headroom_commands_match_the_documented_session(self) -> None:
        self.assertEqual(
            AICONFIG.headroom_command("claude", "48731", "headroom", []),
            ["headroom", "wrap", "claude", "--port", "48731", "--tool-search", "true"],
        )
        proxy = AICONFIG.headroom_command("proxy", "48731", "headroom", ["--lossless"])
        self.assertEqual(proxy[:2], ["headroom", "proxy"])
        self.assertIn("127.0.0.1", proxy)
        self.assertEqual(proxy[-1], "--lossless")

    def test_headroom_dry_run_never_launches(self) -> None:
        argv = ["aiconfig", "headroom", "claude", "--dry-run", "--no-mcp"]
        with (
            mock.patch.object(AICONFIG.sys, "argv", argv),
            mock.patch.object(AICONFIG, "which", return_value="headroom"),
            mock.patch.object(AICONFIG, "tls_inspection_status", return_value=("ok", None)),
            mock.patch.object(AICONFIG.subprocess, "call") as call,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(AICONFIG.main(), 0)
        call.assert_not_called()
        self.assertIn("--no-mcp", output.getvalue())

    def test_unknown_arguments_are_rejected_outside_headroom(self) -> None:
        with (
            mock.patch.object(AICONFIG.sys, "argv", ["aiconfig", "doctor", "--bogus"]),
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            AICONFIG.main()

    def test_doctor_flags_persisted_headroom_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / ".claude.json"
            state.write_text(json.dumps({"mcpServers": {"headroom": {"command": "headroom"}}}), encoding="utf-8")
            environment = {
                "CLAUDE_STATE_FILE": str(state),
                "CLAUDE_CONFIG_DIR": str(Path(temp) / "c"),
                "CODEX_HOME": str(Path(temp) / "x"),
                "ANTHROPIC_BASE_URL": "",
                "OPENAI_BASE_URL": "",
            }
            with (
                mock.patch.dict(os.environ, environment),
                mock.patch.object(AICONFIG, "_windows_persistent_provider_env", return_value=set()),
            ):
                text = "\n".join(AICONFIG.headroom_persistence_findings())
        self.assertIn("MCP `headroom`", text)

class HeadroomAutoTests(unittest.TestCase):
    def _ctx(self, dry_run: bool = False):
        return AICONFIG.Ctx(SimpleNamespace(dry_run=dry_run, prefer_repo=False, keep_existing=True, yes=True))

    def test_healthy_claude_goes_through_wrap_without_persistent_side_effects(self) -> None:
        command = AICONFIG.auto_agent_command("claude", "claude.exe", "headroom", "48731", True, ["-p", "oi"])
        self.assertEqual(command[:3], ["headroom", "wrap", "claude"])
        self.assertIn("--no-proxy", command)
        self.assertIn("--no-mcp", command)
        self.assertNotIn("--1m", command)
        separator = command.index("--")
        self.assertEqual(command[separator + 1 : separator + 3], ["-p", "oi"])
        self.assertEqual(command[-2], "--mcp-config")

    def test_unhealthy_proxy_falls_back_to_the_direct_agent(self) -> None:
        self.assertEqual(
            AICONFIG.auto_agent_command("claude", "claude.exe", "headroom", "48731", False, ["--resume", "x"]),
            ["claude.exe", "--resume", "x"],
        )
        self.assertEqual(
            AICONFIG.auto_agent_command("codex", "codex.cmd", "headroom", "48731", False, []), ["codex.cmd"]
        )

    def test_healthy_codex_uses_the_opt_in_profile(self) -> None:
        self.assertEqual(
            AICONFIG.auto_agent_command("codex", "codex.cmd", "headroom", "48731", True, ["exec", "x"]),
            ["codex.cmd", "--profile", "headroom", "exec", "x"],
        )

    def test_management_calls_skip_the_proxy(self) -> None:
        self.assertTrue(AICONFIG.is_management_call("claude", ["--version"]))
        self.assertTrue(AICONFIG.is_management_call("claude", ["mcp", "list"]))
        self.assertTrue(AICONFIG.is_management_call("codex", ["login"]))
        self.assertTrue(AICONFIG.is_management_call("codex", ["exec", "--help"]))
        self.assertFalse(AICONFIG.is_management_call("claude", []))
        self.assertFalse(AICONFIG.is_management_call("claude", ["-p", "oi"]))
        self.assertFalse(AICONFIG.is_management_call("codex", ["exec", "faça x"]))

    def _run(self, argv: list[str], *, healthy: bool, environment: dict | None = None):
        with (
            mock.patch.object(AICONFIG.sys, "argv", ["aiconfig", "run", *argv]),
            mock.patch.object(AICONFIG, "which", side_effect=lambda *names: names[0]),
            mock.patch.object(AICONFIG, "ensure_headroom_proxy", return_value=healthy) as ensure,
            mock.patch.object(AICONFIG, "write_headroom_mcp_config"),
            mock.patch.object(AICONFIG, "_run_foreground", return_value=0) as run,
            mock.patch.dict(os.environ, environment or {"AICONFIG_HEADROOM": ""}),
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            code = AICONFIG.main()
        return code, ensure, run, stderr.getvalue()

    def test_run_falls_back_and_says_so_when_proxy_is_down(self) -> None:
        code, ensure, run, stderr = self._run(["claude", "-p", "oi"], healthy=False)
        self.assertEqual(code, 0)
        ensure.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["claude", "-p", "oi"])
        self.assertNotIn("ANTHROPIC_BASE_URL", " ".join(run.call_args.args[0]))
        self.assertIn("abrindo claude direto", stderr)

    def test_run_uses_headroom_when_proxy_is_healthy(self) -> None:
        _code, _ensure, run, _stderr = self._run(["claude"], healthy=True)
        self.assertEqual(run.call_args.args[0][:3], ["headroom", "wrap", "claude"])

    def test_kill_switch_never_touches_the_proxy(self) -> None:
        _code, ensure, run, _stderr = self._run(
            ["codex"], healthy=True, environment={"AICONFIG_HEADROOM": "off"}
        )
        ensure.assert_not_called()
        self.assertEqual(run.call_args.args[0], ["codex"])

    def test_agent_help_is_passed_through_untouched(self) -> None:
        _code, ensure, run, _stderr = self._run(["claude", "--help"], healthy=True)
        ensure.assert_not_called()
        self.assertEqual(run.call_args.args[0], ["claude", "--help"])

    def test_session_env_disables_wrap_telemetry(self) -> None:
        with mock.patch.object(AICONFIG, "default_ca_bundle_path", return_value=Path("nao-existe.pem")):
            env, _notes = AICONFIG.headroom_session_env({})
        self.assertEqual(env["HEADROOM_BEACON"], "off")

    def test_start_lock_prevents_a_second_proxy_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / "proxy.starting"
            with (
                mock.patch.object(AICONFIG, "_headroom_start_lock", return_value=lock),
                mock.patch.object(AICONFIG, "start_headroom_proxy") as start,
            ):
                self.assertTrue(AICONFIG.start_headroom_proxy_once("headroom", "48731", {}))
                self.assertFalse(AICONFIG.start_headroom_proxy_once("headroom", "48731", {}))
        start.assert_called_once()

    def test_shell_block_is_ascii_and_defines_both_agents(self) -> None:
        for shell in ("powershell", "posix"):
            block = AICONFIG.shell_integration_block(shell, "C:/Py/python.exe", "C:/repo/tools/aiconfig.py")
            block.encode("ascii")
            self.assertIn("run claude", block)
            self.assertIn("run codex", block)
            self.assertIn("warm", block)
            self.assertTrue(block.startswith(AICONFIG.SHELL_BEGIN))

    def test_shell_profile_block_is_added_updated_and_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp) / "profile.ps1"
            profile.write_bytes(b"\xef\xbb\xbf# meu perfil\r\nSet-Alias g git\r\n")
            first = AICONFIG.shell_integration_block("powershell", "py1", "s")
            second = AICONFIG.shell_integration_block("powershell", "py2", "s")
            with contextlib.redirect_stdout(io.StringIO()):
                AICONFIG.update_shell_profile(profile, first, self._ctx())
                AICONFIG.update_shell_profile(profile, second, self._ctx())
                text = profile.read_bytes()
                self.assertTrue(text.startswith(b"\xef\xbb\xbf"))
                decoded = text.decode("utf-8-sig")
                self.assertIn("Set-Alias g git", decoded)
                self.assertEqual(decoded.count(AICONFIG.SHELL_BEGIN), 1)
                self.assertIn("py2", decoded)
                self.assertNotIn("py1", decoded)
                AICONFIG.update_shell_profile(profile, None, self._ctx())
            final = profile.read_bytes().decode("utf-8-sig")
        self.assertNotIn(AICONFIG.SHELL_BEGIN, final)
        self.assertIn("Set-Alias g git", final)

    def test_install_does_not_touch_shell_profiles_without_the_flag(self) -> None:
        source = (ROOT / "tools/aiconfig.py").read_text(encoding="utf-8")
        self.assertIn('getattr(args, "headroom_auto", False) or getattr(args, "no_headroom_auto", False)', source)

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


class PythonDistVersionTests(unittest.TestCase):
    def test_reads_version_from_owning_interpreter_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            scripts = Path(temp) / "Scripts"
            scripts.mkdir()
            (Path(temp) / "python.exe").write_text("", encoding="utf-8")
            exe = scripts / "semgrep.exe"
            exe.write_text("", encoding="utf-8")
            done = subprocess.CompletedProcess([], 0, stdout="1.178.0\n", stderr="")
            with mock.patch.object(AICONFIG.subprocess, "run", return_value=done) as run:
                self.assertEqual(AICONFIG.python_dist_version(str(exe), "semgrep"), "1.178.0")
        self.assertIn("importlib.metadata", run.call_args.args[0][2])

    def test_returns_none_without_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertIsNone(AICONFIG.python_dist_version(str(Path(temp) / "semgrep.exe"), "semgrep"))


class SharedSkillTests(unittest.TestCase):
    def test_shared_skills_are_neutral_across_agents(self) -> None:
        openspec = (ROOT / "claude/skills/openspec/SKILL.md").read_text(encoding="utf-8")
        for client in ("claude", "codex", "gemini"):
            self.assertIn(f"openspec init --tools {client}", openspec)
        self.assertNotIn("no Claude Code.", openspec)
        self.assertNotIn("impeccable", AICONFIG.SHARED_SKILLS)
