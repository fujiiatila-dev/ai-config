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
SKIP_TOOLS=false
ARGS=()
for a in "$@"; do
    case "$a" in
        --doctor|doctor) CMD=doctor ;;
        --skip-tools)    SKIP_TOOLS=true ;;
        -h|--help)
            cat <<'USO'
uso: ./install.sh [--dry-run] [--keep-existing|--prefer-repo] [--yes] [--skip-tools]
     ./install.sh --doctor

  --dry-run        mostra o que faria, sem escrever nada
  --keep-existing  em conflito, mantém sempre o valor atual
  --prefer-repo    em conflito, usa sempre o valor do repo
  --yes            não pergunta nada (equivale a --keep-existing)
  --skip-tools     pula a instalação de dependências (openspec, semgrep, etc.)
  --doctor         verifica python, node, rtk, headroom, aurum, openspec,
                   semgrep, gitleaks, trivy e os CLIs (claude, codex, git)

Sem flags: instala configuração + dependências externas num comando só.
Nada é sobrescrito sem backup.

Variáveis: CLAUDE_CONFIG_DIR, CODEX_HOME, GEMINI_HOME, RTK_CONFIG_DIR,
           HEADROOM_PORT
USO
            exit 0 ;;
        *) ARGS+=("$a") ;;
    esac
done

# ── 1. Instalar/fixar configuração ──────────────────────────────────────────
"$PY" "$ROOT/tools/aiconfig.py" "$CMD" ${ARGS[@]+"${ARGS[@]}"}
RC=$?

# ── 2. Instalar dependências externas ────────────────────────────────────────
# Só instala no modo normal (não --doctor)
if [ "$CMD" = install ] && [ "$SKIP_TOOLS" = false ]; then

    # --dry-run detectado nos args → pula ferramentas
    for a in "${ARGS[@]}"; do
        if [ "$a" = "--dry-run" ]; then
            echo ""
            echo "  (--dry-run: dependências não instaladas)"
            exit 0
        fi
    done

    echo ""
    echo "== Instalando dependências externas =="
    FAIL=false

    # openspec (npm)
    if command -v openspec &>/dev/null; then
        echo "  = openspec já instalado"
    else
        echo "  + openspec…"
        npm install -g @fission-ai/openspec@latest && \
            echo "    openspec instalado" || { echo "    aviso: falha ao instalar openspec"; FAIL=true; }
    fi

    # semgrep (pip)
    if command -v semgrep &>/dev/null; then
        echo "  = semgrep já instalado"
    else
        echo "  + semgrep…"
        pip install --user semgrep || pip install semgrep && \
            echo "    semgrep instalado" || { echo "    aviso: falha ao instalar semgrep"; FAIL=true; }
    fi

    # gitleaks
    if command -v gitleaks &>/dev/null; then
        echo "  = gitleaks já instalado"
    else
        echo "  + gitleaks…"
        if command -v winget &>/dev/null; then
            winget install gitleaks --accept-package-agreements --silent && \
                echo "    gitleaks instalado via winget" && hash -r || \
                { echo "    aviso: winget falhou"; FAIL=true; }
        elif command -v choco &>/dev/null; then
            choco install gitleaks -y --no-progress && \
                echo "    gitleaks instalado via choco" || \
                { echo "    aviso: choco falhou"; FAIL=true; }
        else
            echo "    aviso: sem winget ou choco. Instale manualmente:"
            echo "           https://github.com/gitleaks/gitleaks/releases"
            FAIL=true
        fi
    fi

    # trivy
    if command -v trivy &>/dev/null; then
        echo "  = trivy já instalado"
    else
        echo "  + trivy…"
        if command -v winget &>/dev/null; then
            winget install aquasecurity.trivy --accept-package-agreements --silent && \
                echo "    trivy instalado via winget" && hash -r || \
                { echo "    aviso: winget falhou"; FAIL=true; }
        elif command -v choco &>/dev/null; then
            choco install trivy -y --no-progress && \
                echo "    trivy instalado via choco" || \
                { echo "    aviso: choco falhou"; FAIL=true; }
        else
            echo "    aviso: sem winget ou choco. Instale manualmente:"
            echo "           https://github.com/aquasecurity/trivy/releases"
            FAIL=true
        fi
    fi

    echo ""
    if [ "$FAIL" = false ]; then
        echo "  Todas as dependências já estavam ou foram instaladas."
    else
        echo "  Algumas dependências podem não ter sido instaladas."
        echo "  Rode  ./install.sh --doctor  para conferir."
    fi

    echo "  Nota: ferramentas instaladas via winget/choco podem exigir"
    echo "        reiniciar o terminal para ficarem disponíveis no PATH."
fi

exit "$RC"
