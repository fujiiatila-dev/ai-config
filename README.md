# ai-config

Configuração das ferramentas de IA do ambiente de trabalho — instruções,
skills, subagentes e as camadas de economia de tokens e auditoria. O mesmo
padrão para Claude Code, Codex e Gemini/Antigravity, em qualquer máquina.

## Instalação

```bash
git clone https://github.com/fujiiatila-dev/ai-config.git
cd ai-config
./install.sh
```

No Windows PowerShell: `.\install.ps1` (mesmas flags).

Requer Python 3.9+ — usado pelo instalador e pelo status line. Nada mais.

### O instalador nunca sobrescreve nada em silêncio

| situação | o que acontece |
| --- | --- |
| a chave/arquivo não existe | é adicionada |
| existe e é igual | nada acontece |
| existe com valor diferente | **pergunta qual manter** |
| listas (`permissions`, `hooks`) | são unidas; nenhuma entrada é removida |

Rodar duas vezes seguidas não muda nada na segunda. Todo arquivo alterado é
copiado antes para `~/.claude/backups/ai-config-<timestamp>/`.

Arquivos de instrução (`CLAUDE.md`, `RTK.md`, `AGENTS.md`, `GEMINI.md`,
`WORKFLOW.md`) usam um bloco delimitado:

```markdown
<!-- ai-config:begin -->
...conteúdo gerenciado pelo repo...
<!-- ai-config:end -->
```

O que estiver fora do bloco é seu e nunca é tocado. Nas próximas instalações só
o miolo do bloco é atualizado.

### Flags

```bash
./install.sh --dry-run          # mostra o que faria, sem escrever
./install.sh --keep-existing    # em conflito, mantém sempre o valor atual
./install.sh --prefer-repo      # em conflito, usa sempre o valor do repo
./install.sh --yes              # não pergunta nada (= --keep-existing)
./install.sh --doctor           # verifica rtk, headroom, aurum, node e os CLIs
```

Sem flags, cada conflito vira uma pergunta. Em sessão não interativa (CI, pipe)
o valor atual é sempre mantido.

Destinos, se você quiser mudá-los: `CLAUDE_CONFIG_DIR`, `CODEX_HOME`,
`GEMINI_HOME`, `RTK_CONFIG_DIR`, `HEADROOM_PORT`.

## Dependências externas

Nenhuma é obrigatória — o ai-config instala e funciona sem elas, e `--doctor`
mostra o que está faltando.

**RTK** (reduz a saída do shell antes de virar contexto):

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
```

**Headroom** (comprime o contexto que chega ao modelo, via proxy local):

```bash
uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"
headroom init --global --memory claude
headroom init --global --memory codex
headroom proxy --port 48731
```

`48731` é só uma sugestão de porta; troque com `HEADROOM_PORT` se estiver
ocupada. Detalhes em [HEADROOM.md](HEADROOM.md).

**aurum** (auditoria de qualidade de projeto, usada pela skill `qualidade`) —
instale pelo canal interno do padrão FreedomAI.

## O que fica no repositório e o que não fica

Vai para o Git: instruções, skills, subagentes, hooks e um conjunto **portátil**
de permissões (`git`, `gh`, `npm`, `python3`, `rtk`, `aurum`, leitura de
arquivos…).

Nunca vai para o Git: tokens, credenciais, histórico de sessão, memória, e
permissões amarradas a uma máquina ou projeto (caminhos absolutos, `localhost:<porta>`,
scripts de um projeto só). Essas ficam no `settings.local.json` de cada máquina,
que o instalador não toca.

Veja [CONFIGURATION_MAP.md](CONFIGURATION_MAP.md) para o mapa completo de
origem → destino.
