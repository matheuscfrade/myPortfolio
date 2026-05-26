@echo off
echo ============================================================
echo  Abrindo Portfolio Profissional
echo ============================================================
echo.
echo  Para melhor funcionamento, rode iniciar_admin.bat e acesse:
echo  http://localhost:5000/portfolio/
echo.
echo  Abrindo o site diretamente pelo navegador...
echo.

start "" "%~dp0site-publico\index.html"

echo.
echo  Dica: o servidor local oferece melhor suporte a PDFs e dados salvos.
echo.
pause
