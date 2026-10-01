## ADDED Requirements

### Requirement: Modo automático é opt-in e nunca torna o proxy obrigatório

O instalador SHALL oferecer, somente mediante `--headroom-auto`, funções de
shell que abrem `claude` e `codex` pelo Headroom. O lançador SHALL abrir o
agente diretamente no provedor quando o proxy não estiver saudável dentro do
tempo de espera, e SHALL NOT persistir endpoints de provedor, provider padrão
do Codex ou registro de MCP fora do processo iniciado.

#### Scenario: Proxy saudável

- **GIVEN** o modo automático está instalado e `/readyz` responde 200
- **WHEN** o usuário roda `claude` no terminal
- **THEN** a sessão passa pelo Headroom com o modelo e a janela de contexto configurados
- **AND** `~/.claude.json` e `~/.claude/settings.json` não ganham entradas do Headroom

#### Scenario: Proxy indisponível

- **GIVEN** o proxy não fica pronto dentro do tempo de espera
- **WHEN** o usuário roda `claude` ou `codex`
- **THEN** o agente abre direto no provedor, com um aviso de uma linha

#### Scenario: Chamada de gerenciamento

- **WHEN** o usuário roda `claude --version`, `claude mcp list` ou `codex login`
- **THEN** o comando vai direto ao agente, sem iniciar nem esperar o proxy

#### Scenario: Instalação sem a flag

- **WHEN** o instalador roda sem `--headroom-auto`
- **THEN** nenhum perfil de shell é alterado

#### Scenario: Desativação

- **WHEN** o usuário roda o instalador com `--no-headroom-auto`
- **THEN** o bloco gerenciado é removido e o restante do perfil é preservado
