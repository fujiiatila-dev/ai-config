# Gemini / Antigravity — configuração compartilhada

O padrão de trabalho é mantido em `WORKFLOW.md`, instalado na mesma pasta.
Leia-o antes de começar; ele é a fonte única para OpenSpec, qualidade,
segurança, RTK e Headroom.

@WORKFLOW.md

Antes de sincronizar, valide o checkout (`./install.sh --validate` ou
`.\install.ps1 --validate`) e revise o `--dry-run`. A instalação efetiva repete
o preflight antes de escrever no perfil do Gemini.

Quando o OpenSpec for inicializado manualmente para este cliente, use
`openspec init --tools gemini`. Não copie credenciais, histórico, memória ou
permissões específicas de projeto para arquivos versionados.
