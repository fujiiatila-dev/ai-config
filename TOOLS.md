# Guia de uso das ferramentas

O que cada ferramenta do ai-config faz, quando ela age sozinha, quais comandos
você usa no dia a dia e como diagnosticar quando algo falha. Instalação e
merge estão no [README](README.md); o modo opt-in do Headroom tem detalhes
extras em [HEADROOM.md](HEADROOM.md).

| Ferramenta | Camada | Age sozinha? | Comando de verificação |
| --- | --- | --- | --- |
| [Instalador](#instalador-installsh--installps1) | configuração | não | `./install.sh --doctor` |
| [RTK](#rtk--saída-do-shell-compacta) | economia de tokens (shell) | **sim**, via hook | `rtk gain` |
| [Headroom](#headroom--compressão-de-contexto-opt-in) | economia de tokens (contexto) | não, opt-in por sessão | `headroom doctor` |
| [OpenSpec](#openspec--especificar-antes-de-codar) | especificação | não | `openspec list` |
| [Semgrep, Gitleaks, Trivy](#auditoria-de-segurança) | segurança | não | skill `security-audit` |
| [Codex Security](#codex-security) | segurança (Codex) | não | `npx @openai/codex-security --version` |
| [aurum](#aurum--gate-de-qualidade) | qualidade | não | `aurum check .` |
| [Impeccable](#impeccable--design-de-interface) | UI/UX | hook de aviso em edições | skill `impeccable` |
| [Status line](#status-line) | UX do Claude Code | sim | aparece no rodapé |
| [Recuperação do Codex](#recuperação-de-sessões-do-codex) | reparo local | não | `--require-session` |

## Onde cada agente recebe as ferramentas

| | Claude Code | Codex | Antigravity |
| --- | --- | --- | --- |
| Padrão de trabalho (`WORKFLOW.md`) | `~/.claude/CLAUDE.md` via `@WORKFLOW.md` | incorporado em `~/.codex/AGENTS.md` | regra `always_on` em `~/.gemini/config/rules/ai-config.md` |
| RTK | hook `rtk hook claude` | hook `rtk hook codex` (`~/.codex/hooks.json`) | prefixo `rtk` manual (sem hook) |
| Skills `openspec`, `qualidade`, `security-audit` | `~/.claude/skills` | `~/.agents/skills` | `~/.gemini/config/skills` |
| Impeccable | `~/.claude/skills/impeccable` + hook | build próprio do Impeccable em `~/.agents` + hooks | instalador do Impeccable |
| Headroom | `--headroom claude` | `--headroom proxy` + `codex --profile headroom` | — |

Codex e Antigravity **não expandem `@arquivo`**. Por isso o instalador
incorpora o `WORKFLOW.md` no próprio arquivo de instruções a partir da fonte
única do repositório. O Antigravity também não lê `~/.gemini/GEMINI.md`, que
serve só ao Gemini CLI; a raiz global dele é `~/.gemini/config/`.

Resumo do fluxo de uma mudança:

```text
validate → dry-run → apply → doctor → security → quality → commit
```

---

## Instalador (`install.sh` / `install.ps1`)

Os dois wrappers chamam o mesmo motor, `tools/aiconfig.py`, e aceitam as
mesmas opções.

```bash
./install.sh --validate        # preflight do checkout, somente leitura
./install.sh --dry-run         # mostra o merge nesta máquina
./install.sh                   # aplica, com backup de cada arquivo
./install.sh --doctor          # diagnóstico do ambiente
./install.sh --ca-bundle       # só se o doctor acusar TLS interceptado
./install.sh --headroom claude # sessão Claude via Headroom (TLS e Kompress já ajustados)
./install.sh --headroom proxy  # proxy para `codex --profile headroom`
```

O que o `--doctor` confere e o que fazer em cada aviso:

| Aviso | Significado | Ação |
| --- | --- | --- |
| `ausente <ferramenta>` | não está no PATH | instale pelo canal da seção correspondente |
| versão `?` | a ferramenta não respondeu `--version` no prazo | rode `<ferramenta> --version` à mão; a primeira execução após atualizar é lenta |
| `rtk gain falhou` | o `rtk` do PATH é outro projeto | veja [RTK > problemas](#problemas-comuns) |
| `statusLine usa o alias da Microsoft Store` | `python3` do PATH é o stub `WindowsApps` | rode o instalador de novo e escolha o valor do repo, ou edite o caminho |
| `hook RTK ausente` | `rtk hook claude` não está em `PreToolUse` | rode o instalador |
| `allowlist ampla` | `Bash(rtk:*)` e similares no seu `settings.json` | veja [Permissões](#permissões) |
| `tls HTTPS reassinado por …` | antivírus ou proxy inspeciona HTTPS | veja [TLS interceptado](#tls-interceptado) |
| `headroom-proxy NÃO está respondendo` | normal fora de uma sessão Headroom | nada, o Headroom é opt-in |
| `Roteamento Headroom persistente` | um agente depende do proxy para abrir | [HEADROOM.md > Recuperação](HEADROOM.md#recuperação-de-uma-instalação-legada) |
| `codex … trusted` / sandbox | baseline do Codex fraco | `./install.sh --harden-codex` |
| `features.daemon_auto_start ativo` | janelas de terminal no Codex (Windows) | veja [Codex no Windows](#codex-no-windows--janelas-de-terminal) |
| `hook legado em hooks.json` | `rtk hook claude` ou `commandWindows` em sintaxe cmd | instalador com `--prefer-repo` (vira conflito, com backup) |
| `hook rtk hook codex ausente` | a saída do shell do Codex não é condensada | rode o instalador |
| `AGENTS.md usa @WORKFLOW.md` | o Codex não recebe o padrão de trabalho | rode o instalador |
| `skills ausentes/desatualizadas` | Codex ou Antigravity sem as skills do repo | rode o instalador (`--prefer-repo` para atualizar) |
| `regra global ausente` | o Antigravity não recebe o padrão de trabalho | rode o instalador |
| `MCP headroom persistido` | um `headroom wrap claude` foi interrompido | `claude mcp remove headroom --scope user` |

`--update-tools` atualiza OpenSpec, Semgrep, Gitleaks e Trivy para as versões
de `versions.json`. RTK, Headroom, aurum e Codex Security têm canais próprios,
descritos abaixo.

---

## RTK — saída do shell compacta

[RTK](https://github.com/rtk-ai/rtk) (Rust Token Killer) filtra a saída de
comandos como `git`, `npm`, `cargo`, `pytest` e `docker` antes que ela entre no
contexto. Em uso real, a economia fica acima de 90%.

### Como age

O instalador registra `rtk hook claude` em `PreToolUse` para as ferramentas
`Bash` e `PowerShell`. A cada comando, o hook reescreve para a forma compacta:

| Você/o agente escreve | Executa |
| --- | --- |
| `git status` | `rtk git status` |
| `$env:X='1'; git status` | `$env:X='1'; rtk git status` |
| `cd pasta; git diff --stat` | `cd pasta; rtk git diff --stat` |
| `git log \| Select-Object -First 2` | inalterado: pipelines passam direto |
| `Get-Content a.txt` | inalterado: cmdlets não são reescritos |

O hook **respeita as permissões**: ele só devolve `allow` quando o comando
original já está liberado no `settings.json`. Para os demais, o Claude Code
pergunta normalmente.

No **Codex**, o hook é `rtk hook codex` (matcher `Bash`, nome que o Codex dá a
todo comando de shell, inclusive PowerShell). Lá o `allow` serve só para
entregar o comando reescrito: a sandbox e a `approval_policy` do Codex
continuam valendo. No **Antigravity** não há hook: prefixe `rtk` à mão em
comandos de saída longa.

### Comandos do dia a dia

```bash
rtk gain                 # economia total
rtk gain --history       # economia por comando
rtk discover             # comandos frequentes que ainda não passam pelo RTK
rtk hook check "git log" # mostra como o hook reescreveria um comando
rtk init --show          # confere hook, RTK.md e settings.json
rtk proxy <cmd>          # executa sem filtro, para comparar a saída completa
```

Filtros globais ficam em `~/.config/rtk/filters.toml` (modelo em
`adapters/rtk/filters.toml`); um `.rtk/filters.toml` no projeto tem
precedência.

### Instalar e atualizar

O RTK não é instalado pelo `install.sh`. No Windows, baixe o
`rtk-x86_64-pc-windows-msvc.zip` da página de releases, confira o SHA-256 com o
`checksums.txt` da mesma release e substitua `~/.local/bin/rtk.exe`. Como o
próprio hook mantém o executável em uso, **renomeie** o antigo antes de copiar
o novo:

```powershell
Move-Item $HOME\.local\bin\rtk.exe $HOME\.local\bin\rtk.exe.old
Copy-Item .\rtk.exe $HOME\.local\bin\rtk.exe
rtk --version
```

No Linux/macOS, use o script ou o `brew` indicados no README do projeto.

### Problemas comuns

- **`rtk gain` falha:** há outro `rtk` (Rust Type Kit) antes no PATH. Confira
  com `where.exe rtk` (Windows) ou `which -a rtk`.
- **Economia zerada:** confira `rtk init --show`; se o hook faltar, rode o
  instalador.
- **Precisa da saída completa:** use `rtk proxy <cmd>`.

---

## Headroom — compressão de contexto (opt-in)

[Headroom](https://github.com/chopratejas/headroom) é um proxy local que
comprime o contexto enviado ao modelo. Ele fica **no caminho de rede** entre o
agente e o provedor, por isso o ai-config nunca o ativa globalmente: uma sessão
normal de `claude` ou `codex` funciona com o proxy desligado.

### Uso: Claude Code

O jeito mais simples é o lançador do repositório. Ele desliga o Kompress,
aplica o bundle de CA quando existe (só no processo iniciado) e chama
`headroom wrap claude` com a porta configurada:

```powershell
.\install.ps1 --headroom claude             # Windows
./install.sh --headroom claude              # Linux/macOS
.\install.ps1 --headroom claude --dry-run   # só mostra o comando
```

Argumentos extras vão direto para o `headroom` (ex.: `--headroom claude --no-mcp`).

O `wrap` registra o MCP `headroom` no `~/.claude.json` e o remove ao sair. Se a
sessão for morta à força, o registro fica, e toda sessão comum passa a iniciar
um MCP apontando para o proxy parado. O `doctor` avisa; para limpar, rode
`claude mcp remove headroom --scope user`.

Equivalente manual:

```bash
HEADROOM_DISABLE_KOMPRESS=1 HEADROOM_DISABLE_KOMPRESS_FALLBACK=1 \
  headroom wrap claude --port "${HEADROOM_PORT:-48731}" --tool-search true
```

### Uso: Codex

Em um terminal, suba o proxy e espere o `/readyz`. A partida leva de 30 a 90 s
na primeira vez:

```powershell
.\install.ps1 --headroom proxy
```

Em outro terminal:

```bash
codex --profile headroom
```

O perfil vem de `~/.codex/headroom.config.toml`. Atenção: o Codex **ignora em
silêncio** um perfil inexistente, então um erro de digitação abre uma sessão
direta sem aviso. Confira com `codex --profile headroom mcp list`: o servidor
`headroom` deve aparecer.

### Comandos do dia a dia

```bash
headroom doctor          # diagnóstico somente leitura
headroom savings         # economia acumulada
headroom update --check  # há versão nova?
```

### Instalar e atualizar

```bash
uv tool install --python 3.13 "headroom-ai[proxy,mcp,memory]"
uv tool upgrade headroom-ai              # atualizar
uv tool upgrade --native-tls headroom-ai # atrás de inspeção TLS
```

### Problemas comuns

| Sintoma | Causa | Correção |
| --- | --- | --- |
| proxy não fica pronto, log com `tiktoken` e `CERTIFICATE_VERIFY_FAILED` | inspeção TLS | [TLS interceptado](#tls-interceptado) |
| `uv tool upgrade` com `UnknownIssuer` | inspeção TLS | `--native-tls` |
| `ConnectionRefused` numa sessão normal | rota Headroom persistida | [HEADROOM.md > Recuperação](HEADROOM.md#recuperação-de-uma-instalação-legada) |
| `Model provider 'headroom' not found` ao retomar no Codex | sessão antiga gravou o provider | [Recuperação do Codex](#recuperação-de-sessões-do-codex) |
| CPU alta ou quarentena do compressor | Kompress/ONNX | mantenha as duas variáveis `HEADROOM_DISABLE_KOMPRESS*` |

---

## TLS interceptado

Antivírus com inspeção HTTPS (AVG/Avast Web Shield, Kaspersky, ESET…) e
proxies corporativos reassinam as conexões com uma CA própria. O Windows
confia nela, mas ferramentas Python (`headroom`, `uv`, `pip`, `semgrep`) usam
o bundle Mozilla/`certifi` e falham com `CERTIFICATE_VERIFY_FAILED` ou
`UnknownIssuer`. O `doctor` detecta isso e mostra o emissor.

**Opção 1, preferível:** exclua os domínios dos provedores
(`api.anthropic.com`, `api.openai.com`, `pypi.org`,
`files.pythonhosted.org`, `openaipublic.blob.core.windows.net`) da inspeção
HTTPS do antivírus.

**Opção 2:** gere um bundle local com `certifi` e as raízes do Windows e use-o
somente na sessão:

```powershell
.\install.ps1 --ca-bundle                 # grava ~/.config/ai-config/ca-bundle.pem
$env:SSL_CERT_FILE = "$HOME\.config\ai-config\ca-bundle.pem"
$env:REQUESTS_CA_BUNDLE = $env:SSL_CERT_FILE
```

As duas variáveis são necessárias: `httpx` lê `SSL_CERT_FILE`, mas `requests`
(usado pelo `tiktoken` na partida do Headroom) só lê `REQUESTS_CA_BUNDLE`. O
bundle é específico da máquina, não entra no Git e deve ser regenerado quando
a CA do antivírus mudar. Nunca desative a verificação TLS
(`--trusted-host`, `verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED=0`).

Atalhos por ferramenta:

| Ferramenta | Sem bundle |
| --- | --- |
| `uv` | `--native-tls` ou `UV_NATIVE_TLS=1` |
| `pip` 22.2–24.1 | `--use-feature=truststore` (o instalador já usa) |
| `pip` ≥ 24.2 | usa o repositório do sistema por padrão |
| `winget` | `--source winget` (a origem `msstore` falha com cert pinning) |

---

## OpenSpec — especificar antes de codar

[OpenSpec](https://github.com/Fission-AI/OpenSpec) mantém a especificação em
`openspec/`. Toda funcionalidade nova passa por
propose → apply → archive.

```bash
openspec init --tools claude     # uma vez por projeto (codex/gemini conforme o cliente)
openspec list                    # changes ativos
openspec validate --all --strict # valida specs e changes
```

No Claude Code:

| Comando | O que faz |
| --- | --- |
| `/opsx:propose <nome>` | gera proposal, delta specs, design e tasks |
| `/opsx:apply` | implementa `tasks.md` item a item |
| `/opsx:update <nome> - <detalhe>` | ajusta o planejamento sem tocar no código |
| `/opsx:archive` | valida, sincroniza specs e arquiva |

A skill `openspec` e o subagente `openspec-engineer` conduzem o ciclo.
Instalação: `npm install -g @fission-ai/openspec@<versão>`.

---

## Auditoria de segurança

Três scanners locais, sem API key, orquestrados pela skill `security-audit` e
pelo subagente `security-analyst`:

```bash
gitleaks detect --source .                        # segredos
semgrep scan --config=auto --json .               # SAST
trivy fs --format json --scanners vuln .          # CVEs em dependências
```

No Claude Code, peça "rode a auditoria de segurança" ou use
`/security-audit`. Semgrep e o `--config=auto` precisam de rede. Atrás de
inspeção TLS, exporte o bundle antes (veja acima). O Semgrep demora alguns
segundos só para iniciar; é normal.

### Codex Security

Auditoria profunda para o Codex, cobrada por uso e dependente de login
(`OPENAI_API_KEY` ou `codex login`). Nunca é instalada nem executada pelo
instalador.

```bash
npx @openai/codex-security scan . --diff origin/main --json \
  --fail-on-severity high --output-dir ./codex-security-results
```

---

## aurum — gate de qualidade

A skill `qualidade` roda `aurum check .` e busca score ≥ 70%:

```powershell
$env:PYTHONUTF8 = '1'
aurum check .
```

```bash
aurum check . --json > report.json   # saída estruturada para CI
aurum check . --fix                  # cria templates que faltam — revise antes de commitar
```

### Instalar e atualizar

O aurum vem de
[generalrodolfao/standards](https://github.com/generalrodolfao/standards) e
exige Python ≥ 3.12. **Não use `pip install aurum`**: esse nome no PyPI é
outro projeto. Instale fixando o commit verificado:

```bash
uv tool install --python 3.13 \
  "git+https://github.com/generalrodolfao/standards@07ae8eba9f1f52b4326b1aecc36d552782fb8aa4"
aurum --version   # aurum v0.4.0
```

Para atualizar, repita com o SHA novo e `--force`. Atrás de inspeção TLS, o
`uv` precisa de `--native-tls`, e o `git` que ele chama precisa do backend do
Windows só nessa invocação:

```powershell
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'http.sslBackend'
$env:GIT_CONFIG_VALUE_0 = 'schannel'
uv tool install --native-tls --python 3.13 "git+https://github.com/generalrodolfao/standards@<sha>"
```

Quando o executável não está disponível, registre o gate como não executado
na entrega. Não o marque como aprovado.

**Falso positivo conhecido (v0.4.0):** `GIT-IGNORE-005` reprova qualquer
`.gitignore` que mencione `.env.example`, inclusive a negação
`!.env.example`, que é o padrão correto. Mantenha o `.gitignore` e registre o
check como falso positivo.

---

## Impeccable — design de interface

Skill para criar, revisar e polir UI (`/impeccable`, com subcomandos como
`shape`, `critique`, `audit`, `polish` e `live`), acompanhada dos subagentes
`impeccable-asset-producer`, `impeccable-documenter`,
`impeccable-finish-reviewer` e `impeccable-manual-edit-applier`. O instalador
registra um hook `PostToolUse` que avisa sobre padrões problemáticos quando
arquivos de interface são editados. Ele não bloqueia a edição.

A versão vendorizada é a 4.3.1 (Apache 2.0). O motor é um binário nativo
chamado pelo launcher `scripts/impeccable` (ou `impeccable.cmd`). O binário
(~14 MB por plataforma) **não** é versionado: na primeira execução o launcher
usa `~/.impeccable/bin`, o cache de versão ou baixa e confere o motor. Se o
hook falhar logo após instalar numa máquina nova, rode uma vez
`~/.claude/skills/impeccable/scripts/impeccable doctor`.

Ao atualizar a skill, copie a pasta inteira e remova antes a versão anterior
do perfil. O instalador só **adiciona** arquivos, então misturar versões deixa
scripts órfãos.

---

## Status line

`~/.claude/statusline.py` mostra modelo, branch e diretório no rodapé do
Claude Code. Precisa de um Python real: se o rodapé sumir no Windows, rode o
`doctor`. O aviso `alias da Microsoft Store` indica a causa.

---

## Codex no Windows — janelas de terminal

**Sintoma:** a cada comando, hook ou consulta ao git, abre (e às vezes fica
aberta) uma janela do Windows Terminal, às vezes com
`erro 2147942632 (0x800700e8) ao iniciar "git" ... status --porcelain`.

**Causa:** desde a 0.157, o `codex` do terminal se conecta a um **daemon
compartilhado** (`codex app-server daemon`). Esse daemon roda sem console e
inicia hooks e o `git` interno sem `CREATE_NO_WINDOW`, então o Windows cria uma
janela para cada processo (openai/codex#44768, ainda aberta na 0.159.1). No
modo embutido, os mesmos processos herdam o console da sessão e nada aparece.

**Correção aplicada pelo instalador (Windows):**

1. `~/.codex/config.toml` recebe `[features] daemon_auto_start = false`: o
   `codex` do terminal passa a usar o servidor embutido.
2. `~/.codex/hooks.json` troca `rtk hook claude` por `rtk hook codex` e corrige
   o `commandWindows` do Impeccable. A forma antiga, em sintaxe de cmd
   (`if exist … & exit /b`), dava `ParserError` porque o Codex executa hooks
   no PowerShell.

**Depois de instalar, uma vez:**

```powershell
codex app-server daemon stop   # encerra o daemon que já está rodando (feche as sessões antes)
codex                          # abra uma sessão e revise os hooks com /hooks
```

O Codex marca como `Modified` todo hook alterado e só volta a executá-lo
depois que você o revisa e confia de novo em `/hooks`. O instalador não faz
isso por você, de propósito.

**Quando a correção oficial sair**, volte com `daemon_auto_start = true` no
`~/.codex/config.toml` (ou remova a linha).

---

## Recuperação de sessões do Codex

```bash
python tools/recover_codex_sessions.py --require-session <UUID>            # auditoria
python tools/recover_codex_sessions.py --apply --require-session <UUID>    # reparo
python tools/recover_codex_sessions.py --apply \
  --replace-provider headroom=openai --require-session <UUID>             # provider legado
```

Cria backup em `~/.codex/backups/session-recovery-*`. Reinicie o app do Codex
uma vez depois de aplicar.

---

## Permissões

O `claude/settings.json` libera só subcomandos de leitura do RTK e do
Headroom (`rtk gain`, `rtk discover`, `headroom doctor`, `headroom savings`…).
Evite `Bash(rtk:*)`, `PowerShell(rtk:*)` e `Bash(headroom:*)`:

- com o hook, `docker ps` vira `rtk docker ps`, e `rtk:*` aprovaria esse e
  qualquer outro comando que o RTK saiba envolver, sem pergunta;
- `headroom:*` aprovaria `headroom init --global` e `headroom install`, que
  tornam o proxy obrigatório.

O instalador nunca remove entradas de lista. Se o `doctor` acusar
`allowlist ampla`, apague essas regras do `~/.claude/settings.json` à mão.
