@echo off
REM Quita las corridas automaticas. No borra el programa ni tus datos.
title Vacantia - Desinstalar
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\desinstalar.ps1"
