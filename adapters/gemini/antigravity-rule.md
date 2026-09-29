# Antigravity — configuração compartilhada

Regra global instalada pelo ai-config em `~/.gemini/config/rules/`. O padrão
de trabalho abaixo vem de `shared/WORKFLOW.md`, a fonte única no repositório.

<!-- ai-config:include shared/WORKFLOW.md -->

## Skills

As skills `openspec`, `qualidade`, `security-audit` e `impeccable` ficam em
`~/.gemini/config/skills/`. Ative-as quando a tarefa pedir especificação,
auditoria de qualidade, auditoria de segurança ou trabalho de interface.

## RTK

O Antigravity não tem hook de reescrita instalado pelo ai-config. Para saídas
longas de `git`, testes ou builds, prefixe o comando com `rtk` (por exemplo,
`rtk git status`) e use `rtk proxy <cmd>` quando precisar da saída completa.
