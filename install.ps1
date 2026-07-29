# Instalador do ai-config no Windows. A logica de merge vive em
# tools/aiconfig.py, a mesma usada pelo install.sh.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$Py = $null
foreach ($c in @('python', 'python3', 'py')) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $Py = $c; break }
}
if (-not $Py) {
    Write-Error "Python 3.9+ e necessario para instalar (e para o status line). Instale e rode de novo."
    exit 1
}

$Cmd = 'install'
$Rest = @()
foreach ($a in $args) {
    switch -Regex ($a) {
        '^(--doctor|doctor)$' { $Cmd = 'doctor' }
        '^(-h|--help)$' {
            Write-Host @'
uso: .\install.ps1 [--dry-run] [--keep-existing|--prefer-repo] [--yes]
     .\install.ps1 --doctor

  --dry-run        mostra o que faria, sem escrever nada
  --keep-existing  em conflito, mantem sempre o valor atual
  --prefer-repo    em conflito, usa sempre o valor do repo
  --yes            nao pergunta nada (equivale a --keep-existing)
  --doctor         verifica rtk, headroom, aurum, node, openspec, semgrep, gitleaks, trivy e os CLIs

Sem flags, cada conflito e perguntado. Nada e sobrescrito sem backup.

Variaveis: CLAUDE_CONFIG_DIR, CODEX_HOME, GEMINI_HOME, RTK_CONFIG_DIR,
           HEADROOM_PORT
'@
            exit 0
        }
        default { $Rest += $a }
    }
}

$env:PYTHONUTF8 = '1'
& $Py (Join-Path $Root 'tools\aiconfig.py') $Cmd @Rest
exit $LASTEXITCODE
