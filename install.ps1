$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $Root 'claude'
$ClaudeHome = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
$HeadroomPort = if ($env:HEADROOM_PORT) { $env:HEADROOM_PORT } else { '48731' }
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$GeminiHome = if ($env:GEMINI_HOME) { $env:GEMINI_HOME } else { Join-Path $env:USERPROFILE '.gemini' }
New-Item -ItemType Directory -Force $ClaudeHome, (Join-Path $ClaudeHome 'agents'), (Join-Path $ClaudeHome 'skills') | Out-Null
$Settings = Join-Path $ClaudeHome 'settings.json'
if (Test-Path $Settings) { Copy-Item $Settings "$Settings.bak-$(Get-Date -Format yyyyMMddHHmmss)" }
Copy-Item (Join-Path $Source 'CLAUDE.md'), (Join-Path $Source 'RTK.md'), (Join-Path $Source 'settings.json'), (Join-Path $Source 'statusline.py') $ClaudeHome -Force
Copy-Item (Join-Path $Source 'agents\*') (Join-Path $ClaudeHome 'agents') -Recurse -Force
Copy-Item (Join-Path $Source 'skills\*') (Join-Path $ClaudeHome 'skills') -Recurse -Force
New-Item -ItemType Directory -Force $CodexHome, $GeminiHome | Out-Null
Copy-Item (Join-Path $Root 'adapters\codex\AGENTS.md') (Join-Path $CodexHome 'AGENTS.md') -Force
Copy-Item (Join-Path $Root 'adapters\gemini\GEMINI.md') (Join-Path $GeminiHome 'GEMINI.md') -Force
if (Get-Command rtk -ErrorAction SilentlyContinue) { Write-Host "RTK encontrado: $(& rtk --version)" } else { Write-Warning 'RTK não encontrado.' }
if (Get-Command headroom -ErrorAction SilentlyContinue) { & headroom init --global --memory claude; if (Get-Command codex -ErrorAction SilentlyContinue) { & headroom init --global --memory codex }; Write-Host "Inicie o proxy Headroom com: headroom proxy --port $HeadroomPort" } else { Write-Warning 'Headroom não encontrado; consulte README.md.' }
Write-Host "Configuração instalada em $ClaudeHome. Reinicie os agentes."
