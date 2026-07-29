# Gemini / Antigravity — configuração compartilhada

O padrão de trabalho está em `WORKFLOW.md`, instalado nesta mesma pasta
(`~/.gemini/WORKFLOW.md`). Leia-o antes de começar.

Resumo: use RTK para reduzir a saída do shell, Headroom como proxy local quando
o cliente aceitar endpoints compatíveis com Anthropic/OpenAI, e rode
`aurum check .` com `PYTHONUTF8=1` antes de encerrar uma entrega.

## OpenSpec

Use o OpenSpec para especificar mudanças antes de codificar (se o Gemini suportar
slash commands):

```bash
openspec init --tools gemini
```

## Auditoria de segurança

O Gemini usa a **skill `security-audit`** (mesma do Claude Code), baseada em
ferramentas 100% locais sem API key:

```bash
# Tríade completa
semgrep scan --config=auto --json .       # SAST
gitleaks detect --source .                 # Segredos
trivy fs --format json --scanners vuln .  # Dependências
```

Consulte `WORKFLOW.md` → seção Segurança para detalhes.

## Agentes de referência (Claude Code)

Os agentes abaixo vivem no Claude Code, mas suas instruções servem como
referência para qualquer agente:

| Agente | Função |
| --- | --- |
| `openspec-engineer` | Ciclo SDD completo (propose → apply → archive) |
| `security-analyst` | Auditoria de segurança (Semgrep + Gitleaks + Trivy) |

Não copie credenciais, histórico, memória local ou configuração de sessão para
o repositório de configuração.
