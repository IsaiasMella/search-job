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

echo.
echo  Buscando ofertas para todos los perfiles de esta computadora.
echo  Esto puede tardar unos minutos. Podes seguir usando la computadora.
echo.

REM --all corre los perfiles uno despues del otro, con una pausa en el medio:
REM los limites del plan gratis son de la cuenta, no del perfil.
".venv\Scripts\python.exe" -m vacantia.run --all

echo.
echo  Listo. Si hubo ofertas nuevas, te llegaron por Telegram.
echo.
pause
