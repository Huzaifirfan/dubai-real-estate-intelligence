param([switch]$Start)
$ErrorActionPreference = 'Stop'
$stage11Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$stage11Project = Join-Path $stage11Root 'powerbi\Dubai_Real_Estate_Intelligence\Dubai_Real_Estate_Intelligence.pbip'
$stage11Exe = 'C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe'
$stage11PidPath = Join-Path $PSScriptRoot 'desktop_process.json'
if ($Start) {
    if (Test-Path -LiteralPath $stage11PidPath) {
        $oldProbe = Get-Content -LiteralPath $stage11PidPath -Raw | ConvertFrom-Json
        if (Get-Process -Id $oldProbe.pid -ErrorAction SilentlyContinue) {
            throw 'The recorded Desktop process is still running; refusing to launch another instance.'
        }
    }
    $stage11Process = Start-Process -FilePath $stage11Exe -ArgumentList ('"' + $stage11Project + '"') -WindowStyle Hidden -PassThru
    $stage11Record = [pscustomobject]@{pid=$stage11Process.Id;startedUtc=(Get-Date).ToUniversalTime().ToString('o');project=$stage11Project;desktopVersion=(Get-Item -LiteralPath $stage11Exe).VersionInfo.FileVersion}
    $stage11Record | ConvertTo-Json | Set-Content -LiteralPath $stage11PidPath -Encoding UTF8
    $stage11Record | ConvertTo-Json
    return
}
$stage11Record = Get-Content -LiteralPath $stage11PidPath -Raw | ConvertFrom-Json
$stage11Process = Get-Process -Id $stage11Record.pid -ErrorAction SilentlyContinue
$stage11Windows = @()
if ($stage11Process) {
    Add-Type -AssemblyName UIAutomationClient
    $stage11Condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$stage11Record.pid)
    $stage11Elements = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $stage11Condition)
    foreach ($stage11Window in $stage11Elements) {
        $stage11Text = New-Object System.Collections.Generic.List[string]
        $stage11Children = $stage11Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($stage11Element in $stage11Children) {
            if ($stage11Element.Current.Name) { $stage11Text.Add($stage11Element.Current.Name) }
        }
        $stage11Windows += [pscustomobject]@{title=$stage11Window.Current.Name;offscreen=$stage11Window.Current.IsOffscreen;uiText=@($stage11Text | Select-Object -Unique)}
    }
}
$stage11Engines = @(Get-CimInstance Win32_Process -Filter "Name='msmdsrv.exe'" | Select-Object ProcessId,ParentProcessId,CommandLine)
$stage11Probe = [pscustomobject]@{checkedUtc=(Get-Date).ToUniversalTime().ToString('o');pid=$stage11Record.pid;running=[bool]$stage11Process;windowTitle=$stage11Process.MainWindowTitle;windows=$stage11Windows;engines=$stage11Engines;note='Startup/UI text inspection only. This does not certify visual rendering or DAX refresh.'}
$stage11Probe | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_probe.json') -Encoding UTF8
$stage11Probe | ConvertTo-Json -Depth 8
