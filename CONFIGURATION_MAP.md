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
| `adapters/codex/AGENTS.md` | `~/.codex/AGENTS.md` | bloco `ai-config` com `WORKFLOW.md` incorporado (o Codex não expande `@arquivo`) |
| `adapters/codex/config.toml.example` | `~/.codex/config.toml` | TOML, por seção/chave |
| `adapters/codex/headroom.config.toml.example` | `~/.codex/headroom.config.toml` | perfil TOML opt-in, por seção/chave |
| `adapters/codex/windows.config.toml.example` | `~/.codex/config.toml` (só Windows) | TOML, por seção/chave; desliga `features.daemon_auto_start` |
| `adapters/codex/hooks.json` | `~/.codex/hooks.json` | JSON, hooks por matcher (`rtk hook codex`); hooks legados quebrados viram conflito |
| `adapters/codex/hooks.impeccable.json` | `~/.codex/hooks.json` | idem; só quando o build do Impeccable para Codex existe em `~/.agents/skills` |
| `claude/skills/openspec` | `~/.agents/skills/openspec` (Codex) e `~/.gemini/config/skills/openspec` (Antigravity) | por arquivo; skill neutra, servida aos três agentes |
| `claude/skills/qualidade` | `~/.agents/skills/qualidade` (Codex) e `~/.gemini/config/skills/qualidade` (Antigravity) | por arquivo; skill neutra, servida aos três agentes |
| `claude/skills/security-audit` | `~/.agents/skills/security-audit` (Codex) e `~/.gemini/config/skills/security-audit` (Antigravity) | por arquivo; skill neutra, servida aos três agentes |
| `claude/skills/impeccable` | `~/.claude/skills/impeccable` | só Claude; Codex e Antigravity usam o build próprio instalado pelo Impeccable |
| `adapters/gemini/antigravity-rule.md` | `~/.gemini/config/rules/ai-config.md` | frontmatter `always_on` + bloco `ai-config` |
| `HEADROOM.md` | documentação do modo opt-in e recuperação | somente documentação; não é instalado |
| `TOOLS.md` | guia de uso de cada ferramenta e dos avisos do `doctor` | somente documentação; não é instalado |
| — (gerado por `--ca-bundle`) | `~/.config/ai-config/ca-bundle.pem` | específico da máquina; nunca versionado nem persistido em variável global |
| `tools/recover_codex_sessions.py` | reparo explícito do estado local do Codex | somente sob comando; cria backup e não é executado pelo instalador |
| `adapters/gemini/GEMINI.md` | `~/.gemini/GEMINI.md` (Gemini CLI) | bloco `ai-config` com `WORKFLOW.md` incorporado |
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

Os templates usam marcadores que o instalador resolve na máquina de destino,
para que o repositório não carregue caminho absoluto de ninguém:

| marcador | vira |
| --- | --- |
| `{{PYTHON}}` | o Python que roda o instalador; nunca o alias `WindowsApps` da Microsoft Store |
| `{{NODE}}` | caminho do `node` encontrado |
| `{{CLAUDE_HOME}}` | `CLAUDE_CONFIG_DIR` ou `~/.claude` |
| `{{CODEX_HOME}}` | `CODEX_HOME` ou `~/.codex` |
| `{{HEADROOM}}` | caminho do executável Headroom encontrado para o perfil opt-in |
| `{{AGENTS_HOME}}` | `AGENTS_HOME` ou `~/.agents` (skills do Codex) |
| `{{AGENTS_HOME_WIN}}` | o mesmo, com barra invertida e nome curto 8.3 se houver espaço (comandos sem aspas no cmd e no PowerShell) |
| `{{HEADROOM_PORT}}` | `HEADROOM_PORT`, ou `runtime.headroom_port` em `versions.json`, ou `48731` |

Sempre com barra normal, inclusive no Windows — Node, Python e o shell aceitam.

## Fora do Git

Memória, sessões, credenciais, `settings.local.json`, permissões de projeto e
qualquer arquivo gerado por um cliente. O instalador não lê nem escreve nesses.
