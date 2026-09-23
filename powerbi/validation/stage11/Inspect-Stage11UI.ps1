param([string]$Action='Inspect',[string]$Name,[string]$Type='Button',[string]$OutputName='ui_current.json')
$ErrorActionPreference='Stop'
Add-Type @'
using System.Runtime.InteropServices;
public static class Stage11Dpi { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
'@
[Stage11Dpi]::SetProcessDPIAware() | Out-Null
Add-Type -AssemblyName UIAutomationClient
$record=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_process.json') -Raw | ConvertFrom-Json
$process=Get-Process -Id $record.pid
$window=[System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
$nodes=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
if ($Action -in @('Invoke','Click','CtrlClick')) {
    $element=@($nodes | Where-Object { $_.Current.Name -eq $Name -and $_.Current.ControlType.ProgrammaticName -eq ('ControlType.'+$Type) -and -not $_.Current.IsOffscreen }) | Select-Object -First 1
    if (-not $element) { throw "No visible $Type named $Name" }
    if ($Action -in @('Click','CtrlClick')) {
        Add-Type @'
using System; using System.Runtime.InteropServices;
public static class Stage11Click {
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint dx,uint dy,uint data,UIntPtr extra);
 [DllImport("user32.dll")] public static extern void keybd_event(byte key,byte scan,uint flags,UIntPtr extra);
}
'@
        [Stage11Click]::SetForegroundWindow($process.MainWindowHandle) | Out-Null
        $rect=$element.Current.BoundingRectangle
        [Stage11Click]::SetCursorPos([int]($rect.X+$rect.Width/2),[int]($rect.Y+$rect.Height/2)) | Out-Null
        if ($Action -eq 'CtrlClick') { [Stage11Click]::keybd_event(17,0,0,[UIntPtr]::Zero) }
        try {
            [Stage11Click]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
            [Stage11Click]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
        } finally { if ($Action -eq 'CtrlClick') { [Stage11Click]::keybd_event(17,0,2,[UIntPtr]::Zero) } }
        Write-Output "$Action on $Type $Name"
        return
    }
    $pattern=$null
    if ($element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$pattern)) { $pattern.Invoke() }
    elseif ($element.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$pattern)) { $pattern.Select() }
    elseif ($element.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$pattern)) {
        if ($pattern.Current.ExpandCollapseState -eq [System.Windows.Automation.ExpandCollapseState]::Expanded) { $pattern.Collapse() } else { $pattern.Expand() }
    }
    else { throw 'Element does not expose a supported interaction pattern.' }
    Write-Output "Invoked $Type $Name"
    return
}
$data=@($nodes | Where-Object { $_.Current.Name -and -not $_.Current.IsOffscreen } | ForEach-Object {
    [ordered]@{name=$_.Current.Name;type=$_.Current.ControlType.ProgrammaticName;id=$_.Current.AutomationId;bounds=$_.Current.BoundingRectangle.ToString()}
})
$data | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot $OutputName) -Encoding UTF8
$data | Where-Object { $_.name -match 'card$|Error|error|See details' -and $_.type -eq 'ControlType.Button' } | ConvertTo-Json -Depth 4
