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

### Requirement: Instalação padrão é plug-and-play
O modo padrão de instalação SHALL aplicar as configurações de todos os agentes
suportados e preparar OpenSpec, Semgrep, Gitleaks e Trivy quando estiverem
ausentes.

#### Scenario: Instalação padrão
- **WHEN** o usuário executa o instalador sem `--skip-tools`
- **THEN** a configuração é sincronizada e as ferramentas recomendadas ausentes são preparadas

#### Scenario: Instalação somente de configuração
- **WHEN** o usuário executa o instalador com `--skip-tools`
- **THEN** a configuração é sincronizada sem executar gerenciadores de pacotes

#### Scenario: Simulação
- **WHEN** o usuário executa o instalador com `--dry-run`
- **THEN** nenhuma configuração ou ferramenta é instalada

### Requirement: Preparação de ferramentas é centralizada
Os wrappers suportados MUST produzir o mesmo resultado de preparação de
ferramentas e MUST preservar o código de saída do motor comum.

#### Scenario: Windows e Unix
- **WHEN** a mesma instalação é iniciada por PowerShell ou Bash
- **THEN** ambos delegam configuração, ferramentas e diagnóstico ao mesmo motor

#### Scenario: Falha no motor comum
- **WHEN** o motor comum encerra com erro
- **THEN** o wrapper devolve o mesmo código de saída

### Requirement: Padrão compartilhado permanece coerente
O conteúdo instalado para Claude Code, Codex e Gemini SHALL manter OpenSpec,
qualidade e segurança como partes do mesmo padrão compartilhado.

#### Scenario: Instalação em múltiplos agentes
- **WHEN** o instalador sincroniza os arquivos de instrução
- **THEN** cada adapter referencia um `WORKFLOW.md` que documenta OpenSpec, qualidade e segurança

#### Scenario: Documentação pública
- **WHEN** o usuário consulta README, mapa de configuração ou `--help`
- **THEN** o comportamento plug-and-play e a opção `--skip-tools` são descritos de forma consistente
