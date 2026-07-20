#!/usr/bin/env python3
"""
Claude Code status line — mostra modelo, effort, uso de contexto, git e custo.
Recebe um JSON no stdin (fornecido pelo Claude Code) e imprime UMA linha.
Nunca deve crashar: tudo em try/except, com fallbacks.
"""
import json
import os
import subprocess
import sys

# ── cores ANSI (dim/reset + acentos) ────────────────────────────────
R = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
SEP = f"{DIM} · {R}"


def read_stdin_json():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def read_effort():
    """Lê o effortLevel do settings global (o stdin não expõe effort)."""
    for path in (
        os.path.expanduser("~/.claude/settings.json"),
        os.path.expanduser("~/.config/claude/settings.json"),
    ):
        try:
            with open(path) as f:
                s = json.load(f)
            v = s.get("effortLevel")
            if v:
                return str(v)
        except Exception:
            continue
    return None


def context_tokens(transcript_path):
    """Soma dos tokens que ocupam a janela de contexto, do último uso no
    transcript (input + cache_read + cache_creation)."""
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    try:
        last = None
        with open(transcript_path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or '"usage"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                usage = (obj.get("message") or {}).get("usage") or obj.get("usage")
                if isinstance(usage, dict) and (
                    "input_tokens" in usage or "cache_read_input_tokens" in usage
                ):
                    last = usage
        if not last:
            return None
        return (
            int(last.get("input_tokens", 0) or 0)
            + int(last.get("cache_read_input_tokens", 0) or 0)
            + int(last.get("cache_creation_input_tokens", 0) or 0)
        )
    except Exception:
        return None


def window_for(model_str):
    m = (model_str or "").lower()
    if "1m" in m:
        return 1_000_000
    return 200_000


def human(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}k"
    return str(n)


def git_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd or ".", "branch", "--show-current"],
            capture_output=True, text=True, timeout=1.5,
        )
        b = out.stdout.strip()
        return b or None
    except Exception:
        return None


def main():
    data = read_stdin_json()
    parts = []

    # modelo
    model = ((data.get("model") or {}).get("display_name")) or (
        (data.get("model") or {}).get("id")
    ) or "?"
    parts.append(f"{CYAN}{BOLD}{model}{R}")

    # effort
    eff = read_effort()
    if eff:
        parts.append(f"{DIM}effort{R} {MAGENTA}{eff}{R}")

    # contexto
    cwd = ((data.get("workspace") or {}).get("current_dir")) or data.get("cwd") or "."
    tok = context_tokens(data.get("transcript_path"))
    win = window_for(model + " " + str((data.get("model") or {}).get("id", "")))
    if tok is not None:
        pct = (tok / win) * 100 if win else 0
        col = GREEN if pct < 50 else (YELLOW if pct < 80 else RED)
        parts.append(f"{DIM}ctx{R} {col}{human(tok)}/{human(win)} ({pct:.0f}%){R}")
    else:
        # fallback: flag booleana quando o transcript não dá o número
        if data.get("exceeds_200k_tokens"):
            parts.append(f"{RED}ctx >200k{R}")

    # git
    br = git_branch(cwd)
    if br:
        parts.append(f"{DIM}⎇{R} {br}")

    # dir (basename) — só se for um caminho real
    base = os.path.basename(os.path.normpath(cwd)) if cwd else ""
    if base and base not in (".", os.sep):
        parts.append(f"{DIM}{base}{R}")

    # custo
    cost = (data.get("cost") or {}).get("total_cost_usd")
    if isinstance(cost, (int, float)):
        parts.append(f"{DIM}${cost:.2f}{R}")

    sys.stdout.write(SEP.join(parts))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # último recurso: nunca deixar o status line vazio/quebrado
        sys.stdout.write("Claude Code")
