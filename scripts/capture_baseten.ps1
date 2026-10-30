# LIFELINE AI - record the Baseten proof, one command.
#
#   powershell -ExecutionPolicy Bypass -File scripts\capture_baseten.ps1
#
# Produces artifacts/proof/baseten_proof.mp4: 45 s of this desktop while
# `python openweight.py` makes a real call to muse-spark-open-1026 on Baseten.
#
# It records the screen, it does not stage it. If the call fails, the video shows
# the failure and the artefact records an invalid run - which is why the counts
# quoted in the README are re-read from artifacts/openweight_proof.json after
# every capture instead of being typed in.
#
# Before running: close Chrome and anything you would not show a judge. Put this
# terminal where the recording can see it, and do not touch the mouse for the
# first two seconds.

[CmdletBinding()]
param(
    [int]$CountdownSeconds = 6,
    [int]$VideoSeconds = 45
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$proof = Join-Path $root "artifacts\proof"
New-Item -ItemType Directory -Force -Path $proof | Out-Null
$mp4 = Join-Path $proof "baseten_proof.mp4"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Error "ffmpeg is not on PATH. Install it, or record with another tool and say so."
}
if (-not $env:BASETEN_API_KEY) {
    # allocator.load_env() reads .env, so the key may only exist there. The python
    # call will fail loudly if it is missing - no need to guess here.
    Write-Host "BASETEN_API_KEY is not in this shell; openweight.py will read .env." -ForegroundColor DarkGray
}

$before = & python (Join-Path $PSScriptRoot "proof_summary.py")
Write-Host ""
Write-Host "LIFELINE AI - Baseten proof" -ForegroundColor Cyan
Write-Host "  runs on file before this capture: $before (runs, valid)"
Write-Host "  recording ${VideoSeconds}s of screen to artifacts\proof\baseten_proof.mp4"
Write-Host ""
Write-Host "  Arrange the terminal now. Recording in $CountdownSeconds seconds..." -ForegroundColor Yellow
for ($i = $CountdownSeconds; $i -gt 0; $i--) {
    Write-Host "    $i..."
    Start-Sleep -Seconds 1
}

Push-Location $root
$ffmpeg = Start-Process ffmpeg `
    -ArgumentList @("-y", "-f", "gdigrab", "-framerate", "15", "-i", "desktop",
                    "-t", "$VideoSeconds", "-pix_fmt", "yuv420p", $mp4) `
    -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  calling muse-spark-open-1026 on Baseten..." -ForegroundColor Yellow
python openweight.py
$exit = $LASTEXITCODE

Write-Host ""
Write-Host "  waiting for the recorder to finish..." -ForegroundColor Yellow
$ffmpeg.WaitForExit()
Pop-Location

Write-Host ""
Write-Host "  wrote $mp4" -ForegroundColor Green
$after = & python (Join-Path $PSScriptRoot "proof_summary.py")
Write-Host "  artefact now: $after (runs, valid, latencies)" -ForegroundColor Green
if ($exit -ne 0) {
    Write-Warning "openweight.py exited $exit. The video shows what happened; do not claim a valid run."
}

Write-Host ""
Write-Host "Next: refresh the numbers that quote this artefact -" -ForegroundColor Cyan
Write-Host "  python export_ui_data.py"
Write-Host "  update the 'N/M valid' line in README.md and artifacts/proof/README.md"
Write-Host "  python -m pytest -q    (test_claims.py fails if the prose disagrees)"
