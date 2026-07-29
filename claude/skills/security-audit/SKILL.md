---
name: security-audit
description: Auditoria de segurança para o código-fonte do projeto. Usa Semgrep (SAST) e Gitleaks (segredos) localmente, sem API keys. Roda antes de entregar uma mudança, complementando a skill qualidade. Alternativa gratuita e local ao Codex Security da OpenAI para agentes que não são Codex.
version: 1.0.0
user-invocable: true
argument-hint: "[scan|secrets|deps|full|ci] [target]"
---

# Auditoria de segurança (Semgrep + Gitleaks + Trivy)

Tríade de ferramentas **100% locais, gratuitas e sem API key** para auditar a
segurança do código-fonte. Alternativa direta ao Codex Security para Claude
Code e Gemini.

## Pré-requisitos

```bash
# Semgrep — SAST (análise estática de padrões inseguros)
pip install semgrep
# ou: brew install semgrep, ou curl do release

# Gitleaks — detecção de segredos e credenciais
# macOS/Linux:
brew install gitleaks
# Windows (scoop):
scoop install gitleaks

# Trivy — vulnerabilidades em dependências (opcional, recomendado)
# macOS/Linux:
brew install trivy
# Windows:
scoop install trivy
```

## Comandos

### `scan [caminho]` — varredura SAST completa

```bash
semgrep scan --config=auto --json <caminho> 2>/dev/null
```

- Usa `--config=auto` para regras recomendadas pela comunidade
- Suporta Python, JavaScript, TypeScript, Go, Java e dezenas de outras
- Saída JSON estruturada que o agente pode parsear para sugerir correções

### `secrets [caminho]` — detecção de segredos

```bash
gitleaks detect --source <caminho> --verbose
```

- Varre todo o repositório por tokens, chaves de API, senhas, etc.
- Usa heurística de entropia + regex patterns
- Ideal como pre-commit hook ou antes de cada entrega

### `deps [caminho]` — varredura de dependências

```bash
trivy fs --format json --scanners vuln <caminho> 2>/dev/null
```

- Identifica CVEs em `package.json`, `requirements.txt`, `go.mod`, etc.
- Alternativa: `npm audit` para projetos Node, `pip audit` para Python

### `full [caminho]` — tríade completa

Roda scan + secrets + deps em sequência e compila um relatório unificado.

### `ci` — modo CI (diff-aware)

Varre apenas arquivos modificados vs um branch base:

```bash
git diff --name-only origin/main...HEAD | xargs semgrep scan --config=auto --json 2>/dev/null
gitleaks detect --source . --log-opts=origin/main...HEAD
```

## Relatório de saída

Para qualquer comando, produza um relatório Markdown neste formato:

```markdown
# Relatório de Segurança — <tipo> — <timestamp>

## Resumo
- Total de achados: N
- Críticos/Alta: N | Médios: N | Baixos: N
- Segredos encontrados: N

## Achados por severidade

### 🔴 Críticos
1. **Título** — arquivo:linha
   - Descrição: o que o padrão indica
   - Risco: exploração remota / vazamento de dados / ...
   - Correção sugerida: diff ou instrução

### 🟡 Médios
...

### 🔵 Baixos / Informativos
...

## Segredos (Gitleaks)
- [ ] arquivo:linha — tipo de segredo (API key, token JWT, ...)

## Dependências (Trivy)
- pacote@versão → CVE-XXXX-XXXX (severidade) — upgrade para >= X.Y.Z

## Recomendações
1. Corrigir agora: [itens críticos]
2. Corrigir na sprint: [itens médios]
3. Agendar: [itens baixos]
```

## Integração com o workflow

No ciclo OpenSpec, rode a auditoria de segurança:

- **Antes do archive**: `security-audit full .` — garante que a mudança não
  introduz vulnerabilidades
- **Em CI**: `security-audit ci` no pipeline de PR
- **Junto da qualidade**: `aurum check .` + `security-audit full .` antes de
  entregar

## Limitações vs Codex Security

| Funcionalidade | Semgrep + Gitleaks | Codex Security |
|---|---|---|
| Threat model | ❌ Não gera | ✅ Gera automático |
| Validação com sandbox | ❌ Não valida exploit | ✅ Valida em sandbox |
| PR de correção automático | ❌ Sugestão manual | ✅ Gera PR |
| Custo | ✅ Gratuito, 100% local | 💰 Requer API key OpenAI |
| Privacidade | ✅ Código nunca sai da máquina | ☁️ Processado na nuvem OpenAI |
| Velocidade | ✅ Segundos | ⏱️ Minutos (análise profunda) |
