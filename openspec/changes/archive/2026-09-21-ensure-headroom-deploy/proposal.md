## Why

O Codex pode iniciar com o Headroom parado após reinicialização ou falha do
processo. Nesse cenário, o `SessionStart` tenta executar `headroom init hook
ensure`, mas o cold start ultrapassa o timeout atual e bloqueia a sessão.

## What Changes

- O motor comum do instalador verificará a deploy `init-user` do Headroom após
  sincronizar as configurações e a iniciará quando estiver parada ou não
  saudável.
- O healthcheck será reutilizável pelo instalador e pelo hook do Codex, sem
  caminhos absolutos versionados.
- A execução em `--dry-run` apenas reportará a ação, sem iniciar processos ou
  alterar arquivos.
- O hook do Codex ganhará tempo suficiente para o cold start e usará o
  healthcheck antes de garantir o marker.

## Capabilities

### New Capabilities

Nenhuma; o comportamento pertence à confiabilidade do instalador existente.

### Modified Capabilities

- `installer-reliability`: a instalação deve garantir que a deploy Headroom
  configurada para o Codex esteja ativa, e o hook deve recuperar uma deploy
  parada antes de executar o `ensure`.

## Impact

Afeta `tools/aiconfig.py`, os wrappers `install.sh` e `install.ps1`, a
configuração portátil do hook do Codex e os testes automatizados do instalador.
Não adiciona dependências de runtime além do executável Headroom já opcional.
