$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($PythonCommand) {
    $PythonExe = $PythonCommand.Source
} else {
    $PythonExe = Join-Path $env:LOCALAPPDATA "Python\bin\python.exe"
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python nao encontrado. Instale o Python ou adicione python ao PATH."
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$Arguments
    )

    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Comando falhou ($LASTEXITCODE): $Exe $($Arguments -join ' ')"
    }
}

$BuildWorkPath = Join-Path ".codex_tmp" "pyinstaller-build-$PID"
New-Item -ItemType Directory -Force -Path $BuildWorkPath | Out-Null

Invoke-Checked $PythonExe @("-m", "pip", "install", "-r", "requirements.txt")
Invoke-Checked $PythonExe @("-m", "pip", "install", "pyinstaller")
Invoke-Checked $PythonExe @(
    "-m", "PyInstaller",
    "packaging\portfolio-admin.spec",
    "--noconfirm",
    "--workpath", $BuildWorkPath
)

Write-Host "[OK] EXE gerado em dist\PortfolioProfissional"
Write-Host "Para gerar o instalador, instale Inno Setup e compile packaging\installer.iss"
