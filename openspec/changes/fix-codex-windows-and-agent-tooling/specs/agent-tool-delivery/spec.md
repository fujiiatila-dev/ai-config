## ADDED Requirements

### Requirement: O Codex no Windows não abre janelas de console

No Windows, o baseline instalado SHALL desligar `features.daemon_auto_start`
do Codex, e os hooks instalados SHALL usar comandos válidos no shell com que o
Codex os executa.

#### Scenario: Sessão do terminal após a instalação

- **GIVEN** o daemon compartilhado não está rodando
- **WHEN** o usuário inicia `codex` e o agente roda comandos de shell
- **THEN** a sessão usa o servidor embutido e nenhuma janela de console é criada

#### Scenario: Hook legado quebrado

- **GIVEN** `~/.codex/hooks.json` contém `rtk hook claude` ou `commandWindows` em sintaxe de cmd
- **WHEN** o instalador roda
- **THEN** cada hook legado vira um conflito explícito, com backup
- **AND** `--keep-existing` preserva o hook atual

### Requirement: Todos os agentes recebem o padrão de trabalho e as skills

O instalador SHALL incorporar `shared/WORKFLOW.md` nos arquivos de instruções
de clientes que não expandem `@arquivo`, e SHALL instalar as skills neutras no
local que cada cliente lê.

#### Scenario: Codex

- **WHEN** o instalador roda
- **THEN** `~/.codex/AGENTS.md` contém o conteúdo do `WORKFLOW.md`
- **AND** `~/.agents/skills` contém `openspec`, `qualidade` e `security-audit`

#### Scenario: Antigravity

- **WHEN** o instalador roda
- **THEN** `~/.gemini/config/rules/ai-config.md` começa com `trigger: always_on`
- **AND** `~/.gemini/config/skills` contém as skills neutras

#### Scenario: Adapter com import não suportado

- **WHEN** um adapter de Codex, Gemini ou Antigravity usa `@arquivo`
- **THEN** o preflight falha com `adapter-import-unsupported`

### Requirement: Sessão Headroom sem configuração manual

O repositório SHALL oferecer um lançador que aplica, só ao processo iniciado,
as variáveis de Kompress e o bundle de CA, e SHALL respeitar `--dry-run`.

#### Scenario: Dry-run

- **WHEN** o usuário roda `--headroom claude --dry-run`
- **THEN** o comando é exibido e nenhum processo é iniciado
