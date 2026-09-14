# Instalador do ai-config no Windows. A logica de merge vive em
# tools/aiconfig.py, a mesma usada pelo install.sh.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$Py = $null
foreach ($c in @('python', 'python3', 'py')) {
    if (Get-Command $c -ErrorAction SilentlyContinue) {
        try {
            & $c -c "import sys; raise SystemExit(sys.version_info < (3, 10))" *> $null
            if ($LASTEXITCODE -eq 0) { $Py = $c; break }
        } catch {
            # Continua procurando outro interpretador funcional.
        }
    }
}
if (-not $Py) {
    Write-Error "Python 3.10+ e necessario para instalar (e para o status line). Instale e rode de novo."
    exit 1
}

$Cmd = 'install'
$Rest = @()
foreach ($a in $args) {
    switch -Regex ($a) {
        '^(--doctor|doctor)$' { $Cmd = 'doctor' }
        '^(-h|--help)$' {
            Write-Host @'
uso: .\install.ps1 [--dry-run] [--keep-existing|--prefer-repo] [--yes] [--skip-tools]
     [--update-tools] [--harden-codex]
     .\install.ps1 --doctor

  --dry-run        mostra o que faria, sem escrever nada
  --keep-existing  em conflito, mantem sempre o valor atual
  --prefer-repo    em conflito, usa sempre o valor do repo
  --yes            nao pergunta nada (equivale a --keep-existing)
  --skip-tools     sincroniza so configuracoes, sem instalar ferramentas
  --update-tools   atualiza ferramentas gerenciadas para as referencias do repo
  --harden-codex   aplica defaults seguros ao Codex e remove confianca ampla exata
  --doctor         verifica Python, Node, agentes e ferramentas recomendadas

Sem flags: configura todos os agentes e prepara OpenSpec, Semgrep,
Gitleaks e Trivy. Nada e sobrescrito sem backup.

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
