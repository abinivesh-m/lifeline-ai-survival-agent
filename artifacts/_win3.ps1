Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class W3 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int L,T,R,B; }
}
"@
$target = 25800
$wins = New-Object System.Collections.ArrayList
[W3]::EnumWindows({ param($h,$l)
  $p = 0
  [void][W3]::GetWindowThreadProcessId($h,[ref]$p)
  if ($p -eq $target) {
    $sb = New-Object Text.StringBuilder 512
    [void][W3]::GetWindowText($h,$sb,512)
    $cls = New-Object Text.StringBuilder 256
    [void][W3]::GetClassName($h,$cls,256)
    $r = New-Object W3+RECT
    [void][W3]::GetWindowRect($h,[ref]$r)
    [void]$wins.Add([pscustomobject]@{H=[int64]$h;Cls=$cls.ToString();Vis=[W3]::IsWindowVisible($h);Iconic=[W3]::IsIconic($h);Rect="$($r.L),$($r.T) $($r.R-$r.L)x$($r.B-$r.T)";Title=$sb.ToString()})
  }
  return $true
}, [IntPtr]::Zero) | Out-Null
"BEFORE:"; $wins | Format-Table -AutoSize | Out-String -Width 200
foreach ($w in $wins) {
  $h = [IntPtr]$w.H
  [void][W3]::ShowWindow($h,5)
  [void][W3]::ShowWindow($h,9)
  [void][W3]::BringWindowToTop($h)
  [void][W3]::SetForegroundWindow($h)
}
Start-Sleep -Seconds 2
"AFTER:"; $wins | ForEach-Object { [pscustomobject]@{H=$_.H;Vis=[W3]::IsWindowVisible([IntPtr]$_.H);Iconic=[W3]::IsIconic([IntPtr]$_.H);Title=$_.Title} } | Format-Table -AutoSize | Out-String -Width 160
