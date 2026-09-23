param([switch]$Refresh)
$ErrorActionPreference='Stop'
$record=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_process.json') -Raw | ConvertFrom-Json
$engine=Get-CimInstance Win32_Process -Filter "Name='msmdsrv.exe'" | Where-Object ParentProcessId -eq $record.pid
if (@($engine).Count -ne 1) { throw 'Expected the engine belonging to the recorded Desktop process.' }
$dir=[regex]::Match($engine.CommandLine,'-s "([^"]+)"').Groups[1].Value
$port=(Get-Content -LiteralPath (Join-Path $dir 'msmdsrv.port.txt') -Encoding Unicode -Raw).Trim()
[System.Reflection.Assembly]::LoadFrom('C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.Tabular.dll') | Out-Null
$server=New-Object Microsoft.AnalysisServices.Tabular.Server
$server.Connect("localhost:$port")
try {
    $db=@($server.Databases | Where-Object { $_.Model.Tables.ContainsName('FactTransactions') })
    if ($db.Count -ne 1) { throw 'Expected exactly one Dubai model.' }
    $db=$db[0]
    $fact=$db.Model.Tables['FactTransactions']
    $dataColumns=@($fact.Columns | Where-Object { $_.GetType().Name -ne 'RowNumberColumn' })
    if ($fact.Measures.Count -ne 21 -or $dataColumns.Count -ne 43) { throw 'Unexpected Stage 11 model. Do not refresh.' }
    $result=[ordered]@{checked_utc=[DateTime]::UtcNow.ToString('o');desktop_pid=$record.pid;port=[int]$port;database=$db.ID;model_collation=$db.Model.Collation;database_collation=$db.Collation;refresh_requested=[bool]$Refresh;refresh_passed=$false}
    if ($Refresh) {
        $db.Model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
        $db.Model.SaveChanges() | Out-Null
        $result.refresh_passed=$true
    }
    $result.partitions=@($db.Model.Tables | ForEach-Object { $t=$_; $_.Partitions | ForEach-Object { [pscustomobject]@{table=$t.Name;state=[string]$_.State;refreshed=$_.RefreshedTime.ToString('o')} } })
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'desktop_refresh.json') -Encoding UTF8
    $result | ConvertTo-Json -Depth 6
} finally { $server.Disconnect() }
