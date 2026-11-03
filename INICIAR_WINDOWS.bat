@echo off
setlocal
cd /d "%~dp0"
title Project Structure Mapper

echo.
echo ==============================================
echo   PROJECT STRUCTURE MAPPER
echo   Leitura local: o projeto nao e alterado e
echo   nada e enviado pela internet.
echo ==============================================
echo.

rem Procura um Python 3.8+ que realmente funcione.
rem (O atalho "python" da Microsoft Store existe mesmo sem Python instalado.)
set "PYCMD="

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYCMD=py -3"
    goto run
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYCMD=python"
    goto run
)

echo ERRO: Python 3.8 ou mais novo nao foi encontrado.
echo.
echo Como resolver:
echo   1. Abra https://www.python.org/downloads/ e baixe o Python 3.
echo   2. Na primeira tela do instalador, marque "Add python.exe to PATH".
echo   3. Termine a instalacao e clique duas vezes neste arquivo de novo.
goto finished

:run
rem Se uma pasta for arrastada para cima deste arquivo, ela ja vem selecionada.
%PYCMD% "%~dp0mapper.py" --assistente %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo O mapeamento terminou com erro. Leia a mensagem acima.
)

:finished
echo.
echo Pressione qualquer tecla para fechar esta janela.
pause >nul
