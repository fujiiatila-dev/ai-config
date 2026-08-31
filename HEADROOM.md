# Headroom

Camada local de compressão de contexto, complementar ao RTK: o RTK encolhe a
saída dos comandos antes de virar contexto, o Headroom comprime o contexto que
chega ao modelo.

## Instalação

```bash
uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"
headroom init --global --memory claude --port "${HEADROOM_PORT:-48731}"
headroom init --global --memory codex  --port "${HEADROOM_PORT:-48731}"
headroom proxy --port "${HEADROOM_PORT:-48731}"
headroom doctor
```

> ⚠️ **O `--port` no `init` é obrigatório.** O padrão do headroom é `8787`; o
> padrão do ai-config é `48731`. Sem o `--port`, o `headroom init` grava `8787`
> no roteamento dos agentes (e no manifest em `~/.headroom/`), enquanto o proxy
> sobe em `48731` — o Codex fica sem conexão e aparece o erro de stream
> desconectado. Passe sempre `--port "${HEADROOM_PORT:-48731}"` no `init` e no
> `proxy`.
>
> Já rodou o init com a porta errada? Repita com a porta certa (o init
> reescreve o roteamento): `headroom init --global --memory codex --port
> "${HEADROOM_PORT:-48731}"`.

Estes comandos são seus, não do `install.sh`. O instalador do ai-config **não**
roda `headroom init` nem sobe o proxy: ele escreve a seção
`[model_providers.headroom]`, instala o hook portátil do Codex e, quando o
executável está disponível, garante que a deploy `init-user` esteja
`running`/`Healthy: yes` usando `headroom install start --profile init-user` se
necessário. Se Headroom não estiver instalado, a configuração continua sendo
aplicada e o instalador emite um aviso; use `./install.sh --doctor` para
conferir.

O hook `SessionStart` chama o mesmo healthcheck antes de garantir o marker
`headroom-init-codex`. O timeout é de 60 segundos para acomodar o cold start de
5–10 segundos no Windows.

## Apontando os agentes para o proxy

```bash
export HEADROOM_PORT=48731
export ANTHROPIC_BASE_URL="http://127.0.0.1:${HEADROOM_PORT}"
export OPENAI_BASE_URL="http://127.0.0.1:${HEADROOM_PORT}/v1"
```

Veja `.env.example`. O proxy fica em `127.0.0.1` — não o exponha na rede.

## Limites

Os arquivos que o `headroom init` escreve podem conter permissões, caminhos e
preferências da máquina. Não os copie para este repositório.

Credenciais de provedor vêm do ambiente ou do login do próprio agente, nunca de
arquivo versionado.
