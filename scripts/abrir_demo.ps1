# Donaria Connect - abre la demo completa en Windows: API (fase 2) + web conectada a la base (fase 3).
# Se puede correr varias veces: actualiza el codigo, aplica los cambios de la base y vuelve a levantar todo.
# Uso: doble clic en "ABRIR DEMO (doble clic).bat", o en PowerShell:  powershell -ExecutionPolicy Bypass -File abrir_demo.ps1
$ErrorActionPreference = "Stop"
$destino = Join-Path $HOME "donaria-connect"

function Falta($que, $como) {
    Write-Host ""
    Write-Host "FALTA: $que" -ForegroundColor Red
    Write-Host $como -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}
function Liberar($puerto) {
    Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host "== Donaria Connect: preparando la demo ==" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Falta "Git" "Instalalo con:  winget install Git.Git   y vuelve a abrir este archivo."
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Falta "Python" "Instalalo con:  winget install Python.Python.3.12   y vuelve a abrir este archivo."
}
$odbc = Get-OdbcDriver -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "ODBC Driver 18 for SQL Server*" }
if (-not $odbc) {
    Falta "ODBC Driver 18 for SQL Server" "Descargalo de https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server (x64) e instalalo."
}
Write-Host "[ok] Git, Python y driver ODBC 18" -ForegroundColor Green

if (Test-Path (Join-Path $destino ".git")) {
    git -C $destino pull
} else {
    git clone https://github.com/PlayerCero/donaria-connect.git $destino
}
Write-Host "[ok] Codigo actualizado en $destino" -ForegroundColor Green

$envFile = Join-Path $destino ".env"
if (-not (Test-Path $envFile)) {
    $secreto = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    (Get-Content (Join-Path $destino ".env.example")) `
        -replace '^DB_USER=.*', 'DB_USER=eric.salinas@alum.udep.edu.pe' `
        -replace '^JWT_SECRET=.*', "JWT_SECRET=$secreto" |
        Set-Content $envFile -Encoding UTF8
    Write-Host "[ok] Archivo .env creado (con una clave propia para los tokens)" -ForegroundColor Green
}

Set-Location (Join-Path $destino "api")
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $py -m pip install -q --disable-pip-version-check -r requirements-dev.txt
Write-Host "[ok] Dependencias instaladas" -ForegroundColor Green

Write-Host "`n== Pruebas automaticas (sin base) ==" -ForegroundColor Cyan
& $py -m pytest -q

Write-Host "`n== Cambios de la base (fase 3: respuestas de los donantes) ==" -ForegroundColor Cyan
Write-Host "Si se abre el inicio de sesion de Microsoft, entra con tu cuenta de la UDEP." -ForegroundColor Yellow
& $py (Join-Path $destino "scripts\migrar.py")
if ($LASTEXITCODE -ne 0) { Falta "aplicar los cambios de la base" "Revisa el mensaje de arriba (firewall de Azure o inicio de sesion) y vuelve a abrir este archivo." }

Write-Host "`n== Levantando la API y la web ==" -ForegroundColor Cyan
Liberar 8000; Liberar 5500
Start-Sleep -Seconds 1
Start-Process powershell -ArgumentList '-NoExit', '-Command', "`$host.UI.RawUI.WindowTitle='Donaria API (no cerrar)'; Set-Location '$destino\api'; & '$py' -m uvicorn app.main:app"
Start-Process $py -ArgumentList '-m', 'http.server', '5500', '--bind', '127.0.0.1' -WorkingDirectory (Join-Path $destino "web") -WindowStyle Minimized

$vivo = $false
foreach ($i in 1..30) {
    try { Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null; $vivo = $true; break } catch { Start-Sleep -Seconds 1 }
}
if (-not $vivo) { Falta "la API no arranco" "Mira la ventana 'Donaria API' para ver el error." }
Start-Process "http://127.0.0.1:5500/#inicio"

Write-Host ""
Write-Host "Demo abierta en http://127.0.0.1:5500  (API en http://127.0.0.1:8000/docs)" -ForegroundColor Green
Write-Host "La primera carga puede tardar hasta un minuto mientras Azure despierta la base." -ForegroundColor Yellow
Write-Host "Si se abre el inicio de sesion de Microsoft, entra con tu cuenta de la UDEP." -ForegroundColor Yellow
Read-Host "Deja abierta la ventana 'Donaria API' mientras uses la demo. Presiona Enter para cerrar esta"
