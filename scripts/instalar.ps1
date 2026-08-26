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

# Perfil: si hay uno solo, se usa ese. Si hay varios, se pregunta.
$Perfiles = @(Get-ChildItem (Join-Path $RaizProyecto "profiles") -Filter *.json |
              Where-Object { $_.BaseName -ne "example" } |
              ForEach-Object { $_.BaseName })

if ($Perfiles.Count -eq 0) {
    Error2 "No hay ningun perfil en la carpeta profiles\. Avisale a Isaias."
    Read-Host "`n  Enter para cerrar"
    exit 1
} elseif ($Perfiles.Count -eq 1) {
    $Perfil = $Perfiles[0]
    Ok "Perfil: $Perfil"
} else {
    Write-Host "  Hay varios perfiles: $($Perfiles -join ', ')"
    $Perfil = Read-Host "  Escribi cual usar"
    if ($Perfiles -notcontains $Perfil) {
        Error2 "Ese perfil no existe."
        Read-Host "`n  Enter para cerrar"
        exit 1
    }
}

# Aviso temprano si falta configuracion, antes de programar nada.
$RutaEnv = Join-Path $RaizProyecto ".env"
if (-not (Test-Path $RutaEnv)) {
    Aviso "Falta el archivo .env con las claves. El programa va a correr limitado."
    Aviso "Pediselo a Isaias y pegalo en: $RaizProyecto"
}

# --- 5. Tarea programada -----------------------------------------------------
Titulo "5 de 6 - Programando las corridas automaticas"

$NombreTarea = "Vacantia - $Perfil"

# pythonw.exe en vez de python.exe: no abre ventana negra. El log igual se
# escribe en vacantia.log, asi que no se pierde nada.
$Ejecutable = if (Test-Path $VenvPythonW) { $VenvPythonW } else { $VenvPython }

$Accion = New-ScheduledTaskAction -Execute $Ejecutable `
    -Argument "-m vacantia.run --profile $Perfil" `
    -WorkingDirectory $RaizProyecto

# Usuario actual, en formato DOMINIO\usuario. Es la clave para que todo esto
# funcione SIN permisos de administrador.
$UsuarioActual = [Security.Principal.WindowsIdentity]::GetCurrent().Name

# Al encender la maquina (con 3 min de espera para que levante la red) y en los
# tres horarios elegidos: mediodia, antes de que RRHH se vaya, y tarde para los
# que publican fuera de horario.
#
# OJO con el -User de AtLogOn: sin el, Windows entiende "cuando inicie sesion
# CUALQUIER usuario" y eso exige permisos de administrador. Acotandolo al
# usuario actual, un usuario comun puede registrar la tarea el solo.
$Disparadores = @(
    (New-ScheduledTaskTrigger -AtLogOn -User $UsuarioActual),
    (New-ScheduledTaskTrigger -Daily -At "12:00"),
    (New-ScheduledTaskTrigger -Daily -At "16:30"),
    (New-ScheduledTaskTrigger -Daily -At "23:59")
)
$Disparadores[0].Delay = "PT3M"

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

try {
    Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $NombreTarea `
        -Action $Accion -Trigger $Disparadores -Settings $Config -Principal $Principal `
        -Description "Busca ofertas de trabajo y las manda por Telegram." | Out-Null
    Ok "Tarea programada: al encender la PC + 12:00, 16:30 y 23:59"
    Ok "Si la PC estaba apagada a esa hora, corre apenas la prendas"
} catch {
    Error2 "No se pudo programar la tarea: $($_.Exception.Message)"
    Aviso "Proba ejecutando instalar.bat con boton derecho > Ejecutar como administrador"
    Read-Host "`n  Enter para cerrar"
    exit 1
}

# --- 6. Prueba ---------------------------------------------------------------
Titulo "6 de 6 - Probando"

Write-Host "  Corriendo una vez para verificar. Puede tardar unos minutos..."
Write-Host "  (podes seguir usando la computadora normalmente)"
Write-Host ""

& $VenvPython -m vacantia.run --profile $Perfil
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
Write-Host "    - Todos los dias a las 12:00, 16:30 y 23:59"
Write-Host ""
Write-Host "  No tenes que hacer nada mas. Las ofertas te llegan por Telegram."
Write-Host ""
Write-Host "  Si alguna vez queres ver como viene: doble clic en estado.bat"
Write-Host "  Para que deje de correr solo:     doble clic en desinstalar.bat"
Write-Host ""
Read-Host "  Enter para cerrar"
