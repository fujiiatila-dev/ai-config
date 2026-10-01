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
`python -m uv tool upgrade headroom-ai`. Se falhar com `UnknownIssuer`, acrescente
`--native-tls` (veja a seção seguinte).

A versão de referência fica em `versions.json`. Atualizar é recomendado, mas
não substitui as proteções abaixo: falhas do executor Kompress/ONNX também foram
observadas em versões posteriores à 0.34.

## Pré-requisito: TLS verificável pelo Python

O proxy é uma aplicação Python. Na partida, o `litellm` baixa o encoding do
`tiktoken` com `requests`, e as chamadas ao provedor usam `httpx`. Ambos
validam o certificado contra o bundle Mozilla/`certifi`. Se um antivírus
(AVG/Avast Web Shield, Kaspersky…) ou um proxy corporativo reassina o HTTPS, o
processo termina antes do `/readyz` com `CERTIFICATE_VERIFY_FAILED`. Nesse
caso, `headroom wrap` parece travar e o `doctor` mostra a porta fechada.

`./install.sh --doctor` detecta a inspeção e mostra o emissor. A correção,
por sessão e sem desativar a verificação:

```powershell
.\install.ps1 --ca-bundle
$env:SSL_CERT_FILE = "$HOME\.config\ai-config\ca-bundle.pem"
$env:REQUESTS_CA_BUNDLE = $env:SSL_CERT_FILE
```

As duas variáveis são necessárias (`requests` ignora `SSL_CERT_FILE`). Com
elas, o proxy fica pronto em cerca de 30 s e repassa ao provedor normalmente.
A alternativa definitiva é excluir os domínios dos provedores da inspeção
HTTPS do antivírus; veja [TOOLS.md > TLS interceptado](TOOLS.md#tls-interceptado).

## Modo automático (opt-in, com fallback direto)

Para não ter de lembrar do Headroom a cada sessão:

```powershell
.\install.ps1 --headroom-auto --keep-existing --skip-tools   # ativa
.\install.ps1 --no-headroom-auto --keep-existing --skip-tools # desativa
```

Isso grava um bloco delimitado no perfil do shell (PowerShell 7, Windows
PowerShell, `~/.bashrc`, `~/.zshrc`) que define `claude` e `codex` como funções.
Ao chamar uma delas, o lançador:

1. confere `/readyz`; se o proxy não estiver de pé, sobe-o em segundo plano,
   sem janela, e espera até 60 s (`AICONFIG_HEADROOM_WAIT` muda o limite);
2. com o proxy saudável, abre o agente pelo Headroom: `headroom wrap claude
   --no-proxy --no-mcp …` ou `codex --profile headroom`;
3. com o proxy fora, avisa em uma linha e abre o agente **direto no provedor**.

O que o modo automático **não** faz, de propósito:

- não persiste `ANTHROPIC_BASE_URL`/`OPENAI_BASE_URL` nem troca o provider
  padrão do Codex: o roteamento vale só para o processo iniciado;
- não registra o MCP `headroom` no `~/.claude.json`: a ferramenta de
  recuperação entra só naquela sessão, por `--mcp-config`;
- não usa `--1m`, que fixaria `ANTHROPIC_MODEL` num Opus específico. Um `model`
  com `[1m]` no `settings.json` já preserva a janela de 1M pelo proxy;
- não espera o proxy em chamadas de gerenciamento (`claude --version`,
  `claude mcp …`, `codex login`, `--help`), que vão direto.

Um terminal interativo novo pré-aquece o proxy em segundo plano, então a espera
de partida a frio (30 a 90 s) normalmente termina antes de você abrir o agente.
O proxy continua rodando depois que a sessão fecha; o log fica em
`~/.headroom/ai-config-proxy.log`.

Para desligar numa sessão do shell: `$env:AICONFIG_HEADROOM = 'off'` (ou
`export AICONFIG_HEADROOM=off`). Atalhos de IDE e o app desktop não passam
pelas funções do shell e continuam abrindo direto.

## Lançador do repositório

`./install.sh --headroom claude` (ou `.\install.ps1 --headroom claude`) aplica
as variáveis `HEADROOM_DISABLE_KOMPRESS*` e, se existir, o bundle de CA, só no
processo iniciado, e roda `headroom wrap claude --port <porta> --tool-search true`.
`--headroom proxy` sobe o proxy para `codex --profile headroom`. Use
`--dry-run` para ver o comando sem executar. As seções abaixo mostram o
equivalente manual.

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

Aguarde `curl http://127.0.0.1:${HEADROOM_PORT:-48731}/readyz` responder 200
(a primeira partida leva ~30 s). Depois, em outro terminal:

```bash
codex --profile headroom
```

O Codex **não** acusa erro para perfil inexistente: `--profile headroom` só
tem efeito se `~/.codex/headroom.config.toml` existir. Para confirmar, rode
`codex --profile headroom mcp list`; o servidor `headroom` deve aparecer.

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
