# RTK + Headroom — camadas de economia de tokens

São camadas complementares: o **RTK** reduz a saída dos comandos de terminal
antes que ela entre no contexto; o **Headroom** comprime o contexto que chega
ao modelo, através de um proxy local em `127.0.0.1`.

## RTK

Com o hook instalado (`rtk hook claude` em `PreToolUse`), os comandos de shell
são reescritos de forma transparente: `git status` vira `rtk git status`, sem
custo de tokens. Fora do hook, use o prefixo `rtk` você mesmo.

Estes comandos são do próprio RTK e devem ser chamados diretos, sem prefixo:

```bash
rtk gain              # quanto foi economizado
rtk gain --history    # histórico por comando
rtk discover          # oportunidades perdidas, lendo o histórico do Claude Code
rtk proxy <cmd>       # executa sem filtro, para depurar
rtk --version
```

⚠️ Colisão de nome: se `rtk gain` falhar, você provavelmente tem o
`reachingforthejack/rtk` (Rust Type Kit) no PATH em vez deste. Confira com
`which rtk`.

## Headroom

```bash
headroom doctor                                   # diagnóstico
headroom savings                                  # economia acumulada
headroom init --global --memory claude --port "${HEADROOM_PORT:-48731}"
headroom init --global --memory codex  --port "${HEADROOM_PORT:-48731}"
headroom proxy --port "${HEADROOM_PORT:-48731}"   # sobe o proxy local
```

⚠️ O padrão do headroom é `8787`; o do ai-config é `48731`. Passe `--port` no
`init` e no `proxy` sempre, para o roteamento dos agentes e o proxy ficarem na
mesma porta.

O proxy fica em loopback. Claude Code e Codex apontam para ele através de
`ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` quando estiver ativo.

Chaves de API, tokens e credenciais nunca entram no repositório de configuração.
