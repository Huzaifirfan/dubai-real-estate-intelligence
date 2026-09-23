param([Parameter(Mandatory=$true)][int]$Port, [Parameter(Mandatory=$true)][string]$Database)
$ErrorActionPreference = 'Stop'
[System.Reflection.Assembly]::LoadFrom('C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll') | Out-Null
$stage10Connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port;Initial Catalog=$Database")
$stage10Connection.Open()
function Read-Stage10Dax([string]$Query) {
    $command = $stage10Connection.CreateCommand()
    $command.CommandText = $Query
    $command.CommandTimeout = 120
    $reader = $command.ExecuteReader()
    $rows = New-Object System.Collections.Generic.List[object]
    try {
        while ($reader.Read()) {
            $row = [ordered]@{}
            for ($i=0; $i -lt $reader.FieldCount; $i++) {
                $name = $reader.GetName($i)
                if ($name.StartsWith('[') -and $name.EndsWith(']')) { $name = $name.Substring(1, $name.Length - 2) }
                $row[$name] = if ($reader.IsDBNull($i)) { $null } else { $reader.GetValue($i) }
            }
            $rows.Add([pscustomobject]$row)
        }
    } finally { $reader.Close(); $command.Dispose() }
    return $rows.ToArray()
}
try {
    $baseline = @(Read-Stage10Dax @'
EVALUATE ROW(
 "Fact Rows", COUNTROWS(FactTransactions),
 "Calendar Rows", COUNTROWS(DimDate),
 "Sales Records", [Sales Records],
 "Distinct Sales Transaction Numbers", [Distinct Sales Transaction Numbers],
 "Non-Sales Records", [Non-Sales Records],
 "Valid Sale Price Records", [Valid Sale Price Records],
 "Median Sale Price per Sqft", [Median Sale Price per Sqft],
 "Average Sale Price per Sqft", [Average Sale Price per Sqft],
 "Off-Plan Sales Records", [Off-Plan Sales Records],
 "Ready Sales Records", [Ready Sales Records],
 "Off-Plan Share", [Off-Plan Share],
 "Ready Share", [Ready Share],
 "Residential Sales Records", [Residential Sales Records],
 "Residential Share", [Residential Share],
 "Commercial Sales Records", [Commercial Sales Records],
 "Freehold Sales Records", [Freehold Sales Records],
 "Non-Freehold Sales Records", [Non-Freehold Sales Records],
 "Previous Month Sales Records", [Previous Month Sales Records],
 "MoM Sales Record Growth %", [MoM Sales Record Growth %],
 "Top Area by Sales Records", [Top Area by Sales Records],
 "Latest Data Date", FORMAT([Latest Data Date], "yyyy-MM-dd"),
 "Data Coverage Label", [Data Coverage Label],
 "Partial Month Warning", [Partial Month Warning]
)
'@)
    $monthly = @(Read-Stage10Dax @'
EVALUATE SUMMARIZECOLUMNS(DimDate[Year Month], "Sales Records", [Sales Records], "Previous Month", [Previous Month Sales Records], "MoM Growth", [MoM Sales Record Growth %])
ORDER BY DimDate[Year Month]
'@)
    $ready = @(Read-Stage10Dax @'
EVALUATE CALCULATETABLE(ROW("Sales Records", [Sales Records], "Ready Share", [Ready Share], "Off-Plan Records", [Off-Plan Sales Records], "Coverage", [Data Coverage Label]), TREATAS({"Ready"},FactTransactions[IS_OFFPLAN_EN]))
'@)
    $september = @(Read-Stage10Dax @'
EVALUATE CALCULATETABLE(ROW("Sales Records", [Sales Records], "Previous Month", [Previous Month Sales Records], "MoM Growth", [MoM Sales Record Growth %]), TREATAS({"September"},DimDate[Month Name]))
'@)
    $b = $baseline[0]
    $expected = @{'Fact Rows'=159223; 'Calendar Rows'=365; 'Sales Records'=119549; 'Distinct Sales Transaction Numbers'=119526; 'Non-Sales Records'=39674; 'Valid Sale Price Records'=119549; 'Off-Plan Sales Records'=81507; 'Ready Sales Records'=38042; 'Residential Sales Records'=116369; 'Commercial Sales Records'=3180; 'Freehold Sales Records'=115844; 'Non-Freehold Sales Records'=3705; 'Previous Month Sales Records'=11844; 'Top Area by Sales Records'='Madinat Al Mataar'; 'Latest Data Date'='2026-09-21'; 'Data Coverage Label'='Data through 21 September 2026'; 'Partial Month Warning'='September 2026 is a partial month.'}
    $failures = New-Object System.Collections.Generic.List[string]
    foreach ($key in $expected.Keys) { if ($b.$key -ne $expected[$key]) { $failures.Add("Unexpected $key : $($b.$key)") } }
    if ([Math]::Round($b.'Median Sale Price per Sqft',2) -ne 1716.79) { $failures.Add('Median mismatch') }
    if ([Math]::Round(100*$b.'Off-Plan Share',2) -ne 68.18) { $failures.Add('Off-plan share mismatch') }
    if ([Math]::Round(100*$b.'Ready Share',2) -ne 31.82) { $failures.Add('Ready share mismatch') }
    if ($ready[0].'Sales Records' -ne 38042 -or $ready[0].'Ready Share' -ne 1 -or $null -ne $ready[0].'Off-Plan Records') { $failures.Add('Ready slicer intersection mismatch') }
    if ($september[0].'Sales Records' -ne 7919 -or $september[0].'Previous Month' -ne 11844) { $failures.Add('September slicer/MoM mismatch') }
    $expectedMonthly = @(17374,16989,13484,14017,10269,13931,13722,11844,7919)
    if ($monthly.Count -ne 9) { $failures.Add('Unexpected monthly result count') }
    for ($i=0; $i -lt [Math]::Min(9,$monthly.Count); $i++) { if ($monthly[$i].'Sales Records' -ne $expectedMonthly[$i]) { $failures.Add("Month $i mismatch") } }
    $result = [ordered]@{checked_utc=[DateTime]::UtcNow.ToString('o');evidence='Live DAX queries against the Stage 10 model opened and refreshed in Power BI Desktop';passed=($failures.Count -eq 0);baseline=$baseline;monthly=$monthly;ready_filter=$ready;september_filter=$september;errors=@($failures);limitations=@('DAX filter tests do not certify visual rendering or mouse interaction.','The imported cache remains local; the delivered PBIP may require Refresh when reopened.')}
    $result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'live_dax_validation.json') -Encoding UTF8
    $result | ConvertTo-Json -Depth 10
    if ($failures.Count) { throw 'Live Stage 10 DAX validation failed.' }
} finally { $stage10Connection.Close(); $stage10Connection.Dispose() }
