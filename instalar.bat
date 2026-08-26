@echo off
REM ===========================================================================
REM  Vacantia - Instalador
REM  Doble clic en este archivo. Se instala solo.
REM ===========================================================================
title Vacantia - Instalacion

REM -ExecutionPolicy Bypass: Windows bloquea scripts de PowerShell por defecto.
REM Esto lo saltea solo para esta ejecucion, no cambia la configuracion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\instalar.ps1"

REM Si PowerShell no llego a arrancar, la ventana se cerraria sin mostrar nada.
if errorlevel 1 (
    echo.
    echo  Hubo un problema al iniciar la instalacion.
    echo  Sacale una foto a esta pantalla y mandasela a Isaias.
    echo.
    pause
)
