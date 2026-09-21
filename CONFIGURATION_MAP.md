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
| `adapters/codex/hooks.json` | `~/.codex/hooks.json` | JSON, hooks unidos por matcher/comando |
| `tools/headroom_healthcheck.py` | `~/.codex/headroom_healthcheck.py` | arquivo (pergunta se diferir) |
| `adapters/gemini/GEMINI.md` | `~/.gemini/GEMINI.md` | bloco `ai-config` |
| `adapters/rtk/filters.toml` | `~/.config/rtk/filters.toml` | TOML, por seção/chave |
| `versions.json` | — | lido por `--doctor` e por `--update-tools` como catálogo |

## Preflight do repositório

Antes de qualquer instalação, o motor executa `validate` em modo somente
leitura. Ele confirma que as fontes deste mapa existem, que os arquivos JSON e
TOML são válidos, que os placeholders são conhecidos, que todas as versões têm
uma checagem no `doctor` e que os templates não carregam caminhos, credenciais,
estado de sessão ou endpoints expostos.

```bash
./install.sh --validate
./install.sh --validate --json
```

```powershell
.\install.ps1 --validate
.\install.ps1 --validate --json
```

O relatório JSON tem `schema_version: 1`, caminhos relativos e não reproduz
valores sensíveis. O preflight não instala ferramentas nem inicia Headroom;
verificações indisponíveis aparecem em `skipped`.

## Operação segura

`--update-tools` atualiza somente OpenSpec, Semgrep, Gitleaks e Trivy, usando
as versões declaradas no catálogo. Sem essa flag, ferramentas já instaladas
são preservadas; `--skip-tools` e `--dry-run` não executam gerenciadores.

`--harden-codex` aplica `sandbox_mode = "workspace-write"`,
`approval_policy = "on-request"`, `approvals_reviewer = "user"` e
`[windows].sandbox = "unelevated"` com backup. A remoção de confiança é
limitada à seção exata da raiz do perfil que contenha somente
`trust_level = "trusted"`; projetos específicos permanecem intactos.

## Skills desta configuração

| Skill | Agente | Finalidade |
| --- | --- | --- |
| `qualidade` | Claude Code | Auditoria de qualidade (`aurum check`, score ≥ 70%) |
| `impeccable` | Claude Code | Design e UX de interfaces frontend |
| `openspec` | Claude Code | Spec-Driven Development antes de codificar |
| `security-audit` | Claude Code | Semgrep + Gitleaks + Trivy |

## Agentes especializados

| Agente | Função |
| --- | --- |
| `openspec-engineer` | Ciclo propose → apply → archive |
| `security-analyst` | Auditoria local de segurança |

As skills e os agentes especializados são nativos do Claude Code. Codex e
Gemini recebem o mesmo padrão por seus adapters e pelo `WORKFLOW.md`
compartilhado.

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
| `{{CODEX_HOME}}` | `CODEX_HOME` ou `~/.codex` |
| `{{HEADROOM}}` | caminho do executável Headroom encontrado |
| `{{HEADROOM_PORT}}` | `HEADROOM_PORT`, ou `runtime.headroom_port` em `versions.json`, ou `48731` |

Sempre com barra normal, inclusive no Windows — Node, Python e o shell aceitam.

## Fora do Git

Memória, sessões, credenciais, `settings.local.json`, permissões de projeto e
qualquer arquivo gerado por um cliente. O instalador não lê nem escreve nesses.
