#!/usr/bin/env python3
"""
Instalador idempotente do ai-config.

Regras invioláveis:
  1. Nada é sobrescrito em silêncio. Toda escrita faz backup antes.
  2. Chave/arquivo que já existe e é igual  -> não faz nada.
  3. Chave/arquivo que não existe           -> adiciona.
  4. Chave/arquivo que existe com valor diferente -> pergunta qual manter.
  5. Listas (permissions, hooks) são unidas; nenhuma entrada é removida.

Uso:
  python3 tools/aiconfig.py install [--dry-run] [--keep-existing|--prefer-repo] [--yes]
    [--skip-tools] [--update-tools] [--harden-codex]
  python3 tools/aiconfig.py doctor
"""
from __future__ import annotations

import argparse
import ast
import copy
import datetime as _dt
import filecmp
import json
import os
import re
import shlex
import signal
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: validation stays dependency-free.
    tomllib = None

ROOT = Path(__file__).resolve().parent.parent
BEGIN = "<!-- ai-config:begin -->"
END = "<!-- ai-config:end -->"
DEFAULT_HEADROOM_PORT = 48731
VERSION_PROBE_TIMEOUT_SEC = 3.0
NPM_ROOT_TIMEOUT_SEC = 3.0

MANAGED_TOOL_VERSION_KEYS = {
    "openspec": "openspec",
    "semgrep": "semgrep",
    "gitleaks": "gitleaks",
    "trivy": "trivy",
}

VALIDATION_SCHEMA_VERSION = 1
VALIDATION_PLACEHOLDERS = frozenset(
    {"PYTHON", "NODE", "CLAUDE_HOME", "CODEX_HOME", "HEADROOM", "HEADROOM_PORT"}
)
VALIDATION_REQUIRED_SOURCES = (
    "claude/settings.json",
    "claude/CLAUDE.md",
    "claude/RTK.md",
    "claude/statusline.py",
    "claude/agents",
    "claude/skills",
    "shared/WORKFLOW.md",
    "adapters/codex/AGENTS.md",
    "adapters/codex/config.toml.example",
    "adapters/codex/hooks.json",
    "tools/headroom_healthcheck.py",
    "adapters/gemini/GEMINI.md",
    "adapters/rtk/filters.toml",
    "versions.json",
)
VALIDATION_PORTABLE_FILES = (
    ".env.example",
    "CONFIGURATION_MAP.md",
    "README.md",
    "shared/WORKFLOW.md",
    "claude/CLAUDE.md",
    "claude/RTK.md",
    "claude/settings.json",
    "adapters/codex/AGENTS.md",
    "adapters/codex/config.toml.example",
    "adapters/codex/hooks.json",
    "adapters/gemini/GEMINI.md",
    "adapters/rtk/filters.toml",
    "versions.json",
)
VALIDATION_SKIP_PARTS = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache"}
)

# ── saída ────────────────────────────────────────────────────────────────────
_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def add(msg: str) -> None:
    print(f"  {_c('32', '+')} {msg}")


def keep(msg: str) -> None:
    print(f"  {_c('2', '=')} {msg}")


def warn(msg: str) -> None:
    print(f"  {_c('33', '!')} {msg}")


def head(msg: str) -> None:
    print(f"\n{_c('1;36', msg)}")


