# =============================================================================
#  Vacantia — instalador para Windows
#
#  Pensado para que lo corra alguien que no programa: doble clic en
#  instalar.bat y listo. Este script hace todo lo que haría a mano un técnico:
#
#    1. Busca Python. Si no está, lo instala con winget.
#    2. Crea el entorno virtual .venv
#    3. Instala las dependencias (con el rodeo que necesita python-jobspy)
#    4. Verifica que todo importe
#    5. Registra la tarea programada: al encender + 12:00, 16:30 y 23:59
#    6. Corre una vez para comprobar que anda
#
#  Se puede correr de nuevo cuantas veces se quiera: no rompe nada, actualiza.
# =============================================================================

$ErrorActionPreference = "Stop"

# --- Ubicación ---------------------------------------------------------------
# El script vive en scripts\, el proyecto es la carpeta de arriba.
$RaizProyecto = Split-Path -Parent $PSScriptRoot
Set-Location $RaizProyecto

$Venv       = Join-Path $RaizProyecto ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$VenvPythonW= Join-Path $Venv "Scripts\pythonw.exe"

function Titulo($texto) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $texto" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}
function Ok($texto)    { Write-Host "  [OK] $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "  [!]  $texto" -ForegroundColor Yellow }
function Error2($texto){ Write-Host "  [X]  $texto" -ForegroundColor Red }

Titulo "VACANTIA - Instalacion"
Write-Host "  Carpeta: $RaizProyecto"

# --- 1. Python ---------------------------------------------------------------
Titulo "1 de 6 - Buscando Python"

$PythonBase = $null
# Se prefiere 3.12: en 3.13+ la libreria de LinkedIn necesita compilar numpy,
# y estas maquinas no tienen compilador de C.
foreach ($intento in @(
    @{ cmd = "py";     args = @("-3.12", "--version") },
    @{ cmd = "py";     args = @("-3.11", "--version") },
    @{ cmd = "py";     args = @("-3",    "--version") },
    @{ cmd = "python"; args = @("--version") }
)) {
    try {
        $salida = & $intento.cmd $intento.args 2>$null
        if ($LASTEXITCODE -eq 0 -and $salida -match "Python 3\.(\d+)") {
            $menor = [int]$Matches[1]
            if ($menor -ge 10) {
                $PythonBase = @{ cmd = $intento.cmd; args = $intento.args[0..($intento.args.Length - 2)] }
                Ok "Encontrado: $salida"
                break
            }
        }
    } catch { }
}

if ($null -eq $PythonBase) {
    Aviso "No hay Python instalado. Lo instalo con winget (puede tardar unos minutos)..."
    try {
        winget install --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    } catch {
        Error2 "No se pudo instalar Python automaticamente."
        Write-Host ""
        Write-Host "  Instalalo a mano desde https://www.python.org/downloads/"
        Write-Host "  IMPORTANTE: tildar 'Add Python to PATH' durante la instalacion."
        Write-Host "  Despues volve a ejecutar instalar.bat"
        Read-Host "`n  Enter para cerrar"
        exit 1
    }
    # winget deja el PATH actualizado recien en la proxima sesion.
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    $PythonBase = @{ cmd = "py"; args = @("-3.12") }
    Ok "Python instalado"
}

# --- 2. Entorno virtual ------------------------------------------------------
Titulo "2 de 6 - Preparando el entorno"

if (Test-Path $VenvPython) {
    Ok "El entorno ya existe"
} else {
    Write-Host "  Creando .venv ..."
    & $PythonBase.cmd $PythonBase.args -m venv $Venv
    if (-not (Test-Path $VenvPython)) {
        Error2 "No se pudo crear el entorno virtual."
        Read-Host "`n  Enter para cerrar"
        exit 1
    }
    Ok "Entorno creado"
}

& $VenvPython -m pip install --quiet --upgrade pip 2>$null

# --- 3. Dependencias ---------------------------------------------------------
Titulo "3 de 6 - Instalando dependencias (tarda un par de minutos)"

Write-Host "  Paquetes principales..."
& $VenvPython -m pip install --quiet -r (Join-Path $RaizProyecto "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Error2 "Fallo la instalacion de los paquetes principales."
    Read-Host "`n  Enter para cerrar"
    exit 1
}
Ok "Paquetes principales listos"

# python-jobspy fija NUMPY==1.26.3. En Python 3.12 hay wheel y entra derecho;
# en 3.13+ no hay wheel e intentaria compilar, asi que se instala sin sus pins.
Write-Host "  Libreria de LinkedIn..."
& $VenvPython -m pip install --quiet python-jobspy 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  (el metodo directo no sirve en esta version de Python, uso el alternativo)"
    & $VenvPython -m pip install --quiet "numpy>=2.1" "pandas>=2.2.3" beautifulsoup4 markdownify "pydantic>=2.3" regex tls-client
    & $VenvPython -m pip install --quiet --no-deps python-jobspy
}

