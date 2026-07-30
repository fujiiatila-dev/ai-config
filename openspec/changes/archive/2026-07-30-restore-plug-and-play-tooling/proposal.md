## Why

O projeto existe para oferecer um ambiente de IA para código realmente
plug-and-play e padronizado. O commit de unificação simplificou o wrapper, mas
removeu a preparação automática das ferramentas, quebrou a suíte e deixou
implementação, documentação e especificação permanente em conflito.

## What Changes

- Restaurar a instalação completa em um comando, mantendo `--skip-tools` para
  quem deseja apenas sincronizar configuração.
- Preparar OpenSpec, Semgrep, Gitleaks e Trivy de forma multiplataforma, com
  falhas parciais claramente reportadas.
- Restaurar o diagnóstico completo e referências atuais de versões.
- Reunificar `WORKFLOW.md`, adapters, skills, README e mapa de configuração em
  torno do mesmo padrão de OpenSpec, qualidade e segurança.
- Reconciliar e ampliar os testes para refletirem o contrato plug-and-play.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `installer-reliability`: explicitar que o modo padrão instala configuração e
  ferramentas recomendadas, preserva uma opção config-only e mantém
  documentação/instruções coerentes com esse contrato.

## Impact

Afeta os wrappers Bash e PowerShell, `tools/aiconfig.py`, `versions.json`,
documentação compartilhada, testes e CI. A instalação poderá executar
gerenciadores globais no modo padrão, comportamento anunciado e evitável com
`--skip-tools`.
