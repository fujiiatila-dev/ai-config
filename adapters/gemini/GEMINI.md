# Gemini — configuração compartilhada

O padrão de trabalho abaixo é incorporado aqui pelo instalador a partir de
`shared/WORKFLOW.md`, a fonte única no repositório ai-config.

<!-- ai-config:include shared/WORKFLOW.md -->

## Sincronização

Antes de sincronizar, valide o checkout (`./install.sh --validate` ou
`.\install.ps1 --validate`) e revise o `--dry-run`. A instalação efetiva repete
o preflight antes de escrever no perfil do Gemini.

O Antigravity não lê este arquivo: ele recebe o mesmo padrão como regra
`always_on` em `~/.gemini/config/rules/ai-config.md` e as skills em
`~/.gemini/config/skills/`.

Quando o OpenSpec for inicializado manualmente para este cliente, use
`openspec init --tools gemini`. Não copie credenciais, histórico, memória ou
permissões específicas de projeto para arquivos versionados.
