# Headroom

Headroom é a camada local de compressão de contexto usada junto com o RTK.

```bash
uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"
headroom init --global --memory claude
headroom init --global --memory codex
headroom proxy --port "${HEADROOM_PORT:-48731}"
headroom doctor
```

O instalador também configura o MCP de recuperação e o roteamento dos agentes quando Claude Code ou Codex estão instalados.

O Headroom registra o roteamento nos arquivos locais de cada agente. Esses arquivos podem conter permissões, caminhos e preferências específicas da máquina e não devem ser copiados para o repositório.

O proxy deve permanecer local em `127.0.0.1`. Credenciais de provedores devem ser fornecidas pelo ambiente ou pelo próprio agente, nunca por arquivos versionados.