class Ctx:
    """Estado global da execução."""

    def __init__(self, args):
        self.dry_run = args.dry_run
        self.policy = (
            "repo" if args.prefer_repo else "local" if args.keep_existing else None
        )
        self.assume_yes = args.yes
        self.interactive = sys.stdin.isatty() and not args.yes and self.policy is None
        stamp = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
        self.backup_dir = Path(
            os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")
        ) / "backups" / f"ai-config-{stamp}"
        self.changed = 0
        self.conflicts = 0

    # ── escolha em caso de conflito ──────────────────────────────────────────
    def choose(self, what: str, local_desc: str, repo_desc: str) -> str:
        """Retorna 'local' ou 'repo'."""
        self.conflicts += 1
        if self.policy:
            warn(f"conflito em {what} -> mantendo '{self.policy}' (--{self.policy})")
            return self.policy
        if not self.interactive:
            warn(f"conflito em {what} -> mantendo o atual (sessão não interativa)")
            return "local"
        print(f"\n  {_c('1;33', 'CONFLITO')} {what}")
        print(f"    [1] manter o atual : {local_desc}")
        print(f"    [2] usar o do repo : {repo_desc}")
        while True:
            try:
                r = input("    escolha [1]: ").strip() or "1"
            except EOFError:
                return "local"
            if r in ("1", "2"):
                return "local" if r == "1" else "repo"

    def choose3(self, what: str, options: list[tuple[str, str]], default: int = 1) -> str:
        self.conflicts += 1
        if self.policy == "local":
            return "local"
        if self.policy == "repo":
            return "repo"
        if not self.interactive:
            warn(f"conflito em {what} -> opção padrão (sessão não interativa)")
            return options[default - 1][0]
        print(f"\n  {_c('1;33', 'CONFLITO')} {what}")
        for i, (_, label) in enumerate(options, 1):
            print(f"    [{i}] {label}")
        while True:
            try:
                r = input(f"    escolha [{default}]: ").strip() or str(default)
            except EOFError:
                return options[default - 1][0]
            if r.isdigit() and 1 <= int(r) <= len(options):
                return options[int(r) - 1][0]

    # ── escrita segura ───────────────────────────────────────────────────────
    def backup(self, path: Path) -> None:
        if not path.exists() or self.dry_run:
            return
        rel = str(path).lstrip("/").replace(":", "_")
        dest = self.backup_dir / rel
        if dest.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    def write(self, path: Path, content: str) -> None:
        if self.dry_run:
            return
        self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.changed += 1

    def copy(self, src: Path, dest: Path) -> None:
        if self.dry_run:
            return
        self.backup(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        self.changed += 1


# ── merge de JSON ────────────────────────────────────────────────────────────
def _key(v) -> str:
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _sig(cmd: str) -> tuple:
    """Assinatura de um comando de hook, ignorando aspas e caminhos absolutos.

    `"/a/b/node" "/c/.claude/skills/x/hook.mjs"` e
    `/d/node /e/.claude/skills/x/hook.mjs` têm a mesma assinatura: são o mesmo
    hook instalado em máquinas diferentes, e não devem coexistir.
    """
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()
    return tuple(os.path.basename(t.replace("\\", "/").rstrip("/")) or t for t in toks)


def _cmds(entry: dict) -> frozenset:
    return frozenset(_sig(h.get("command", "")) for h in entry.get("hooks", []))


def merge_hook_event(local: list, repo: list, ctx: Ctx, path: str) -> list:
    """Une entradas de hook por `matcher`, e dentro delas por `command`.

    Uma união crua de listas duplicaria o hook: matcher "Bash" e matcher
    "Bash|PowerShell" com o mesmo comando fariam esse comando rodar duas vezes
    a cada Bash. Quando os comandos coincidem e só o matcher difere, isso é
    conflito e vira pergunta.
    """
    # Cópia profunda: `dict(e)` compartilharia a lista interna `hooks` com o
    # objeto original, e a mutação dela faria a comparação final concluir que
    # nada mudou — o arquivo nunca seria escrito.
    out = copy.deepcopy(local)
    by_matcher = {e.get("matcher"): e for e in out}

    def is_recovery(command: str) -> bool:
        return "headroom_healthcheck.py" in command.replace("\\", "/").lower()

    def is_headroom_ensure(command: str) -> bool:
        normalized = command.replace("\\", "/").lower()
        return "headroom" in normalized and "init hook ensure" in normalized

    for entry in repo:
        m = entry.get("matcher")
        if m in by_matcher:
            tgt = by_matcher[m]
            for h in entry.get("hooks", []):
                s = _sig(h.get("command", ""))
                gemeo = next(
                    (x for x in tgt.get("hooks", []) if _sig(x.get("command", "")) == s),
                    None,
                )
                if gemeo is None:
                    hooks = tgt.setdefault("hooks", [])
                    before_ensure = None
                    if is_recovery(h.get("command", "")):
                        before_ensure = next(
                            (
                                i
                                for i, item in enumerate(hooks)
                                if is_headroom_ensure(item.get("command", ""))
                            ),
                            None,
                        )
                    if before_ensure is None:
                        hooks.append(copy.deepcopy(h))
                    else:
                        hooks.insert(before_ensure, copy.deepcopy(h))
                    add(f"{path} :: {m} (+comando)")
                elif gemeo.get("command") != h.get("command"):
                    # Mesmo script, invocação diferente: escolher uma só.
                    pick = ctx.choose(
                        f"{path} :: {m} :: {'/'.join(s[-1:]) or 'hook'}",
                        gemeo["command"],
                        h["command"],
                    )
                    if pick == "repo":
                        gemeo.update(h)
                        add(f"{path} :: {m} (comando atualizado)")
            continue

        # Mesmos comandos, matcher diferente -> escolher um, nunca os dois.
        gemeo = next((e for e in out if _cmds(e) == _cmds(entry)), None)
        if gemeo is not None:
            pick = ctx.choose(
                f"{path} :: hook {sorted(_cmds(entry))} tem matcher divergente",
                f"matcher {gemeo.get('matcher')!r}",
                f"matcher {m!r}",
            )
            if pick == "repo":
                gemeo["matcher"] = m
                add(f"{path} :: matcher -> {m!r}")
            continue

        out.append(dict(entry))
        by_matcher[m] = out[-1]
        add(f"{path} :: {m} (novo)")
    return out


def merge_json(local, repo, ctx: Ctx, path: str = ""):
    if isinstance(local, dict) and isinstance(repo, dict):
        out = dict(local)
        for k, rv in repo.items():
            p = f"{path}.{k}" if path else k
            if k not in local:
                out[k] = rv
                add(f"{p}")
            else:
                out[k] = merge_json(local[k], rv, ctx, p)
        return out

    if isinstance(local, list) and isinstance(repo, list):
        # hooks.<Evento> tem estrutura própria
        if re.fullmatch(r"hooks\.[A-Za-z]+", path):
            return merge_hook_event(local, repo, ctx, path)
        out = list(local)
        seen = {_key(v) for v in out}
        novos = 0
        for v in repo:
            if _key(v) not in seen:
                out.append(v)
                seen.add(_key(v))
                novos += 1
        if novos:
            add(f"{path} (+{novos} entrada(s))")
        return out

    if _key(local) == _key(repo):
        return local

    pick = ctx.choose(path, _key(local), _key(repo))
    return local if pick == "local" else repo


def _subst(node, table: dict[str, str]):
    """Aplica {{PLACEHOLDER}} depois do parse, nunca no texto cru — caminhos do
    Windows têm barra invertida e quebrariam o escape do JSON."""
    if isinstance(node, dict):
        return {k: _subst(v, table) for k, v in node.items()}
    if isinstance(node, list):
        return [_subst(v, table) for v in node]
    if isinstance(node, str):
        for k, v in table.items():
            node = node.replace("{{" + k + "}}", v)
    return node


def install_json(src: Path, dest: Path, ctx: Ctx, subst=None) -> None:
    repo = json.loads(src.read_text(encoding="utf-8"))
    if subst:
        repo = _subst(repo, subst)

    if not dest.exists():
        ctx.write(dest, json.dumps(repo, indent=2, ensure_ascii=False) + "\n")
        add(f"{dest} (criado)")
        return

    try:
        local = json.loads(dest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        warn(f"{dest} não é JSON válido ({e}); nada foi alterado")
        return

    # Merge sobre uma cópia: `local` continua sendo a linha de base intacta da
    # comparação abaixo.
    merged = merge_json(copy.deepcopy(local), repo, ctx)
    if _key(merged) == _key(local):
        keep(f"{dest} (já em dia)")
        return
    ctx.write(dest, json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    add(f"{dest} (mesclado)")


# ── merge de markdown via bloco gerenciado ───────────────────────────────────
def install_markdown(src: Path, dest: Path, ctx: Ctx) -> None:
    body = src.read_text(encoding="utf-8").strip()
    block = f"{BEGIN}\n{body}\n{END}\n"

    if not dest.exists() or not dest.read_text(encoding="utf-8").strip():
        ctx.write(dest, block)
        add(f"{dest} (criado)")
        return

    cur = dest.read_text(encoding="utf-8")
    if BEGIN in cur and END in cur:
        novo = re.sub(
            re.escape(BEGIN) + r".*?" + re.escape(END),
            lambda _match: block.rstrip("\n"),
            cur,
            flags=re.S,
        )
        if novo == cur:
            keep(f"{dest} (já em dia)")
        else:
            ctx.write(dest, novo)
            add(f"{dest} (bloco ai-config atualizado)")
        return

    # Arquivo pré-existente sem marcação nossa: nunca sobrescreve sem perguntar.
    pick = ctx.choose3(
        f"{dest} já existe com conteúdo próprio",
        [
            ("append", "manter o seu conteúdo e anexar o bloco do ai-config"),
            ("local", "manter só o seu conteúdo (não instala nada)"),
            ("repo", "substituir pelo conteúdo do ai-config (backup é feito)"),
        ],
        default=1,
    )
    if pick == "local":
        keep(f"{dest} (mantido como está)")
    elif pick == "repo":
        ctx.write(dest, block)
        add(f"{dest} (substituído)")
    else:
        ctx.write(dest, cur.rstrip("\n") + "\n\n" + block)
        add(f"{dest} (bloco ai-config anexado)")


# ── merge de TOML por seção ──────────────────────────────────────────────────
def _toml_sections(text: str) -> dict[str, list[str]]:
    """Divide um TOML em {'': [linhas raiz], '[secao]': [linhas]}. Suficiente
    para o config.toml do Codex, que é raso; não é um parser completo."""
    out: dict[str, list[str]] = {"": []}
    cur = ""
    for line in text.splitlines():
        m = re.match(r"\s*(\[[^\]]+\])\s*$", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, [])
        else:
            out[cur].append(line)
    return out


def _toml_keys(lines: list[str]) -> dict[str, str]:
    out = {}
    for line in lines:
        m = re.match(r"\s*([A-Za-z0-9_.-]+)\s*=\s*(.+?)\s*$", line)
        if m and not line.lstrip().startswith("#"):
            out[m.group(1)] = m.group(2)
    return out


def install_toml(src: Path, dest: Path, ctx: Ctx, subst=None) -> None:
    raw = src.read_text(encoding="utf-8")
    if subst:
        for k, v in subst.items():
            raw = raw.replace("{{" + k + "}}", v)

    if not dest.exists():
        ctx.write(dest, raw)
        add(f"{dest} (criado)")
        return

    cur = dest.read_text(encoding="utf-8")
    repo_s, local_s = _toml_sections(raw), _toml_sections(cur)
    out = cur.rstrip("\n")
    mudou = False

    for sec, lines in repo_s.items():
        rkeys = _toml_keys(lines)
        if not rkeys:
            continue
        if sec not in local_s:
            out += "\n\n" + (sec + "\n" if sec else "") + "\n".join(
                l for l in lines if l.strip()
            )
            add(f"{dest} :: {sec or 'raiz'} (seção adicionada)")
            mudou = True
            continue
        lkeys = _toml_keys(local_s[sec])
        for k, rv in rkeys.items():
            if k not in lkeys:
                out = _toml_append_to_section(out, sec, f"{k} = {rv}")
                add(f"{dest} :: {sec or 'raiz'}.{k}")
                mudou = True
            elif lkeys[k] != rv:
                pick = ctx.choose(f"{dest} :: {sec or 'raiz'}.{k}", lkeys[k], rv)
                if pick == "repo":
                    out = re.sub(
                        rf"^(\s*{re.escape(k)}\s*=\s*).+$",
                        rf"\g<1>{rv}",
                        out,
                        count=1,
                        flags=re.M,
                    )
                    mudou = True

    if mudou:
        ctx.write(dest, out + "\n")
    else:
        keep(f"{dest} (já em dia)")


def _toml_append_to_section(text: str, sec: str, line: str) -> str:
    if not sec:
        return line + "\n" + text
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if l.strip() == sec:
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("["):
                j += 1
            lines.insert(j, line)
            return "\n".join(lines)
    return text + f"\n\n{sec}\n{line}"


# ── árvores (agents, skills) ─────────────────────────────────────────────────
def install_tree(src: Path, dest: Path, ctx: Ctx, rotulo: str) -> None:
    if not src.is_dir():
        return
    novos, iguais, difs = [], 0, []
    for f in sorted(src.rglob("*")):
        if f.is_dir():
            continue
        d = dest / f.relative_to(src)
        if not d.exists():
            novos.append((f, d))
        elif filecmp.cmp(f, d, shallow=False):
            iguais += 1
        else:
            difs.append((f, d))

    for f, d in novos:
        ctx.copy(f, d)
    if novos:
        add(f"{rotulo}: {len(novos)} arquivo(s) novo(s)")
    if iguais:
        keep(f"{rotulo}: {iguais} já em dia")

    if not difs:
        return
    pick = ctx.choose3(
        f"{rotulo}: {len(difs)} arquivo(s) diferem da versão do repo",
        [
            ("local", "manter as suas versões (nada é sobrescrito)"),
            ("repo", "atualizar para as versões do repo (backup é feito)"),
            ("list", "listar os arquivos e decidir um a um"),
        ],
        default=1,
    )
    if pick == "local":
        keep(f"{rotulo}: {len(difs)} mantido(s) como está")
        return
    if pick == "repo":
        for f, d in difs:
            ctx.copy(f, d)
        add(f"{rotulo}: {len(difs)} atualizado(s)")
        return
    for f, d in difs:
        if ctx.choose(str(d), "manter o seu", "usar o do repo") == "repo":
            ctx.copy(f, d)
            add(f"{d}")
        else:
            keep(f"{d}")


def install_file(src: Path, dest: Path, ctx: Ctx, rotulo: str) -> None:
    """Instala um arquivo único preservando a política de conflito."""
    if not dest.exists():
        ctx.copy(src, dest)
        add(f"{rotulo} (criado)")
    elif filecmp.cmp(src, dest, shallow=False):
        keep(f"{rotulo} (já em dia)")
    elif ctx.choose(str(dest), "manter o seu", "usar o do repo") == "repo":
        ctx.copy(src, dest)
        add(f"{rotulo} (atualizado)")
    else:
        keep(f"{rotulo} (mantido como está)")


# ── descoberta de binários ───────────────────────────────────────────────────
def persistent_windows_paths() -> list[str]:
    """Read PATH entries persisted after this process was started."""
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []

    locations = (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
    )
    entries: list[str] = []
    for hive, key_name in locations:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
        except OSError:
            continue
        entries.extend(os.path.expandvars(value).split(os.pathsep))
    return [entry for entry in entries if entry]


def which(*names: str) -> str | None:
    search_path = os.pathsep.join(
        [os.environ.get("PATH", ""), *persistent_windows_paths()]
    )
    for n in names:
        p = shutil.which(n, path=search_path)
        if p:
            return p
    return None


def _stop_version_probe(process: subprocess.Popen) -> None:
    """Stop a version probe and its descendants without leaving pipes open."""
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
    try:
        process.kill()
    except OSError:
        pass


def _probe_version(exe: str, args: tuple[str, ...], timeout: float) -> tuple[int, str, str]:
    """Run one version probe in an isolated process group."""
    options = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "errors": "replace",
    }
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        options["start_new_session"] = True

    process = subprocess.Popen([exe, *args], **options)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _stop_version_probe(process)
        try:
            process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        raise
    return process.returncode, stdout, stderr


def tool_version(exe: str) -> str | None:
    """Read a CLI version without allowing one broken executable to hang doctor."""
    deadline = time.monotonic() + VERSION_PROBE_TIMEOUT_SEC
    for args in (("--version",), ("version",)):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            # errors='replace': binários de terceiros (ex.: stub python3 da
            # Microsoft Store) podem emitir texto fora do utf-8 e o decode
            # falharia em thread, fora do alcance deste try/except.
            returncode, stdout, stderr = _probe_version(exe, args, remaining)
            if returncode != 0:
                continue
            out = (stdout + stderr).strip().splitlines()
            if out:
                m = re.search(r"\d+\.\d+(\.\d+)?", out[0])
                return m.group(0) if m else out[0][:40]
        except subprocess.TimeoutExpired:
            break
        except Exception:
            continue
    return None


def node_package_version(package_name: str) -> str | None:
    """Return an installed npm package version without downloading anything."""
    roots: list[Path] = [ROOT / "node_modules"]
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / "npm" / "node_modules")

    npm = which("npm")
    if npm:
        try:
            result = subprocess.run(
                [npm, "root", "-g"],
                capture_output=True,
                text=True,
                timeout=NPM_ROOT_TIMEOUT_SEC,
            )
            if result.returncode == 0 and result.stdout.strip():
                roots.append(Path(result.stdout.strip()))
        except Exception:
            pass

    relative = Path(*package_name.split("/")) / "package.json"
    for root in roots:
        metadata = root / relative
        try:
            version = json.loads(metadata.read_text(encoding="utf-8")).get("version")
            if isinstance(version, str) and version:
                return version
        except (OSError, ValueError):
            continue
    return None


def doctor_checks() -> list[tuple[str, str, tuple[str, ...], str, str | None]]:
    """Describe doctor checks with explicit versions.json keys."""
    return [
        ("python", "python", (sys.executable,), "obrigatório: instalador e statusline", None),
        ("node", "node", ("node",), "obrigatório para hooks e OpenSpec", None),
        ("rtk", "rtk", ("rtk",), "economia de tokens no shell", None),
        ("headroom", "headroom", ("headroom",), "compressão de contexto (proxy local)", None),
        ("aurum", "aurum", ("aurum",), "auditoria de qualidade (skill qualidade)", None),
        ("claude", "claude_code", ("claude",), "Claude Code CLI", None),
        ("codex", "codex_cli", ("codex",), "Codex CLI", None),
        ("git", "git", ("git",), "controle de versão", None),
        ("openspec", "openspec", ("openspec",), "especificação SDD (skill openspec)", None),
        ("semgrep", "semgrep", ("semgrep",), "SAST de segurança (skill security-audit)", None),
        ("gitleaks", "gitleaks", ("gitleaks",), "detecção de segredos (skill security-audit)", None),
        ("trivy", "trivy", ("trivy",), "SCA de dependências (skill security-audit)", None),
        (
            "codex-security",
            "codex_security",
            ("codex-security",),
            "auditoria profunda de segurança para Codex",
            "@openai/codex-security",
        ),
    ]


def _tool_reference(tool_name: str) -> str | None:
    key = MANAGED_TOOL_VERSION_KEYS.get(tool_name)
    if not key:
        return None
    try:
        versions = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))
        version = versions.get("tools", {}).get(key)
    except (OSError, ValueError, TypeError):
        return None
    return version if isinstance(version, str) and version else None


