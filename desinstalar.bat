@echo off
REM Desinstala: saca las corridas automaticas y borra el programa.
REM Pregunta aparte si tambien queres borrar tus datos.
title Vacantia - Desinstalar
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\desinstalar.ps1"
