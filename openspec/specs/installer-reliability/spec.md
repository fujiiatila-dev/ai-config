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
instalar Gitleaks e Trivy, incluindo Homebrew em macOS e Linux. A instalação
padrão SHALL preparar apenas ferramentas ausentes; uma atualização de
ferramentas SHALL ser opt-in, usar as referências de `versions.json` quando
disponíveis e não executar se `--skip-tools` estiver ativo.

#### Scenario: Homebrew disponível
- **WHEN** Gitleaks ou Trivy está ausente e `brew` está disponível
- **THEN** o instalador usa a fórmula Homebrew correspondente

#### Scenario: Nenhum gerenciador compatível
- **WHEN** a ferramenta está ausente e nenhum gerenciador suportado está disponível
- **THEN** o instalador emite orientação manual e registra falha parcial

#### Scenario: Atualização explicitamente solicitada
- **WHEN** o usuário executa o instalador com `--update-tools` e uma ferramenta gerenciada já está instalada
- **THEN** o instalador solicita ao gerenciador compatível a versão de referência do repositório

#### Scenario: Instalação padrão preserva versões existentes
- **WHEN** o usuário executa o instalador sem `--update-tools` e a ferramenta já está instalada
- **THEN** o instalador não executa um upgrade silencioso

#### Scenario: Atualização desativada
- **WHEN** o usuário combina `--update-tools` com `--skip-tools`
- **THEN** nenhum gerenciador de pacotes é executado

### Requirement: Doctor cobre todas as referências declaradas

O diagnóstico SHALL associar cada ferramenta à chave correta de
`versions.json`, SHALL verificar Codex Security quando sua referência estiver
declarada e SHALL limitar cada sondagem de versão a um prazo finito. Também
SHALL informar o estado do proxy Headroom na porta configurada e emitir avisos
acionáveis para a linha de base do Codex, sem transformar avisos de ambiente em
falhas de instalação.

#### Scenario: Referência do Python
- **WHEN** `versions.json` contém a chave `python`
- **THEN** a versão descoberta de Python é comparada com essa referência

#### Scenario: Codex Security via npx
- **WHEN** o comando local direto de Codex Security não está disponível
- **THEN** o diagnóstico tenta descobrir sua versão sem instalar nem executar um scan

#### Scenario: CLI não responde à versão
- **WHEN** uma ferramenta não responde a uma flag de versão dentro do prazo
- **THEN** o diagnóstico continua para a próxima ferramenta e marca aquela versão como desconhecida

#### Scenario: Headroom usa porta configurada
- **WHEN** `HEADROOM_PORT` ou a porta de runtime de `versions.json` está definida
- **THEN** o diagnóstico consulta o endpoint de prontidão nessa porta e mostra uma ação para corrigi-lo quando estiver fora do ar

#### Scenario: Baseline do Codex requer atenção
- **WHEN** o `config.toml` do Codex usa sandbox elevada, omite política de aprovação ou confia na raiz do perfil do usuário
- **THEN** o diagnóstico exibe um aviso específico e não altera o arquivo

### Requirement: Comportamentos críticos têm regressão automatizada

O repositório MUST fornecer testes automatizados dos códigos de saída, da
seleção de gerenciadores, do mapeamento das referências do diagnóstico, do
limite de tempo das sondagens e da opção explícita de atualização.

#### Scenario: Execução da suíte
- **WHEN** a suíte de testes é executada em um checkout suportado
- **THEN** ela valida os contratos do instalador sem instalar dependências globais

#### Scenario: Sondagem limitada
- **WHEN** uma ferramenta simulada bloqueia a consulta de versão
- **THEN** o teste confirma que o diagnóstico encerra a sondagem e continua

#### Scenario: Atualização sem efeitos colaterais
- **WHEN** o modo padrão é executado sem `--update-tools`
- **THEN** o teste confirma que nenhum comando de upgrade é chamado

### Requirement: Instalação padrão é plug-and-play

O modo padrão de instalação SHALL aplicar as configurações de todos os agentes
suportados e preparar OpenSpec, Semgrep, Gitleaks e Trivy quando estiverem
ausentes. O instalador SHALL oferecer `--update-tools` para atualizar essas
ferramentas de forma explícita e SHALL oferecer `--harden-codex` para aplicar a
linha de base segura do Codex com backup.

#### Scenario: Instalação padrão
- **WHEN** o usuário executa o instalador sem `--skip-tools`
- **THEN** a configuração é sincronizada e as ferramentas recomendadas ausentes são preparadas

#### Scenario: Instalação somente de configuração
- **WHEN** o usuário executa o instalador com `--skip-tools`
- **THEN** a configuração é sincronizada sem executar gerenciadores de pacotes

#### Scenario: Simulação
- **WHEN** o usuário executa o instalador com `--dry-run`
- **THEN** nenhuma configuração ou ferramenta é instalada

#### Scenario: Atualização explícita
- **WHEN** o usuário executa o instalador com `--update-tools`
- **THEN** ferramentas gerenciadas existentes são atualizadas para as referências declaradas, sem modificar configurações fora do fluxo normal

#### Scenario: Endurecimento explícito
- **WHEN** o usuário executa o instalador com `--harden-codex`
- **THEN** os defaults de sandbox/aprovação do Codex são aplicados com backup e permissões de projetos não relacionadas permanecem intactas

### Requirement: Preparação de ferramentas é centralizada

Os wrappers suportados MUST produzir o mesmo resultado de preparação de
ferramentas e MUST preservar o código de saída do motor comum. As opções de
atualização e endurecimento SHALL estar disponíveis de forma equivalente em
Bash e PowerShell.

#### Scenario: Windows e Unix
- **WHEN** a mesma instalação é iniciada por PowerShell ou Bash
- **THEN** ambos delegam configuração, ferramentas, atualização e diagnóstico ao mesmo motor

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
