# ai-config

Configuração das ferramentas de IA do ambiente de trabalho — instruções,
skills, subagentes e as camadas de economia de tokens, especificação,
auditoria de qualidade e segurança. O mesmo padrão para Claude Code, Codex e
Gemini/Antigravity, em qualquer máquina.

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
mostra o que está faltando. Instale apenas o que for usar no seu fluxo.

### Economia de tokens

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

### Qualidade

**aurum** (auditoria de qualidade de projeto, usada pela skill `qualidade`) —
instale pelo canal interno do padrão FreedomAI.

### Especificação (Spec-Driven Development)

**OpenSpec** (especificação e planejamento antes de codificar, skills
`openspec` para Claude Code e `WORKFLOW.md` para todos os agentes):

```bash
npm install -g @fission-ai/openspec@latest
```

Compatível com Claude Code, Codex, Cursor, Copilot e mais 30+ assistentes.
Uso: `openspec init --tools claude` no projeto.

### Segurança (100% local, gratuito, sem API key)

Para Claude Code e Gemini (o Codex tem suporte nativo ao Codex Security):

**Semgrep** — SAST (análise estática de padrões inseguros):

```bash
pip install semgrep
```

**Gitleaks** — detecção de segredos e credenciais:

```bash
# macOS/Linux:
brew install gitleaks
# Windows (scoop):
scoop install gitleaks
```

**Trivy** — vulnerabilidades em dependências (opcional):

```bash
# macOS/Linux:
brew install trivy
# Windows (scoop):
scoop install trivy
```

**Codex Security** (OpenAI — para o agente Codex, requer API key):

```bash
npx @openai/codex-security login
# ou: export OPENAI_API_KEY="sk-..."
```

### Resumo

## Ferramentas e versões de referência

O `./install.sh --doctor` compara as versões instaladas na máquina com as
abaixo. Divergência gera aviso, nunca erro.

| Ferramenta | Finalidade | Versão ref. | Obrigatória? |
| --- | --- | --- | --- |
| **Python** | Instalador, status line, Semgrep | 3.14.4 | ✅ Sim |
| **Node.js** | Hooks, OpenSpec, Codex Security | 24.15.0 | ✅ Sim |
| **RTK** | Economia de saída do shell | 0.44.1 | Não |
| **Headroom** | Compressão de contexto (proxy local) | 0.32.1 | Não |
| **aurum** | Auditoria de qualidade (skill `qualidade`) | 0.1.0 | Não |
| **Claude Code** | Agente Claude CLI | 2.1.220 | Não |
| **Codex CLI** | Agente Codex CLI | 0.146.0 | Não |
| **git** | Controle de versão | — | Não |
| **OpenSpec** | Especificação SDD (skill `openspec`) | **1.7.0** | Recomendado |
| **Semgrep** | SAST de segurança (skill `security-audit`) | **1.172.0** | Recomendado |
| **Gitleaks** | Detecção de segredos (skill `security-audit`) | **8.30.1** | Recomendado |
| **Trivy** | SCA de dependências | 0.72.0 | Não |
| **Codex Security** | Segurança profunda p/ Codex | 0.1.1 | API key OpenAI |

```bash
# Para verificar o que está instalado na sua máquina
./install.sh --doctor
```

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
