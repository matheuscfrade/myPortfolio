$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller packaging\portfolio-admin.spec --clean --noconfirm

Write-Host "[OK] EXE gerado em dist\PortfolioProfissional"
Write-Host "Para gerar o instalador, instale Inno Setup e compile packaging\installer.iss"
