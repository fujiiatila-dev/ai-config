# installer-reliability Specification

## Purpose

Define o comportamento confiável e multiplataforma dos instaladores e do
diagnóstico de ferramentas externas distribuídos pelo ai-config.

## Requirements

### Requirement: Falhas de configuração são preservadas
Os wrappers de instalação MUST encerrar com o mesmo código diferente de zero
quando o motor de configuração falhar e MUST NOT iniciar a instalação de
dependências após essa falha.

#### Scenario: Argumento inválido em dry-run
- **WHEN** o motor de configuração rejeita um argumento durante `--dry-run`
- **THEN** o wrapper encerra com código diferente de zero

#### Scenario: Falha antes das dependências
- **WHEN** a instalação da configuração termina com erro
- **THEN** nenhuma instalação global de ferramenta é iniciada

### Requirement: Ferramentas de segurança são instaladas conforme a plataforma
O instalador shell SHALL usar um gerenciador disponível e compatível para
instalar Gitleaks e Trivy, incluindo Homebrew em macOS e Linux.

#### Scenario: Homebrew disponível
- **WHEN** Gitleaks ou Trivy está ausente e `brew` está disponível
- **THEN** o instalador usa a fórmula Homebrew correspondente

#### Scenario: Nenhum gerenciador compatível
- **WHEN** a ferramenta está ausente e nenhum gerenciador suportado está disponível
- **THEN** o instalador emite orientação manual e registra falha parcial

### Requirement: Doctor cobre todas as referências declaradas
O diagnóstico SHALL associar cada ferramenta à chave correta de
`versions.json` e SHALL verificar Codex Security quando sua referência estiver
declarada.

#### Scenario: Referência do Python
- **WHEN** `versions.json` contém a chave `python`
- **THEN** a versão descoberta de Python é comparada com essa referência

#### Scenario: Codex Security via npx
- **WHEN** o comando local direto de Codex Security não está disponível
- **THEN** o diagnóstico tenta descobrir sua versão sem instalar nem executar um scan

### Requirement: Comportamentos críticos têm regressão automatizada
O repositório MUST fornecer testes automatizados dos códigos de saída, da
seleção de gerenciadores e do mapeamento das referências do diagnóstico.

#### Scenario: Execução da suíte
- **WHEN** a suíte de testes é executada em um checkout suportado
- **THEN** ela valida os contratos do instalador sem instalar dependências globais
