#!/usr/bin/env bash
# Instalador do ai-config. A lógica de merge vive em tools/aiconfig.py para ser
# exatamente a mesma no Linux, no macOS e no Windows.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

PY=""
for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && \
       "$c" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        PY="$c"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "erro: Python 3.10+ é necessário para instalar (e para o status line)." >&2
    echo "      instale python3 e rode de novo." >&2
    exit 1
fi

CMD=install
ARGS=()
for a in "$@"; do
    case "$a" in
        --doctor|doctor) CMD=doctor ;;
        --validate|validate) CMD=validate ;;
        -h|--help)
            cat <<'USO'
uso: ./install.sh [--dry-run] [--keep-existing|--prefer-repo] [--yes] [--skip-tools]
     [--update-tools] [--harden-codex]
     ./install.sh --validate [--json]
     ./install.sh --doctor

  --dry-run        mostra o que faria, sem escrever nada
  --keep-existing  em conflito, mantém sempre o valor atual
  --prefer-repo    em conflito, usa sempre o valor do repo
  --yes            não pergunta nada (equivale a --keep-existing)
  --skip-tools     sincroniza só configurações, sem instalar ferramentas
  --update-tools   atualiza ferramentas gerenciadas para as referências do repo
  --harden-codex   aplica defaults seguros ao Codex e remove confiança ampla exata
  --validate       valida o checkout sem escrever nem instalar ferramentas
  --doctor         verifica Python, Node, agentes e ferramentas recomendadas

Sem flags: configura todos os agentes e prepara OpenSpec, Semgrep,
Gitleaks e Trivy. Nada é sobrescrito sem backup.

Variáveis: CLAUDE_CONFIG_DIR, CODEX_HOME, GEMINI_HOME, RTK_CONFIG_DIR,
           HEADROOM_PORT
USO
            exit 0 ;;
        *) ARGS+=("$a") ;;
    esac
done

exec "$PY" "$ROOT/tools/aiconfig.py" "$CMD" ${ARGS[@]+"${ARGS[@]}"}
