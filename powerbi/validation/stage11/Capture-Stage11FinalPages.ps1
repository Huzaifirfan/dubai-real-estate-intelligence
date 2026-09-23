# Final observed-window interaction/capture pass. Does not modify report definitions.
# Coordinates refer to the 1040x744 Desktop window inspected in this validation run.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class Stage11Final {
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left,Top,Right,Bottom; }
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr w,out RECT r);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr w);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr w,IntPtr dc,uint flags);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint data,UIntPtr extra);
 [DllImport("user32.dll")] public static extern void keybd_event(byte key,byte scan,uint flags,UIntPtr extra);
}
'@
$record=Get-Content (Join-Path $PSScriptRoot 'desktop_process.json') -Raw | ConvertFrom-Json
$p=Get-Process -Id $record.pid
if ($p.MainWindowTitle -notlike '*Dubai_Real_Estate_Intelligence*') { throw 'Unexpected window.' }
$handle=$p.MainWindowHandle
$rect=New-Object Stage11Final+RECT
[Stage11Final]::GetWindowRect($handle,[ref]$rect) | Out-Null
if (($rect.Right-$rect.Left) -ne 1040 -or ($rect.Bottom-$rect.Top) -ne 744) { throw 'Window geometry differs from the observed screenshots; inspect before using point interactions.' }
[Stage11Final]::SetForegroundWindow($handle) | Out-Null
function Click-Point([int]$X,[int]$Y,[bool]$Ctrl=$false) {
 [Stage11Final]::SetCursorPos($rect.Left+$X,$rect.Top+$Y) | Out-Null
 if ($Ctrl) { [Stage11Final]::keybd_event(17,0,0,[UIntPtr]::Zero) }
 try {
  [Stage11Final]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
  [Stage11Final]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
 } finally { if ($Ctrl) { [Stage11Final]::keybd_event(17,0,2,[UIntPtr]::Zero) } }
}
function Capture-Page([string]$File) {
 [Stage11Final]::SetCursorPos($rect.Left+25,$rect.Top+28) | Out-Null
 Start-Sleep -Milliseconds 500
 $bitmap=New-Object System.Drawing.Bitmap(1040,744)
 $g=[System.Drawing.Graphics]::FromImage($bitmap)
 $dc=$g.GetHdc()
 try { $ok=[Stage11Final]::PrintWindow($handle,$dc,2) } finally { $g.ReleaseHdc($dc) }
 try { $bitmap.Save((Join-Path $PSScriptRoot $File),[System.Drawing.Imaging.ImageFormat]::Png) } finally { $g.Dispose();$bitmap.Dispose() }
 if (-not $ok) { throw 'PrintWindow failed.' }
 Write-Output "Captured $File"
}
# Clear the Ready checkbox selected by the preceding native slicer test.
Click-Point 583 289
Start-Sleep -Milliseconds 500
Click-Point 464 332
Start-Sleep -Seconds 2
Click-Point 601 307
Start-Sleep -Seconds 2
Capture-Page 'executive_overview_cleared.png'
Click-Point 380 244 $true
Start-Sleep -Seconds 3
Capture-Page 'market_trends.png'
Click-Point 596 244 $true
Start-Sleep -Seconds 3
Capture-Page 'area_intelligence.png'
Click-Point 168 244 $true
Start-Sleep -Seconds 2
Write-Output 'Returned to Executive Overview; inspect captures to certify page results.'
