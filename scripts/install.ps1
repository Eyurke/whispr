# Whispr installer: venv + dependencies + Start Menu shortcut.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\install.ps1 [-Autostart] [-Launch]

param(
    [switch]$Autostart,
    [switch]$Launch
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host "== Whispr installer ==" -ForegroundColor Cyan

# --- find a suitable Python (3.10 - 3.13) ------------------------------
$python = $null
foreach ($candidate in @("3.13", "3.12", "3.11", "3.10")) {
    try {
        & py "-$candidate" -c "pass" 2>$null
        if ($LASTEXITCODE -eq 0) { $python = @("py", "-$candidate"); break }
    } catch {}
}
if (-not $python) {
    try {
        $v = & python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]"3.10" -and [version]$v -lt [version]"3.14") {
            $python = @("python")
        }
    } catch {}
}
if (-not $python) {
    Write-Host "No Python 3.10-3.13 found. Install it from https://www.python.org/downloads/ and re-run." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python: $($python -join ' ')"

# --- venv + dependencies ------------------------------------------------
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & $python[0] $python[1..($python.Length-1)] -m venv .venv
}
$venvPy = Join-Path $repo ".venv\Scripts\python.exe"
$venvPyw = Join-Path $repo ".venv\Scripts\pythonw.exe"

Write-Host "Installing dependencies (this can take a few minutes)..."
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed." -ForegroundColor Red; exit 1 }

# --- Start Menu shortcut ------------------------------------------------
$launcher = Join-Path $repo "run_whispr.pyw"
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Programs")) "Whispr.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $venvPyw
$shortcut.Arguments = "`"$launcher`""
$shortcut.WorkingDirectory = $repo
$shortcut.Description = "Whispr - local push-to-talk dictation"
$shortcut.Save()
Write-Host "Start Menu shortcut created: $shortcutPath"

# --- optional autostart -------------------------------------------------
if ($Autostart) {
    $cmd = "`"$venvPyw`" `"$launcher`""
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Whispr" -Value $cmd
    Write-Host "Autostart enabled (HKCU Run key)."
}

Write-Host ""
Write-Host "Done! Launch 'Whispr' from the Start Menu, then HOLD Ctrl+Win and speak." -ForegroundColor Green
Write-Host "First run downloads the speech model (~460 MB) - watch the tray icon."

if ($Launch) {
    Start-Process $venvPyw "`"$launcher`"" -WorkingDirectory $repo
    Write-Host "Whispr started - look for the tray icon."
}
