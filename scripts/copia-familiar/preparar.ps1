# =============================================================================
#  Vacantia - preparar la copia de un familiar
#
#  Lo corre Isaias UNA VEZ, en la carpeta recien descargada para la otra
#  persona, antes de instalar:
#
#      powershell -NoProfile -ExecutionPolicy Bypass -File scripts\copia-familiar\preparar.ps1
#
#  Deja la copia independiente: su propio repo de git, el CLAUDE.md y los
#  permisos pensados para alguien que no programa. Se puede correr de nuevo:
#  no pisa nada que ya este.
#
#  Los textos van sin acentos: Windows PowerShell 5.1 lee los .ps1 sin BOM como
#  ANSI y los acentos salen rotos en pantalla.
# =============================================================================

$ErrorActionPreference = "Stop"

$Aca  = $PSScriptRoot
$Raiz = Split-Path -Parent (Split-Path -Parent $Aca)
Set-Location $Raiz

function Titulo($texto) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $texto" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}
function Ok($texto)    { Write-Host "  [OK] $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "  [!]  $texto" -ForegroundColor Yellow }
function Error2($texto){ Write-Host "  [X]  $texto" -ForegroundColor Red }
function Cerrar($codigo) { Read-Host "`n  Enter para cerrar" | Out-Null; exit $codigo }

Titulo "VACANTIA - Preparar la copia de un familiar"
Write-Host "  Carpeta: $Raiz"

# --- 1. Git instalado --------------------------------------------------------
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Error2 "Git no esta instalado."
    Write-Host "  Instalalo con:  winget install Git.Git GitHub.cli"
    Write-Host "  Cerra esta ventana, abri una nueva y volve a correr este script."
    Cerrar 1
}

# --- 2. Que no sea el repo de Isaias -----------------------------------------
# Es la guarda mas importante: correr esto en el repo de desarrollo le pisaria
# el CLAUDE.md y le pondria permisos que no son para el. Un repo conectado a
# IsaiasMella/search-job es el suyo, o una copia que todavia no se separo.
if (Test-Path (Join-Path $Raiz ".git")) {
    $remotos = (& git remote -v 2>$null) -join "`n"
    if ($remotos -match "IsaiasMella/search-job") {
        Error2 "Esta carpeta todavia esta conectada al repo de Isaias."
        Write-Host ""
        Write-Host "  Si es la copia para un familiar: borra la carpeta .git y volve a correr esto."
        Write-Host "  Si es tu carpeta de trabajo: no hagas nada, no se toco ningun archivo."
        Cerrar 1
    }
    $YaTieneRepo = $true
} else {
    $YaTieneRepo = $false
}

# --- 3. El CLAUDE.md y los permisos ------------------------------------------
Titulo "1 de 3 - Claude Code"

$ClaudeFamilia = Join-Path $Aca "CLAUDE.md"
$ClaudeRaiz    = Join-Path $Raiz "CLAUDE.md"
# La marca es la frase entera del comentario del CLAUDE.md de familia, no sólo
# "copia-familiar": el CLAUDE.md de Isaias nombra la carpeta scripts/copia-familiar,
# y con la palabra suelta se creia que ya estaba puesto y no lo copiaba.
$Marca         = "copia-familiar: este archivo lo instala"

if ((Test-Path $ClaudeRaiz) -and ((Get-Content $ClaudeRaiz -Raw -Encoding UTF8) -match $Marca)) {
    Ok "CLAUDE.md ya es el de la copia"
} else {
    Copy-Item $ClaudeFamilia $ClaudeRaiz -Force
    Ok "CLAUDE.md para alguien que no programa"
}

$DirClaude = Join-Path $Raiz ".claude"
$Settings  = Join-Path $DirClaude "settings.json"
if (Test-Path $Settings) {
    Aviso ".claude\settings.json ya existia: no lo toco"
} else {
    New-Item -ItemType Directory -Force $DirClaude | Out-Null
    Copy-Item (Join-Path $Aca "settings.json") $Settings
    Ok "Permisos: no puede borrar historial ni tocar las claves"
}

# Los permisos de desarrollo de Isaias no viajan con la copia.
$Local = Join-Path $DirClaude "settings.local.json"
if (Test-Path $Local) {
    Remove-Item $Local -Force
    Ok "Saque los permisos locales de Isaias"
}

# --- 4. El repo propio -------------------------------------------------------
Titulo "2 de 3 - Repo propio"

if ($YaTieneRepo) {
    Ok "Ya tiene su propio repo: no lo toco"
} else {
    & git init -b main | Out-Null
    Ok "Repo nuevo, rama main"
}

# Sin nombre y mail configurados, git no deja hacer commits. Se guardan en ESTE
# repo y no en la computadora entera.
if (-not (& git config user.name 2>$null)) {
    $nombre = Read-Host "  Nombre de la persona (para el historial)"
    & git config user.name $nombre
}
if (-not (& git config user.email 2>$null)) {
    $mail = Read-Host "  Mail de su cuenta de GitHub"
    & git config user.email $mail
}

& git add -A
$pendiente = & git status --porcelain
if ($pendiente) {
    $mensaje = if ($YaTieneRepo) { "Configuracion de Claude Code para la copia" } else { "Copia inicial de vacantia" }
    & git commit -q -m $mensaje
    Ok "Commit: $mensaje"
} else {
    Ok "No habia nada nuevo para guardar"
}

# --- 5. Lo que falta, a mano -------------------------------------------------
Titulo "3 de 3 - Subirlo a su GitHub"

$tieneRemoto = (& git remote 2>$null)
if ($tieneRemoto) {
    Ok "Ya esta conectado a: $((& git remote get-url origin 2>$null))"
} else {
    Write-Host "  Con la cuenta de GitHub de la persona, corre estos dos comandos:"
    Write-Host ""
    Write-Host "    gh auth login --web" -ForegroundColor White
    Write-Host "    gh repo create vacantia --private --source . --push" -ForegroundColor White
    Write-Host ""
    Write-Host "  El primero abre el navegador para entrar a GitHub: no hace falta ninguna clave SSH."
}

Titulo "LISTO"
Write-Host "  Despues:"
Write-Host "    1. Borra o renombra en profiles\ los perfiles que no son de esta persona."
Write-Host "    2. Doble clic en instalar.bat"
Write-Host "    3. abrir.bat > Mi perfil: claves, CV, palabras clave y Telegram."
Write-Host ""
Write-Host "  La guia completa esta en NOTAS-PARA-ISAIAS.md, seccion 2.32."
Cerrar 0
