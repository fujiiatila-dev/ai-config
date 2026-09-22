## ADDED Requirements

### Requirement: Os agentes usam os provedores diretamente por padrão

O checkout SHALL manter Claude e Codex independentes do proxy Headroom em uma
inicialização normal. O instalador SHALL NOT persistir endpoints de proxy no
baseline, iniciar deployments ou instalar hooks que iniciem, recuperem ou
reiniciem Headroom.

#### Scenario: Proxy indisponível durante inicialização normal

- **GIVEN** nenhum processo responde em `HEADROOM_PORT`
- **WHEN** o usuário inicia `claude` ou `codex` sem opção Headroom
- **THEN** a configuração instalada não redireciona o agente para loopback
- **AND** nenhum hook tenta iniciar o proxy

#### Scenario: Regressão durável no checkout

- **WHEN** o baseline do Claude contém `ANTHROPIC_BASE_URL`, o baseline do Codex
  seleciona Headroom ou um hook versionado executa recuperação do proxy
- **THEN** o preflight falha com um diagnóstico acionável

### Requirement: Headroom é ativado explicitamente e isolado

O checkout SHALL documentar Claude por `headroom wrap claude` e SHALL instalar
um perfil Codex separado, selecionado somente por `codex --profile headroom`.
O perfil Codex SHALL apontar apenas para loopback e SHALL desabilitar WebSocket.

#### Scenario: Sessão Claude opt-in

- **WHEN** o usuário executa `headroom wrap claude --tool-search true`
- **THEN** o roteamento customizado fica limitado ao processo iniciado
- **AND** uma sessão Claude comum posterior mantém a conexão nativa

#### Scenario: Sessão Codex opt-in

- **WHEN** o usuário inicia o proxy conscientemente e executa
  `codex --profile headroom`
- **THEN** somente esse perfil usa o provider Headroom por SSE
- **AND** `~/.codex/config.toml` não seleciona o proxy globalmente

### Requirement: O modo Windows prioriza disponibilidade do provedor

A receita opt-in SHALL desabilitar Kompress e o fallback Kompress no Windows,
SHALL limitar o pool de compressão e SHALL NOT elevar concorrência como correção
automática para quarentena ou vazamento de threads.

#### Scenario: Executor Kompress degrada

- **GIVEN** há timeouts, quarentena ou crescimento de threads do executor
- **WHEN** o usuário segue a receita suportada
- **THEN** a sessão usa compressão estrutural/passthrough sem Kompress
- **AND** o usuário pode encerrar a sessão e reiniciar o agente diretamente

### Requirement: Diagnóstico não altera o ciclo de vida do proxy

O `doctor` SHALL sondar o endpoint local de forma somente leitura, SHALL detectar
variáveis, hooks e provider global legados sem imprimir os valores das URLs e
SHALL NOT iniciar, parar ou reiniciar Headroom.

#### Scenario: Rota persistente com proxy fora do ar

- **GIVEN** uma configuração legada ainda depende de Headroom
- **AND** o endpoint local não responde
- **WHEN** o usuário executa `doctor`
- **THEN** o relatório explica o risco de `ConnectionRefused`
- **AND** aponta para a recuperação manual sem executar a recuperação
