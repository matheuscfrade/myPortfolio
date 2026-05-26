@echo off
chcp 65001 >nul
color 0A
title Portfolio Profissional

echo.
echo ============================================================
echo   Iniciando Portfolio Profissional
echo ============================================================
echo.

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
echo Para usar o codigo-fonte sem instalador, instale o Python em:
echo https://www.python.org/downloads/
echo.
echo Durante a instalacao, marque a opcao "Add Python to PATH".
echo.
echo Usuarios finais devem preferir o instalador Windows, que nao exige Python manual.
echo.
pause
exit /b 1

:python_found

echo [INFO] Usando: "%PYTHON_EXE%" %PYTHON_ARGS%

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import sys; print('Python', sys.version)" >nul 2>&1
if errorlevel 1 (
    echo [ERRO] O Python encontrado nao consegue executar scripts corretamente.
    echo Instale Python direto do site oficial e marque "Add Python to PATH".
    pause
    exit /b 1
)

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import flask, pypdf, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias necessarias - pode demorar na primeira vez...
    "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --upgrade pip
    "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo.
        echo [ERRO] Falha ao instalar dependencias.
        echo Tente executar manualmente:
        echo   "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
)

if "%PORTFOLIO_CHECK_PYTHON%"=="1" (
    echo [OK] Python encontrado e dependencias disponiveis.
    exit /b 0
)

echo [INFO] Iniciando o servidor...
echo.
echo [INFO] Site publico:   http://127.0.0.1:5000/portfolio/
echo [INFO] Administracao:  http://127.0.0.1:5000/admin/
echo.
echo [ATENCAO] Nao feche esta janela enquanto estiver editando.
echo.

set "PYTHONDONTWRITEBYTECODE=1"

start "" /min cmd /c "timeout /t 3 >nul & start "" http://127.0.0.1:5000/admin/"

call "%PYTHON_EXE%" %PYTHON_ARGS% "%~dp0scripts\servidor_admin.py"

echo.
echo [INFO] O servidor foi encerrado.
pause
