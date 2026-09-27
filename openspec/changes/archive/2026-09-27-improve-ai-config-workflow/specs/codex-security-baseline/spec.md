## ADDED Requirements

### Requirement: Templates portáteis não carregam estado pessoal

O preflight SHALL verificar os templates do Codex e SHALL falhar quando eles
contiverem caminhos absolutos, entradas de projeto, tokens, credenciais,
histórico ou memória que deveriam permanecer no perfil local.

#### Scenario: Projeto específico no template

- **WHEN** um template versionado contém uma seção de projeto identificada por
  caminho da máquina
- **THEN** a validação falha e aponta para a configuração local fora do Git

#### Scenario: Baseline portátil válido

- **WHEN** o template contém somente placeholders e defaults portáteis
- **THEN** a validação confirma o contrato sem exigir que permissões pessoais
  estejam presentes

### Requirement: Relatórios de segurança não vazam dados

As mensagens do preflight e do CI SHALL mascarar valores encontrados em
verificações de segredo e SHALL limitar o contexto exibido a arquivo relativo,
linha quando segura e identificador da regra.

#### Scenario: Padrão sensível encontrado

- **WHEN** uma regra encontra um valor que parece credencial
- **THEN** o relatório mostra somente `<REDACTED>` ou uma descrição do padrão
  sem reproduzir o valor
