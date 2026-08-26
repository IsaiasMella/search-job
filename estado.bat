@echo off
REM Muestra si el programa esta corriendo solo y como le fue la ultima vez.
title Vacantia - Estado
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\estado.ps1"
