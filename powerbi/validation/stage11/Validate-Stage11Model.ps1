param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))),
    [string]$DesktopBin = 'C:\Program Files\Microsoft Power BI Desktop\bin'
)

$ErrorActionPreference = 'Stop'
$modelFolder = Join-Path $ProjectRoot 'powerbi\Dubai_Real_Estate_Intelligence\Dubai_Real_Estate_Intelligence.SemanticModel\definition'
$outputPath = Join-Path $PSScriptRoot 'native_model_validation.json'

# Desktop's PowerBI.Tabular assembly supplies the native TMDL serializer.
# The similarly named Server.Tabular assembly does not supply that serializer.
$assembly = [System.Reflection.Assembly]::LoadFrom((Join-Path $DesktopBin 'Microsoft.PowerBI.Tabular.dll'))
$database = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($modelFolder)
$model = $database.Model
$fact = $model.Tables['FactTransactions']
$date = $model.Tables['DimDate']

if ($model.Tables.Count -ne 2 -or $fact.Columns.Count -ne 43 -or $date.Columns.Count -ne 8) {
    throw 'Unexpected Stage 11 table or column counts.'
}
if ($fact.Measures.Count -ne 21) { throw 'Expected exactly 21 Stage 11 measures.' }
if ($model.Relationships.Count -ne 1) { throw 'Expected exactly one date relationship.' }
$relationship = $model.Relationships[0]
if (-not $relationship.IsActive -or [string]$relationship.CrossFilteringBehavior -ne 'OneDirection' -or
    [string]$relationship.FromCardinality -ne 'Many' -or [string]$relationship.ToCardinality -ne 'One' -or
    $relationship.FromTable.Name -ne 'FactTransactions' -or $relationship.FromColumn.Name -ne 'TRANSACTION_DATE' -or
    $relationship.ToTable.Name -ne 'DimDate' -or $relationship.ToColumn.Name -ne 'Date') {
    throw 'The Stage 11 date relationship is inconsistent with the design.'
}
if (-not $date.Columns['Date'].IsKey -or $date.DataCategory -ne 'Time') {
    throw 'DimDate must be marked as a date table with Date as its key.'
}
if ($fact.Columns['TRANSACTION_NUMBER'].IsKey -or -not $fact.Columns['TRANS_VALUE'].IsHidden -or
    [string]$fact.Columns['TRANS_VALUE'].SummarizeBy -ne 'None') {
    throw 'The source transaction-grain protections are missing.'
}

$result = [ordered]@{
    evidence = 'Local native metadata parsing and structural assertions; no data refresh or DAX/M execution'
    validated_at_utc = [DateTime]::UtcNow.ToString('o')
    native_parser_pass = $true
    parser_assembly = $assembly.FullName
    compatibility_level = $database.CompatibilityLevel
    source_query_culture = $model.SourceQueryCulture
    tables = @($model.Tables | ForEach-Object {
        [ordered]@{
            name = $_.Name
            data_category = $_.DataCategory
            columns = @($_.Columns | ForEach-Object {
                [ordered]@{
                    name = $_.Name
                    data_type = [string]$_.DataType
                    is_key = $_.IsKey
                    hidden = $_.IsHidden
                    summarize_by = [string]$_.SummarizeBy
                    sort_by_column = $(if ($_.SortByColumn) { $_.SortByColumn.Name } else { $null })
                }
            })
            measures = @($_.Measures | ForEach-Object Name)
            partitions = @($_.Partitions | ForEach-Object {
                [ordered]@{ name = $_.Name; mode = [string]$_.Mode; source_type = $_.Source.GetType().Name }
            })
        }
    })
    relationships = @([ordered]@{
        name = $relationship.Name
        active = $relationship.IsActive
        from_table = $relationship.FromTable.Name
        from_column = $relationship.FromColumn.Name
        from_cardinality = [string]$relationship.FromCardinality
        to_table = $relationship.ToTable.Name
        to_column = $relationship.ToColumn.Name
        to_cardinality = [string]$relationship.ToCardinality
        cross_filtering_behavior = [string]$relationship.CrossFilteringBehavior
    })
    expressions = @($model.Expressions | ForEach-Object { [ordered]@{name = $_.Name; kind = [string]$_.Kind} })
    limitations = @(
        'Native deserialization validates TMDL metadata and resolves object references, not DAX formula execution.',
        'Power Query M and local CSV refresh must be tested in Power BI Desktop.',
        'Report rendering and slicer interactions must be tested in Power BI Desktop.'
    )
}
$json = $result | ConvertTo-Json -Depth 15
[System.IO.File]::WriteAllText($outputPath, $json + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "PASS: native TMDL parser; 2 tables, 51 columns, 21 measures, 1 active single-direction date relationship. Evidence: $outputPath"
