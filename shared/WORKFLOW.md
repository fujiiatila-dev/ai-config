# Padrão compartilhado de trabalho

Base comum para Claude Code, Codex, Gemini/Antigravity e demais ferramentas de
IA. É instalado como `WORKFLOW.md` dentro da pasta de configuração de cada
agente, e não apenas referenciado.

## Economia de contexto

- **RTK** reduz a saída dos comandos de shell. Onde houver hook configurado ele
  reescreve os comandos sozinho; onde não houver, prefixe com `rtk`.
- **Headroom** comprime o contexto que chega ao modelo através de um proxy
  local em `127.0.0.1`. Mantenha-o rodando quando estiver instalado.
- Leia só o trecho de arquivo de que precisa. Prefira `grep`/`rg` a despejar
  arquivos inteiros no contexto.

## Qualidade

Antes de encerrar uma entrega, rode a auditoria a partir da raiz do projeto com
`PYTHONUTF8=1`:

```bash
aurum check .
```

Meta: score ≥ 70%. Corrija as falhas com conteúdo real — teste que testa algo,
README com exemplo que roda. Nunca crie arquivo vazio só para passar no check.
Checks que não se aplicam ao tipo do projeto devem ser listados como ignorados,
com uma linha de justificativa cada.

No Claude Code isso está empacotado na skill `qualidade`.

## Precedência das instruções

O arquivo de instruções do projeto (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md` ou
equivalente) vence este padrão sempre que houver divergência. Leia-o antes de
alterar qualquer arquivo.

## Segurança

Não versione nem traga para o contexto: tokens, chaves de API, credenciais,
histórico de sessões, bancos de memória ou caminhos absolutos da máquina.
Permissões específicas de um projeto ficam no `settings.local.json` daquela
máquina, nunca no repositório de configuração.

## Comunicação

Ao concluir, informe o resultado, os arquivos alterados, as validações que
foram de fato executadas e o que ficou de fora. Não declare uma integração como
pronta sem ter testado a configuração correspondente.
