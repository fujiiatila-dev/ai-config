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
$SkipTools = $false
$Rest = @()
foreach ($a in $args) {
    switch -Regex ($a) {
        '^(--doctor|doctor)$' { $Cmd = 'doctor' }
        '^(--skip-tools)$'    { $SkipTools = $true }
        '^(-h|--help)$' {
            Write-Host @'
uso: .\install.ps1 [--dry-run] [--keep-existing|--prefer-repo] [--yes] [--skip-tools]
     .\install.ps1 --doctor

  --dry-run        mostra o que faria, sem escrever nada
  --keep-existing  em conflito, mantem sempre o valor atual
  --prefer-repo    em conflito, usa sempre o valor do repo
  --yes            nao pergunta nada (equivale a --keep-existing)
  --skip-tools     pula a instalacao de dependencias (openspec, semgrep, etc.)
  --doctor         verifica python, node, rtk, headroom, aurum, openspec,
                   semgrep, gitleaks, trivy e os CLIs (claude, codex, git)

Sem flags: instala configuracao + dependencias externas num comando so.
Nada e sobrescrito sem backup.

Variaveis: CLAUDE_CONFIG_DIR, CODEX_HOME, GEMINI_HOME, RTK_CONFIG_DIR,
           HEADROOM_PORT
'@
            exit 0
        }
        default { $Rest += $a }
    }
}

$env:PYTHONUTF8 = '1'

# ── 1. Instalar/fixar configuracao ─────────────────────────────────────────────
& $Py (Join-Path $Root 'tools\aiconfig.py') $Cmd @Rest
$RC = $LASTEXITCODE

# ── 2. Instalar dependencias externas ───────────────────────────────────────────
if ($Cmd -eq 'install' -and -not $SkipTools) {
    # Verifica se e --dry-run
    $isDryRun = $false
    foreach ($a in $Rest) {
        if ($a -eq '--dry-run') { $isDryRun = $true; break }
    }
    if ($isDryRun) {
        Write-Host "`n  (--dry-run: dependencias nao instaladas)"
        exit 0
    }

    Write-Host "`n== Instalando dependencias externas =="
    $Fail = $false

    # openspec (npm)
    if (Get-Command openspec -ErrorAction SilentlyContinue) {
        Write-Host "  = openspec ja instalado"
    } else {
        Write-Host "  + openspec..."
        & npm install -g @fission-ai/openspec@latest
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    openspec instalado"
        } else {
            Write-Host "    aviso: falha ao instalar openspec"
            $Fail = $true
        }
    }

    # semgrep (pip)
    if (Get-Command semgrep -ErrorAction SilentlyContinue) {
        Write-Host "  = semgrep ja instalado"
    } else {
        Write-Host "  + semgrep..."
        $pipCmd = if (Get-Command pip -ErrorAction SilentlyContinue) { 'pip' } else { 'pip3' }
        & $pipCmd install --user semgrep
        if ($LASTEXITCODE -ne 0) { & $pipCmd install semgrep }
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    semgrep instalado"
        } else {
            Write-Host "    aviso: falha ao instalar semgrep"
            $Fail = $true
        }
    }

    # gitleaks
    if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
        Write-Host "  = gitleaks ja instalado"
    } else {
        Write-Host "  + gitleaks..."
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            & winget install gitleaks --accept-package-agreements --silent
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    gitleaks instalado via winget"
            } else {
                Write-Host "    aviso: winget falhou"
                $Fail = $true
            }
        } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
            & choco install gitleaks -y --no-progress
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    gitleaks instalado via choco"
            } else {
                Write-Host "    aviso: choco falhou"
                $Fail = $true
            }
        } else {
            Write-Host "    aviso: sem winget ou choco. Instale manualmente:"
            Write-Host "           https://github.com/gitleaks/gitleaks/releases"
            $Fail = $true
        }
    }

    # trivy
    if (Get-Command trivy -ErrorAction SilentlyContinue) {
        Write-Host "  = trivy ja instalado"
    } else {
        Write-Host "  + trivy..."
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            & winget install aquasecurity.trivy --accept-package-agreements --silent
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    trivy instalado via winget"
            } else {
                Write-Host "    aviso: winget falhou"
                $Fail = $true
            }
        } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
            & choco install trivy -y --no-progress
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    trivy instalado via choco"
            } else {
                Write-Host "    aviso: choco falhou"
                $Fail = $true
            }
        } else {
            Write-Host "    aviso: sem winget ou choco. Instale manualmente:"
            Write-Host "           https://github.com/aquasecurity/trivy/releases"
            $Fail = $true
        }
    }

    Write-Host ""
    if (-not $Fail) {
        Write-Host "  Todas as dependencias ja estavam ou foram instaladas."
    } else {
        Write-Host "  Algumas dependencias podem nao ter sido instaladas."
        Write-Host "  Rode  ./install.sh --doctor  para conferir."
    }

    Write-Host "  Nota: ferramentas instaladas via winget/choco podem exigir"
    Write-Host "        reiniciar o terminal para ficarem no PATH."
}

exit $RC
