# RTK + Headroom — camadas de economia de tokens

São camadas complementares: o **RTK** reduz a saída dos comandos de terminal
antes que ela entre no contexto; o **Headroom** comprime o contexto que chega
ao modelo, através de um proxy local em `127.0.0.1`.

## RTK

Com o hook instalado (`rtk hook claude` em `PreToolUse`, para `Bash` e
`PowerShell`), os comandos são reescritos de forma transparente: `git status`
vira `rtk git status`, sem custo de tokens. Prefixos como `cd x;` e
`$env:X='1';` são preservados. Pipelines (`cmd | Select-Object …`) e cmdlets
passam sem reescrita. Nesses casos, prefira o comando simples e deixe o RTK
filtrar. O hook respeita as permissões: só aprova sozinho o que já está na
allowlist.

Estes comandos são do próprio RTK e devem ser chamados diretos, sem prefixo:

```bash
rtk gain                  # quanto foi economizado
rtk gain --history        # histórico por comando
rtk discover              # oportunidades perdidas, lendo o histórico do Claude Code
rtk hook check "<cmd>"    # como o hook reescreveria um comando
rtk proxy <cmd>           # executa sem filtro, quando precisar da saída completa
```

⚠️ Colisão de nome: se `rtk gain` falhar, você provavelmente tem o
`reachingforthejack/rtk` (Rust Type Kit) no PATH em vez deste. Confira com
`where.exe rtk` ou `which -a rtk`.

## Headroom

```bash
headroom doctor                                  # diagnóstico somente leitura
headroom savings                                 # economia acumulada
HEADROOM_DISABLE_KOMPRESS=1 \
HEADROOM_DISABLE_KOMPRESS_FALLBACK=1 \
headroom wrap claude --port "${HEADROOM_PORT:-48731}" --tool-search true
```

Headroom é opt-in. Não use `headroom init --global`, deployments `init-user` ou
hooks de inicialização, e não persista `ANTHROPIC_BASE_URL`/`OPENAI_BASE_URL`.
Se o proxy degradar, encerre a sessão e reinicie `claude` diretamente. Para o
Codex, use apenas `codex --profile headroom`.

Com o modo automático do ai-config (`install --headroom-auto`), `claude` e
`codex` no terminal já passam pelo Headroom e caem para a conexão direta se o
proxy não responder. `AICONFIG_HEADROOM=off` desliga para a sessão do shell.

Se o proxy não sobe ou `uv`/`pip` falham com `CERTIFICATE_VERIFY_FAILED`, há
inspeção HTTPS (antivírus/proxy). Rode o `doctor` do ai-config e exporte
`SSL_CERT_FILE` **e** `REQUESTS_CA_BUNDLE` para o bundle gerado por
`install --ca-bundle`, só na sessão. Nunca desative a verificação TLS. Detalhes
em `TOOLS.md` e `HEADROOM.md` no repositório ai-config.

Chaves de API, tokens e credenciais nunca entram no repositório de configuração.