def tool_install_command(tool_name: str, upgrade: bool = False) -> list[str] | None:
    """Build an install/upgrade command using available package managers."""
    reference = _tool_reference(tool_name)

    if tool_name == "openspec":
        npm = which("npm")
        if not npm:
            return None
        package = f"@fission-ai/openspec@{reference}" if reference else "@fission-ai/openspec"
        return [
            npm,
            "install",
            "-g",
            "--no-audit",
            "--no-fund",
            "--fetch-retries=0",
            "--fetch-timeout=15000",
            package,
        ]

    if tool_name == "semgrep":
        package = f"semgrep=={reference}" if reference else "semgrep"
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--user",
            "--disable-pip-version-check",
            "--retries",
            "0",
            "--timeout",
            "15",
        ]
        if upgrade:
            command.append("--upgrade")
        command.append(package)
        return command

    packages = {
        "gitleaks": {
            "winget": "Gitleaks.Gitleaks",
            "choco": "gitleaks",
            "brew": "gitleaks",
        },
        "trivy": {
            "winget": "AquaSecurity.Trivy",
            "choco": "trivy",
            "brew": "trivy",
        },
    }
    package = packages.get(tool_name)
    if not package:
        return None

    winget = which("winget")
    if winget:
        command = [
            winget,
            "upgrade" if upgrade else "install",
            "--id",
            package["winget"],
            "--exact",
        ]
        if reference:
            command.extend(["--version", reference])
        command.extend(
            [
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--silent",
            ]
        )
        return command
    choco = which("choco")
    if choco:
        command = [choco, "upgrade" if upgrade else "install", package["choco"]]
        if reference:
            command.extend(["--version", reference])
        command.extend(["-y", "--no-progress"])
        return command
    brew = which("brew")
    if brew:
        return [brew, "upgrade" if upgrade else "install", package["brew"]]
    return None


