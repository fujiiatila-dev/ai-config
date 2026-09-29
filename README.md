# ai-config

Configuração das ferramentas de IA do ambiente de trabalho — instruções,
skills, subagentes e as camadas de economia de tokens, especificação,
auditoria de qualidade e segurança. O mesmo padrão para Claude Code, Codex e
Gemini/Antigravity, em qualquer máquina.

## O que vem no repositório

| Ferramenta | Para que serve | Como você usa |
| --- | --- | --- |
| **RTK** | compacta a saída do shell (git, npm, pytest…) | automático via hook; `rtk gain` mostra a economia |
| **Headroom** | comprime o contexto enviado ao modelo | opt-in: `headroom wrap claude` ou `codex --profile headroom` |
| **OpenSpec** | especificação antes do código | `/opsx:propose`, `/opsx:apply`, `/opsx:archive` |
| **Semgrep, Gitleaks, Trivy** | SAST, segredos e CVEs | skill `security-audit` |
| **aurum** | gate de qualidade (score ≥ 70%) | skill `qualidade` |
| **Impeccable** | design e revisão de UI | skill `impeccable` |
| **Subagentes** | `openspec-engineer`, `security-analyst`, `qa`, `tester`… | o Claude Code delega |
| **Status line** | modelo, branch e pasta no rodapé | automático |

O instalador entrega as mesmas regras e skills ao **Claude Code**, ao **Codex**
(`~/.codex`, `~/.agents/skills`) e ao **Antigravity** (`~/.gemini/config`).

**[TOOLS.md](TOOLS.md) é o guia de uso**: comandos do dia a dia, o que cada
aviso do `--doctor` significa e como resolver os problemas conhecidos, como
TLS interceptado por antivírus, statusLine vazia no Windows, Headroom que não
sobe e janelas de terminal abrindo no Codex.

## Instalação

```bash
git clone https://github.com/fujiiatila-dev/ai-config.git
cd ai-config
./install.sh
```

**Um comando faz tudo:** instala a configuração completa de Claude Code,
Codex e Gemini/Antigravity e prepara OpenSpec, Semgrep, Gitleaks e Trivy.

No Windows PowerShell: `.\install.ps1` (mesmas flags).

Requer Python 3.10+ e Node.js — usados pelo instalador, status line, hooks e
OpenSpec.

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
./install.sh --skip-tools       # sincroniza só configurações
./install.sh --update-tools     # atualiza ferramentas gerenciadas para versions.json
./install.sh --harden-codex      # aplica baseline seguro do Codex com backup
./install.sh --validate          # valida o checkout sem escrever nada
./install.sh --validate --json   # relatório estruturado para CI
./install.sh --doctor           # verifica runtimes, agentes e ferramentas
./install.sh --ca-bundle        # bundle de CA para Headroom/uv/pip atrás de inspeção TLS
./install.sh --headroom claude  # sessão Headroom para o Claude (ou `proxy` para o Codex)
```

No Windows, use as mesmas opções com `.\install.ps1`. `--update-tools` é
opt-in: a instalação normal somente prepara ferramentas ausentes. `--harden-codex`
força os defaults de sandbox/aprovação e remove apenas uma confiança ampla
exata na raiz do perfil quando a seção não contém outras chaves.

### Fluxo recomendado

Para alterar ou distribuir esta configuração, siga as etapas nesta ordem:

```text
validate → dry-run → apply → doctor → security → quality → commit
```

1. `validate` verifica contratos, fontes, JSON/TOML, placeholders, wrappers,
   versões e higiene de segurança sem escrever, iniciar serviços ou instalar
   ferramentas.
2. `dry-run` mostra o merge específico da máquina e os conflitos que serão
   preservados ou perguntados.
3. `apply` é a instalação normal, com backup antes de cada escrita. Ela executa
   o mesmo preflight automaticamente e para antes do primeiro backup se a
   origem estiver inválida.
4. `doctor` verifica runtimes, ferramentas, Headroom e o baseline local do
   Codex; ele não substitui o `validate`.
5. `security` executa as auditorias completas configuradas (`security-audit`,
   Gitleaks, Semgrep, Trivy ou Codex Security).
6. `quality` executa `aurum check .`; só então a mudança deve ser commitada.

O comando `validate` retorna `0` quando o checkout passa e `1` quando há erro.
`--json` produz um único documento com `schema_version`, `status`, contagens,
erros, avisos, verificações ignoradas e checks executados. Ausência de Bash no
Windows é registrada como `skipped`; a validação Bash é coberta pelos runners
Unix do CI.

Sem flags: **configuração + ferramentas recomendadas ausentes**, num comando só.
Sem flags, cada conflito vira uma pergunta. Em sessão não interativa (CI, pipe)
o valor atual é sempre mantido.

Destinos, se você quiser mudá-los: `CLAUDE_CONFIG_DIR`, `CODEX_HOME`,
`GEMINI_HOME`, `RTK_CONFIG_DIR`, `HEADROOM_PORT`.

Headroom é opt-in e nunca é iniciado nem injetado globalmente pelo instalador.
Veja [`HEADROOM.md`](HEADROOM.md) para sessões isoladas, mitigação do
Kompress/ONNX, perfil Codex sem WebSocket e recuperação de instalações legadas.

## Recuperação de sessões locais do Codex

Se conversas intactas desaparecerem da barra lateral após uma migração de
projetos, audite primeiro sem escrever nada:

```bash
python tools/recover_codex_sessions.py --require-session <UUID>
```

Para reparar, acrescente `--apply`. A ferramenta cria um backup transacional
dos bancos e do estado global em `~/.codex/backups/session-recovery-*`,
reconstrói `session_index.jsonl` a partir de todos os rollouts preservados e
associa as conversas existentes à raiz de projeto mais específica. Registros
suplementares, como títulos personalizados, são mantidos. Reinicie o aplicativo
Codex uma vez após a aplicação para recarregar a barra lateral.

Se `codex resume` falhar com `Model provider 'headroom' not found`, migre também
o provider salvo nas sessões antigas. Os JSONL afetados são copiados
integralmente para o mesmo backup antes da alteração:

```bash
python tools/recover_codex_sessions.py --apply \
  --replace-provider headroom=openai \
  --require-session <UUID>
