## Why

O ai-config instala configurações e ferramentas, mas ainda não consegue manter
ferramentas já instaladas de forma explícita e seu `doctor` pode demorar vários
minutos ao sondar CLIs que não respondem a flags de versão. A configuração
compartilhada também mistura instruções específicas de Claude com Codex,
assume shell Unix em pontos importantes e não oferece uma linha de base clara
para a segurança do Codex no Windows.

Precisamos corrigir isso agora para que novas instalações sejam portáteis,
repetíveis e seguras, e para que a atualização do ambiente não dependa de
edições manuais ou de diagnósticos que ficam presos.

## What Changes

- Adicionar manutenção explícita de ferramentas ao instalador, com referências
  versionadas, atualização opt-in e seleção segura de gerenciadores por
  plataforma.
- Tornar o `doctor` limitado no tempo, coerente com `versions.json` e capaz de
  reportar estado do Headroom e da linha de base do Codex de forma acionável.
- Definir defaults portáteis de sandbox/aprovação para o Codex e detectar
  configurações locais excessivamente amplas, sem remover credenciais,
  histórico ou permissões de projeto automaticamente.
- Corrigir a divergência `--tools claude`/`--tools codex`, documentar comandos
  Bash e PowerShell e alinhar README, adapters, workflow e help do instalador.
- Atualizar testes, especificações e referências de versões preservando as
  alterações locais já existentes em `tests/test_installer.py` e
  `versions.json`.

## Capabilities

### New Capabilities

- `codex-security-baseline`: defaults seguros e diagnóstico de sandbox,
  aprovação e escopo de confiança do Codex.
- `shared-agent-workflow`: instruções compartilhadas coerentes entre Claude,
  Codex, Gemini e shells suportados.

### Modified Capabilities

- `installer-reliability`: manutenção de ferramentas, sondagem de versões com
  timeout, diagnóstico do proxy e comportamento multiplataforma do instalador.

## Impact

- Afeta `tools/aiconfig.py`, `install.ps1`, `install.sh`, `versions.json`, os
  adapters de Codex/Gemini, `shared/WORKFLOW.md`, README e testes.
- Pode executar gerenciadores locais de pacotes somente quando solicitado pela
  instalação/atualização; não fará download de credenciais nem enviará código
  para serviços externos.
- A instalação continuará fazendo backup antes de alterar arquivos locais e
  mantendo conflitos e permissões pessoais fora do escopo gerenciado.
