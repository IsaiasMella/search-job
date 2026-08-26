# =============================================================================
#  Vacantia — quitar las corridas automaticas
#
#  Saca la tarea programada. NO borra el programa, ni la configuracion, ni el
#  historial: con volver a ejecutar instalar.bat queda todo como estaba.
# =============================================================================

$ErrorActionPreference = "Stop"
$RaizProyecto = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "  VACANTIA - Quitar las corridas automaticas" -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""

$Tareas = @(Get-ScheduledTask -ErrorAction SilentlyContinue |
            Where-Object { $_.TaskName -like "Vacantia*" })

if ($Tareas.Count -eq 0) {
    Write-Host "  No habia ninguna corrida automatica configurada."
    Write-Host ""
    Read-Host "  Enter para cerrar"
    exit 0
}

Write-Host "  Se va a desactivar:"
foreach ($t in $Tareas) { Write-Host "    - $($t.TaskName)" }
Write-Host ""
Write-Host "  El programa NO se borra. Tus datos y tu configuracion quedan."
Write-Host "  Para volver a activarlo: doble clic en instalar.bat"
Write-Host ""

$respuesta = Read-Host "  Seguro? (escribi SI para confirmar)"
if ($respuesta -notmatch "^(si|s|sí)$") {
    Write-Host ""
    Write-Host "  Cancelado. No se toco nada."
    Write-Host ""
    Read-Host "  Enter para cerrar"
    exit 0
}

foreach ($t in $Tareas) {
    try {
        Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
        Write-Host "  [OK] Desactivada: $($t.TaskName)" -ForegroundColor Green
    } catch {
        Write-Host "  [X] No se pudo quitar $($t.TaskName): $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "      Proba con boton derecho > Ejecutar como administrador"
    }
}

Write-Host ""
Write-Host "  Listo. Ya no se ejecuta solo."
Write-Host ""
Read-Host "  Enter para cerrar"
