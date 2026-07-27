# Padrão compartilhado de trabalho

Estas regras são a base comum para Claude Code, Codex, Gemini/Antigravity e
outras ferramentas de IA.

## Contexto e ferramentas

- Use RTK para comandos de shell quando o ambiente o disponibilizar.
- Mantenha o Headroom localmente ativo para compressão de contexto.
- Preserve a intenção do usuário, trabalhando de forma incremental e verificável.
- Não exponha credenciais, tokens, históricos, bancos de memória ou caminhos absolutos.

## Qualidade

Antes de finalizar uma entrega em um projeto, execute `aurum check .` com
`PYTHONUTF8=1` e busque score mínimo de 70%. Corrija falhas relevantes com
conteúdo real e justifique checks ignorados por não se aplicarem ao projeto.

Respeite o `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` ou equivalente encontrado no
projeto antes de alterar arquivos.

## Comunicação

Informe o resultado, os arquivos alterados, as validações executadas e
qualquer limitação restante. Não declare uma integração como concluída sem
testar a configuração correspondente.
