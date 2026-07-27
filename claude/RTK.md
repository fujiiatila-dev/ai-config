# RTK + Headroom — instruções de contexto

O RTK reduz a saída dos comandos de terminal. O Headroom comprime o contexto que chega aos agentes através de um proxy local. São camadas complementares.

Use o prefixo `rtk` nos comandos de shell.

Claude Code e Codex devem apontar para o endereço loopback definido por `HEADROOM_PORT` quando o proxy local estiver ativo.

## RTK

```bash
rtk gain
rtk gain --history
rtk discover
rtk proxy <cmd>
rtk --version
```

## Headroom

```bash
headroom doctor
headroom savings
headroom proxy --port "${HEADROOM_PORT:-48731}"
```

Não coloque chaves de API, tokens ou credenciais neste repositório.
