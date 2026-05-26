@echo off
chcp 65001 >nul
color 0A
title Gerar Pasta Publica

echo.
echo ============================================================
echo   Gerar pasta publica do Portfolio Profissional
echo ============================================================
echo.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PYTHON_EXE="
set "PYTHON_ARGS="

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
    goto :python_found
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    set "PYTHON_ARGS="
    goto :python_found
)

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
    set "PYTHON_ARGS="
    goto :python_found
)

for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-*") do (
    if exist "%%~fD\python.exe" (
        set "PYTHON_EXE=%%~fD\python.exe"
        set "PYTHON_ARGS="
        goto :python_found
    )
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%~fD\python.exe" (
        set "PYTHON_EXE=%%~fD\python.exe"
        set "PYTHON_ARGS="
        goto :python_found
    )
)

if exist "%PROGRAMFILES%\Python313\python.exe" (
    set "PYTHON_EXE=%PROGRAMFILES%\Python313\python.exe"
    set "PYTHON_ARGS="
    goto :python_found
)

if exist "%PROGRAMFILES%\Python312\python.exe" (
    set "PYTHON_EXE=%PROGRAMFILES%\Python312\python.exe"
    set "PYTHON_ARGS="
    goto :python_found
)

echo [ERRO] Python nao encontrado.
echo.
echo Instale o Python e marque a opcao "Add Python to PATH".
echo.
if not "%PORTFOLIO_NO_PAUSE%"=="1" pause
exit /b 1

:python_found

echo [INFO] Usando: "%PYTHON_EXE%" %PYTHON_ARGS%
echo.

pushd "%ROOT%"

echo [1/2] Sincronizando dados a partir da pasta Documentos...
"%PYTHON_EXE%" %PYTHON_ARGS% "%ROOT%\scripts\gerar_dados.py"
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao sincronizar os dados.
    echo Verifique os PDFs em Documentos e tente novamente.
    echo.
    popd
    if not "%PORTFOLIO_NO_PAUSE%"=="1" pause
    exit /b 1
)

echo.
echo [2/2] Gerando pasta publica...
"%PYTHON_EXE%" %PYTHON_ARGS% "%ROOT%\scripts\create_public_package.py"
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao gerar a pasta publica.
    echo.
    popd
    if not "%PORTFOLIO_NO_PAUSE%"=="1" pause
    exit /b 1
)

echo.
echo [OK] Pasta publica pronta em:
echo   "%ROOT%\dist-publico"
echo.
echo Envie o conteudo dessa pasta para GitHub Pages, Netlify,
echo Vercel, Cloudflare Pages ou outra hospedagem estatica.
echo.

popd

if not "%PORTFOLIO_NO_OPEN%"=="1" (
    start "" "%ROOT%\dist-publico"
)

if not "%PORTFOLIO_NO_PAUSE%"=="1" pause
