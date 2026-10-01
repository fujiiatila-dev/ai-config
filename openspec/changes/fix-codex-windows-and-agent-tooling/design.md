## Evidência coletada (2026-09-29, Windows 11, Codex 0.159.1)

| Observação | Como foi obtida |
| --- | --- |
| Janelas vêm de `pwsh.exe` filho do daemon (`app-server-daemon/.../codex.exe`) | snapshot Toolhelp a cada 15 ms + `EnumWindows` durante uso real |
| O daemon executa hooks como `pwsh -NoProfile -Command "<commandWindows>"` | linha de comando lida via `NtQueryInformationProcess` no instante da criação |
| Hook do Impeccable dá `ParserError` no PowerShell | reprodução direta com o mesmo comando |
| `codex exec` (servidor embutido) roda `pwsh`/`git` sem abrir janelas | mesmo monitor, A/B com e sem hooks |
| `daemon_auto_start=false` faz a TUI não iniciar/usar o daemon | `codex-rs/tui/src/startup_orchestration.rs` (0.159.1) |
| Carregador de `AGENTS.md` não trata `@` | `codex-rs/core/src/agents_md.rs` (0 ocorrências) |
| Hooks alterados ficam `Modified` até nova confiança | `codex-rs/hooks/src/engine/discovery.rs` |
| Ferramenta de shell chega aos hooks como `Bash` | `HookToolName::bash()` em `unified_exec` |
| `allow` do PreToolUse só entrega `updatedInput` | `codex-rs/hooks/src/engine/output_parser.rs` |
| `rtk hook codex` exige `permission_mode` no payload | `src/hooks/hook_cmd.rs` (RTK 0.50) |
| Antigravity: raiz global `~/.gemini/config/` (rules, skills) | skill embutida `agy-customizations` |

## Decisões

- **Fragmento só no Windows.** O daemon funciona no macOS/Linux; desligá-lo lá
  seria regressão. `install_toml` aplica o fragmento apenas com `os.name == "nt"`.
- **Comando de hook sem aspas.** É a única forma válida ao mesmo tempo no cmd e
  no PowerShell; caminhos com espaço usam o nome curto 8.3
  (`{{AGENTS_HOME_WIN}}`).
- **Migração como conflito.** A regra do repositório é nunca remover entrada de
  lista em silêncio; `drop_legacy_hooks` pergunta, e `--keep-existing` mantém.
- **Include na instalação.** A fonte continua única (`shared/WORKFLOW.md`); o
  arquivo instalado fica autocontido para clientes sem `@import`.
- **Skills neutras.** As cópias do Codex eram substituições mecânicas de
  "Claude" por "Codex" sobre versões antigas; o texto do repo passou a servir
  aos três agentes.
- **`nargs="*"` no lançador.** `REMAINDER` engoliu `--dry-run` num teste e
  iniciou um `wrap` real, que registrou o MCP `headroom`; o registro foi
  removido e o `doctor` passou a detectá-lo.