def install_command_succeeded(command: list[str], returncode: int) -> bool:
    """Treat winget's 'already installed/no upgrade' result as success."""
    if returncode == 0:
        return True
    executable = Path(command[0]).name.lower()
    unsigned_code = returncode & 0xFFFFFFFF
    return executable in {"winget", "winget.exe"} and unsigned_code == 0x8A15002B


def install_recommended_tools(update: bool = False) -> bool:
    """Install missing tools, or explicitly update them when requested."""
    head("Ferramentas recomendadas")
    complete = True
    notes = {
        "openspec": "OpenSpec (especificação SDD)",
        "semgrep": "Semgrep (SAST)",
        "gitleaks": "Gitleaks (segredos)",
        "trivy": "Trivy (dependências)",
    }
    for tool_name, description in notes.items():
        installed = which(tool_name)
        if installed and not update:
            keep(f"{description} já instalado")
            continue

        if installed and update:
            command = tool_install_command(tool_name, upgrade=True)
        else:
            command = tool_install_command(tool_name)
        if not command:
            action = "atualizar" if installed and update else "instalar"
            warn(f"{description}: nenhum gerenciador compatível disponível para {action}")
            complete = False
            continue

        action = "atualizando" if installed and update else "instalando"
        add(f"{action} {description}...")
        try:
            result = subprocess.run(command, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as exc:
            warn(f"{description}: falha ao executar instalador ({exc})")
            complete = False
            continue
        if install_command_succeeded(command, result.returncode):
            add(f"{description} instalado")
        else:
            warn(f"{description}: instalador terminou com código {result.returncode}")
            complete = False

    if complete:
        print("  ferramentas recomendadas prontas.")
    else:
        print("  algumas ferramentas não ficaram disponíveis; rode --doctor para conferir.")
    print("  reinicie o terminal se um gerenciador acabou de atualizar o PATH.")
    return complete


# ── comandos ─────────────────────────────────────────────────────────────────
def ensure_headroom_deploy(ctx: Ctx, executable: str | None, profile: str = "init-user") -> bool:
    """Run the portable Headroom healthcheck after configuration sync."""
    if not executable:
        warn("Headroom não está disponível; deploy init-user não verificada")
        return False
    if ctx.dry_run:
        print(f"  [dry-run] verificaria a deploy Headroom '{profile}' e faria start se necessário")
        return True

    script = ROOT / "tools" / "headroom_healthcheck.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--headroom", executable, "--profile", profile],
            timeout=75,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        warn(f"healthcheck Headroom falhou: {exc}")
        return False
    if result.returncode != 0:
        warn(f"deploy Headroom '{profile}' não ficou ativa (código {result.returncode})")
        return False
    return True


def proxy_status(porta: str) -> str:
    """Probe real do proxy Headroom: 'ok', 'http <status>' ou 'fora'."""
    # Sem ProxyHandler: o opener padrão do urllib respeita proxy de ambiente e
    # do registro do Windows, que podem interceptar até chamadas de loopback.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{porta}/readyz", timeout=3) as r:
            return "ok" if r.status == 200 else f"http {r.status}"
    except Exception:
        return "fora"


def configured_headroom_port() -> str:
    """Return a validated port from the environment or the version catalog."""
    if os.environ.get("HEADROOM_PORT", "").strip():
        raw = os.environ["HEADROOM_PORT"].strip()
    else:
        try:
            versions = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))
            raw = str(versions.get("runtime", {}).get("headroom_port", DEFAULT_HEADROOM_PORT))
        except (OSError, ValueError, TypeError):
            raw = str(DEFAULT_HEADROOM_PORT)

    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError("HEADROOM_PORT deve ser um número inteiro entre 1 e 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("HEADROOM_PORT deve estar entre 1 e 65535")
    return str(port)


def _toml_unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        try:
            decoded = json.loads(value)
            if isinstance(decoded, str):
                return decoded
        except (json.JSONDecodeError, TypeError):
            pass
        return value[1:-1]
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1]
    return value


def _project_path_from_section(section: str) -> str | None:
    match = re.fullmatch(r"\[projects\.(?P<quote>['\"])(?P<path>.*)(?P=quote)\]", section.strip())
    if not match:
        return None
    quote = match.group("quote")
    return _toml_unquote(f"{quote}{match.group('path')}{quote}")


def _normalized_path(value: str) -> str:
    normalized = os.path.normpath(value.replace("\\", "/"))
    return os.path.normcase(normalized.rstrip("/"))


