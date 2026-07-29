# Mapa de compatibilidade

Origem no repositório → destino na máquina, e como cada um é mesclado.

| Fonte versionada | Instalado em | Merge |
| --- | --- | --- |
| `claude/settings.json` | `~/.claude/settings.json` | JSON, chave a chave |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | bloco `ai-config` |
| `claude/RTK.md` | `~/.claude/RTK.md` | bloco `ai-config` |
| `claude/statusline.py` | `~/.claude/statusline.py` | arquivo (pergunta se diferir) |
| `claude/agents/` | `~/.claude/agents/` | por arquivo |
| `claude/skills/` | `~/.claude/skills/` | por arquivo |
| `shared/WORKFLOW.md` | `~/.claude/WORKFLOW.md` | bloco `ai-config` |
| `shared/WORKFLOW.md` | `~/.codex/WORKFLOW.md` | bloco `ai-config` |
| `shared/WORKFLOW.md` | `~/.gemini/WORKFLOW.md` | bloco `ai-config` |
| `adapters/codex/AGENTS.md` | `~/.codex/AGENTS.md` | bloco `ai-config` |
| `adapters/codex/config.toml.example` | `~/.codex/config.toml` | TOML, por seção/chave |
| `adapters/gemini/GEMINI.md` | `~/.gemini/GEMINI.md` | bloco `ai-config` |
| `adapters/rtk/filters.toml` | `~/.config/rtk/filters.toml` | TOML, por seção/chave |
| `versions.json` | — | lido por `--doctor` como referência |

## Skills desta configuração

| Skill | Agente | Finalidade |
| --- | --- | --- |
| `qualidade` | Claude Code | Auditoria de qualidade (aurum check, score ≥ 70%) |
| `impeccable` | Claude Code | Design e UX de interfaces frontend |
| `openspec` | Claude Code | Spec-Driven Development (especificação antes de codificar) |
| `security-audit` | Claude Code | Auditoria de segurança (Semgrep + Gitleaks + Trivy) |

## Agentes desta configuração

| Agente | Função | Automático via | Manual via |
| --- | --- | --- | --- |
| `openspec-engineer` | Ciclo SDD (propose→apply→archive) | Skill `openspec` | `/openspec-engineer` |
| `security-analyst` | Auditoria de segurança | Skill `security-audit` | `/security-analyst` |

Tanto skills quanto agentes são instalados apenas no Claude Code (sistema
nativo). Codex e Gemini recebem as instruções equivalentes via seus adapters
(`AGENTS.md`, `GEMINI.md`) e o `WORKFLOW.md` compartilhado.

Skills e agentes de OpenSpec e segurança também são referenciados nos adapters
do Codex e Gemini para manter o padrão compartilhado.

`WORKFLOW.md` é a única fonte do padrão de trabalho. `CLAUDE.md`, `AGENTS.md` e
`GEMINI.md` apontam para ele em vez de repetir as regras.

## Placeholders

`claude/settings.json` e `adapters/codex/config.toml.example` usam marcadores
que o instalador resolve na máquina de destino, para que o repositório não
carregue caminho absoluto de ninguém:

| marcador | vira |
| --- | --- |
| `{{PYTHON}}` | caminho do `python3`/`python` encontrado |
| `{{NODE}}` | caminho do `node` encontrado |
| `{{CLAUDE_HOME}}` | `CLAUDE_CONFIG_DIR` ou `~/.claude` |
| `{{HEADROOM_PORT}}` | `HEADROOM_PORT` ou `48731` |

Sempre com barra normal, inclusive no Windows — Node, Python e o shell aceitam.

## Fora do Git

Memória, sessões, credenciais, `settings.local.json`, permissões de projeto e
qualquer arquivo gerado por um cliente. O instalador não lê nem escreve nesses.
