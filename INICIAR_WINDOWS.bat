@echo off
setlocal
cd /d "%~dp0"
title Project Structure Mapper

echo.
echo ==============================================
echo   PROJECT STRUCTURE MAPPER
echo ==============================================
echo.

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    py -3 "%~dp0mapper.py"
    goto finished
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python "%~dp0mapper.py"
    goto finished
)

echo ERRO: Python 3 nao encontrado.
echo Instale o Python em https://www.python.org/downloads/
echo Durante a instalacao, habilite "Add Python to PATH".

:finished
echo.
echo Pressione qualquer tecla para fechar esta janela.
pause >nul
