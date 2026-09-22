# Headroom (opcional e sob demanda)

O Headroom comprime o contexto que chega ao modelo por meio de um proxy local.
Ele é complementar ao RTK, mas também entra no caminho de rede entre o agente e
o provedor. Por isso o ai-config mantém Claude e Codex conectados diretamente
aos provedores por padrão.

O instalador não executa `headroom init`, não cria hooks, não inicia deployments
e não grava `ANTHROPIC_BASE_URL` ou `OPENAI_BASE_URL` globalmente. Se o proxy
parar ou degradar, uma nova sessão normal de `claude` ou `codex` continua
funcionando sem ele.

## Instalar e atualizar

```bash
uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"
headroom update --check
headroom update
```

Se o updater informar que `uv` não está no `PATH`, use o módulo já instalado:
`python -m uv tool upgrade headroom-ai`.

A versão de referência fica em `versions.json`. Atualizar é recomendado, mas
não substitui as proteções abaixo: falhas do executor Kompress/ONNX também foram
observadas em versões posteriores à 0.34.

## Claude: sessão opt-in

Use o wrapper, que limita `ANTHROPIC_BASE_URL` ao processo iniciado:

```bash
HEADROOM_DISABLE_KOMPRESS=1 \
HEADROOM_DISABLE_KOMPRESS_FALLBACK=1 \
HEADROOM_COMPRESSION_MAX_WORKERS=4 \
headroom wrap claude --port "${HEADROOM_PORT:-48731}" --tool-search true
```

No PowerShell:

```powershell
$headroomPort = if ($env:HEADROOM_PORT) { $env:HEADROOM_PORT } else { '48731' }
$env:HEADROOM_DISABLE_KOMPRESS = '1'
$env:HEADROOM_DISABLE_KOMPRESS_FALLBACK = '1'
$env:HEADROOM_COMPRESSION_MAX_WORKERS = '4'
headroom wrap claude --port $headroomPort --tool-search true
```

O wrapper preserva a busca dinâmica de ferramentas explicitamente. Fora dessa
sessão, inicie `claude` normalmente para usar a conexão nativa.

## Codex: perfil opt-in e transporte estável

O instalador cria `~/.codex/headroom.config.toml`, separado do
`~/.codex/config.toml`. Esse perfil aponta para loopback e define
`supports_websockets = false`, evitando o caminho WebSocket associado aos
encerramentos de stream observados. A integração MCP de recuperação também fica
dentro desse perfil; nenhuma sessão normal a inicia. O perfil só é ativado por
`--profile`.

Primeiro inicie o proxy em um terminal dedicado:

```bash
HEADROOM_DISABLE_KOMPRESS=1 \
HEADROOM_DISABLE_KOMPRESS_FALLBACK=1 \
HEADROOM_COMPRESSION_MAX_WORKERS=4 \
headroom proxy --host 127.0.0.1 --port "${HEADROOM_PORT:-48731}" --mode cache --no-telemetry
```

Depois, em outro terminal:

```bash
codex --profile headroom
```

No PowerShell, defina as três variáveis `HEADROOM_*` como no exemplo do Claude,
execute `headroom proxy --host 127.0.0.1 --port $headroomPort --mode cache
--no-telemetry` e então `codex --profile headroom` em outro terminal.

Se o proxy apresentar demora, quarentena ou desconexão, encerre a sessão opt-in
e reabra com `codex`, sem `--profile headroom`.

## Concorrência

Não use `HEADROOM_MAX_CONCURRENCY`: essa variável não corresponde a uma opção
do proxy atual. Também não eleve a concorrência para mascarar saturação do
compressor; mais trabalho paralelo pode agravar vazamento de threads e pressão
de CPU.

As opções suportadas são `HEADROOM_LIMIT_CONCURRENCY` para conexões de entrada
e `HEADROOM_ANTHROPIC_PRE_UPSTREAM_CONCURRENCY` para o estágio Anthropic. O
segundo já usa um limite baseado na CPU, com máximo padrão de oito. Ajuste-os
somente com métricas que demonstrem fila saudável e ausência de quarentena.

## Recuperação de uma instalação legada

Se Claude ou Codex falhar com `ConnectionRefused`, feche as sessões afetadas e
remova primeiro o vínculo durável:

```bash
headroom unwrap claude --port "${HEADROOM_PORT:-48731}"
headroom unwrap codex  --port "${HEADROOM_PORT:-48731}"
headroom install stop --profile init-user
```

Depois confira e remova, se ainda existirem:

- `ANTHROPIC_BASE_URL` e `OPENAI_BASE_URL` do ambiente de usuário/sistema;
- `ANTHROPIC_BASE_URL` em `~/.claude/settings.json`;
- hooks `SessionStart`/`PreToolUse` que executem `headroom init hook ensure` ou
  `headroom_healthcheck.py`;
- `model_provider = "headroom"` na raiz de `~/.codex/config.toml`.

O Codex também salva o provider no `session_meta` de cada rollout. Remover o
provider global pode fazer uma conversa antiga falhar antes de abrir com
`Model provider 'headroom' not found`. Migre somente esse metadado e a coluna
correspondente do banco, sempre com backup:

```bash
python tools/recover_codex_sessions.py --apply \
  --replace-provider headroom=openai \
  --require-session <UUID>
```

A ferramenta não substitui ocorrências em mensagens: apenas o campo estruturado
`model_provider` e a coluna equivalente são alterados.

O instalador não apaga essas entradas automaticamente porque elas podem ter
sido personalizadas e todo conflito exige backup/decisão explícita. O comando
`./install.sh --doctor` ou `.\install.ps1 --doctor` as sinaliza sem iniciar nem
parar processos e sem imprimir URLs potencialmente sensíveis.

No PowerShell, verifique também os escopos persistentes:

```powershell
[Environment]::GetEnvironmentVariable('ANTHROPIC_BASE_URL', 'User')
[Environment]::GetEnvironmentVariable('OPENAI_BASE_URL', 'User')
[Environment]::GetEnvironmentVariable('ANTHROPIC_BASE_URL', 'Machine')
[Environment]::GetEnvironmentVariable('OPENAI_BASE_URL', 'Machine')
```

Após a limpeza, uma sessão normal de `claude` e uma de `codex` devem funcionar
mesmo com a porta `48731` fechada.

## Limites de segurança

Mantenha o proxy em `127.0.0.1`; não o exponha na rede. Credenciais vêm do
ambiente da sessão ou do login do agente e nunca de arquivo versionado. Os
arquivos produzidos por `headroom init` podem conter caminhos e preferências da
máquina e não devem ser copiados para este repositório.
