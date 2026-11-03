# show_browser.ps1
#
# WHY THIS EXISTS
# The browser automation runs Microsoft Edge with `--no-startup-window`. Its
# windows are created invisible, minimized, and parked off-screen at
# (-25600, -25600) with a 159x27 rect. `browser.screenshot` refuses to capture a
# tab whose desktop window is not visible ("Screenshot needs a visible tab").
#
# AppActivate / SetForegroundWindow alone do NOT fix it: those change z-order,
# not size or position. The window has to be shown AND moved back onto the
# primary monitor.
#
# WHAT IT DOES
#   1. finds the Edge process started with --no-startup-window
#   2. for every top-level window it owns: ShowWindow(SW_SHOW), ShowWindow(SW_RESTORE)
#   3. SetWindowPos to the top-left of the primary screen at a usable size
#   4. BringWindowToTop + SetForegroundWindow
#
# USAGE
#   powershell -ExecutionPolicy Bypass -File show_browser.ps1
#   powershell -ExecutionPolicy Bypass -File show_browser.ps1 -Width 1600 -Height 1000
#
# Then call browser.tabs.focus followed by browser.screenshot.

param(
    [string]$ProcName = "msedge",
    [int]$Width = 1440,
    [int]$Height = 960,
    [int]$X = 0,
    [int]$Y = 0
)

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public class LifelineWin {
    public delegate bool EnumProc(IntPtr h, IntPtr l);

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);

    public struct RECT { public int L, T, R, B; }

    public const int SW_SHOW = 5;
    public const int SW_RESTORE = 9;
    public const uint SWP_SHOWWINDOW = 0x0040;
    public static readonly IntPtr HWND_TOP = IntPtr.Zero;
}
"@

$targets = Get-CimInstance Win32_Process -Filter "Name='$ProcName.exe'" |
    Where-Object { $_.CommandLine -match '--no-startup-window' } |
    Select-Object -ExpandProperty ProcessId

if (-not $targets) {
    Write-Host "No $ProcName process with --no-startup-window found." -ForegroundColor Yellow
    Write-Host "Open a browser tab through the automation first (browser.tabs.open)."
    exit 1
}

foreach ($target in $targets) {
    Write-Host "automation browser pid $target"

    $wins = New-Object System.Collections.ArrayList
    [LifelineWin]::EnumWindows({
        param($h, $l)
        $p = 0
        [void][LifelineWin]::GetWindowThreadProcessId($h, [ref]$p)
        if ($p -eq $target) {
            $cls = New-Object System.Text.StringBuilder 256
            [void][LifelineWin]::GetClassName($h, $cls, 256)
            $name = $cls.ToString()
            if ($name -like 'Chrome_WidgetWin*') {
                $title = New-Object System.Text.StringBuilder 512
                [void][LifelineWin]::GetWindowText($h, $title, 512)
                [void]$wins.Add([pscustomobject]@{ Handle = [int64]$h; Title = $title.ToString(); Class = $name })
            }
        }
        return $true
    }, [IntPtr]::Zero) | Out-Null

    if (-not $wins) {
        Write-Host "  no Chrome_WidgetWin window yet - open a tab, then re-run." -ForegroundColor Yellow
        continue
    }

    foreach ($w in $wins) {
        $h = [IntPtr]$w.Handle
        [void][LifelineWin]::ShowWindow($h, [LifelineWin]::SW_SHOW)
        [void][LifelineWin]::ShowWindow($h, [LifelineWin]::SW_RESTORE)
        [void][LifelineWin]::SetWindowPos(
            $h, [LifelineWin]::HWND_TOP, $X, $Y, $Width, $Height,
            [LifelineWin]::SWP_SHOWWINDOW
        )
        [void][LifelineWin]::BringWindowToTop($h)
        [void][LifelineWin]::SetForegroundWindow($h)

        $r = New-Object LifelineWin+RECT
        [void][LifelineWin]::GetWindowRect($h, [ref]$r)
        $state = if ([LifelineWin]::IsWindowVisible($h)) { "visible" } else { "HIDDEN" }
        $rect = "$($r.L),$($r.T) $($r.R - $r.L)x$($r.B - $r.T)"
        Write-Host ("  handle {0,-10} {1,-8} {2,-10} {3}" -f $w.Handle, $state, $rect, $w.Title)
    }
}

Write-Host ""
Write-Host "done. now: browser.tabs.focus, then browser.screenshot." -ForegroundColor Green
