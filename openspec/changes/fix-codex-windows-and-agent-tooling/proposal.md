## Why

Mesmo após `fix-tool-interop`, o uso diário no Windows continuava quebrado:

- **Janelas de terminal no Codex.** O `codex` do terminal (0.157+) se conecta
  ao daemon compartilhado, que roda sem console e inicia hooks e o `git`
  interno sem `CREATE_NO_WINDOW`. Cada processo abre uma janela do Windows
  Terminal, às vezes presa com `0x800700e8` (openai/codex#44768, aberta na
  0.159.1).
- **Hooks do Codex quebrados.** `~/.codex/hooks.json` usava `rtk hook claude`
  (processador errado) e o `commandWindows` do Impeccable em sintaxe de cmd,
  que o Codex executa no PowerShell (`ParserError` a cada hook).
- **O Codex nunca recebeu o padrão de trabalho.** `AGENTS.md` usava
  `@WORKFLOW.md`, e o Codex não expande `@arquivo`.
- **O Antigravity não recebia nada.** Ele lê regras e skills globais de
  `~/.gemini/config/`, e não de `~/.gemini/GEMINI.md`.
- **Skills do Codex órfãs.** `~/.agents/skills` tinha cópias antigas
  adaptadas à mão, fora do instalador.
- **Headroom difícil de usar.** A sessão exigia exportar quatro variáveis à
  mão; um `wrap` interrompido deixava o MCP `headroom` registrado para sempre.
- **Checkout com CRLF.** Com `core.autocrlf=true`, cada instalação no Windows
  acusava dezenas de arquivos "diferentes" só por fim de linha.

## What Changes

- Fragmento `windows.config.toml.example`: `features.daemon_auto_start = false`.
- `adapters/codex/hooks.json` (`rtk hook codex`) e `hooks.impeccable.json`
  (comando sem aspas, válido em cmd e PowerShell; só com o build do Impeccable
  para Codex presente). Hooks legados quebrados viram conflito explícito.
- Diretiva `<!-- ai-config:include … -->` para incorporar o `WORKFLOW.md` em
  Codex, Gemini e Antigravity; o preflight rejeita `@arquivo` nesses adapters.
- Regra `always_on` e skills neutras (`openspec`, `qualidade`,
  `security-audit`) em `~/.gemini/config`; as mesmas skills em `~/.agents/skills`.
- Subcomando `headroom claude|proxy` nos wrappers.
- `doctor`: checagens de Codex, Antigravity e MCP `headroom` persistido;
  versão do Semgrep lida dos metadados.
- `.gitattributes` com LF para todo texto (CRLF só em `.ps1`/`.cmd`).

## Non-goals

- Gravar `trusted_hash` de hooks no Codex: a revisão em `/hooks` é do usuário.
- Parar o daemon do Codex automaticamente (encerraria sessões abertas).
- Distribuir o Impeccable para Codex/Antigravity: ele tem instalador próprio.
