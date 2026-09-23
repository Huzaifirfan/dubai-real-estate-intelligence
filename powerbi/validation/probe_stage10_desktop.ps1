param([switch]$Start)
$ErrorActionPreference = 'Stop'
$stage10Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$stage10Project = Join-Path $stage10Root 'powerbi\Dubai_Real_Estate_Intelligence\Dubai_Real_Estate_Intelligence.pbip'
$stage10Exe = 'C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe'
$stage10PidPath = Join-Path $PSScriptRoot 'desktop_process.json'
if ($Start) {
    if (Test-Path -LiteralPath $stage10PidPath) {
        $oldProbe = Get-Content -LiteralPath $stage10PidPath -Raw | ConvertFrom-Json
        if (Get-Process -Id $oldProbe.pid -ErrorAction SilentlyContinue) {
            throw 'The recorded Desktop process is still running; refusing to launch another instance.'
        }
    }
    $stage10Process = Start-Process -FilePath $stage10Exe -ArgumentList ('"' + $stage10Project + '"') -WindowStyle Hidden -PassThru
    $stage10Record = [pscustomobject]@{pid=$stage10Process.Id;startedUtc=(Get-Date).ToUniversalTime().ToString('o');project=$stage10Project;desktopVersion=(Get-Item -LiteralPath $stage10Exe).VersionInfo.FileVersion}
    $stage10Record | ConvertTo-Json | Set-Content -LiteralPath $stage10PidPath -Encoding UTF8
    $stage10Record | ConvertTo-Json
    return
}
$stage10Record = Get-Content -LiteralPath $stage10PidPath -Raw | ConvertFrom-Json
$stage10Process = Get-Process -Id $stage10Record.pid -ErrorAction SilentlyContinue
$stage10Windows = @()
if ($stage10Process) {
    Add-Type -AssemblyName UIAutomationClient
    $stage10Condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$stage10Record.pid)
    $stage10Elements = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $stage10Condition)
    foreach ($stage10Window in $stage10Elements) {
        $stage10Text = New-Object System.Collections.Generic.List[string]
        $stage10Children = $stage10Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($stage10Element in $stage10Children) {
            if ($stage10Element.Current.Name) { $stage10Text.Add($stage10Element.Current.Name) }
        }
        $stage10Windows += [pscustomobject]@{title=$stage10Window.Current.Name;offscreen=$stage10Window.Current.IsOffscreen;uiText=@($stage10Text | Select-Object -Unique)}
    }
}
$stage10Engines = @(Get-CimInstance Win32_Process -Filter "Name='msmdsrv.exe'" | Select-Object ProcessId,ParentProcessId,CommandLine)
$stage10Probe = [pscustomobject]@{checkedUtc=(Get-Date).ToUniversalTime().ToString('o');pid=$stage10Record.pid;running=[bool]$stage10Process;windowTitle=$stage10Process.MainWindowTitle;windows=$stage10Windows;engines=$stage10Engines;note='Startup/UI text inspection only. This does not certify visual rendering or DAX refresh.'}
$stage10Probe | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_probe.json') -Encoding UTF8
$stage10Probe | ConvertTo-Json -Depth 8
