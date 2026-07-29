# Codex — configuração compartilhada

O padrão de trabalho está em `WORKFLOW.md`, instalado nesta mesma pasta
(`~/.codex/WORKFLOW.md`). Leia-o antes de começar.

Resumo: use RTK para reduzir a saída do shell, Headroom como proxy local de
compressão de contexto, e rode `aurum check .` com `PYTHONUTF8=1` antes de
encerrar uma entrega (meta: score ≥ 70%).

## OpenSpec

Use o OpenSpec para especificar mudanças antes de codificar:

```bash
openspec init --tools codex
```

Comandos via slash: `/opsx:propose`, `/opsx:apply`, `/opsx:archive`.
Veja `WORKFLOW.md` para o ciclo completo.

## Codex Security (auditoria de segurança)

O Codex tem suporte nativo ao **Codex Security** da OpenAI. Para usar:

```bash
# Autenticação (uma vez)
export OPENAI_API_KEY="sk-..."
# ou: npx codex-security login

# Scan do diretório atual
npx @openai/codex-security scan . \
  --json \
  --fail-on-severity high
```

### Variáveis de ambiente

| Variável | Finalidade |
| --- | --- |
| `OPENAI_API_KEY` ou `CODEX_API_KEY` | Chave de API para autenticação |
| `CODEX_SECURITY_STATE_DIR` | Diretório de estado dos scans (default: `$CODEX_HOME/state/plugins/codex-security/`) |

### Modo CI (GitHub Actions, pipelines)

```bash
npx @openai/codex-security scan . \
  --diff <base-sha> \
  --head <head-sha> \
  --json \
  --fail-on-severity high \
  --output-dir ./codex-security-results
```

Saídas disponíveis: JSON (`--json`), SARIF (`codex-security export --export-format sarif`),
e CSV (`--export-format csv`).

### ⚠️ Limitações

- Requer **API key OpenAI** (custo por scan, controlado por `--max-cost`)
- Processa o código na nuvem OpenAI (não aplicável para código sensível)
- Scan completo leva minutos (análise profunda com threat model)

## Agentes disponíveis no Claude Code

Os agentes especializados abaixo vivem no Claude Code, mas suas instruções
servem como referência para qualquer agente:

| Agente | Função | Como usar no Claude |
| --- | --- | --- |
| `openspec-engineer` | Ciclo SDD completo (propose→apply→archive) | `/openspec-engineer` ou skill `openspec` |
| `security-analyst` | Auditoria de segurança (Semgrep + Gitleaks + Trivy) | `/security-analyst` ou skill `security-audit` |

Para o Codex, os comandos equivalentes estão documentados na seção
**Codex Security** acima e no `WORKFLOW.md`.

O `AGENTS.md` do projeto vence este arquivo em caso de divergência.
