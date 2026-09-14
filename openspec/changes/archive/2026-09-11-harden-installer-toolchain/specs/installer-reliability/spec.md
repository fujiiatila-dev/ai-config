## MODIFIED Requirements

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
