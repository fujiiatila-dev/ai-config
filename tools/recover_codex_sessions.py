#!/usr/bin/env python3
"""Audit and repair Codex's local session index and project assignments.

The Codex desktop app can temporarily hide otherwise intact threads when its
project migration is interrupted.  This utility treats rollout JSONL files as
the durable source of truth, creates a recoverable backup, rebuilds the session
index, and assigns existing user-facing threads to the most specific project
root recorded in ``state_5.sqlite``.  It can also migrate an obsolete provider
stored in historical session metadata without changing conversation content.

Nothing is changed unless ``--apply`` is supplied.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import ntpath
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Rollout:
    thread_id: str
    session_id: str
    path: Path
    cwd: str | None
    source: str | None
    originator: str | None
    model_provider: str | None


def _is_windows_path(value: str) -> bool:
    return bool(re.match(r"^(?:\\\\\?\\)?[A-Za-z]:[\\/]", value)) or value.startswith("\\\\")


def _normalise_path(value: str) -> str:
    path_module = ntpath if _is_windows_path(value) else os.path
    normalised = path_module.normpath(value)
    if normalised.startswith("\\\\?\\UNC\\"):
        normalised = "\\\\" + normalised[8:]
    elif normalised.startswith("\\\\?\\"):
        normalised = normalised[4:]
    return path_module.normcase(normalised)


def _is_within(path: str, root: str) -> bool:
    try:
        path_module = ntpath if _is_windows_path(path) or _is_windows_path(root) else os.path
        return path_module.commonpath(
            (_normalise_path(path), _normalise_path(root))
        ) == _normalise_path(root)
    except (ValueError, OSError):
        return False


def _read_rollout(path: Path) -> Rollout | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if item.get("type") != "session_meta":
                    continue
                payload = item.get("payload") or {}
                thread_id = payload.get("id")
                if not isinstance(thread_id, str) or not thread_id:
                    return None
                return Rollout(
                    thread_id=thread_id,
                    session_id=path.stem,
                    path=path.resolve(),
                    cwd=payload.get("cwd") if isinstance(payload.get("cwd"), str) else None,
                    source=(
                        payload.get("source")
                        if isinstance(payload.get("source"), str)
                        else None
                    ),
                    originator=(
                        payload.get("originator")
                        if isinstance(payload.get("originator"), str)
                        else None
                    ),
                    model_provider=(
                        payload.get("model_provider")
                        if isinstance(payload.get("model_provider"), str)
                        else None
                    ),
                )
    except OSError:
        return None
    return None


def discover_rollouts(codex_home: Path) -> tuple[list[Rollout], list[Path]]:
    rollouts: list[Rollout] = []
    unreadable: list[Path] = []
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.is_dir():
        return rollouts, unreadable
    for path in sorted(sessions_dir.rglob("*.jsonl")):
        rollout = _read_rollout(path)
        if rollout is None:
            unreadable.append(path)
        else:
            rollouts.append(rollout)
    return rollouts, unreadable


def read_index(path: Path) -> tuple[dict[str, str], list[dict[str, Any]], int]:
    entries: dict[str, str] = {}
    supplemental: list[dict[str, Any]] = []
    invalid = 0
    if not path.exists():
        return entries, supplemental, invalid
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError
                if "session_id" in item and "path" in item:
                    session_id = item["session_id"]
                    rollout_path = item["path"]
                    if not isinstance(session_id, str) or not isinstance(rollout_path, str):
                        raise ValueError
                    entries[session_id] = rollout_path
                elif isinstance(item.get("id"), str):
                    # The app appends title/metadata updates to this JSONL too.
                    supplemental.append(item)
                else:
                    raise ValueError
            except (json.JSONDecodeError, TypeError, ValueError):
                invalid += 1
    return entries, supplemental, invalid


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def read_state(state_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    if not state_path.exists():
        return {}, []
    with contextlib.closing(_connect(state_path)) as connection:
        threads = {
            row["id"]: dict(row)
            for row in connection.execute(
                """
                SELECT id, cwd, project_id, source, originator, archived,
                       model_provider
                FROM threads
                """
            )
        }
        projects = [
            dict(row)
            for row in connection.execute(
                """
                SELECT p.id AS project_id, p.name AS project_name, pr.path AS root_path
                FROM projects AS p
                JOIN project_roots AS pr ON pr.project_id = p.id
                ORDER BY length(pr.path) DESC, pr.path
                """
            )
        ]
    return threads, projects


def project_for(cwd: str | None, projects: Iterable[dict[str, str]]) -> str | None:
    if not cwd:
        return None
    matches = [project for project in projects if _is_within(cwd, project["root_path"])]
    if not matches:
        return None
    return max(matches, key=lambda item: len(_normalise_path(item["root_path"])))["project_id"]


def read_project_migrations(global_state_path: Path) -> list[dict[str, Any]]:
    if not global_state_path.exists():
        return []
    state = json.loads(global_state_path.read_text(encoding="utf-8"))
    migrations: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if "threadAssignmentsMigrated" in value:
                pending = value.get("pendingThreadAssignmentIds")
                migrations.append(
                    {
                        "complete": value.get("threadAssignmentsMigrated") is True,
                        "pending_count": len(pending) if isinstance(pending, list) else 0,
                    }
                )
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(state)
    return migrations


def audit(codex_home: Path, required_ids: set[str]) -> dict[str, Any]:
    rollouts, unreadable = discover_rollouts(codex_home)
    index_path = codex_home / "session_index.jsonl"
    state_path = codex_home / "state_5.sqlite"
    index, supplemental_index_records, invalid_index_lines = read_index(index_path)
    threads, projects = read_state(state_path)
    migrations = read_project_migrations(codex_home / ".codex-global-state.json")

    rollout_by_thread = {item.thread_id: item for item in rollouts}
    rollout_by_session = {item.session_id: item for item in rollouts}
    rollout_session_ids = set(rollout_by_session)
    index_ids = set(index)
    thread_ids = set(threads)
    assignments = {
        thread_id: project_for(thread.get("cwd"), projects)
        for thread_id, thread in threads.items()
    }
    rollout_providers = Counter(item.model_provider or "<unset>" for item in rollouts)
    thread_providers = Counter(
        str(thread.get("model_provider") or "<unset>") for thread in threads.values()
    )

    required_status: dict[str, dict[str, bool]] = {}
    for required_id in sorted(required_ids):
        rollout = rollout_by_thread.get(required_id) or rollout_by_session.get(required_id)
        required_status[required_id] = {
            "rollout": rollout is not None,
            "index": bool(rollout and rollout.session_id in index_ids),
            "state": required_id in thread_ids,
        }

    return {
        "codex_home": str(codex_home.resolve()),
        "counts": {
            "rollouts": len(rollouts),
            "indexed": len(index_ids),
            "threads": len(thread_ids),
            "projects": len({item["project_id"] for item in projects}),
            "unreadable_rollouts": len(unreadable),
            "invalid_index_lines": invalid_index_lines,
            "project_migration_records": len(migrations),
        },
        "missing_from_index": sorted(rollout_session_ids - index_ids),
        "dangling_index_entries": sorted(index_ids - rollout_session_ids),
        "missing_from_state": sorted(set(rollout_by_thread) - thread_ids),
        "dangling_state_threads": sorted(thread_ids - set(rollout_by_thread)),
        "threads_without_project": sorted(
            thread_id
            for thread_id, thread in threads.items()
            if not thread.get("project_id") and assignments.get(thread_id)
        ),
        "threads_without_matching_root": sorted(
            thread_id
            for thread_id, thread in threads.items()
            if not thread.get("project_id") and not assignments.get(thread_id)
        ),
        "rollout_model_providers": dict(sorted(rollout_providers.items())),
        "thread_model_providers": dict(sorted(thread_providers.items())),
        "project_migration_incomplete": any(
            not item["complete"] or item["pending_count"] for item in migrations
        ),
        "unreadable_rollouts": [str(path) for path in unreadable],
        "required": required_status,
        "_rollouts": rollouts,
        "_threads": threads,
        "_projects": projects,
        "_assignments": assignments,
        "_supplemental_index_records": supplemental_index_records,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_backup(source: Path, target: Path) -> None:
    with contextlib.closing(_connect(source)) as src, contextlib.closing(
        sqlite3.connect(target)
    ) as dst:
        src.backup(dst)


def create_backup(
    codex_home: Path, rollout_backups: Iterable[Rollout] = ()
) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = codex_home / "backups" / f"session-recovery-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "created_at": dt.datetime.now().astimezone().isoformat(),
        "files": {},
    }

    sqlite_files = {"state_5.sqlite", "thread_history_1.sqlite"}
    for name in (
        "session_index.jsonl",
        ".codex-global-state.json",
        "state_5.sqlite",
        "thread_history_1.sqlite",
    ):
        source = codex_home / name
        if not source.exists():
            continue
        target = backup_dir / name
        if name in sqlite_files:
            _sqlite_backup(source, target)
        else:
            shutil.copy2(source, target)
        manifest["files"][name] = {"sha256": _sha256(target), "size": target.stat().st_size}

    for rollout in rollout_backups:
        try:
            relative = rollout.path.relative_to(codex_home)
        except ValueError as error:
            raise ValueError(f"Rollout is outside CODEX_HOME: {rollout.path}") from error
        target = backup_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rollout.path, target)
        manifest["files"][relative.as_posix()] = {
            "sha256": _sha256(target),
            "size": target.stat().st_size,
        }

    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return backup_dir


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def rebuild_index(
    codex_home: Path,
    rollouts: Iterable[Rollout],
    supplemental_records: Iterable[dict[str, Any]],
) -> None:
    lines = [
        json.dumps({"session_id": item.session_id, "path": str(item.path)}, ensure_ascii=False)
        for item in sorted(
            rollouts,
            key=lambda entry: (str(entry.path).casefold(), entry.session_id),
        )
    ]
    lines.extend(json.dumps(item, ensure_ascii=False) for item in supplemental_records)
    _atomic_write(codex_home / "session_index.jsonl", "\n".join(lines) + ("\n" if lines else ""))


def assign_threads(state_path: Path, assignments: dict[str, str | None]) -> int:
    changed = 0
    with contextlib.closing(_connect(state_path)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            for thread_id, project_id in assignments.items():
                if not project_id:
                    continue
                cursor = connection.execute(
                    "UPDATE threads SET project_id = ? WHERE id = ? AND project_id IS NULL",
                    (project_id, thread_id),
                )
                changed += cursor.rowcount
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return changed


def rewrite_rollout_providers(
    rollouts: Iterable[Rollout], old_provider: str, new_provider: str
) -> int:
    changed = 0
    for rollout in rollouts:
        if rollout.model_provider != old_provider:
            continue
        lines = rollout.path.read_text(encoding="utf-8").splitlines(keepends=True)
        replaced = False
        for index, line in enumerate(lines):
            item = json.loads(line)
            if item.get("type") != "session_meta":
                continue
            payload = item.get("payload")
            if not isinstance(payload, dict) or payload.get("model_provider") != old_provider:
                continue
            payload["model_provider"] = new_provider
            newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            lines[index] = (
                json.dumps(item, ensure_ascii=False, separators=(",", ":")) + newline
            )
            replaced = True
            break
        if not replaced:
            raise ValueError(
                f"Provider metadata disappeared while repairing {rollout.path}"
            )
        _atomic_write(rollout.path, "".join(lines))
        changed += 1
    return changed


def replace_thread_provider(
    state_path: Path, old_provider: str, new_provider: str
) -> int:
    with contextlib.closing(_connect(state_path)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = connection.execute(
                "UPDATE threads SET model_provider = ? WHERE model_provider = ?",
                (new_provider, old_provider),
            )
            connection.commit()
            return cursor.rowcount
        except Exception:
            connection.rollback()
            raise


def complete_project_migration(
    global_state_path: Path, assigned_thread_ids: Iterable[str]
) -> int:
    if not global_state_path.exists():
        return 0
    state = json.loads(global_state_path.read_text(encoding="utf-8"))
    assigned = set(assigned_thread_ids)
    changed = 0

    def visit(value: Any) -> None:
        nonlocal changed
        if isinstance(value, dict):
            pending = value.get("pendingThreadAssignmentIds")
            if isinstance(pending, list):
                remaining = [item for item in pending if item not in assigned]
                if remaining != pending:
                    value["pendingThreadAssignmentIds"] = remaining
                    changed += 1
                if "threadAssignmentsMigrated" in value:
                    complete = not remaining
                    if value["threadAssignmentsMigrated"] is not complete:
                        value["threadAssignmentsMigrated"] = complete
                        changed += 1
            elif (
                "threadAssignmentsMigrated" in value
                and value["threadAssignmentsMigrated"] is not True
            ):
                value["threadAssignmentsMigrated"] = True
                changed += 1
            projectless = value.get("projectless-thread-ids")
            if isinstance(projectless, list):
                remaining = [item for item in projectless if item not in assigned]
                if remaining != projectless:
                    value["projectless-thread-ids"] = remaining
                    changed += 1
            for child in list(value.values()):
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(state)
    if changed:
        _atomic_write(
            global_state_path,
            json.dumps(state, ensure_ascii=False, separators=(",", ":")),
        )
    return changed


def public_report(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if not key.startswith("_")}


def print_human(report: dict[str, Any]) -> None:
    counts = report["counts"]
    print(
        "Codex sessions: "
        f"{counts['rollouts']} rollouts, {counts['indexed']} indexed, "
        f"{counts['threads']} user-facing threads, {counts['projects']} projects"
    )
    print(f"Missing from index: {len(report['missing_from_index'])}")
    print(f"Threads awaiting project assignment: {len(report['threads_without_project'])}")
    print(f"Project migration incomplete: {report['project_migration_incomplete']}")
    print(f"Rollout providers: {report['rollout_model_providers']}")
    print(f"Thread providers: {report['thread_model_providers']}")
    print(
        "Internal/non-interactive rollouts outside state DB: "
        f"{len(report['missing_from_state'])}"
    )
    if report["required"]:
        for session_id, status in report["required"].items():
            print(
                f"Required {session_id}: rollout={status['rollout']} "
                f"index={status['index']} state={status['state']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex data directory (default: CODEX_HOME or ~/.codex)",
    )
    parser.add_argument("--apply", action="store_true", help="Back up and apply the repair")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    parser.add_argument(
        "--require-session",
        action="append",
        default=[],
        metavar="ID",
        help="Verify that a thread UUID or rollout session id is recoverable",
    )
    parser.add_argument(
        "--replace-provider",
        metavar="OLD=NEW",
        help="Replace an obsolete saved provider in rollout metadata and the thread DB",
    )
    return parser.parse_args()


def parse_provider_replacement(raw: str | None) -> tuple[str, str] | None:
    if raw is None:
        return None
    old, separator, new = raw.partition("=")
    if not separator or not old.strip() or not new.strip() or old == new:
        raise ValueError("--replace-provider must use distinct non-empty values: OLD=NEW")
    return old.strip(), new.strip()


def main() -> int:
    args = parse_args()
    codex_home = args.codex_home.expanduser().resolve()
    required_ids = set(args.require_session)
    try:
        provider_replacement = parse_provider_replacement(args.replace_provider)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    before = audit(codex_home, required_ids)

    missing_required = [
        session_id for session_id, status in before["required"].items() if not status["rollout"]
    ]
    if missing_required:
        print(
            f"Required session rollout not found: {', '.join(missing_required)}",
            file=sys.stderr,
        )
        return 2
    if args.apply and (
        before["counts"]["unreadable_rollouts"] or before["counts"]["invalid_index_lines"]
    ):
        print("Refusing to repair while rollout or index records are unreadable.", file=sys.stderr)
        return 3

    result: dict[str, Any] = {"before": public_report(before), "applied": False}
    if args.apply:
        affected_rollouts = (
            [
                rollout
                for rollout in before["_rollouts"]
                if rollout.model_provider == provider_replacement[0]
            ]
            if provider_replacement
            else []
        )
        backup_dir = create_backup(codex_home, affected_rollouts)
        rebuild_index(
            codex_home,
            before["_rollouts"],
            before["_supplemental_index_records"],
        )
        assigned = assign_threads(codex_home / "state_5.sqlite", before["_assignments"])
        assigned_thread_ids = {
            thread_id
            for thread_id, project_id in before["_assignments"].items()
            if project_id
        }
        migration_updates = complete_project_migration(
            codex_home / ".codex-global-state.json", assigned_thread_ids
        )
        rewritten_rollouts = 0
        rewritten_threads = 0
        if provider_replacement:
            old_provider, new_provider = provider_replacement
            rewritten_rollouts = rewrite_rollout_providers(
                before["_rollouts"], old_provider, new_provider
            )
            rewritten_threads = replace_thread_provider(
                codex_home / "state_5.sqlite", old_provider, new_provider
            )
        after = audit(codex_home, required_ids)
        result.update(
            {
                "applied": True,
                "backup_dir": str(backup_dir),
                "assigned_threads": assigned,
                "migration_fields_updated": migration_updates,
                "rewritten_rollouts": rewritten_rollouts,
                "rewritten_threads": rewritten_threads,
                "after": public_report(after),
            }
        )

        if (
            after["missing_from_index"]
            or after["threads_without_project"]
            or after["project_migration_incomplete"]
            or (
                provider_replacement
                and (
                    after["rollout_model_providers"].get(provider_replacement[0], 0)
                    or after["thread_model_providers"].get(provider_replacement[0], 0)
                )
            )
        ):
            print(
                "Repair verification failed; original files remain in the backup.",
                file=sys.stderr,
            )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 4

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(before)
        if args.apply:
            print(f"Backup: {result['backup_dir']}")
            print(f"Assigned threads: {result['assigned_threads']}")
            if provider_replacement:
                print(
                    "Replaced saved providers: "
                    f"{result['rewritten_rollouts']} rollouts, "
                    f"{result['rewritten_threads']} threads"
                )
            print("Session index rebuilt and project migration marked complete.")
            print("Restart the Codex app once so the sidebar reloads the repaired state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
