#!/usr/bin/env bash
# Instala a configuração padrão do Claude Code em ~/.claude/
set -euo pipefail

SRC="$(cd "$(dirname "$0")/claude" && pwd)"
DEST="$HOME/.claude"

mkdir -p "$DEST"

if [ -f "$DEST/settings.json" ]; then
    cp "$DEST/settings.json" "$DEST/settings.json.bak-$(date +%Y%m%d%H%M%S)"
    echo "Backup do settings.json existente criado em $DEST"
fi

cp "$SRC/CLAUDE.md" "$SRC/RTK.md" "$SRC/settings.json" "$SRC/statusline.py" "$DEST/"
mkdir -p "$DEST/agents" "$DEST/skills"
cp -r "$SRC/agents/." "$DEST/agents/"
cp -r "$SRC/skills/." "$DEST/skills/"

echo "Configuração instalada em $DEST"
echo "Lembre-se das dependências externas: rtk e Node.js (ver README.md)."
echo "Reinicie o Claude Code para carregar tudo."
