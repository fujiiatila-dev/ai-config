# shared-agent-workflow Specification

## Purpose
Manter as instruções compartilhadas executáveis e coerentes entre agentes,
plataformas e shells, sem fazer um cliente assumir o lugar de outro.

## Requirements

### Requirement: OpenSpec identifica o cliente correto

O workflow compartilhado SHALL explicar que o valor de `--tools` depende do
cliente em execução e SHALL fornecer exemplos específicos para Claude Code,
Codex e Gemini, sem prescrever um único agente como padrão universal.

#### Scenario: Fluxo no Codex
- **WHEN** um usuário segue o exemplo de OpenSpec no Codex
- **THEN** o exemplo usa `openspec init --tools codex`

#### Scenario: Fluxo no Claude Code
- **WHEN** um usuário segue o exemplo de OpenSpec no Claude Code
- **THEN** o exemplo usa `openspec init --tools claude`

#### Scenario: Fluxo no Gemini
- **WHEN** um usuário segue o exemplo de OpenSpec no Gemini
- **THEN** o exemplo usa `openspec init --tools gemini`

### Requirement: Comandos documentados cobrem Bash e PowerShell

As instruções SHALL fornecer sintaxe equivalente para variáveis de ambiente,
auditoria de qualidade e comandos de segurança nos shells Bash e PowerShell.

#### Scenario: Auditoria em PowerShell
- **WHEN** o usuário executa a auditoria no Windows PowerShell
- **THEN** consegue definir `PYTHONUTF8` e rodar `aurum check .` sem usar atribuição Unix

#### Scenario: Auditoria em Bash
- **WHEN** o usuário executa a auditoria em Bash
- **THEN** consegue usar a forma `PYTHONUTF8=1 aurum check .`

### Requirement: Headroom usa uma porta documentada e parametrizável

Os exemplos de Headroom SHALL usar a porta configurada por `HEADROOM_PORT`,
com fallback explícito para a porta de referência do repositório, e SHALL
manter o proxy limitado a loopback.

#### Scenario: Porta padrão
- **WHEN** `HEADROOM_PORT` não está definida
- **THEN** os exemplos usam a porta padrão documentada pelo ai-config

#### Scenario: Porta personalizada
- **WHEN** `HEADROOM_PORT` está definida
- **THEN** init, proxy, doctor e configuração do Codex usam o mesmo valor

### Requirement: O workflow começa pelo preflight

O workflow compartilhado SHALL orientar a sequência `validate → dry-run →
apply → doctor → security → quality → commit`, explicando que cada etapa tem
um propósito distinto e que a etapa seguinte depende do resultado da anterior.

#### Scenario: Mudança de configuração

- **WHEN** um agente altera o `ai-config`
- **THEN** ele registra a mudança no OpenSpec, executa o preflight e o dry-run
  antes de aplicar ou commitar

#### Scenario: Configuração de usuário

- **WHEN** um usuário quer instalar a configuração em uma máquina
- **THEN** ele pode executar o preflight sem escrever nada, revisar o dry-run,
  aplicar com backup e depois usar `doctor` para validar o ambiente

### Requirement: Comandos equivalentes permanecem explícitos

As instruções SHALL manter exemplos equivalentes para Bash e PowerShell e SHALL
separar comandos read-only de comandos que escrevem, instalam ferramentas ou
alteram o baseline do Codex.

#### Scenario: Usuário Windows

- **WHEN** o usuário segue o fluxo no PowerShell
- **THEN** encontra as formas PowerShell de validar, simular, instalar,
  diagnosticar e auditar sem precisar traduzir atribuições Unix

#### Scenario: Usuário Unix

- **WHEN** o usuário segue o fluxo no Bash
- **THEN** encontra comandos Bash equivalentes com os mesmos efeitos e códigos
  de saída

### Requirement: A entrega declara evidências e limitações

O workflow SHALL exigir que a entrega informe branch, arquivos alterados,
validações executadas, verificações ignoradas e qualquer limitação de ambiente,
sem declarar integração pronta quando a configuração correspondente não foi
testada.

#### Scenario: Validação incompleta

- **WHEN** uma ferramenta opcional não está disponível
- **THEN** o relatório identifica a verificação ausente e não a apresenta como
  executada
