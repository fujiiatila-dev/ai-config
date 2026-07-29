## Why

Os instaladores recém-ampliados apresentam sucesso mesmo quando a etapa de
configuração falha, prometem suporte Homebrew que não foi implementado e deixam
referências de versão fora do diagnóstico. Isso torna a instalação e o
`--doctor` menos confiáveis justamente nos cenários em que deveriam orientar o
usuário.

## What Changes

- Preservar e retornar imediatamente códigos de erro da etapa de configuração.
- Implementar instalação de Gitleaks e Trivy via Homebrew no macOS/Linux.
- Fazer o `doctor` comparar corretamente Python e verificar Codex Security.
- Adicionar testes automatizados para códigos de saída, seleção do gerenciador
  de pacotes e cobertura das referências de versão.
- Documentar somente comportamentos realmente implementados.

## Capabilities

### New Capabilities

- `installer-reliability`: Contrato de códigos de saída, instalação
  multiplataforma de ferramentas e diagnóstico completo de versões.

### Modified Capabilities

Nenhuma.

## Impact

Afeta `install.sh`, `install.ps1`, `tools/aiconfig.py`, a documentação do
instalador e a nova suíte de testes. Não altera formatos de configuração nem
remove compatibilidade existente.
