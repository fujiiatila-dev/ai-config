# Headroom

Camada local de compressão de contexto, complementar ao RTK: o RTK encolhe a
saída dos comandos antes de virar contexto, o Headroom comprime o contexto que
chega ao modelo.

## Instalação

```bash
uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"
headroom init --global --memory claude
headroom init --global --memory codex
headroom proxy --port "${HEADROOM_PORT:-48731}"
headroom doctor
```

Estes comandos são seus, não do `install.sh`. O instalador do ai-config **não**
roda `headroom init` nem sobe o proxy — ele só escreve a seção
`[model_providers.headroom]` no `~/.codex/config.toml` e reporta a presença do
binário em `./install.sh --doctor`. O roteamento em si é registrado pelo próprio
`headroom init`, nos arquivos locais de cada agente.

## Apontando os agentes para o proxy

```bash
export HEADROOM_PORT=48731
export ANTHROPIC_BASE_URL="http://127.0.0.1:${HEADROOM_PORT}"
export OPENAI_BASE_URL="http://127.0.0.1:${HEADROOM_PORT}/v1"
```

Veja `.env.example`. O proxy fica em `127.0.0.1` — não o exponha na rede.

## Limites

Os arquivos que o `headroom init` escreve podem conter permissões, caminhos e
preferências da máquina. Não os copie para este repositório.

Credenciais de provedor vêm do ambiente ou do login do próprio agente, nunca de
arquivo versionado.
