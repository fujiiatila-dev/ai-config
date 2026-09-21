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
próprios. Codex Security exige autenticação e nunca é instalado
automaticamente.

## Ferramentas e versões de referência

O `./install.sh --doctor` compara as versões locais com estas referências.
Divergências geram aviso, não impedem a instalação.

| Ferramenta | Versão ref. |
| --- | --- |
| Python | 3.14.4 |
| Node.js | 24.20.0 |
| RTK | 0.46.0 |
| Headroom | 0.37.0 |
| aurum | 0.4.0 |
| Claude Code | 2.1.251 |
| Codex CLI | 0.151.0 |
| OpenSpec | 1.11.0 |
| Semgrep | 1.175.0 |
| Gitleaks | 8.30.1 |
| Trivy | 0.74.0 |
| Codex Security | 0.1.6 |

O `doctor` também valida `HEADROOM_PORT`, consulta
`http://127.0.0.1:<porta>/readyz` e alerta sobre sandbox/aprovação inseguras no
Codex sem alterar o arquivo local.

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
