Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class W2 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
"@
$rows = New-Object System.Collections.ArrayList
[W2]::EnumWindows({ param($h,$l)
  $sb = New-Object Text.StringBuilder 256
  [void][W2]::GetClassName($h,$sb,256)
  $cls = $sb.ToString()
  if ($cls -match 'Chrome|Chromium|Edge|WebView') {
    $t = New-Object Text.StringBuilder 512
    [void][W2]::GetWindowText($h,$t,512)
    $p = 0
    [void][W2]::GetWindowThreadProcessId($h,[ref]$p)
    $name = try { (Get-Process -Id $p -ErrorAction Stop).ProcessName } catch { '?' }
    [void]$rows.Add([pscustomobject]@{ Handle=[int64]$h; Vis=[W2]::IsWindowVisible($h); PID=$p; Proc=$name; Class=$cls; Title=$t.ToString() })
  }
  return $true
}, [IntPtr]::Zero) | Out-Null
$rows | Where-Object { $_.Title -ne '' -or $_.Vis } | Sort-Object Proc,PID | Format-Table -AutoSize | Out-String -Width 200
"--- automation-ish processes ---"
Get-Process | Where-Object { $_.ProcessName -match 'chrom|node|electron' } | Group-Object ProcessName | Select-Object Name,Count | Format-Table -AutoSize | Out-String -Width 60
