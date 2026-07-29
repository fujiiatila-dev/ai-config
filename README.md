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

**Um comando faz tudo:** clona o repositório, instala a configuração (instruções,
skills, agentes, hooks) **e** as dependências externas (OpenSpec, Semgrep,
Gitleaks e Trivy) automaticamente.

No Windows PowerShell: `.\install.ps1` (mesmas flags).

Requer Python 3.9+ e Node.js — usados pelo instalador, status line e hooks.

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
./install.sh --skip-tools      # pula instalação de dependências externas
./install.sh --doctor           # verifica python, node e todas as ferramentas
```

Sem flags: **configuração + dependências**, num comando só.
Sem flags, cada conflito vira uma pergunta. Em sessão não interativa (CI, pipe)
o valor atual é sempre mantido.

Destinos, se você quiser mudá-los: `CLAUDE_CONFIG_DIR`, `CODEX_HOME`,
`GEMINI_HOME`, `RTK_CONFIG_DIR`, `HEADROOM_PORT`.

## Dependências externas

Nenhuma é obrigatória — o `install.sh` instala automaticamente as principais
(OpenSpec, Semgrep, Gitleaks). Use `--skip-tools` se quiser só a configuração.

### Instalação manual (alternativa)

Se preferir instalar por conta própria ou se a automação falhar:

| Ferramenta | Finalidade | Instalação |
| --- | --- | --- |
| **RTK** | Economia de saída do shell | `npm install -g rtk` ou `curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh \| sh` |
| **Headroom** | Compressão de contexto | `uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"` e `headroom init --global --memory claude` |
| **aurum** | Auditoria de qualidade | Canal interno FreedomAI |
| **OpenSpec** | Especificação SDD | `npm install -g @fission-ai/openspec@latest` |
| **Semgrep** | SAST de segurança | `pip install semgrep` |
| **Gitleaks** | Detecção de segredos | `winget install gitleaks` (Windows) / `brew install gitleaks` (macOS/Linux) |
| **Trivy** | SCA de dependências | `winget install aquasecurity.trivy` (Windows) / `brew install trivy` (macOS/Linux) |
| **Codex Security** | Segurança profunda p/ Codex | `npx @openai/codex-security login` (requer API key OpenAI) |

> O `install.sh` instala automaticamente: OpenSpec (npm), Semgrep (pip),
> Gitleaks e Trivy (winget/choco no Windows, brew no macOS/Linux).
> RTK, Headroom e aurum são instalados manualmente por serem opcionais.

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
