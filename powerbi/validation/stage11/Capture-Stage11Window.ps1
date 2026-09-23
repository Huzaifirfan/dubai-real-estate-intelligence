param([string]$OutputName = 'desktop_window_final.png')
$ErrorActionPreference = 'Stop'
$record = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_process.json') -Raw | ConvertFrom-Json
$process = Get-Process -Id $record.pid
if ($process.ProcessName -ne 'PBIDesktop' -or $process.MainWindowTitle -notlike '*Dubai_Real_Estate_Intelligence*') { throw 'Stage 11 report window is not ready.' }
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Stage11Capture {
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int cx, int cy, uint flags);
}
'@
[Stage11Capture]::SetProcessDPIAware() | Out-Null
$handle = $process.MainWindowHandle
# Capture the current native window without resizing it beyond the available screen.
Start-Sleep -Milliseconds 1500
$rect = New-Object Stage11Capture+RECT
[Stage11Capture]::GetWindowRect($handle,[ref]$rect) | Out-Null
$bitmap = New-Object System.Drawing.Bitmap(($rect.Right-$rect.Left),($rect.Bottom-$rect.Top))
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
try { $captured = [Stage11Capture]::PrintWindow($handle,$hdc,2) } finally { $graphics.ReleaseHdc($hdc) }
$path = Join-Path $PSScriptRoot $OutputName
try { $bitmap.Save($path,[System.Drawing.Imaging.ImageFormat]::Png) } finally { $graphics.Dispose(); $bitmap.Dispose() }
[pscustomobject]@{captured=$captured;path=$path;windowTitle=$process.MainWindowTitle} | ConvertTo-Json
