# Padrão compartilhado de trabalho

Base comum para Claude Code, Codex, Gemini/Antigravity e demais ferramentas de
IA. É instalado como `WORKFLOW.md` dentro da pasta de configuração de cada
agente, e não apenas referenciado.

## Economia de contexto

- **RTK** reduz a saída dos comandos de shell. Onde houver hook configurado ele
  reescreve os comandos sozinho; onde não houver, prefixe com `rtk`.
- **Headroom** comprime o contexto que chega ao modelo através de um proxy
  local em `127.0.0.1`. Mantenha-o rodando quando estiver instalado.
- Leia só o trecho de arquivo de que precisa. Prefira `grep`/`rg` a despejar
  arquivos inteiros no contexto.

## Especificação com OpenSpec

Antes de codificar uma nova funcionalidade, use o **OpenSpec** para alinhar o
que será construído. O fluxo é:

```bash
# Certifique-se de ter o OpenSpec instalado globalmente
npm install -g @fission-ai/openspec@latest

# Inicialize no projeto (uma vez), usando o cliente em execução
cd <projeto>
openspec init --tools claude  # Claude Code
openspec init --tools codex   # Codex
openspec init --tools gemini  # Gemini/Antigravity
```

Use somente a linha correspondente ao cliente atual. Os comandos equivalentes
em PowerShell são os mesmos; apenas a definição de variáveis de ambiente muda
de sintaxe. No Claude Code, os comandos `/opsx:*` ficam disponíveis após o
`init`; no Codex e no Gemini, use o fluxo equivalente suportado pelo cliente.

### Ciclo propose → design → tasks → apply → archive

1. **`/opsx:propose <nome-da-feature>`** — Gera proposal, delta specs, design e
   tasks em um passo. O humano revisa antes de seguir.
2. **`/opsx:apply`** — O agente implementa item por item do `tasks.md`,
   executando testes e marcando checkboxes.
3. **`/opsx:update <nome> - <detalhe>`** — Ajusta os artefatos de
   planejamento sem mexer no código, se algo mudou.
4. **`/opsx:archive`** — Valida conclusão, sincroniza delta specs com o
   `specs/` principal e arquiva o change folder.

Para sincronizar este repositório, o instalador usa o mesmo motor nos dois
shells:

```bash
./install.sh --dry-run
./install.sh --update-tools --harden-codex --keep-existing
./install.sh --doctor
```

```powershell
.\install.ps1 --dry-run
.\install.ps1 --update-tools --harden-codex --keep-existing
.\install.ps1 --doctor
```

`--update-tools` é opt-in e atualiza somente OpenSpec, Semgrep, Gitleaks e
Trivy para as referências de `versions.json`. `--harden-codex` aplica o
baseline de sandbox/aprovação com backup; `--skip-tools` e `--dry-run` não
executam gerenciadores de pacotes.

Os artefatos ficam em `openspec/`:

```text
openspec/
├── specs/                  # Especificação permanente (fonte da verdade)
├── changes/                # Mudanças ativas
│   └── minha-feature/
│       ├── .openspec.yaml
│       ├── proposal.md     # Intenção e escopo
│       ├── specs/          # Delta specs (ADDED/MODIFIED/REMOVED)
│       ├── design.md       # Arquitetura técnica
│       └── tasks.md        # Checklist de implementação
└── config.yaml             # Contexto tech stack + regras
```

No Claude Code isso está empacotado na skill `openspec`. O projeto pode ter um
`openspec/config.yaml` com regras de especificação específicas.

## Qualidade

Antes de encerrar uma entrega, rode a auditoria a partir da raiz do projeto com
`PYTHONUTF8=1`:

```bash
PYTHONUTF8=1 aurum check .
```

No PowerShell:

```powershell
$env:PYTHONUTF8 = '1'
aurum check .
```

Meta: score ≥ 70%. Corrija as falhas com conteúdo real — teste que testa algo,
README com exemplo que roda. Nunca crie arquivo vazio só para passar no check.
Checks que não se aplicam ao tipo do projeto devem ser listados como ignorados,
com uma linha de justificativa cada.

No Claude Code isso está empacotado na skill `qualidade`.

## Segurança

### Política base

Não versione nem traga para o contexto: tokens, chaves de API, credenciais,
histórico de sessões, bancos de memória ou caminhos absolutos da máquina.
Permissões específicas de um projeto ficam no `settings.local.json` daquela
máquina, nunca no repositório de configuração.

### Auditoria de segurança

Cada agente tem sua ferramenta de auditoria de segurança primária:

| Agente | Ferramenta | Como ativar |
| --- | --- | --- |
| **Claude Code** | `semgrep` + `gitleaks` (skill `security-audit`) | Skill empacotada; use `/security-audit` |
| **Codex** | `codex-security` | `npx @openai/codex-security scan .` (requer `OPENAI_API_KEY` ou login) |
| **Gemini** | `semgrep` + `gitleaks` (mesmo que Claude) | Via skill ou comando direto |

**Tríade de verificações manuais** (qualquer agente, antes de entregar):

### Bash

```bash
gitleaks detect --source .
semgrep scan --config=auto --json .
trivy fs --format json --scanners vuln .
```

### PowerShell

```powershell
gitleaks detect --source .
semgrep scan --config=auto --json .
trivy fs --format json --scanners vuln .
```

Esses comandos varrem, respectivamente, segredos, padrões SAST e CVEs em
dependências (`package.json`, `requirements.txt` etc.). Use `npm audit` ou
`pip audit` como alternativa para o último item.

### Codex Security (OpenAI)

Para o agente Codex, com uma chave `OPENAI_API_KEY` configurada:

### Bash

```bash
BASE_SHA=origin/main
npx @openai/codex-security scan . \
  --diff "$BASE_SHA" \
  --json \
  --fail-on-severity high \
  --output-dir ./codex-security-results
```

### PowerShell

```powershell
$baseSha = 'origin/main'
npx @openai/codex-security scan . --diff $baseSha --json --fail-on-severity high --output-dir ./codex-security-results
```

Saídas: JSON estruturado, SARIF (integrável com GitHub Code Scanning) e
relatório Markdown. O diretório de estado usa `$CODEX_SECURITY_STATE_DIR` ou
`$CODEX_HOME/state/plugins/codex-security/scans/<repo>`.

Consulte a skill `security-audit` (Claude/Gemini) ou a documentação do Codex
Security (Codex) para detalhes.

## Precedência das instruções

O arquivo de instruções do projeto (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md` ou
equivalente) vence este padrão sempre que houver divergência. Leia-o antes de
alterar qualquer arquivo.

## Comunicação

Ao concluir, informe o resultado, os arquivos alterados, as validações que
foram de fato executadas e o que ficou de fora. Não declare uma integração como
pronta sem ter testado a configuração correspondente.
