# shot.ps1
#
# Deterministic screenshots that do NOT depend on the automation window's
# visibility, position, DPI scaling, or minimized state.
#
# WHY: the automation browser runs Edge with `--no-startup-window`. That shell
# has no tab host attached until a tab is focused, so the window can render as a
# black rectangle even when IsWindowVisible() is true. browser.screenshot also
# refuses to capture a tab whose desktop window is not visible. Both are avoided
# by launching a separate headless instance with its own profile.
#
# USAGE
#   powershell -ExecutionPolicy Bypass -File shot.ps1
#   powershell -ExecutionPolicy Bypass -File shot.ps1 -Width 1920 -Height 1080
#
# IMPORTANT - read before using a tall Height for a "full page" shot.
# A tall viewport (e.g. -Height 9000) does NOT produce a valid full-page capture
# of this app. Every section below the hero uses scroll-reveal with
# initial opacity 0; the IntersectionObserver never fires for a viewport that is
# already 9000 px tall, so those sections render pure black. The result looks
# like a full page and is almost entirely empty.
#
# For a full-page capture use the live tab instead (see SCREENSHOTS.md):
#   1. show_browser.ps1          # make the automation window visible
#   2. browser.tabs.focus
#   3. scroll the page in steps so reveals fire
#   4. browser.screenshot { fullPage: true }
#
# This script is the right tool for hero / above-the-fold shots at an exact
# viewport size, including 1920x1080 which the physical display cannot reach
# because it is 1920x1080 @ 125% scaling (CSS viewport caps at ~1536).

param(
    [string]$Url = "http://127.0.0.1:3000/",
    [int]$Width = 1920,
    [int]$Height = 1080,
    [string]$Out = "artifacts\shots\shot.png",
    [int]$WaitMs = 9000
)

$ErrorActionPreference = "Stop"

$edge = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $edge) { throw "No Edge or Chrome binary found." }

$outFull = if ([System.IO.Path]::IsPathRooted($Out)) { $Out } else { Join-Path (Get-Location) $Out }
$outDir = Split-Path $outFull -Parent
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Remove-Item $outFull -ErrorAction SilentlyContinue

$profile = Join-Path $env:TEMP ("lifeline-shot-" + [guid]::NewGuid().ToString("N").Substring(0, 8))

try {
    # Each value is quoted because the workspace path contains a space.
    $args = @(
        "--headless=new",
        "--disable-gpu",
        "--enable-unsafe-swiftshader",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--no-first-run",
        "--disable-extensions",
        "--user-data-dir=`"$profile`"",
        "--window-size=$Width,$Height",
        "--virtual-time-budget=$WaitMs",
        "--screenshot=`"$outFull`"",
        "`"$Url`""
    )

    # Start-Process rather than '&': PowerShell 5.1 turns Chromium's stderr
    # noise (task_manager warnings) into a terminating NativeCommandError.
    $proc = Start-Process -FilePath $edge -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 800

    if (-not (Test-Path $outFull)) { throw "No screenshot written to $outFull" }

    Add-Type -AssemblyName System.Drawing
    $img = [System.Drawing.Image]::FromFile($outFull)
    $w = $img.Width; $h = $img.Height
    $img.Dispose()

    $kb = [math]::Round((Get-Item $outFull).Length / 1KB, 1)
    Write-Host "OK  ${w}x${h}  ${kb} KB  $outFull" -ForegroundColor Green
}
finally {
    Start-Sleep -Milliseconds 300
    Remove-Item $profile -Recurse -Force -ErrorAction SilentlyContinue
}