def codex_security_findings(config_path: Path) -> list[str]:
    """Inspect only portable Codex policy signals; never mutate the file."""
    if not config_path.exists():
        return []
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"não foi possível ler o config.toml ({exc})"]

    sections = _toml_sections(raw)
    root = _toml_keys(sections.get("", []))
    windows = _toml_keys(sections.get("[windows]", []))
    findings: list[str] = []

    sandbox = _toml_unquote(root.get("sandbox_mode", ""))
    if not sandbox:
        findings.append("sandbox_mode não está definido; fixe workspace-write ou read-only")
    elif sandbox not in {"workspace-write", "read-only"}:
        findings.append(f"sandbox_mode={sandbox!r} é mais permissivo que o baseline")

    approval = _toml_unquote(root.get("approval_policy", ""))
    if not approval:
        findings.append("approval_policy não está definida; use on-request")
    elif approval != "on-request":
        findings.append(f"approval_policy={approval!r}; o baseline usa on-request")

    reviewer = _toml_unquote(root.get("approvals_reviewer", ""))
    if reviewer and reviewer != "user":
        findings.append(f"approvals_reviewer={reviewer!r}; revise quem aprova ações")

    native_sandbox = _toml_unquote(windows.get("sandbox", ""))
    if native_sandbox == "elevated":
        findings.append("windows.sandbox=elevated concede sandbox nativa elevada")
    elif not native_sandbox:
        findings.append("windows.sandbox não está definido; o baseline usa unelevated")

    home = _normalized_path(str(Path.home()))
    for section, lines in sections.items():
        project_path = _project_path_from_section(section)
        if not project_path or _normalized_path(project_path) != home:
            continue
        project_keys = _toml_keys(lines)
        if _toml_unquote(project_keys.get("trust_level", "")) == "trusted":
            findings.append("a raiz do perfil do usuário está marcada como trusted")
            break
    return findings


def _set_toml_key(text: str, section: str, key: str, value: str) -> str:
    """Replace or append one simple TOML key while preserving other content."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    if section:
        try:
            section_start = next(i for i, line in enumerate(lines) if line.strip() == section)
        except StopIteration:
            base = text.rstrip("\r\n")
            separator = newline * 2 if base else ""
            return f"{base}{separator}{section}{newline}{key} = {value}{newline}"
        content_start = section_start + 1
        content_end = len(lines)
        for i in range(content_start, len(lines)):
            if lines[i].strip().startswith("["):
                content_end = i
                break
    else:
        content_start = 0
        content_end = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith("["):
                content_end = i
                break

    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*).*$")
    for i in range(content_start, content_end):
        if pattern.match(lines[i]):
            lines[i] = pattern.sub(rf"\g<1>{value}", lines[i], count=1)
            return newline.join(lines) + newline

    lines.insert(content_end, f"{key} = {value}")
    return newline.join(lines) + newline


def _remove_broad_home_trust(text: str) -> tuple[str, bool, bool]:
    """Remove only an exact home trust section containing trust_level alone."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    headers = [i for i, line in enumerate(lines) if line.strip().startswith("[")]
    home = _normalized_path(str(Path.home()))
    removed = False
    skipped = False

    for index in reversed(headers):
        section = lines[index].strip()
        project_path = _project_path_from_section(section)
        if not project_path or _normalized_path(project_path) != home:
            continue
        end = len(lines)
        for next_header in headers:
            if next_header > index:
                end = next_header
                break
        keys = _toml_keys(lines[index + 1 : end])
        meaningful = [line.strip() for line in lines[index + 1 : end] if line.strip() and not line.strip().startswith("#")]
        if set(keys) == {"trust_level"} and _toml_unquote(keys["trust_level"]) == "trusted" and len(meaningful) == 1:
            del lines[index:end]
            removed = True
        else:
            skipped = True

    if not removed:
        return text, False, skipped
    trailing = newline if text.endswith(("\n", "\r")) else ""
    return newline.join(lines) + trailing, True, skipped


def harden_codex_config(config_path: Path, ctx: Ctx) -> None:
    """Apply the explicit Codex baseline without rewriting unrelated TOML."""
    if not config_path.exists():
        warn(f"{config_path}: não existe; hardening não aplicado")
        return
    try:
        original = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        warn(f"{config_path}: não foi possível ler para hardening ({exc})")
        return

    updated = original
    for section, key, value in (
        ("", "sandbox_mode", '"workspace-write"'),
        ("", "approval_policy", '"on-request"'),
        ("", "approvals_reviewer", '"user"'),
        ("[windows]", "sandbox", '"unelevated"'),
    ):
        updated = _set_toml_key(updated, section, key, value)

    updated, removed, skipped = _remove_broad_home_trust(updated)
    if skipped:
        warn(f"{config_path}: confiança ampla preservada porque a seção contém outras chaves")
    if updated == original:
        keep(f"{config_path} (baseline já aplicado)")
        return

    ctx.write(config_path, updated)
    details = "baseline aplicado"
    if removed:
        details += "; confiança ampla da raiz removida"
    add(f"{config_path} ({details})")


class ValidationReport:
    """Structured, side-effect-free result for the repository preflight."""

    def __init__(self) -> None:
        self.errors: list[dict[str, str | None]] = []
        self.warnings: list[dict[str, str | None]] = []
        self.skipped: list[dict[str, str | None]] = []
        self.checks: list[dict[str, str]] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def _finding(
        self,
        severity: str,
        code: str,
        path: str | None,
        message: str,
        action: str,
    ) -> dict[str, str | None]:
        return {
            "severity": severity,
            "code": code,
            "path": path,
            "message": message,
            "action": action,
        }

    def error(self, code: str, path: str | None, message: str, action: str) -> None:
        self.errors.append(self._finding("error", code, path, message, action))

    def warning(self, code: str, path: str | None, message: str, action: str) -> None:
        self.warnings.append(self._finding("warning", code, path, message, action))

    def skip(self, code: str, path: str | None, message: str, action: str) -> None:
        self.skipped.append(self._finding("skipped", code, path, message, action))

    def check(self, check_id: str, before_errors: int) -> None:
        self.checks.append(
            {
                "id": check_id,
                "status": "failed" if len(self.errors) > before_errors else "passed",
            }
        )

    def as_dict(self) -> dict:
        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "status": "passed" if self.ok else "failed",
            "counts": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "skipped": len(self.skipped),
                "checks": len(self.checks),
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "skipped": self.skipped,
            "checks": self.checks,
        }

    def print_human(self) -> None:
        print("ai-config preflight")
        for check in self.checks:
            marker = "ok" if check["status"] == "passed" else "erro"
            print(f"  {marker:<5} {check['id']}")
        for label, findings in (
            ("Erros", self.errors),
            ("Avisos", self.warnings),
            ("Ignorados", self.skipped),
        ):
            if not findings:
                continue
            print(f"\n{label}")
            for finding in findings:
                location = f" [{finding['path']}]" if finding["path"] else ""
                print(f"  - {finding['code']}{location}: {finding['message']}")
                print(f"    ação: {finding['action']}")
        status = "passou" if self.ok else "falhou"
        print(
            f"\nPreflight {status}: {len(self.errors)} erro(s), "
            f"{len(self.warnings)} aviso(s), {len(self.skipped)} verificação(ões) ignorada(s)."
        )


