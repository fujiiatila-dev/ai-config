# Codex — configuração compartilhada

O Codex não expande `@arquivo` em `AGENTS.md`. Por isso o padrão de trabalho
abaixo é incorporado aqui pelo instalador a partir de `shared/WORKFLOW.md`, a
fonte única no repositório ai-config.

<!-- ai-config:include shared/WORKFLOW.md -->

## RTK no Codex

O hook `rtk hook codex` (em `~/.codex/hooks.json`) condensa a saída dos
comandos de shell. Rode os comandos normalmente, sem prefixar `rtk`, e trate a
saída condensada como resultado completo. Agrupe comandos relacionados numa
chamada. Use `rtk proxy <cmd>` só quando o resultado vier vazio sem motivo,
contradizer o código de saída ou estiver ilegível.

## Skills

As skills `openspec`, `qualidade`, `security-audit` e `impeccable` ficam em
`~/.agents/skills`. Use-as pelo nome quando a tarefa pedir especificação,
auditoria de qualidade, auditoria de segurança ou trabalho de interface.

## Configuração do Codex

Antes de sincronizar, valide o checkout (`./install.sh --validate` ou
`.\install.ps1 --validate`) e revise o `--dry-run`. A instalação efetiva repete
o preflight antes de escrever no perfil do Codex.

No Windows, o baseline desliga `features.daemon_auto_start`: o daemon
compartilhado abre uma janela de console para cada hook e consulta ao git
(openai/codex#44768). Sessões do terminal usam o servidor embutido.

Atualizações globais exigem `--update-tools`. O hardening exige
`--harden-codex`, cria backup antes da escrita e remove somente uma confiança
exata na raiz do perfil quando a seção contém apenas `trust_level`. Confianças
de projetos específicos, credenciais, sessões, memória e arquivos locais não
são copiados para este repositório.
