#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/claude"
DEST="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
HEADROOM_PORT="${HEADROOM_PORT:-48731}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
GEMINI_HOME="${GEMINI_HOME:-$HOME/.gemini}"

mkdir -p "$DEST" "$DEST/agents" "$DEST/skills"
if [ -f "$DEST/settings.json" ]; then
    cp "$DEST/settings.json" "$DEST/settings.json.bak-$(date +%Y%m%d%H%M%S)"
fi
cp "$SRC/CLAUDE.md" "$SRC/RTK.md" "$SRC/settings.json" "$SRC/statusline.py" "$DEST/"
cp -r "$SRC/agents/." "$DEST/agents/"
cp -r "$SRC/skills/." "$DEST/skills/"
mkdir -p "$CODEX_HOME" "$GEMINI_HOME"
cp "$ROOT/adapters/codex/AGENTS.md" "$CODEX_HOME/AGENTS.md"
cp "$ROOT/adapters/gemini/GEMINI.md" "$GEMINI_HOME/GEMINI.md"

if command -v rtk >/dev/null 2>&1; then echo "RTK encontrado: $(rtk --version)"; else echo "RTK não encontrado; instale-o pelo instalador oficial."; fi
if command -v headroom >/dev/null 2>&1; then
    headroom init --global --memory claude || true
    if command -v codex >/dev/null 2>&1; then headroom init --global --memory codex || true; fi
    echo "Inicie o proxy Headroom com: headroom proxy --port $HEADROOM_PORT"
else echo "Headroom não encontrado; instale-o conforme README.md."; fi
echo "Configuração instalada em $DEST. Reinicie os agentes."