```

O reparo não copia histórico para o repositório e não converte rollouts
técnicos de execuções/subagentes em conversas de usuário.

## Dependências externas

As configurações funcionam sem ferramentas externas, mas o instalador prepara
automaticamente as recomendadas. Use `--skip-tools` para o modo config-only.

| Ferramenta | Finalidade | Preparação automática |
| --- | --- | --- |
| **OpenSpec** | Spec-Driven Development | npm |
| **Semgrep** | SAST de segurança | pip do Python atual |
| **Gitleaks** | Detecção de segredos | winget, Chocolatey ou Homebrew |
| **Trivy** | CVEs em dependências | winget, Chocolatey ou Homebrew |

Se a automação falhar, consulte as versões em `versions.json` e use
`npm install -g @fission-ai/openspec@<versão>`,
`python -m pip install --user semgrep==<versão>` e o gerenciador do sistema
para Gitleaks/Trivy (`winget`, `choco` ou `brew`). O modo `--update-tools`
mostra e executa esses comandos somente quando solicitado.

RTK, Headroom e aurum continuam opcionais e são instalados pelos seus canais
próprios (veja [TOOLS.md](TOOLS.md)). Codex Security exige autenticação e nunca
é instalado automaticamente.

Se `pip`, `uv` ou `winget` falharem com `CERTIFICATE_VERIFY_FAILED`,
`UnknownIssuer` ou `0x8a15005e`, há inspeção HTTPS na máquina: rode
`--doctor` e siga [TOOLS.md > TLS interceptado](TOOLS.md#tls-interceptado).

## Ferramentas e versões de referência

O `./install.sh --doctor` compara as versões locais com estas referências
(verificadas em 2026-09-29; a fonte é `versions.json`). Divergências geram
aviso, não impedem a instalação.

| Ferramenta | Versão ref. |
| --- | --- |
| Python | 3.14.7 |
| Node.js | 24.21.0 |
| RTK | 0.50.0 |
| Headroom | 0.39.1 |
| aurum | 0.4.0 |
| Claude Code | 2.1.285 |
| Codex CLI | 0.159.1 |
| OpenSpec | 1.13.2 |
| Semgrep | 1.178.0 |
| Gitleaks | 8.30.1 |
| Trivy | 0.74.0 |
| Codex Security | 0.1.31 |

O `doctor` também valida `HEADROOM_PORT`, consulta
`http://127.0.0.1:<porta>/readyz`, detecta rotas e hooks Headroom persistentes e
alerta sobre sandbox/aprovação inseguras no Codex sem alterar arquivos nem
iniciar processos. Também aponta statusLine com alias da Microsoft Store, hook
RTK ausente, allowlist ampla (`Bash(rtk:*)`) e inspeção HTTPS, com a ação
corretiva de cada um.

## O que fica no repositório e o que não fica

Vai para o Git: instruções, skills, subagentes, hooks e um conjunto **portátil**
de permissões (`git`, `gh`, `npm`, `python3`, subcomandos de leitura do `rtk` e
do `headroom`, `aurum`, leitura de arquivos…).

Nunca vai para o Git: tokens, credenciais, histórico de sessão, memória, e
permissões amarradas a uma máquina ou projeto (caminhos absolutos, `localhost:<porta>`,
scripts de um projeto só). Essas ficam no `settings.local.json` de cada máquina,
que o instalador não toca.

Veja [CONFIGURATION_MAP.md](CONFIGURATION_MAP.md) para o mapa completo de
origem → destino.