& $VenvPython -c "import jobspy" 2>$null
if ($LASTEXITCODE -eq 0) {
    Ok "Libreria de LinkedIn lista"
} else {
    Aviso "No se pudo instalar la libreria de LinkedIn."
    Aviso "No es grave: el programa va a funcionar igual con las otras fuentes."
}

# --- 4. Verificacion ---------------------------------------------------------
Titulo "4 de 6 - Verificando"

& $VenvPython -c "import vacantia.engine, vacantia.scoring, vacantia.filters" 2>$null
if ($LASTEXITCODE -ne 0) {
    Error2 "El programa no arranca. Avisale a Isaias y mostrale esta pantalla."
    Read-Host "`n  Enter para cerrar"
    exit 1
}
Ok "El programa arranca bien"

# Perfiles: pueden ser varios en la misma PC (dos personas de la misma casa).
# No se pregunta cual: se programan TODOS, escalonados.
$Perfiles = @(Get-ChildItem (Join-Path $RaizProyecto "profiles") -Filter *.json |
              Where-Object { $_.BaseName -ne "example" } |
              ForEach-Object { $_.BaseName })

if ($Perfiles.Count -eq 0) {
    Aviso "Todavia no hay ningun perfil cargado."
    Write-Host ""
    Write-Host "  Abri la pantalla con abrir.bat, crea el perfil de la persona que va"
    Write-Host "  a buscar trabajo, y despues volve a ejecutar instalar.bat."
    Write-Host ""
    Read-Host "  Enter para cerrar"
    exit 0
}
Ok "Perfil(es): $($Perfiles -join ', ')"

# Aviso temprano si falta configuracion, antes de programar nada.
$RutaEnv = Join-Path $RaizProyecto ".env"
if (-not (Test-Path $RutaEnv)) {
    Aviso "Falta el archivo .env con las claves. Cargalas desde abrir.bat > Mis datos."
}

# --- 5. Tareas programadas ---------------------------------------------------
Titulo "5 de 6 - Programando las corridas automaticas"

# Los horarios los reparte vacantia.agenda, que es la unica fuente de verdad:
# cada perfil arranca 20 minutos despues del anterior. Los limites del plan
# gratis son de la CUENTA, no del perfil, asi que si dos personas de la misma
# casa arrancan juntas se pisan contra el tope por minuto.
$Reparto = & $VenvPython -m vacantia.agenda --json | ConvertFrom-Json

# Usuario actual, en formato DOMINIO\usuario. Es la clave para que todo esto
# funcione SIN permisos de administrador.
$UsuarioActual = [Security.Principal.WindowsIdentity]::GetCurrent().Name

$Config = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