def _validation_relative(root: Path, path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return candidate.name or None


def _validation_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or VALIDATION_SKIP_PARTS.intersection(path.parts):
            continue
        files.append(path)
    return sorted(files)


def _validation_read(path: Path, report: ValidationReport, root: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        report.error(
            "unreadable-source",
            _validation_relative(root, path),
            "não foi possível ler o arquivo de origem",
            "corrija permissões ou codificação e rode validate novamente",
        )
        return None


def _validation_check(report: ValidationReport, check_id: str, callback) -> None:
    before = len(report.errors)
    try:
        callback()
    except Exception as exc:  # Keep CI output structured even for an unexpected parser failure.
        report.error(
            "validator-error",
            None,
            f"a verificação {check_id} terminou com {type(exc).__name__}",
            "corrija o checkout ou abra uma issue com o identificador da verificação",
        )
    report.check(check_id, before)


def _validate_structure(root: Path, report: ValidationReport) -> None:
    map_path = root / "CONFIGURATION_MAP.md"
    map_text = _validation_read(map_path, report, root)
    if map_text is None:
        return

    for relative in VALIDATION_REQUIRED_SOURCES:
        source = root / relative
        if relative.endswith("/"):
            valid = source.is_dir()
        elif relative in {"claude/agents", "claude/skills"}:
            valid = source.is_dir()
        else:
            valid = source.is_file()
        if not valid:
            report.error(
                "missing-source",
                relative,
                "origem declarada pelo instalador não existe",
                "crie ou remova a referência antes de distribuir a configuração",
            )

    mapping_table = map_text.split("## Operação segura", 1)[0]
    references = {
        reference.rstrip("/")
        for reference in re.findall(r"^\|\s*`([^`]+)`\s*\|", mapping_table, flags=re.M)
    }
    if not references:
        report.error(
            "configuration-map-empty",
            "CONFIGURATION_MAP.md",
            "o mapa não contém fontes versionadas em formato reconhecível",
            "mantenha as fontes no primeiro campo das tabelas do mapa",
        )
        return

    for relative in VALIDATION_REQUIRED_SOURCES:
        if relative not in references:
            report.error(
                "configuration-map-drift",
                "CONFIGURATION_MAP.md",
                f"a fonte obrigatória {relative} não está documentada",
                "adicione a origem ao mapa ou remova-a do contrato do instalador",
            )

    for reference in sorted(references):
        source = root / reference
        if reference.startswith("~"):
            continue
        valid = source.is_file() or source.is_dir()
        if not valid:
            report.error(
                "map-source-missing",
                reference,
                "o mapa aponta para uma origem inexistente",
                "corrija o caminho relativo no mapa ou restaure o arquivo",
            )

    for relative in (
        "claude/CLAUDE.md",
        "adapters/codex/AGENTS.md",
        "adapters/gemini/GEMINI.md",
    ):
        path = root / relative
        text = _validation_read(path, report, root)
        if text is not None and "@WORKFLOW.md" not in text:
            report.error(
                "workflow-reference-missing",
                relative,
                "o adapter não referencia o WORKFLOW compartilhado",
                "use @WORKFLOW.md para manter uma única fonte de regras",
            )


def _validate_syntax(root: Path, report: ValidationReport) -> None:
    for path in _validation_files(root):
        relative = _validation_relative(root, path)
        if path.suffix.lower() == ".json":
            text = _validation_read(path, report, root)
            if text is None:
                continue
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                report.error(
                    "invalid-json",
                    relative,
                    f"JSON inválido na linha {exc.lineno}, coluna {exc.colno}",
                    "corrija a sintaxe JSON e rode validate novamente",
                )

        if path.suffix.lower() == ".py":
            text = _validation_read(path, report, root)
            if text is None:
                continue
            try:
                compile(text, relative or path.name, "exec")
            except SyntaxError as exc:
                report.error(
                    "invalid-python",
                    relative,
                    f"Python inválido na linha {exc.lineno or '?'}",
                    "corrija a sintaxe antes de instalar",
                )

    toml_paths = [
        path
        for path in _validation_files(root)
        if path.suffix.lower() == ".toml" or path.name.endswith(".toml.example")
    ]
    if not toml_paths:
        return
    if tomllib is None:
        report.skip(
            "toml-parser",
            None,
            "tomllib não está disponível neste Python",
            "use Python 3.11+ ou valide TOML no CI",
        )
        return
    for path in toml_paths:
        text = _validation_read(path, report, root)
        if text is None:
            continue
        try:
            tomllib.loads(text)
        except (tomllib.TOMLDecodeError, ValueError):
            report.error(
                "invalid-toml",
                _validation_relative(root, path),
                "TOML inválido",
                "corrija a sintaxe TOML antes de instalar",
            )


def _validate_placeholders(root: Path, report: ValidationReport) -> None:
    placeholder_re = re.compile(r"\{\{([^{}]+)\}\}")
    for relative in VALIDATION_PORTABLE_FILES:
        path = root / relative
        if not path.is_file():
            continue
        text = _validation_read(path, report, root)
        if text is None:
            continue
        for match in placeholder_re.finditer(text):
            token = match.group(1)
            if token not in VALIDATION_PLACEHOLDERS:
                report.error(
                    "unknown-placeholder",
                    relative,
                    "placeholder não possui resolução conhecida",
                    "use um placeholder documentado em CONFIGURATION_MAP.md",
                )
        if text.count("{{") != text.count("}}"):
            report.error(
                "malformed-placeholder",
                relative,
                "há marcadores de placeholder sem fechamento correspondente",
                "corrija os delimitadores {{...}}",
            )


def _validate_versions(root: Path, report: ValidationReport) -> None:
    path = root / "versions.json"
    text = _validation_read(path, report, root)
    if text is None:
        return
    try:
        versions = json.loads(text)
    except json.JSONDecodeError:
        return
    tools = versions.get("tools") if isinstance(versions, dict) else None
    if not isinstance(tools, dict):
        report.error(
            "versions-tools-missing",
            "versions.json",
            "o catálogo não possui o objeto tools",
            "mantenha as referências de ferramentas no catálogo",
        )
    else:
        doctor_keys = {item[1] for item in doctor_checks()}
        for key in sorted(tools):
            if key not in doctor_keys:
                report.error(
                    "doctor-coverage-missing",
                    "versions.json",
                    f"a ferramenta {key} não possui checagem correspondente no doctor",
                    "adicione a checagem ao doctor ou remova a referência obsoleta",
                )

    runtime = versions.get("runtime", {}) if isinstance(versions, dict) else {}
    port = runtime.get("headroom_port") if isinstance(runtime, dict) else None
    if not isinstance(port, int) or not 1 <= port <= 65535:
        report.error(
            "invalid-headroom-port",
            "versions.json",
            "runtime.headroom_port não é uma porta válida",
            "use um inteiro entre 1 e 65535",
        )
    if isinstance(runtime, dict) and runtime.get("headroom_scope") != "loopback-only":
        report.error(
            "headroom-scope",
            "versions.json",
            "o escopo do Headroom precisa ser loopback-only",
            "mantenha o proxy local e não o exponha na rede",
        )


def _validate_wrapper_parity(root: Path, report: ValidationReport) -> None:
    wrappers = {
        "install.sh": "--validate|validate",
        "install.ps1": "validate",
    }
    for relative, marker in wrappers.items():
        path = root / relative
        text = _validation_read(path, report, root)
        if text is None:
            continue
        if "--validate" not in text or "validate" not in text:
            report.error(
                "wrapper-command-missing",
                relative,
                "o wrapper não expõe o comando validate",
                "mantenha validate e --validate equivalentes nos dois shells",
            )
        if "aiconfig.py" not in text:
            report.error(
                "wrapper-engine-missing",
                relative,
                "o wrapper não encaminha para o motor comum",
                "reutilize tools/aiconfig.py para evitar drift entre shells",
            )


def _validation_json_values(value, key: str = ""):
    if isinstance(value, dict):
        for name, child in value.items():
            yield from _validation_json_values(child, str(name))
    elif isinstance(value, list):
        for child in value:
            yield from _validation_json_values(child, key)
    elif isinstance(value, str):
        yield key, value


def _is_loopback_url(value: str) -> bool:
    match = re.match(r"^https?://([^/\s\"']+)", value, flags=re.I)
    if not match:
        return True
    host = match.group(1).split("@")[-1].split(":", 1)[0].lower()
    return host in {"127.0.0.1", "localhost", "::1"} or "{{" in host


def _validate_portability_and_security(root: Path, report: ValidationReport) -> None:
    secret_patterns = (
        re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(
            r"(?im)^\s*(?:export\s+)?[A-Z0-9_]*(?:API[_-]?KEY|SECRET|PASSWORD|TOKEN)"
            r"\s*=\s*[\"']?(?!\{\{|\$)[A-Za-z0-9+/=_-]{20,}"
        ),
    )
    absolute_path_re = re.compile(r"(?<![A-Za-z])(?:[A-Za-z]:[\\/]|/(?:Users|home|root)/)")
    for path in _validation_files(root):
        relative = _validation_relative(root, path)
        if path.name in {".env", ".env.local", ".env.production"} or path.suffix in {".pem", ".key"}:
            report.error(
                "local-secret-file",
                relative,
                "arquivo de credencial local não pode ser distribuído",
                "remova o arquivo do Git e mantenha somente um exemplo sem valores",
            )
        text = _validation_read(path, report, root)
        if text is None:
            continue
        for pattern in secret_patterns:
            if pattern.search(text):
                report.error(
                    "credential-pattern",
                    relative,
                    "padrão de credencial detectado (valor omitido)",
                    "remova o segredo e use o mecanismo de credenciais local",
                )
                break

    for relative in VALIDATION_PORTABLE_FILES:
        path = root / relative
        if not path.is_file():
            continue
        text = _validation_read(path, report, root)
        if text is None:
            continue
        match = absolute_path_re.search(text)
        if match:
            report.error(
                "machine-absolute-path",
                relative,
                "caminho absoluto de uma máquina foi encontrado no template",
                "substitua-o por placeholder ou configuração local",
            )

    structured = (
        root / "claude/settings.json",
        root / "adapters/codex/hooks.json",
        root / "adapters/codex/config.toml.example",
        root / "adapters/rtk/filters.toml",
        root / ".env.example",
    )
    for path in structured:
        if not path.is_file():
            continue
        relative = _validation_relative(root, path)
        text = _validation_read(path, report, root)
        if text is None:
            continue
        values = []
        if path.suffix.lower() == ".json":
            try:
                values = list(_validation_json_values(json.loads(text)))
            except json.JSONDecodeError:
                continue
        elif path.suffix.lower() == ".toml" or path.name.endswith(".toml.example"):
            if tomllib is None:
                continue
            try:
                values = list(_validation_json_values(tomllib.loads(text)))
            except (tomllib.TOMLDecodeError, ValueError):
                continue
        else:
            for line in text.splitlines():
                if line.lstrip().startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values.append((key.strip(), value.strip().strip('"\'')))
        for key, value in values:
            if any(token in key.lower() for token in ("url", "endpoint", "host")) and not _is_loopback_url(value):
                report.error(
                    "non-loopback-endpoint",
                    relative,
                    "endpoint de configuração não aponta para loopback",
                    "use localhost/127.0.0.1 ou mova o endpoint para a configuração local",
                )
                break

    codex_template = root / "adapters/codex/config.toml.example"
    if codex_template.is_file():
        text = _validation_read(codex_template, report, root)
        if text is not None:
            sections = _toml_sections(text)
            for section, lines in sections.items():
                if _project_path_from_section(section):
                    report.error(
                        "project-state-in-template",
                        "adapters/codex/config.toml.example",
                        "template contém estado específico de projeto",
                        "mantenha permissões, sessões, memória e confiança no perfil local",
                    )
                    break
                keys = {key.lower() for key in _toml_keys(lines)}
                personal = keys.intersection({"history", "memory", "session", "credentials", "api_key", "token", "trust_level"})
                if personal:
                    report.error(
                        "personal-state-in-template",
                        "adapters/codex/config.toml.example",
                        "template contém estado pessoal ou credencial",
                        "remova a chave do template e mantenha-a no perfil local",
                    )
                    break


def _validate_workflow(root: Path, report: ValidationReport) -> None:
    path = root / "shared/WORKFLOW.md"
    text = _validation_read(path, report, root)
    if text is None:
        return
    required = ("validate", "dry-run", "apply", "doctor", "security", "quality", "commit")
    missing = [term for term in required if term not in text]
    if missing:
        report.error(
            "workflow-sequence-missing",
            "shared/WORKFLOW.md",
            "o fluxo compartilhado não documenta todas as etapas obrigatórias",
            "documente validate, dry-run, apply, doctor, security, quality e commit",
        )


def _bash_for_validation() -> str | None:
    if os.name != "nt":
        return which("bash")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = (
        Path(program_files) / "Git" / "bin" / "bash.exe",
        Path(program_files) / "Git" / "usr" / "bin" / "bash.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _validate_optional_checks(root: Path, report: ValidationReport) -> None:
    executable = _bash_for_validation()
    if not executable:
        report.skip(
            "bash-syntax",
            "install.sh",
            "Bash não está disponível neste ambiente",
            "instale Bash ou deixe o CI Unix executar esta verificação",
        )
        return
    path = root / "install.sh"
    if not path.is_file():
        return
    try:
        result = subprocess.run(
            [executable, "-n", str(path)],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        report.skip(
            "bash-syntax",
            "install.sh",
            "Bash não pôde ser executado neste ambiente",
            "repita a verificação em um runner Unix",
        )
        return
    if result.returncode != 0:
        report.error(
            "invalid-bash",
            "install.sh",
            "wrapper Bash inválido",
            "corrija a sintaxe do wrapper antes de instalar",
        )


def validate_repository(root: Path = ROOT) -> ValidationReport:
    """Validate repository contracts without writing files or invoking installers."""
    report = ValidationReport()
    _validation_check(report, "structure", lambda: _validate_structure(root, report))
    _validation_check(report, "syntax", lambda: _validate_syntax(root, report))
    _validation_check(report, "placeholders", lambda: _validate_placeholders(root, report))
    _validation_check(report, "versions", lambda: _validate_versions(root, report))
    _validation_check(report, "wrappers", lambda: _validate_wrapper_parity(root, report))
    _validation_check(report, "portability-security", lambda: _validate_portability_and_security(root, report))
    _validation_check(report, "workflow", lambda: _validate_workflow(root, report))
    _validation_check(report, "optional-tools", lambda: _validate_optional_checks(root, report))
    return report


def cmd_validate(args) -> int:
    report = validate_repository()
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        report.print_human()
    return 0 if report.ok else 1


def cmd_doctor(_args) -> int:
    versions = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))
    esperado = versions.get("tools", {})
    head("Diagnóstico do ambiente")
    faltando = []
    for nome, chave, cands, nota, npm_package in doctor_checks():
        exe = which(*cands)
        package_version = node_package_version(npm_package) if npm_package and not exe else None
        if not exe and not package_version:
            print(f"  {_c('33', 'ausente')}  {nome:<10} — {nota}")
            faltando.append(nome)
            continue
        v = tool_version(exe) if exe else package_version
        v = v or "?"
        ref = esperado.get(chave)
        marca = ""
        if ref and v != "?" and v != ref:
            marca = _c("2", f" (referência do repo: {ref})")
        print(f"  {_c('32', 'ok')}       {nome:<10} {v}{marca}")

    try:
        porta = configured_headroom_port()
    except ValueError as exc:
        porta = None
        print(f"\n  {_c('33', '!')}       HEADROOM_PORT inválida — {exc}")

    if porta:
        print(f"\n  HEADROOM_PORT = {porta}")

        # Probe real da porta: um proxy configurado mas fora do ar derruba o Codex
        # com erro críptico de stream. Aqui o motivo aparece na hora.
        st = proxy_status(porta)
        if st == "ok":
            print(
                f"  {_c('32', 'ok')}       headroom-proxy  respondendo em "
                f"http://127.0.0.1:{porta}/readyz"
            )
        else:
            if which("headroom"):
                acao = f"rode: headroom proxy --port {porta}  (ou o atalho de inicialização)"
            else:
                acao = f"instale o headroom (veja README.md) e rode: headroom proxy --port {porta}"
            if st.startswith("http"):
                print(
                    f"  {_c('33', '!')}       headroom-proxy  respondeu HTTP {st.split()[-1]} "
                    f"em http://127.0.0.1:{porta}/readyz (não saudável)"
                )
            else:
                print(
                    f"  {_c('33', '!')}       headroom-proxy  NÃO está respondendo em "
                    f"http://127.0.0.1:{porta}/readyz"
                )
            print(f"        {acao}")

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    codex_config = codex_home / "config.toml"
    findings = codex_security_findings(codex_config)
    if codex_config.exists():
        print("\n  Baseline Codex")
        if findings:
            for finding in findings:
                print(f"  {_c('33', '!')}       codex       {finding}")
            print("        use --harden-codex para aplicar defaults com backup")
        else:
            print("  ok       codex       baseline de sandbox/aprovação detectado")

    if faltando:
        print(
            f"\n  {_c('33', 'Ausentes:')} {', '.join(faltando)} — rode o instalador "
            "padrão e reinicie o terminal; veja README.md para alternativas."
        )
    return 0


def cmd_install(args) -> int:
    preflight = validate_repository()
    if not preflight.ok:
        print("A instalação foi interrompida pelo preflight do repositório.")
        preflight.print_human()
        return 2
    ctx = Ctx(args)
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    gemini_home = Path(os.environ.get("GEMINI_HOME", Path.home() / ".gemini"))
    rtk_home = Path(os.environ.get("RTK_CONFIG_DIR", Path.home() / ".config" / "rtk"))
    try:
        porta = configured_headroom_port()
    except ValueError as exc:
        warn(str(exc))
        return 2

    py = which("python3", "python") or sys.executable
    node = which("node") or "node"
    headroom = which("headroom", "headroom.exe") or "headroom"

    if ctx.dry_run:
        print(_c("1;33", "\n== simulação (--dry-run): nada será escrito =="))
    print(f"\n  destino Claude : {claude_home}")
    print(f"  destino Codex  : {codex_home}")
    print(f"  destino Gemini : {gemini_home}")
    if not ctx.dry_run:
        print(f"  backups em     : {ctx.backup_dir}")
    if not ctx.interactive and ctx.policy is None and not ctx.dry_run:
        warn("sessão não interativa: em caso de conflito, o valor atual é mantido")

    # Barra normal em todo lugar: Node, Python e o shell do Windows aceitam,
    # e assim o mesmo valor serve para JSON, TOML e linha de comando.
    def fwd(p) -> str:
        return str(p).replace("\\", "/")

    subst = {
        "PYTHON": fwd(py),
        "NODE": fwd(node),
        "CLAUDE_HOME": fwd(claude_home),
        "CODEX_HOME": fwd(codex_home),
        "HEADROOM": fwd(headroom),
        "HEADROOM_PORT": porta,
    }

    head("Claude Code")
    install_json(ROOT / "claude/settings.json", claude_home / "settings.json", ctx, subst)
    install_markdown(ROOT / "claude/CLAUDE.md", claude_home / "CLAUDE.md", ctx)
    install_markdown(ROOT / "claude/RTK.md", claude_home / "RTK.md", ctx)
    install_markdown(ROOT / "shared/WORKFLOW.md", claude_home / "WORKFLOW.md", ctx)
    install_tree(ROOT / "claude/agents", claude_home / "agents", ctx, "agents")
    install_tree(ROOT / "claude/skills", claude_home / "skills", ctx, "skills")

    sl = ROOT / "claude/statusline.py"
    dst_sl = claude_home / "statusline.py"
    if not dst_sl.exists():
        ctx.copy(sl, dst_sl)
        add(f"{dst_sl} (criado)")
    elif filecmp.cmp(sl, dst_sl, shallow=False):
        keep(f"{dst_sl} (já em dia)")
    elif ctx.choose(str(dst_sl), "manter o seu", "usar o do repo") == "repo":
        ctx.copy(sl, dst_sl)
        add(f"{dst_sl} (atualizado)")
    if not ctx.dry_run and dst_sl.exists():
        dst_sl.chmod(0o755)

    head("Codex")
    install_markdown(ROOT / "adapters/codex/AGENTS.md", codex_home / "AGENTS.md", ctx)
    install_markdown(ROOT / "shared/WORKFLOW.md", codex_home / "WORKFLOW.md", ctx)
    install_toml(
        ROOT / "adapters/codex/config.toml.example", codex_home / "config.toml", ctx, subst
    )
    if getattr(args, "harden_codex", False):
        harden_codex_config(codex_home / "config.toml", ctx)
    install_file(
        ROOT / "tools/headroom_healthcheck.py",
        codex_home / "headroom_healthcheck.py",
        ctx,
        "Codex healthcheck Headroom",
    )
    install_json(ROOT / "adapters/codex/hooks.json", codex_home / "hooks.json", ctx, subst)

    head("Gemini / Antigravity")
    install_markdown(ROOT / "adapters/gemini/GEMINI.md", gemini_home / "GEMINI.md", ctx)
    install_markdown(ROOT / "shared/WORKFLOW.md", gemini_home / "WORKFLOW.md", ctx)

    head("RTK")
    install_toml(ROOT / "adapters/rtk/filters.toml", rtk_home / "filters.toml", ctx)

    head("Headroom")
    ensure_headroom_deploy(ctx, which("headroom", "headroom.exe"))

    head("Resumo")
    if ctx.dry_run:
        print("  simulação concluída — nada foi escrito.")
    else:
        print(f"  {ctx.changed} arquivo(s) escrito(s), {ctx.conflicts} conflito(s).")
        if ctx.backup_dir.exists():
            print(f"  backup do estado anterior: {ctx.backup_dir}")
        print("  reinicie o Claude Code / Codex para carregar as mudanças.")

    if ctx.dry_run:
        print("  (--dry-run: ferramentas não instaladas)")
    elif args.skip_tools:
        print("  (--skip-tools: ferramentas não instaladas)")
    else:
        if getattr(args, "update_tools", False):
            install_recommended_tools(update=True)
        else:
            install_recommended_tools()

    print("  rode  ./install.sh --doctor  para conferir as ferramentas externas.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="aiconfig", description=__doc__)
    sub = p.add_subparsers(dest="cmd")

    i = sub.add_parser("install", help="instala/atualiza as configurações")
    i.add_argument("--dry-run", action="store_true", help="mostra o que faria")
    i.add_argument("--yes", action="store_true", help="não pergunta nada")
    i.add_argument(
        "--skip-tools",
        action="store_true",
        help="sincroniza apenas configurações, sem instalar ferramentas",
    )
    i.add_argument(
        "--update-tools",
        action="store_true",
        help="atualiza ferramentas gerenciadas para as referências do repo",
    )
    i.add_argument(
        "--harden-codex",
        action="store_true",
        help="aplica defaults seguros ao Codex e remove confiança ampla exata",
    )
    g = i.add_mutually_exclusive_group()
    g.add_argument("--keep-existing", action="store_true", help="conflito: mantém o local")
    g.add_argument("--prefer-repo", action="store_true", help="conflito: usa o do repo")
    i.set_defaults(func=cmd_install)

    v = sub.add_parser("validate", help="valida contratos do repositório sem escrever")
    v.add_argument("--json", action="store_true", help="emite um relatório JSON para CI")
    v.set_defaults(func=cmd_validate)

    d = sub.add_parser("doctor", help="verifica as ferramentas externas")
    d.set_defaults(func=cmd_doctor)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
