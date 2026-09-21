## Why

O `ai-config` já protege conflitos, faz backup, aplica um baseline seguro ao
Codex e possui testes do instalador, mas as regras críticas ainda estão
espalhadas entre README, adapters, `WORKFLOW.md`, código e CI. O repositório de
skills usado como legado mostrou o custo desse modelo: catálogos, instruções e
comportamentos podem divergir sem um gate determinístico. Precisamos de um
preflight local e de CI que detecte drift, referências inválidas, segredos,
caminhos de máquina e inconsistências entre shells antes de qualquer instalação.

## What Changes

- Introduzir um comando somente leitura de validação do repositório, disponível
  pelos wrappers Bash e PowerShell, com saída humana e relatório JSON para CI.
- Fazer o instalador validar suas fontes antes de escrever configurações, sem
  instalar ferramentas externas e sem alterar o estado do usuário no preflight.
- Validar contratos de distribuição: arquivos de origem e destinos declarados,
  placeholders portáteis, JSON/TOML/Python, adapters que apontam para a fonte
  compartilhada, catálogo de versões e cobertura do `doctor`.
- Validar higiene de segurança do repositório, rejeitando credenciais,
  caminhos absolutos de máquina e permissões/configurações locais fora dos
  arquivos explicitamente permitidos.
- Adicionar gates de CI para validação, testes, sintaxe dos wrappers e relatório
  acionável, mantendo o fluxo multiplataforma existente.
- Documentar um fluxo operacional único: validar, simular, aplicar, diagnosticar,
  auditar e só então commitar ou publicar.

## Capabilities

### New Capabilities

- `configuration-preflight`: validação determinística e somente leitura dos
  contratos de configuração, distribuição e segurança do repositório.

### Modified Capabilities

- `installer-reliability`: o instalador deve executar o preflight das fontes
  antes de qualquer escrita e expor o mesmo comando por Bash e PowerShell.
- `shared-agent-workflow`: o fluxo compartilhado deve incluir o preflight e
  separar claramente validação local, dry-run, aplicação, doctor e auditoria.
- `codex-security-baseline`: a validação deve impedir que templates carreguem
  caminhos, credenciais ou permissões específicas de uma máquina/projeto.

## Impact

Afeta `tools/aiconfig.py`, `install.sh`, `install.ps1`, testes, o workflow de
CI, `README.md`, `CONFIGURATION_MAP.md`, `shared/WORKFLOW.md` e os adapters. A
interface ganha um comando read-only de validação e uma etapa automática de
preflight antes da instalação. Não altera credenciais, sessões, memória ou
configurações locais do usuário, e não torna a instalação de ferramentas
externas obrigatória para validar o repositório.
