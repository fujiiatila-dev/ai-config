## Context

Ver `proposal.md` para a motivação. O repositório tem wrappers finos para Bash
e PowerShell e concentra merge, instalação e diagnóstico em
`tools/aiconfig.py`. O catálogo `versions.json` já é a fonte das versões
comparadas pelo `doctor`, mas a preparação atual só trata ferramentas ausentes
e usa sondagens que podem bloquear por vários segundos para cada flag.

Os templates de agente são mesclados em arquivos locais; configurações de
credencial, histórico e permissões de projeto não devem ser copiadas para o
repositório. A mudança precisa funcionar em um checkout limpo sem depender de
um caminho específico de usuário.

## Goals / Non-Goals

**Goals:**

- Permitir atualização explícita e reproduzível das ferramentas gerenciadas,
  usando as versões de referência do repositório.
- Fazer o `doctor` terminar em tempo finito, informar o proxy Headroom e
  detectar a linha de base insegura do Codex.
- Oferecer defaults seguros para instalações novas e uma opção explícita de
  hardening com backup para configurações existentes.
- Alinhar instruções e exemplos entre agentes e shells, mantendo wrappers
  delegados ao mesmo motor Python.

**Non-Goals:**

- Instalar ou atualizar automaticamente RTK, Headroom, aurum ou Codex Security,
  que têm canais/credenciais próprios.
- Executar scans de segurança, enviar código para a nuvem ou manipular
  `auth.json`, sessões, memória e bancos do agente.
- Alterar valores locais conflitantes durante uma instalação comum ou apagar
  permissões específicas de projeto sem a opção explícita de hardening.

## Decisions

### 1. Catálogo de versões e atualização opt-in

`versions.json` continua sendo a fonte única das versões de OpenSpec, Semgrep,
Gitleaks e Trivy. A instalação normal prepara somente ausentes. A nova flag
`--update-tools` passa a solicitar a versão exata do catálogo: `npm install`
para OpenSpec, `pip install --upgrade` para Semgrep e `install`/`upgrade` no
gerenciador escolhido para Gitleaks e Trivy. A escolha entre winget,
Chocolatey e Homebrew permanece determinística e os códigos de “já instalado”
do winget continuam sucesso.

Codex Security permanece somente no diagnóstico; atualizar um pacote que pode
processar código na nuvem não será efeito colateral da instalação padrão.

### 2. Sondagem de versão limitada

`tool_version` usará flags conhecidas por ferramenta, com fallback mínimo e um
deadline monotônico compartilhado por cada ferramenta. `subprocess.run` recebe
o tempo restante, de modo que CLIs que abrem uma UI ou travam não prendem o
`doctor` indefinidamente. A versão desconhecida vira aviso, não falha global.

### 3. Diagnóstico e porta Headroom

O valor de `HEADROOM_PORT` será validado como inteiro entre 1 e 65535; sem ele,
o catálogo fornece o fallback. O probe usa `127.0.0.1/<port>/readyz` com
`ProxyHandler({})` e mostra a ação de inicialização correspondente. O mesmo
valor é usado na instalação e no `doctor`, evitando o falso negativo do probe
em `8787` quando o Codex está em `48731`.

O `doctor` fará uma inspeção textual conservadora do `config.toml` do Codex:
política de sandbox/aprovação ausente ou insegura e confiança exata na raiz do
perfil serão avisos acionáveis. Nenhum arquivo será alterado pelo `doctor`.

### 4. Hardening explícito e preservação do TOML

O template do Codex incluirá `sandbox_mode = "workspace-write"`,
`approval_policy = "on-request"`, `approvals_reviewer = "user"` e
`[windows] sandbox = "unelevated"`. A instalação comum usa o merge existente e
respeita conflitos locais.

`--harden-codex` aplicará somente essas chaves conhecidas em linhas TOML
simples, preservando seções e chaves desconhecidas. Também removerá apenas a
seção `[projects.<perfil-do-usuário>]` quando o caminho for exatamente a raiz
do perfil e o corpo contiver somente `trust_level`; entradas de projetos
específicos e seções com conteúdo adicional ficam intactas e continuam sendo
reportadas pelo `doctor`. Toda alteração passa por `Ctx.write`, portanto o
backup é criado antes.

### 5. Workflow compartilhado

`shared/WORKFLOW.md` deixará de escolher `claude` como ferramenta universal e
passará a listar o comando correspondente para cada cliente. Os exemplos de
qualidade e segurança terão blocos equivalentes para Bash e PowerShell. A
documentação do Headroom sempre informará a porta parametrizável e o escopo de
loopback.

## Risks / Trade-offs

- **[Versão de referência indisponível]** → o gerenciador pode rejeitar uma
  versão antiga; registrar falha parcial e orientar atualização do catálogo,
  sem mascarar o código de saída.
- **[Upgrade altera ambiente global]** → exigir `--update-tools` explícito,
  mostrar os comandos no dry-run e manter a instalação padrão sem upgrade.
- **[TOML não trivial ou corrompido]** → não reescrever; emitir aviso e manter
  o arquivo, preservando o comportamento de backup das escritas suportadas.
- **[Hardening remove uma confiança usada pelo usuário]** → exigir flag
  explícita, remover somente a entrada exata da raiz e manter backup
  recuperável; nunca tocar entradas de projetos específicos.
- **[Headroom usa outra porta entre agentes]** → validar a porta configurada,
  exibir o valor efetivo e documentar `doctor --port` no guia operacional.

## Migration Plan

1. Rodar `install.ps1 --dry-run --update-tools --harden-codex` (ou o wrapper
   Bash equivalente) e revisar conflitos/comandos.
2. Executar a instalação explícita em cada máquina que deve receber as
   atualizações; o instalador cria backup antes de alterar configurações.
3. Reiniciar os clientes e validar com `install.ps1 --doctor` e
   `headroom doctor --port <HEADROOM_PORT>`.
4. Em caso de regressão, restaurar o backup criado pelo instalador e executar o
   `doctor` novamente.
