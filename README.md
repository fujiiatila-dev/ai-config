# ai-config

Configuração oficial das ferramentas de IA do ambiente de trabalho — instruções, skills, subagentes e integrações de redução de contexto.

## Instalação

```bash
git clone https://github.com/fujiiatila-dev/ai-config.git
cd ai-config
./install.sh
```

No Windows PowerShell, use `.\install.ps1`.

O instalador copia instruções, skills, sub-agents e hooks para o Claude Code, adapta as instruções para Codex e Gemini/Antigravity, cria backup das configurações existentes e registra Headroom no Claude Code e no Codex quando os CLIs estão disponíveis. Consulte `CONFIGURATION_MAP.md`.

## Dependências externas

RTK:

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
```

Headroom:

```bash
uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"
headroom init --global --memory claude
headroom init --global --memory codex
headroom proxy --port 48731
```

`48731` é uma porta padrão sugerida; altere-a se estiver ocupada. Consulte [HEADROOM.md](HEADROOM.md).

Nunca versione tokens, credenciais, histórico, permissões específicas de projetos ou URLs com chaves.
