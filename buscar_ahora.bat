@echo off
REM Corre una busqueda ahora mismo, sin esperar al horario programado.
title Vacantia - Buscando...
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  El programa no esta instalado todavia.
    echo  Ejecuta primero instalar.bat
    echo.
    pause
    exit /b 1
)

REM Perfil: el primero que haya en profiles\, ignorando el de ejemplo.
set PERFIL=
for %%f in (profiles\*.json) do (
    if /i not "%%~nf"=="example" if not defined PERFIL set PERFIL=%%~nf
)

if not defined PERFIL (
    echo.
    echo  No hay ningun perfil configurado. Avisale a Isaias.
    echo.
    pause
    exit /b 1
)

echo.
echo  Buscando ofertas para: %PERFIL%
echo  Esto puede tardar unos minutos. Podes seguir usando la computadora.
echo.

".venv\Scripts\python.exe" -m vacantia.run --profile %PERFIL%

echo.
echo  Listo. Si hubo ofertas nuevas, te llegaron por Telegram.
echo.
pause
