#!/usr/bin/env python3
"""Garante que a deploy de usuário do Headroom esteja ativa.

O script é intencionalmente independente do instalador para poder ser copiado
para o diretório do Codex e chamado por um hook em qualquer plataforma.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess


DEFAULT_PROFILE = "init-user"
STATUS_TIMEOUT = 5
START_TIMEOUT = 20
ENSURE_TIMEOUT = 25


def _field(output: str, name: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(name)}:\s*(\S+)", output, re.IGNORECASE | re.MULTILINE)
    return match.group(1).lower() if match else None


def deployment_status(executable: str, profile: str) -> tuple[str | None, str | None, str]:
    """Return status, health and combined command output."""
    try:
        result = subprocess.run(
            [executable, "install", "status", "--profile", profile],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=STATUS_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, None, str(exc)
    output = (result.stdout or "") + (result.stderr or "")
    return _field(output, "Status"), _field(output, "Healthy"), output.strip()


def _healthy(status: str | None, health: str | None) -> bool:
    return status == "running" and health == "yes"


def ensure_deployment(executable: str, profile: str, dry_run: bool = False) -> bool:
    """Start a stopped/unhealthy deployment and verify it became healthy."""
    if dry_run:
        print(f"  [dry-run] verificaria a deploy Headroom '{profile}' e faria start se necessário")
        return True

    status, health, output = deployment_status(executable, profile)
    if _healthy(status, health):
        print(f"  Headroom deploy '{profile}': running / healthy")
        return True

    if status is None:
        print(f"  aviso: não foi possível obter o status da deploy '{profile}': {output}")
        return False

    if status not in {"running", "stopped"}:
        print(f"  aviso: status desconhecido da deploy '{profile}': {status}")
        return False

    print(f"  iniciando Headroom deploy '{profile}' (status={status}, healthy={health or '?'})...")
    try:
        started = subprocess.run(
            [executable, "install", "start", "--profile", profile],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=START_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"  aviso: falha ao iniciar a deploy '{profile}': {exc}")
        return False
    if started.returncode != 0:
        detail = ((started.stdout or "") + (started.stderr or "")).strip()
        print(f"  aviso: start da deploy '{profile}' terminou com código {started.returncode}: {detail}")
        return False

    status, health, output = deployment_status(executable, profile)
    if _healthy(status, health):
        print(f"  Headroom deploy '{profile}': running / healthy após recuperação")
        return True
    print(f"  aviso: deploy '{profile}' não ficou saudável após o start: {output}")
    return False


def run_ensure(executable: str, profile: str, marker: str) -> int:
    try:
        result = subprocess.run(
            [executable, "init", "hook", "ensure", "--profile", profile, "--marker", marker],
            timeout=ENSURE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"  aviso: falha ao garantir o hook Headroom: {exc}")
        return 1
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headroom", help="caminho do executável Headroom")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ensure", action="store_true", help="garante também o marker do hook")
    parser.add_argument("--marker", default="headroom-init-codex")
    args = parser.parse_args(argv)

    executable = args.headroom or shutil.which("headroom") or shutil.which("headroom.exe")
    if not executable:
        print("  aviso: Headroom não está disponível; deploy não verificada")
        return 0 if not args.ensure else 1

    if not ensure_deployment(executable, args.profile, args.dry_run):
        return 1
    if args.ensure and not args.dry_run:
        return run_ensure(executable, args.profile, args.marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
