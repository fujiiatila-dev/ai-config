## 1. Codex no Windows

- [x] 1.1 Fragmento `windows.config.toml.example` com `daemon_auto_start = false`, aplicado só no Windows.
- [x] 1.2 `hooks.json` com `rtk hook codex` e `hooks.impeccable.json` sem aspas (cmd e PowerShell).
- [x] 1.3 `drop_legacy_hooks`: migração de hooks legados como conflito, com backup.

## 2. Entrega aos agentes

- [x] 2.1 Diretiva `ai-config:include` e validação contra `@arquivo` nos adapters.
- [x] 2.2 Skills neutras em `~/.agents/skills` (Codex) e `~/.gemini/config/skills` (Antigravity).
- [x] 2.3 Regra `always_on` do Antigravity com preâmbulo fora do bloco gerenciado.

## 3. Ferramentas

- [x] 3.1 Lançador `headroom claude|proxy` nos dois wrappers, com `--dry-run` confiável.
- [x] 3.2 `doctor`: Codex, Antigravity, MCP `headroom` persistido e versão do Semgrep por metadados.
- [x] 3.3 `.gitattributes` com LF para todo texto e cópia de trabalho normalizada.
- [x] 3.4 Codex CLI 0.159.1 e Claude Code 2.1.285 em `versions.json`.

## 4. Documentação e testes

- [x] 4.1 `TOOLS.md`: mapa por agente, janelas do Codex, lançador do Headroom e novos avisos.
- [x] 4.2 README, HEADROOM.md, CONFIGURATION_MAP e regras do repositório.
- [x] 4.3 Testes de include, hooks legados, findings, lançador e metadados.

## 6. Headroom automático (pedido em 2026-10-01)

- [x] 6.1 `run <claude|codex>`: garante o proxy, usa o Headroom se saudável e cai para o provedor direto.
- [x] 6.2 Sem persistência: `--no-mcp` + `--mcp-config` por sessão, sem `--1m` (trocava o modelo para `claude-opus-5`), telemetria do `wrap` desligada.
- [x] 6.3 `--headroom-auto` / `--no-headroom-auto`: bloco gerenciado nos perfis de shell, com pré-aquecimento só em sessão interativa.
- [x] 6.4 Trava de partida e chamadas de gerenciamento direto ao agente.
- [x] 6.5 Testes e documentação (HEADROOM.md, TOOLS.md, README, WORKFLOW.md).

## 5. Verificação

- [x] 5.1 Preflight, suíte, `py_compile`, `bash -n`, dry-run e doctor.
- [x] 5.2 Instalação real com `--prefer-repo --harden-codex` e doctor sem pendências de Codex/Antigravity.
- [ ] 5.3 Após o usuário parar o daemon e aprovar os hooks em `/hooks`: sessão real do Codex sem janelas e com `rtk gain` incrementando.
