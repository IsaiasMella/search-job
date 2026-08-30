@echo off
REM Abre la pantalla de vacantia en el navegador.
title Vacantia - Pantalla
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  El programa no esta instalado todavia.
    echo  Ejecuta primero instalar.bat
    echo.
    pause
    exit /b 1
)

echo.
echo  Abriendo vacantia en el navegador...
echo.
echo  Direccion: http://localhost:8756
echo.
echo  DEJA ESTA VENTANA ABIERTA mientras uses la pantalla.
echo  Para cerrarla: volve aca y apreta Ctrl+C, o cerra la ventana.
echo.

".venv\Scripts\python.exe" -m vacantia.ui

echo.
echo  Pantalla cerrada.
echo.
pause
