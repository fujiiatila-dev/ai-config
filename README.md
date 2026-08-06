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
./install.sh --doctor           # verifica runtimes, agentes e ferramentas
```

Sem flags: **configuração + ferramentas recomendadas**, num comando só.
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

Se a automação falhar, use `npm install -g @fission-ai/openspec@latest`,
`python -m pip install --user semgrep` e o gerenciador do sistema para
Gitleaks/Trivy (`winget`, `choco` ou `brew`).

RTK, Headroom e aurum continuam opcionais e são instalados pelos seus canais
próprios. Codex Security exige autenticação e nunca é instalado
automaticamente.

## Ferramentas e versões de referência

O `./install.sh --doctor` compara as versões locais com estas referências.
Divergências geram aviso, não impedem a instalação.

| Ferramenta | Versão ref. |
| --- | --- |
| Python | 3.14.4 |
| Node.js | 24.15.0 |
| RTK | 0.44.1 |
| Headroom | 0.34.0 |
| aurum | 0.4.0 |
| Claude Code | 2.1.220 |
| Codex CLI | 0.146.1 |
| OpenSpec | 1.7.0 |
| Semgrep | 1.172.0 |
| Gitleaks | 8.30.1 |
| Trivy | 0.72.0 |
| Codex Security | 0.1.1 |

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
