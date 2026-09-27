## ADDED Requirements

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
