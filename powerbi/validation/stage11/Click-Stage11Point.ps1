param([Parameter(Mandatory=$true)][int]$X,[Parameter(Mandatory=$true)][int]$Y,[switch]$Ctrl)
# Coordinates must come from a current PrintWindow screenshot of this report.
$ErrorActionPreference='Stop'
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class Stage11Point {
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left,Top,Right,Bottom; }
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr w,out RECT rect);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr w);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint data,UIntPtr extra);
 [DllImport("user32.dll")] public static extern void keybd_event(byte key,byte scan,uint flags,UIntPtr extra);
}
'@
[Stage11Point]::SetProcessDPIAware() | Out-Null
$r=Get-Content (Join-Path $PSScriptRoot 'desktop_process.json') -Raw | ConvertFrom-Json
$p=Get-Process -Id $r.pid
if ($p.MainWindowTitle -notlike '*Dubai_Real_Estate_Intelligence*') { throw 'Unexpected target window.' }
$rect=New-Object Stage11Point+RECT
[Stage11Point]::GetWindowRect($p.MainWindowHandle,[ref]$rect) | Out-Null
if ($X -lt 0 -or $Y -lt 0 -or $X -ge ($rect.Right-$rect.Left) -or $Y -ge ($rect.Bottom-$rect.Top)) { throw 'Point is outside the report window.' }
[Stage11Point]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
[Stage11Point]::SetCursorPos($rect.Left+$X,$rect.Top+$Y) | Out-Null
if ($Ctrl) { [Stage11Point]::keybd_event(17,0,0,[UIntPtr]::Zero) }
try {
 [Stage11Point]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
 [Stage11Point]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
} finally { if ($Ctrl) { [Stage11Point]::keybd_event(17,0,2,[UIntPtr]::Zero) } }
Write-Output "Clicked observed report-window point ($X,$Y)."
