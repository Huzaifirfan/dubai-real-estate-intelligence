param([string]$OutputName = 'desktop_window_final.png', [int]$Width = 1600, [int]$Height = 1000)
$ErrorActionPreference = 'Stop'
$record = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_process.json') -Raw | ConvertFrom-Json
$process = Get-Process -Id $record.pid
if ($process.ProcessName -ne 'PBIDesktop' -or $process.MainWindowTitle -notlike '*Dubai_Real_Estate_Intelligence*') { throw 'Stage 10 report window is not ready.' }
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Stage10Capture {
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int cx, int cy, uint flags);
}
'@
$handle = $process.MainWindowHandle
[Stage10Capture]::SetWindowPos($handle,[IntPtr]::Zero,0,0,$Width,$Height,0x0016) | Out-Null
Start-Sleep -Milliseconds 1500
$rect = New-Object Stage10Capture+RECT
[Stage10Capture]::GetWindowRect($handle,[ref]$rect) | Out-Null
$bitmap = New-Object System.Drawing.Bitmap(($rect.Right-$rect.Left),($rect.Bottom-$rect.Top))
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
try { $captured = [Stage10Capture]::PrintWindow($handle,$hdc,2) } finally { $graphics.ReleaseHdc($hdc) }
$path = Join-Path $PSScriptRoot $OutputName
try { $bitmap.Save($path,[System.Drawing.Imaging.ImageFormat]::Png) } finally { $graphics.Dispose(); $bitmap.Dispose() }
[pscustomobject]@{captured=$captured;path=$path;windowTitle=$process.MainWindowTitle} | ConvertTo-Json
