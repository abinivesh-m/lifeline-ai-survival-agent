Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
"@
$rows = New-Object System.Collections.ArrayList
[W]::EnumWindows({ param($h,$l)
  $sb = New-Object Text.StringBuilder 256
  [void][W]::GetClassName($h,$sb,256)
  $cls = $sb.ToString()
  if ($cls -like 'Chrome_WidgetWin*') {
    $t = New-Object Text.StringBuilder 256
    [void][W]::GetWindowText($h,$t,256)
    $pid2 = 0
    [void][W]::GetWindowThreadProcessId($h,[ref]$pid2)
    $vis = [W]::IsWindowVisible($h)
    $par = [W]::GetParent($h)
    [void]$rows.Add([pscustomobject]@{
      Handle=[int64]$h; Visible=$vis; Parent=[int64]$par; PID=$pid2
      Title=$t.ToString(); Class=$cls
    })
  }
  return $true
}, [IntPtr]::Zero) | Out-Null
$rows | Sort-Object Visible,PID | Format-Table -AutoSize | Out-String -Width 160
