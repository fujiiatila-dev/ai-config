## Context

Os wrappers Bash e PowerShell chamam o mesmo motor Python, mas tratam códigos de
saída de forma diferente. A instalação de ferramentas está duplicada entre os
wrappers e o `doctor` usa nomes de exibição como chaves implícitas de versão.

## Goals / Non-Goals

**Goals:**

- Tornar falhas do motor Python fatais antes de qualquer efeito global.
- Completar a seleção de gerenciadores já documentada.
- Tornar explícito o mapeamento entre comandos e chaves de versão.
- Testar os contratos sem depender da máquina do desenvolvedor.

**Non-Goals:**

- Instalar RTK, Headroom, aurum ou Codex Security automaticamente.
- Executar scans de segurança durante instalação ou diagnóstico.
- Alterar a política de merge/idempotência do motor Python.

## Decisions

1. Os wrappers verificarão o código do motor imediatamente. Em PowerShell,
   `exit $RC` ocorrerá antes do bloco de ferramentas; no Bash, o comportamento
   explícito substituirá a dependência indireta de `set -e`.
2. O Bash tentará Homebrew depois de `winget`/Chocolatey para preservar o
   comportamento existente em ambientes compatíveis.
3. A tabela do `doctor` carregará uma chave de versão explícita por ferramenta.
   Codex Security será consultado por executável direto ou por metadados locais
   do npm; o diagnóstico não deverá baixar pacotes.
4. Testes Python usarão subprocessos e comandos falsos em um `PATH` temporário.
   Isso valida os wrappers sem instalações globais. Testes estruturais cobrirão
   os casos que não podem executar nativamente em todas as plataformas.

## Risks / Trade-offs

- [Homebrew pode existir em Linux sem fórmula utilizável] → tratar retorno
  diferente de zero como falha parcial e manter orientação manual.
- [Descoberta do Codex Security varia conforme a instalação npm] → aceitar
  executável direto e leitura local de metadados, sem rede.
- [Testes estruturais não substituem execução real em todos os sistemas] →
  manter dry-run/doctor manuais e preparar CI multiplataforma.

## Migration Plan

A mudança é retrocompatível. Após os testes locais, os wrappers atualizados
podem substituir diretamente os atuais. O rollback consiste em reverter este
change, pois não há migração de dados ou formato.
