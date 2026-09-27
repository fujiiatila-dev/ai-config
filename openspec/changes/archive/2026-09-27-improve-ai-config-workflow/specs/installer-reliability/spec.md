## ADDED Requirements

### Requirement: Instalação valida fontes antes de escrever

O comando de instalação SHALL executar o preflight estrutural antes da primeira
escrita, SHALL abortar quando houver erro obrigatório e SHALL preservar o
comportamento de backup e merge quando o preflight passar.

#### Scenario: Fonte inválida impede escrita

- **WHEN** uma origem versionada obrigatória está inválida ou ausente
- **THEN** a instalação termina com código diferente de zero antes de alterar
  qualquer destino

#### Scenario: Fonte válida mantém o fluxo existente

- **WHEN** o preflight passa
- **THEN** a instalação continua usando as políticas atuais de conflito, backup,
  merge de listas e códigos de saída

### Requirement: Wrappers expõem validação equivalente

`install.sh` e `install.ps1` SHALL oferecer o mesmo comando de validação e SHALL
repassar seu código de saída sem iniciar instaladores de dependências.

#### Scenario: Validação por Bash

- **WHEN** o usuário executa `./install.sh --validate`
- **THEN** o wrapper chama o preflight e devolve o mesmo resultado do motor

#### Scenario: Validação por PowerShell

- **WHEN** o usuário executa `./install.ps1 --validate`
- **THEN** o wrapper chama o mesmo preflight e devolve o mesmo resultado do
  motor

#### Scenario: Validação não instala ferramentas

- **WHEN** o usuário executa a validação, com ou sem saída JSON
- **THEN** nenhum gerenciador de pacotes, Headroom ou serviço externo é iniciado

### Requirement: Instalação não torna proxy opcional em dependência global

A instalação padrão SHALL criar apenas um perfil Headroom opt-in para Codex e
SHALL NOT iniciar Headroom, persistir URLs de proxy nos baselines ou instalar
hooks de recuperação automática.

#### Scenario: Instalação com Headroom ausente ou parado

- **GIVEN** o executável Headroom não existe ou nenhum proxy está ativo
- **WHEN** o usuário instala o ai-config
- **THEN** a instalação conclui sem tentar executar Headroom
- **AND** Claude e Codex padrão permanecem configurados para seus provedores