# Idem: sin -Principal explicito, Register-ScheduledTask intenta registrar con
# privilegios elevados y devuelve "Acceso denegado" en una cuenta comun.
$Principal = New-ScheduledTaskPrincipal -UserId $UsuarioActual `
    -LogonType Interactive -RunLevel Limited

# pythonw.exe en vez de python.exe: no abre ventana negra. El log igual se
# escribe en vacantia.log, asi que no se pierde nada.
$Ejecutable = if (Test-Path $VenvPythonW) { $VenvPythonW } else { $VenvPython }

# Se limpian las tareas viejas antes de registrar: si se borro o se renombro un
# perfil, su tarea quedaria huerfana corriendo un perfil que ya no existe.
Get-ScheduledTask -ErrorAction SilentlyContinue |
    Where-Object { $_.TaskName -like "Vacantia*" } |
    ForEach-Object { Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false -ErrorAction SilentlyContinue }

$Primero = $true
foreach ($Perfil in $Perfiles) {
    $Horarios = $Reparto.$Perfil
    if (-not $Horarios) { $Horarios = @("12:00", "16:30", "23:59") }

    $NombreTarea = "Vacantia - $Perfil"
    $Accion = New-ScheduledTaskAction -Execute $Ejecutable `
        -Argument "-m vacantia.run --profile $Perfil" `
        -WorkingDirectory $RaizProyecto

    # Al encender la maquina + los horarios que le tocaron a este perfil.
    #
    # OJO con el -User de AtLogOn: sin el, Windows entiende "cuando inicie sesion
    # CUALQUIER usuario" y eso exige permisos de administrador. Acotandolo al
    # usuario actual, un usuario comun puede registrar la tarea el solo.
    $Disparadores = @(New-ScheduledTaskTrigger -AtLogOn -User $UsuarioActual)
    foreach ($h in $Horarios) {
        $Disparadores += (New-ScheduledTaskTrigger -Daily -At $h)
    }
    # El retraso al encender tambien se escalona, por el mismo motivo que los
    # horarios: si no, todos los perfiles arrancan juntos al prender la PC.
    if ($Primero) { $Disparadores[0].Delay = "PT3M" } else { $Disparadores[0].Delay = "PT13M" }
    $Primero = $false

    try {
        Register-ScheduledTask -TaskName $NombreTarea `
            -Action $Accion -Trigger $Disparadores -Settings $Config -Principal $Principal `
            -Description "Busca ofertas de trabajo para $Perfil y las manda por Telegram." | Out-Null
        Ok "$Perfil : $($Horarios -join ', ')"
    } catch {
        Error2 "No se pudo programar '$Perfil': $($_.Exception.Message)"
        Aviso "Proba ejecutando instalar.bat con boton derecho > Ejecutar como administrador"
        Read-Host "  Enter para cerrar"
        exit 1
    }
}
Ok "Tambien corren al encender la PC. Si estaba apagada, corren apenas la prendas"

# --- 6. Prueba ---------------------------------------------------------------
Titulo "6 de 6 - Probando"

$PerfilPrueba = $Perfiles[0]
Write-Host "  Corriendo una vez ($PerfilPrueba) para verificar. Puede tardar unos minutos..."
Write-Host "  (podes seguir usando la computadora normalmente)"
Write-Host ""

& $VenvPython -m vacantia.run --profile $PerfilPrueba
$CodigoSalida = $LASTEXITCODE

Titulo "LISTO"
if ($CodigoSalida -eq 0) {
    Ok "Todo funcionando"
} else {
    Aviso "La prueba termino con avisos. Mira el detalle mas arriba."
}
Write-Host ""
Write-Host "  A partir de ahora se ejecuta solo:"
Write-Host "    - Cada vez que prendas la computadora"
foreach ($Perfil in $Perfiles) {
    $h = $Reparto.$Perfil
    if (-not $h) { $h = @("12:00", "16:30", "23:59") }
    Write-Host "    - $Perfil : todos los dias a las $($h -join ', ')"
}
Write-Host ""
Write-Host "  No tenes que hacer nada mas. Las ofertas te llegan por Telegram."
Write-Host ""
Write-Host "  Para ver las ofertas y cargar tus datos: doble clic en abrir.bat"
Write-Host "  Ahi adentro esta todo: buscar ahora sin esperar el horario, y ver"
Write-Host "  como viene funcionando (en Metricas)."
Write-Host "  Para que deje de correr solo:     doble clic en desinstalar.bat"
Write-Host ""
Read-Host "  Enter para cerrar"
