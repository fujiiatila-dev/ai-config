## ADDED Requirements

### Requirement: A recuperação usa os rollouts preservados como fonte durável

A ferramenta SHALL descobrir todos os rollouts válidos no diretório local do
Codex, SHALL reconstruir o índice sem descartar registros suplementares e SHALL
verificar uma sessão solicitada por UUID ou identificador de rollout.

#### Scenario: Conversa desapareceu da barra lateral

- **GIVEN** o rollout da conversa ainda existe em `~/.codex/sessions`
- **AND** a entrada do índice ou a associação de projeto está ausente
- **WHEN** o usuário executa a recuperação com `--apply`
- **THEN** o rollout volta a constar no índice
- **AND** uma thread existente recebe a raiz de projeto mais específica

### Requirement: Toda aplicação é recuperável e idempotente

Antes de escrever, a ferramenta SHALL criar backups consistentes do estado
global, do índice e dos bancos SQLite. Uma segunda execução SHALL produzir um
estado válido sem duplicar registros ou alterar a recência das conversas.

#### Scenario: Reexecução após reparo concluído

- **GIVEN** todos os rollouts já estão indexados e as threads já têm projeto
- **WHEN** a ferramenta é executada novamente
- **THEN** nenhuma thread adicional é modificada
- **AND** a verificação continua sem ausências ou entradas pendentes

### Requirement: Rollouts técnicos não viram conversas fabricadas

A ferramenta SHALL preservar no índice rollouts de execuções e subagentes que
não possuem thread no banco, mas SHALL NOT inserir linhas sintéticas na tabela
de conversas.

#### Scenario: Rollout interno não existe no banco de threads

- **WHEN** a reconstrução encontra um rollout interno válido sem thread
- **THEN** o arquivo permanece recuperável pelo índice
- **AND** nenhum título, projeto ou metadado de interface é inventado

### Requirement: Providers removidos podem ser migrados sem alterar mensagens

A ferramenta SHALL permitir substituir um `model_provider` obsoleto no campo
estruturado `session_meta` e na coluna correspondente do banco de threads. Ela
SHALL copiar integralmente todo rollout afetado para o backup e SHALL NOT fazer
substituições textuais no conteúdo da conversa.

#### Scenario: Sessão antiga depende do provider Headroom removido

- **GIVEN** o rollout ou a thread seleciona `model_provider=headroom`
- **AND** o provider global foi removido para restaurar a conexão direta
- **WHEN** o usuário aplica `--replace-provider headroom=openai`
- **THEN** o bootstrap da sessão resolve o provider OpenAI
- **AND** mensagens, títulos e ordem dos eventos permanecem inalterados
