# =============================================================================
#  Vacantia — pantalla de estado
#
#  Para que alguien que no programa pueda contestar "esto anda?" sin abrir un
#  log ni el Programador de tareas. Muestra: si esta programado, cuando corrio
#  por ultima vez, como le fue, y que encontro.
# =============================================================================

$ErrorActionPreference = "SilentlyContinue"
$RaizProyecto = Split-Path -Parent $PSScriptRoot
Set-Location $RaizProyecto

function Titulo($texto) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $texto" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}

Titulo "VACANTIA - Estado"

# --- Esta programado? --------------------------------------------------------
$Tareas = @(Get-ScheduledTask | Where-Object { $_.TaskName -like "Vacantia*" })

if ($Tareas.Count -eq 0) {
    Write-Host "  [X] NO esta programado para correr solo." -ForegroundColor Red
    Write-Host ""
    Write-Host "      Ejecuta instalar.bat para activarlo."
} else {
    foreach ($t in $Tareas) {
        $info = $t | Get-ScheduledTaskInfo
        Write-Host "  [OK] Programado: $($t.TaskName)" -ForegroundColor Green
        Write-Host "       Estado actual : $($t.State)"
        if ($info.LastRunTime -and $info.LastRunTime.Year -gt 1999) {
            Write-Host "       Ultima corrida: $($info.LastRunTime)"
            if ($info.LastTaskResult -eq 0) {
                Write-Host "       Resultado     : termino bien" -ForegroundColor Green
            } else {
                Write-Host "       Resultado     : codigo $($info.LastTaskResult)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "       Ultima corrida: todavia no corrio"
        }
        Write-Host "       Proxima       : $($info.NextRunTime)"
    }
}

# --- Que paso en la ultima corrida? -----------------------------------------
Titulo "Ultima busqueda"

$Log = Join-Path $RaizProyecto "vacantia.log"
if (-not (Test-Path $Log)) {
    Write-Host "  Todavia no hay registro de ninguna busqueda."
} else {
    $lineas = Get-Content $Log -Encoding UTF8

    # El resumen final de cada corrida empieza con "=== Listo en".
    $resumen = $lineas | Where-Object { $_ -match "=== Listo en" } | Select-Object -Last 1
    if ($resumen) {
        # Se muestra el resumen crudo del motor: ya viene en castellano.
        Write-Host "  $($resumen -replace '^\[.*?\]\s*\w+\s*', '')"
    }

    $telegram = $lineas | Where-Object { $_ -match "Telegram enviado" } | Select-Object -Last 1
    if ($telegram) {
        $fecha = if ($telegram -match "^\[(.*?)\]") { $Matches[1] } else { "?" }
        Write-Host "  [OK] Ultimo aviso enviado por Telegram: $fecha" -ForegroundColor Green
    } else {
        Write-Host "  [!] Todavia no se envio ningun aviso por Telegram." -ForegroundColor Yellow
        Write-Host "      Puede ser normal si no hubo ofertas que pasen el filtro."
    }

    # Problemas que el motor decidio no considerar fatales pero conviene ver.
    $avisos = $lineas | Where-Object { $_ -match "\bWARNING\b|\bERROR\b" } | Select-Object -Last 5
    if ($avisos) {
        Titulo "Avisos recientes"
        foreach ($a in $avisos) {
            Write-Host "  $($a -replace '^\[.*?\]\s*', '')" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "  Si esto se repite siempre, mandale una foto a Isaias."
    }
}

Titulo "Que hacer"
Write-Host "  Correr una busqueda ahora  ->  buscar_ahora.bat"
Write-Host "  Reinstalar / reparar       ->  instalar.bat"
Write-Host "  Que deje de correr solo    ->  desinstalar.bat"
Write-Host ""
Read-Host "  Enter para cerrar"
