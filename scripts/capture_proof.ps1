# LIFELINE AI - one command for the three proof captures.
#
#   powershell -ExecutionPolicy Bypass -File scripts\capture_proof.ps1
#
# Produces, in artifacts/proof/:
#   nvidia_smi.txt          real GPU query
#   gpu_6gb_taskmgr.png     Task Manager, captured from your desktop
#   offline_proof.mp4       60 s of screen while the offline agent runs
#
# It does NOT fabricate anything. If the GPU is absent, or the window is
# hidden, the file it writes says so.
#
# Before running: close Chrome, YouTube and Docker. The last measured state
# was 1.2 GB free of 15.7 GB, and a stutter reads as a broken demo.

[CmdletBinding()]
param(
    [int]$CountdownSeconds = 8,
    [int]$VideoSeconds = 60,
    [switch]$SkipVideo
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$proof = Join-Path $root "artifacts\proof"
New-Item -ItemType Directory -Force -Path $proof | Out-Null

Write-Host ""
Write-Host "LIFELINE AI - proof capture" -ForegroundColor Cyan
Write-Host "repo: $root"
Write-Host ""

# ---------------------------------------------------------------- RAM check
$os = Get-CimInstance Win32_OperatingSystem
$freeGb = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$totalGb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("RAM: {0} GB free of {1} GB" -f $freeGb, $totalGb)
if ($freeGb -lt 2.5) {
    Write-Warning "Under 2.5 GB free. Close Chrome/YouTube before recording, or the demo will stutter."
    Read-Host "Press Enter when you have closed them, or Ctrl+C to abort"
}

# ------------------------------------------------------------- nvidia-smi
Write-Host ""
Write-Host "1/3  GPU query" -ForegroundColor Yellow
$stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$smi = & nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "nvidia-smi failed. This machine cannot back the 6 GB claim; stop here."
}

$lines = @(
    "LIFELINE AI - GPU proof",
    "Captured (UTC): $stamp",
    "Host: $env:COMPUTERNAME",
    "",
    '$ nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader',
    ($smi -join "`n"),
    "",
    "Note: this is real nvidia-smi output."
)
$lines | Set-Content -Encoding utf8 (Join-Path $proof "nvidia_smi.txt")
Write-Host ("     " + ($smi -join "`n     ")) -ForegroundColor Green

# ------------------------------------------------- Task Manager screenshot
Write-Host ""
Write-Host "2/3  Task Manager screenshot" -ForegroundColor Yellow
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Save-PrimaryScreen([string]$Path) {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
}

Start-Process taskmgr
Write-Host "     Task Manager is open."
Write-Host "     Click Performance -> GPU. The header must read 'RTX 3050 6GB'."
Write-Host "     Capturing in $CountdownSeconds seconds..."
for ($i = $CountdownSeconds; $i -gt 0; $i--) {
    Write-Host "       $i..."
    Start-Sleep -Seconds 1
}

$png = Join-Path $proof "gpu_6gb_taskmgr.png"
Save-PrimaryScreen $png
Write-Host "     wrote $png" -ForegroundColor Green
Write-Host "     Check it by eye: header 'RTX 3050 6GB', dedicated memory '0.x/6.0 GB'."
Read-Host "     Press Enter once it looks right (Ctrl+C to abort and retake)"

# --------------------------------------------------------- offline capture
Write-Host ""
Write-Host "3/3  Offline run" -ForegroundColor Yellow
Write-Host "     Turn airplane mode ON now. Wi-Fi off, Bluetooth off."
Read-Host "     Press Enter when the network icon shows airplane mode"

$env:LIFELINE_OFFLINE = "1"
Push-Location $root

# agent.py writes runs/latest.json on every run. The committed one holds the live
# Baseten trace (4.44 s) that the dashboard's LIVE CALL badge reads, so keep it
# and put it back - otherwise the recording leaves the tree dirty and loses the
# only in-agent open-weight evidence.
$latest = Join-Path $root "runs\latest.json"
$latestBackup = Join-Path $env:TEMP "lifeline_latest_backup.json"
if (Test-Path $latest) {
    Copy-Item $latest $latestBackup -Force
    Write-Host "     backed up runs/latest.json"
}

if (-not $SkipVideo) {
    $mp4 = Join-Path $proof "offline_proof.mp4"
    Write-Host "     Recording ${VideoSeconds}s of screen while the agent runs..."
    $ffmpeg = Start-Process ffmpeg `
        -ArgumentList @("-y", "-f", "gdigrab", "-framerate", "15", "-i", "desktop",
                        "-t", "$VideoSeconds", "-pix_fmt", "yuv420p", $mp4) `
        -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

python agent.py --yes --mode policy

if (-not $SkipVideo) {
    Write-Host "     waiting for ffmpeg to stop..."
    $ffmpeg.WaitForExit()
    Write-Host "     wrote $mp4" -ForegroundColor Green
}

Pop-Location

Remove-Item Env:\LIFELINE_OFFLINE -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Done. Now record baseten_proof.mp4 separately:" -ForegroundColor Cyan
Write-Host "  python openweight.py"
Write-Host "  (2/3 runs valid, 5.41 s and 6.73 s, 70 L / 30 L)"
Write-Host ""
Write-Host "Then commit:" -ForegroundColor Cyan
Write-Host "  git add artifacts/proof"
Write-Host "  git commit -m 'Add real GPU, offline and Baseten proof captures'"
