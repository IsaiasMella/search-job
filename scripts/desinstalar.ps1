# =============================================================================
#  Vacantia — desinstalar
#
#  Para cuando la persona consiguio trabajo y no quiere buscar mas.
#
#  Se hace en dos pasos, y el segundo hay que pedirlo aparte:
#
#    1. Deja de correr solo y borra el programa (tareas programadas + .venv +
#       el registro de las corridas). Esto NO toca los datos de la persona.
#    2. Solo si lo confirma DE NUEVO: borra tambien sus datos — el perfil, el
#       CV, las ofertas guardadas, los documentos generados y las claves.
#
#  Nunca borra la carpeta del proyecto: este script vive adentro.
# =============================================================================

$ErrorActionPreference = "Stop"
$RaizProyecto = Split-Path -Parent $PSScriptRoot
Set-Location $RaizProyecto

function Titulo($texto) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $texto" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}
function Ok($texto)    { Write-Host "  [OK] $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "  [!]  $texto" -ForegroundColor Yellow }
function Error2($texto){ Write-Host "  [X]  $texto" -ForegroundColor Red }

function Borrar($ruta, $etiqueta) {
    if (-not (Test-Path $ruta)) { return $false }
    try {
        Remove-Item $ruta -Recurse -Force -ErrorAction Stop
        Ok "Borrado: $etiqueta"
        return $true
    } catch {
        Error2 "No pude borrar $etiqueta ($($_.Exception.Message))"
        return $false
    }
}

Titulo "VACANTIA - Desinstalar"

# --- Que hay para sacar ------------------------------------------------------
$Tareas = @(Get-ScheduledTask -ErrorAction SilentlyContinue |
            Where-Object { $_.TaskName -like "Vacantia*" })
$Perfiles = @(Get-ChildItem (Join-Path $RaizProyecto "profiles") -Filter *.json -ErrorAction SilentlyContinue |
              Where-Object { $_.BaseName -ne "example" } |
              ForEach-Object { $_.BaseName })

Write-Host "  Se va a desactivar y borrar el programa:"
if ($Tareas.Count -gt 0) {
    foreach ($t in $Tareas) { Write-Host "    - Busqueda automatica: $($t.TaskName)" }
} else {
    Write-Host "    - (no habia busquedas automaticas configuradas)"
}
Write-Host "    - El entorno de Python (.venv)"
Write-Host "    - El registro de las corridas (vacantia.log)"
Write-Host ""
Write-Host "  Tus datos NO se tocan en este paso: perfil, CV, ofertas guardadas"
Write-Host "  y claves quedan como estan. Despues se pregunta aparte."
Write-Host ""

$respuesta = Read-Host "  Seguro? (escribi SI para confirmar)"
if ($respuesta -notmatch "^(si|s|si.)$") {
    Write-Host ""
    Write-Host "  Cancelado. No se toco nada."
    Write-Host ""
    Read-Host "  Enter para cerrar"
    exit 0
}

# --- 1. Las busquedas automaticas -------------------------------------------
Titulo "1 de 3 - Sacando las busquedas automaticas"

if ($Tareas.Count -eq 0) {
    Write-Host "  No habia ninguna configurada."
} else {
    foreach ($t in $Tareas) {
        try {
            Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
            Ok "Desactivada: $($t.TaskName)"
        } catch {
            Error2 "No se pudo quitar $($t.TaskName): $($_.Exception.Message)"
            Aviso "Proba con boton derecho > Ejecutar como administrador"
        }
    }
}

# --- 2. El programa ----------------------------------------------------------
Titulo "2 de 3 - Borrando el programa"

# El .venv puede estar en uso si quedo una corrida abierta: se avisa y sigue.
[void](Borrar (Join-Path $RaizProyecto ".venv") "el entorno de Python")
[void](Borrar (Join-Path $RaizProyecto "vacantia.log") "el registro de corridas")
[void](Borrar (Join-Path $RaizProyecto "__pycache__") "archivos temporales")
[void](Borrar (Join-Path $RaizProyecto ".pytest_cache") "archivos temporales de pruebas")
Get-ChildItem $RaizProyecto -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }

# --- 3. Los datos personales -------------------------------------------------
Titulo "3 de 3 - Tus datos"

Write-Host "  Falta decidir que hacer con lo tuyo:"
foreach ($p in $Perfiles) { Write-Host "    - Perfil y CV de: $p" }
Write-Host "    - Las ofertas guardadas y lo que marcaste (state\)"
Write-Host "    - Los documentos generados (output\)"
Write-Host "    - Tus claves (.env)"
Write-Host ""
Write-Host "  Si los borras NO SE PUEDEN RECUPERAR." -ForegroundColor Yellow
Write-Host "  Si los dejas, podes volver a usar el programa cuando quieras:"
Write-Host "  con ejecutar instalar.bat de nuevo queda todo como estaba."
Write-Host ""

$borrarDatos = Read-Host "  Borrar tambien tus datos? (escribi BORRAR TODO, o Enter para conservarlos)"
if ($borrarDatos -eq "BORRAR TODO") {
    foreach ($p in $Perfiles) {
        [void](Borrar (Join-Path $RaizProyecto "profiles\$p.json") "perfil de $p")
        [void](Borrar (Join-Path $RaizProyecto "resume\$p.md") "CV de $p")
        # Los otros CV del perfil (resume\<perfil>-<id>.md) y su lista de empresas.
        Get-ChildItem (Join-Path $RaizProyecto "resume") -Filter "$p-*.md" -ErrorAction SilentlyContinue |
            ForEach-Object { [void](Borrar $_.FullName "CV $($_.Name)") }
        [void](Borrar (Join-Path $RaizProyecto "companies-$p.json") "empresas de $p")
    }
    [void](Borrar (Join-Path $RaizProyecto "state") "las ofertas guardadas")
    [void](Borrar (Join-Path $RaizProyecto "output") "los documentos generados")
    [void](Borrar (Join-Path $RaizProyecto ".env") "tus claves")
    Write-Host ""
    Ok "Se borro todo. Ya no queda nada tuyo en esta computadora."
} else {
    Write-Host ""
    Ok "Tus datos quedan donde estaban."
}

# --- Cierre ------------------------------------------------------------------
Titulo "LISTO"
Write-Host "  El programa ya no se ejecuta solo y no vuelve a buscar nada."
Write-Host ""
Write-Host "  Si algun dia queres volver a usarlo: doble clic en instalar.bat"
Write-Host ""
Write-Host "  Para sacarlo del todo, borra esta carpeta a mano:"
Write-Host "    $RaizProyecto"
Write-Host ""
Read-Host "  Enter para cerrar"
