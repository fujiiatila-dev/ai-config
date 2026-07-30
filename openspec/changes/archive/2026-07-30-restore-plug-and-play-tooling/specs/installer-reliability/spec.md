## ADDED Requirements

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
