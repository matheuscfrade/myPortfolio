$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Installer = Join-Path $Root "dist-installer\PortfolioProfissionalSetup.exe"
$LandingDownloads = Join-Path $Root "landing\downloads"
$LandingInstaller = Join-Path $LandingDownloads "PortfolioProfissionalSetup.exe"
$GithubDownloads = Join-Path $Root "publicar-github\downloads"
$GithubInstaller = Join-Path $GithubDownloads "PortfolioProfissionalSetup.exe"

if (-not (Test-Path -LiteralPath $Installer)) {
    throw "Instalador nao encontrado em $Installer. Compile packaging\installer.iss no Inno Setup antes de preparar o download da landing."
}

New-Item -ItemType Directory -Force -Path $LandingDownloads | Out-Null
Copy-Item -LiteralPath $Installer -Destination $LandingInstaller -Force

New-Item -ItemType Directory -Force -Path $GithubDownloads | Out-Null
Copy-Item -LiteralPath $Installer -Destination $GithubInstaller -Force

Write-Host "[OK] Instalador copiado para landing\downloads\PortfolioProfissionalSetup.exe"
Write-Host "[OK] Instalador copiado para publicar-github\downloads\PortfolioProfissionalSetup.exe"
Write-Host "A landing agora pode baixar o arquivo pelo botao Baixar instalador Windows."
