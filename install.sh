#!/usr/bin/env bash
# Instalador do ai-config. A lógica de merge vive em tools/aiconfig.py para ser
# exatamente a mesma no Linux, no macOS e no Windows.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

PY=""
for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
    echo "erro: Python 3.9+ é necessário para instalar (e para o status line)." >&2
    echo "      instale python3 e rode de novo." >&2
    exit 1
fi

CMD=install
ARGS=()
for a in "$@"; do
    case "$a" in
        --doctor|doctor) CMD=doctor ;;
        -h|--help)
            cat <<'USO'
uso: ./install.sh [--dry-run] [--keep-existing|--prefer-repo] [--yes]
     ./install.sh --doctor

  --dry-run        mostra o que faria, sem escrever nada
  --keep-existing  em conflito, mantém sempre o valor atual
  --prefer-repo    em conflito, usa sempre o valor do repo
  --yes            não pergunta nada (equivale a --keep-existing)
  --doctor         verifica rtk, headroom, aurum, node e os CLIs

Sem flags, cada conflito é perguntado. Nada é sobrescrito sem backup.

Variáveis: CLAUDE_CONFIG_DIR, CODEX_HOME, GEMINI_HOME, RTK_CONFIG_DIR,
           HEADROOM_PORT
USO
            exit 0 ;;
        *) ARGS+=("$a") ;;
    esac
done

exec "$PY" "$ROOT/tools/aiconfig.py" "$CMD" ${ARGS[@]+"${ARGS[@]}"}
