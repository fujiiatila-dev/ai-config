## Purpose

Estabelecer uma linha de base segura e explícita para a execução do Codex no
Windows, mantendo permissões pessoais fora da configuração versionada.

## ADDED Requirements

### Requirement: Codex inicia com defaults restritos

O instalador SHALL fornecer, para configurações novas, sandbox de workspace
write, aprovação sob demanda, revisão pelo usuário e sandbox nativa do Windows
não elevada. Uma execução normal SHALL preservar valores locais conflitantes;
somente `--harden-codex` pode forçar esses defaults e deve criar backup antes.

#### Scenario: Configuração nova
- **WHEN** o instalador cria um `config.toml` do Codex
- **THEN** o arquivo contém `sandbox_mode = "workspace-write"`, `approval_policy = "on-request"`, `approvals_reviewer = "user"` e `windows.sandbox = "unelevated"`

#### Scenario: Configuração local conflitante
- **WHEN** o arquivo existente possui um valor diferente e o usuário não usa `--harden-codex`
- **THEN** o instalador aplica a política normal de conflito e não força a substituição

#### Scenario: Endurecimento solicitado
- **WHEN** o usuário usa `--harden-codex`
- **THEN** os quatro defaults restritos são aplicados, o estado anterior é salvo e as demais chaves são preservadas

#### Scenario: Confiança ampla endurecida explicitamente
- **WHEN** o usuário usa `--harden-codex` e existe uma entrada confiável exatamente para a raiz do seu perfil contendo somente `trust_level`
- **THEN** essa entrada ampla é removida, as entradas de projetos específicos permanecem e o backup permite recuperar o estado anterior

### Requirement: Configurações de confiança excessivas são diagnosticadas

O `doctor` SHALL alertar quando o `config.toml` confia explicitamente na raiz
do perfil do usuário ou em outro escopo equivalente amplo. O diagnóstico SHALL
indicar que a correção é uma decisão local e SHALL evitar apagar permissões
automaticamente.

#### Scenario: Raiz do perfil confiável
- **WHEN** existe uma entrada `projects` para a raiz do perfil com `trust_level = "trusted"`
- **THEN** o `doctor` emite um aviso sobre o escopo amplo e não remove a entrada

#### Scenario: Apenas projetos específicos confiáveis
- **WHEN** as entradas confiáveis apontam somente para diretórios de projetos específicos
- **THEN** o `doctor` não classifica essas entradas como confiança ampla

### Requirement: Dados pessoais ficam fora do baseline versionado

O instalador SHALL manter credenciais, histórico, memória, sessões e permissões
específicas de projeto fora dos templates versionados, e SHALL fazer backup de
qualquer arquivo local antes de uma alteração explícita de hardening.

#### Scenario: Template do repositório
- **WHEN** o usuário inspeciona os templates do Codex
- **THEN** não encontra tokens, credenciais ou entradas de projeto dependentes da máquina

#### Scenario: Hardening de arquivo existente
- **WHEN** o hardening altera um `config.toml` local
- **THEN** existe uma cópia recuperável do estado anterior antes da escrita
