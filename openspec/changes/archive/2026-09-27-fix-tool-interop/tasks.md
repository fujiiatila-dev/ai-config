## 1. Motor (`tools/aiconfig.py`)

- [x] 1.1 Resolver `{{PYTHON}}` pelo interpretador em execução, ignorando `WindowsApps`.
- [x] 1.2 Prazo de sondagem por ferramenta e Semgrep sem check online.
- [x] 1.3 Subcomando `ca-bundle` e opção nos dois wrappers.
- [x] 1.4 `doctor`: inspeção TLS, statusLine, hook/identidade do RTK e permissões amplas.
- [x] 1.5 Semgrep com truststore; winget com `--source winget`.

## 2. Configuração portátil

- [x] 2.1 Restringir as permissões de `rtk`/`headroom` a subcomandos de leitura.
- [x] 2.2 Atualizar `versions.json` para a toolchain verificada.

## 3. Testes

- [x] 3.1 Cobrir resolução do Python, bundle, detecções do `doctor` e comandos de instalação.

## 4. Documentação

- [x] 4.1 Criar `TOOLS.md` com o uso de cada ferramenta e reorganizar README.
- [x] 4.2 Atualizar `HEADROOM.md`, `claude/RTK.md` e `CONFIGURATION_MAP.md`.

## 5. Verificação

- [x] 5.1 Preflight, suíte, `py_compile`, dry-run e doctor.
- [x] 5.2 Gitleaks, Semgrep e Trivy; `openspec validate --strict`.

### Registro da verificação — 2026-09-27 (Windows 11)

- Ferramentas atualizadas na máquina: RTK 0.44.0 → 0.50.0 (SHA-256 conferido
  com `checksums.txt`; binário antigo em `~/.local/bin/rtk.exe.0.44.0.bak`),
  Headroom 0.38.0 → 0.39.1, OpenSpec 1.7.0 → 1.13.2, Codex Security 0.1.6 →
  0.1.31, Semgrep 1.172.0 → 1.178.0, Trivy 0.72.0 → 0.74.0. Claude Code
  2.1.283, Codex 0.157.1, Gitleaks 8.30.1 e Node 24.21.0 já estavam atuais.
- Headroom ponta a ponta: sem o bundle, o proxy morre na partida
  (`tiktoken` → `CERTIFICATE_VERIFY_FAILED`, CA "AVG Web/Mail Shield Root").
  Com `SSL_CERT_FILE` + `REQUESTS_CA_BUNDLE`, `/readyz` respondeu em 28 s e
  `POST /v1/messages` voltou `401 invalid x-api-key` da Anthropic.
- Hook RTK: reescreve payloads `Bash` e `PowerShell`; só devolve `allow` para
  comandos já liberados (`docker ps`, `curl`, `kubectl` ficaram sem decisão).
- `validate` (PowerShell e Git Bash), 55 testes (1 skip Bash esperado),
  `py_compile`, `bash -n`, `dry-run` e `doctor` (16 s aquecido, todas as
  versões resolvidas) passaram. `openspec validate --all --strict`: 5/5.
- Gitleaks (árvore e histórico): sem vazamentos. Trivy: limpo. Semgrep
  `--config=auto` via bundle: 0 achados nos arquivos alterados.
- aurum: instalado de `generalrodolfao/standards@07ae8eb` via `uv tool`
  (Python 3.13). `aurum check .`: **80%** (8 ok, 2 falhas, 36 ignorados como
  não aplicáveis ao tipo `generic`). `GIT-IGNORE-005` é falso positivo do
  aurum 0.4.0: o `.gitignore` ignora `.env`, mas o check reprova a negação
  `!.env.example`. `DOC-ADR-001` é informativo; o histórico de decisões fica
  nos `design.md` do OpenSpec.

## 6. Impeccable e aurum (adicionado após a revisão)

- [x] 6.1 Documentar a instalação correta do aurum e o falso positivo conhecido.
- [x] 6.2 Vendorizar o Impeccable 4.3.1 (sem o binário nativo) e os quatro
  subagentes; trocar o hook `hook.mjs` pelo launcher `scripts/impeccable hook`.
- [x] 6.3 `.gitattributes` com LF para scripts `sh` e bit de execução no Git.
- [x] 6.4 Desfazer no perfil local a mistura 3.9.1/4.3.1 criada pelo merge
  (72 arquivos movidos para `~/.claude/backups/`) e remover o hook órfão.

## 7. CI (vermelho desde 601604a na main)

- [x] 7.1 `recover_codex_sessions.create_backup` compara caminhos resolvidos:
  `CODEX_HOME` via symlink (`/var` → `/private/var`) ou nome 8.3 (`RUNNER~1`)
  fazia o backup falhar com "Rollout is outside CODEX_HOME". Reproduzido
  localmente com `TMP` numa junction; corrigido.
- [x] 7.2 `test_tool_version_stops_after_shared_deadline` verifica a flag de
  cada plataforma e isola `os.killpg` (o teste sinalizava um PID falso no Unix).
- [x] 7.3 O decorador Windows-only voltou para `PowerShellInstallerTests`; os
  17 testes de `ToolInteropTests` passam a rodar em Linux e macOS.
