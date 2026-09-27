from __future__ import annotations

import contextlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "recover_codex_sessions.py"
SPEC = importlib.util.spec_from_file_location("session_recovery_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
RECOVERY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RECOVERY
SPEC.loader.exec_module(RECOVERY)


def write_rollout(
    path: Path,
    thread_id: str,
    cwd: str,
    source: str = "cli",
    model_provider: str = "headroom",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-09-22T00:00:00Z",
                "type": "session_meta",
                "payload": {
                    "id": thread_id,
                    "cwd": cwd,
                    "source": source,
                    "originator": "codex-tui",
                    "model_provider": model_provider,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def create_state(path: Path) -> None:
    with contextlib.closing(sqlite3.connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE project_roots (
                project_id TEXT,
                position INTEGER,
                path TEXT
            );
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                cwd TEXT,
                project_id TEXT,
                source TEXT,
                originator TEXT,
                archived INTEGER,
                model_provider TEXT
            );
            INSERT INTO projects VALUES ('project-user', 'user');
            INSERT INTO projects VALUES ('project-app', 'app');
            INSERT INTO project_roots VALUES ('project-user', 0, 'C:\\Users\\rayan');
            INSERT INTO project_roots VALUES (
                'project-app', 0, 'C:\\Users\\rayan\\work\\app'
            );
            """
        )
        connection.executemany(
            "INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    "thread-root",
                    r"\\?\C:\Users\rayan",
                    None,
                    "cli",
                    "codex-tui",
                    0,
                    "headroom",
                ),
                (
                    "thread-app",
                    r"\\?\C:\Users\rayan\work\app\src",
                    None,
                    "cli",
                    "codex-tui",
                    0,
                    "headroom",
                ),
            ),
        )
        connection.commit()


class SessionRecoveryTests(unittest.TestCase):
    def test_audit_and_repair_preserve_all_rollouts_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            codex_home = Path(temp) / ".codex"
            write_rollout(
                codex_home / "sessions" / "2026" / "09" / "rollout-one.jsonl",
                "thread-root",
                r"\\?\C:\Users\rayan",
            )
            write_rollout(
                codex_home / "sessions" / "2026" / "09" / "rollout-two.jsonl",
                "thread-app",
                r"\\?\C:\Users\rayan\work\app\src",
            )
            (codex_home / "session_index.jsonl").write_text(
                json.dumps(
                    {
                        "session_id": "rollout-one",
                        "path": str(
                            codex_home
                            / "sessions"
                            / "2026"
                            / "09"
                            / "rollout-one.jsonl"
                        ),
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "id": "thread-root",
                        "thread_name": "Important title",
                        "updated_at": "2026-09-22T00:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            create_state(codex_home / "state_5.sqlite")
            with contextlib.closing(
                sqlite3.connect(codex_home / "thread_history_1.sqlite")
            ) as history:
                history.execute("CREATE TABLE marker (value TEXT)")
                history.commit()
            global_state = codex_home / ".codex-global-state.json"
            global_state.write_text(
                json.dumps(
                    {
                        "migration": {
                            "threadAssignmentsMigrated": False,
                            "pendingThreadAssignmentIds": ["thread-root", "thread-app"],
                        },
                        "projectless-thread-ids": ["thread-root", "thread-app", "unknown"],
                        "unrelated": {"preserved": True},
                    }
                ),
                encoding="utf-8",
            )

            before = RECOVERY.audit(codex_home, {"thread-root"})
            self.assertEqual(before["missing_from_index"], ["rollout-two"])
            self.assertTrue(before["project_migration_incomplete"])
            self.assertEqual(before["rollout_model_providers"], {"headroom": 2})
            self.assertEqual(before["thread_model_providers"], {"headroom": 2})
            self.assertEqual(
                before["threads_without_project"], ["thread-app", "thread-root"]
            )
            self.assertEqual(
                before["_assignments"],
                {"thread-root": "project-user", "thread-app": "project-app"},
            )

            backup = RECOVERY.create_backup(codex_home, before["_rollouts"])
            RECOVERY.rebuild_index(
                codex_home,
                before["_rollouts"],
                before["_supplemental_index_records"],
            )
            self.assertEqual(
                RECOVERY.assign_threads(
                    codex_home / "state_5.sqlite", before["_assignments"]
                ),
                2,
            )
            self.assertGreater(
                RECOVERY.complete_project_migration(
                    global_state, before["_assignments"].keys()
                ),
                0,
            )
            self.assertEqual(
                RECOVERY.rewrite_rollout_providers(
                    before["_rollouts"], "headroom", "openai"
                ),
                2,
            )
            self.assertEqual(
                RECOVERY.replace_thread_provider(
                    codex_home / "state_5.sqlite", "headroom", "openai"
                ),
                2,
            )

            after = RECOVERY.audit(codex_home, {"thread-root"})
            self.assertEqual(after["missing_from_index"], [])
            self.assertEqual(after["threads_without_project"], [])
            self.assertFalse(after["project_migration_incomplete"])
            self.assertEqual(after["rollout_model_providers"], {"openai": 2})
            self.assertEqual(after["thread_model_providers"], {"openai": 2})
            self.assertTrue((backup / "manifest.json").is_file())
            self.assertTrue((backup / "state_5.sqlite").is_file())
            self.assertTrue(
                (backup / "sessions" / "2026" / "09" / "rollout-one.jsonl").is_file()
            )

            index_records = [
                json.loads(line)
                for line in (codex_home / "session_index.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                {item["session_id"] for item in index_records if "session_id" in item},
                {"rollout-one", "rollout-two"},
            )
            self.assertIn(
                "Important title",
                {item.get("thread_name") for item in index_records},
            )
            repaired_global_state = json.loads(global_state.read_text(encoding="utf-8"))
            self.assertTrue(
                repaired_global_state["migration"]["threadAssignmentsMigrated"]
            )
            self.assertEqual(
                repaired_global_state["migration"]["pendingThreadAssignmentIds"], []
            )
            self.assertEqual(
                repaired_global_state["projectless-thread-ids"], ["unknown"]
            )
            self.assertTrue(repaired_global_state["unrelated"]["preserved"])

            RECOVERY.rebuild_index(
                codex_home,
                after["_rollouts"],
                after["_supplemental_index_records"],
            )
            self.assertEqual(
                RECOVERY.assign_threads(
                    codex_home / "state_5.sqlite", after["_assignments"]
                ),
                0,
            )
            self.assertEqual(
                RECOVERY.complete_project_migration(
                    global_state, after["_assignments"].keys()
                ),
                0,
            )
            self.assertEqual(
                RECOVERY.rewrite_rollout_providers(
                    after["_rollouts"], "headroom", "openai"
                ),
                0,
            )
            self.assertEqual(
                RECOVERY.replace_thread_provider(
                    codex_home / "state_5.sqlite", "headroom", "openai"
                ),
                0,
            )
            repeated = RECOVERY.audit(codex_home, {"thread-root"})
            self.assertEqual(repeated["counts"]["indexed"], 2)

    def test_windows_extended_paths_match_on_every_host_os(self) -> None:
        projects = [
            {"project_id": "root", "root_path": r"C:\Users\rayan"},
            {"project_id": "nested", "root_path": r"C:\Users\rayan\repo"},
        ]

        self.assertEqual(
            RECOVERY.project_for(r"\\?\C:\Users\rayan\repo\src", projects),
            "nested",
        )
        self.assertIsNone(RECOVERY.project_for(r"C:\Users\other", projects))


if __name__ == "__main__":
    unittest.main()
