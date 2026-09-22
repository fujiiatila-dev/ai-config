## MODIFIED Requirements

### Requirement: Instalação padrão é plug-and-play
O modo padrão de instalação SHALL aplicar as configurações de todos os agentes
suportados, preparar OpenSpec, Semgrep, Gitleaks e Trivy quando estiverem
ausentes e garantir que a deploy `init-user` do Headroom esteja ativa quando o
executável Headroom estiver disponível.

#### Scenario: Instalação padrão com deploy parada
- **WHEN** o usuário executa o instalador sem `--skip-tools` e o status da
  deploy `init-user` informa `Status: stopped` ou uma deploy não saudável
- **THEN** o motor sincroniza as configurações, executa
  `headroom install start --profile init-user` e verifica novamente o status

#### Scenario: Deploy já saudável
- **WHEN** o status da deploy `init-user` informa `Status: running` e
  `Healthy: yes`
- **THEN** o instalador não executa o comando de start

#### Scenario: Headroom indisponível
- **WHEN** o executável Headroom não está disponível
- **THEN** a configuração é sincronizada, o instalador emite uma orientação
  acionável e não falha por causa do healthcheck opcional

#### Scenario: Instalação somente de configuração
- **WHEN** o usuário executa o instalador com `--skip-tools`
- **THEN** a configuração é sincronizada sem executar gerenciadores de
  pacotes, mas o healthcheck do Headroom disponível ainda pode garantir a
  deploy configurada

#### Scenario: Simulação
- **WHEN** o usuário executa o instalador com `--dry-run`
- **THEN** nenhuma configuração, start de deploy ou ferramenta é instalada e
  a possível ação de recuperação é apenas reportada

### Requirement: Comportamentos críticos têm regressão automatizada
O repositório MUST fornecer testes automatizados dos códigos de saída, da
seleção de gerenciadores, do mapeamento das referências do diagnóstico e do
healthcheck da deploy Headroom.

#### Scenario: Execução da suíte
- **WHEN** a suíte de testes é executada em um checkout suportado
- **THEN** ela valida os contratos do instalador sem instalar dependências
  globais nem iniciar uma deploy real

#### Scenario: Recuperação da deploy
- **WHEN** um status simulado retorna `Status: stopped` ou `Healthy: no`
- **THEN** o healthcheck executa exatamente um start e confirma o status
  saudável antes de retornar sucesso
