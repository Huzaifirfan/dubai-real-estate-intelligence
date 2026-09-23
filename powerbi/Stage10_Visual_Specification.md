# Stage 10 - Executive Overview visual specification

Evidence: authored native PBIR definitions, based on Microsoft published schemas and native BCApps examples. This document is not a claim that the page has rendered in Power BI Desktop. The Stage 10 build report records validation actually completed.

## Report and layout

- One page: Executive Overview, 1280 x 720 (16:9), FitToPage.
- Fixed header contains the requested title and subtitle, Data through 21 September 2026, and September 2026 is a partial month.
- Five dropdown slicers span y=96-160. Two rows of four KPI cards span y=176-336. Four chart panels span y=352-652. The source-grain note appears at the bottom.
- Palette: light neutral #F3F5F6, white panels, navy #192D3A, teal #147D83 and muted gold #AD823E. Segoe UI typography, no decorative borders or shadows.
- Numeric KPI value font 26 pt; area-name KPI value font 16 pt; KPI labels 10 pt. Individual cards accommodate different font sizing. Cards have explicit 8 px vertical padding and no additional content margins.

## Exactly eight KPI visuals

| Visual name | Native type | FactTransactions measure |
| --- | --- | --- |
| kpi_sales_records | cardVisual | Sales Records |
| kpi_distinct_sales | cardVisual | Distinct Sales Transaction Numbers |
| kpi_median_price | cardVisual | Median Sale Price per Sqft |
| kpi_offplan_share | cardVisual | Off-Plan Share |
| kpi_ready_share | cardVisual | Ready Share |
| kpi_residential_share | cardVisual | Residential Share |
| kpi_top_area | cardVisual | Top Area by Sales Records |
| kpi_valid_price | cardVisual | Valid Sale Price Records |

All cards bind a semantic-model measure through the native Data role. Data values are not stored in report artifacts. Formatting comes from the model measures.

Desktop review found automatic display units rounded both Sales-count cards to 120K. The Sales Records, Distinct Sales Transaction Numbers, Valid Sale Price Records, and Median Sale Price per Sqft card definitions now explicitly use display units None. Counts use zero decimals and price uses two decimals; measures remain unchanged.

## Exactly four chart visuals

| Chart | Native type | Category | Value |
| --- | --- | --- | --- |
| Monthly Sales Activity | lineChart | DimDate[Month Short], ascending calendar order via model sort column | Sales Records |
| Off-Plan vs Ready Sales | donutChart | FactTransactions[IS_OFFPLAN_EN] | Sales Records |
| Top 10 Areas by Sales Activity | barChart | FactTransactions[AREA_EN] | Sales Records |
| Property Type Sales Mix | barChart | FactTransactions[PROP_TYPE_EN] | Sales Records |

Top 10 is a genuine native visual-level TopN filter, with Top=10 in a semantic subquery and an outer IN semijoin. It ranks CountNonNull(TRANSACTION_NUMBER), restricted to GROUP_EN = Sales, to match sales row count rather than distinct transaction count. Source verification found no null transaction numbers. The chart also explicitly filters GROUP_EN = Sales. Aggregation function 5 is CountNonNull. Native TopN can include ties at the boundary; verify rendering and slicer interaction in Desktop.

The monthly axis uses Month Short sorted by Month Number in DimDate; the model covers only 2026 for this snapshot. No monthly values are entered manually. September is partial and should not be read as a full month.

## Exactly five slicers

- FactTransactions[AREA_EN] - Area
- FactTransactions[PROP_TYPE_EN] - Property type
- FactTransactions[IS_OFFPLAN_EN] - Off-plan / ready
- FactTransactions[TRANSACTION_VALUE_BAND] - Transaction value band
- DimDate[Month Name] - Month, sorted by Month Number in the semantic model

Each uses native slicer/Values binding and Dropdown mode. No initial selections are baked into slicers. The page has no blanket Sales filter, preserving non-sales measures for later ad hoc use; all required Sales measures define their own Sales scope.

## Required visible note

Transaction numbers are not always unique at row level. Total market value is intentionally excluded pending transaction-grain reconciliation.

No total-sales-value, total-market-value, forecast, or investment-recommendation visual is present. Transaction value band is a categorical slicer only.

## Theme registration

The valid JSON theme exists at powerbi/dubai_real_estate_theme.json and a registered resource with identical JSON content inside the Report/StaticResources/RegisteredResources folder. Desktop reformatted the registered copy when saving; the external theme bytes were preserved. report.json identifies it as a CustomTheme resource. Theme schema corresponds to installed Power BI Desktop 2.157.

## Desktop review

Open the .pbip, refresh the local CSV data, and confirm all cards/charts render with the expected baseline metrics. Check chart labels, especially long area names, text wrapping, dropdown usability, all five slicers, TopN interactions, and the partial-month warning. FitToPage may scale the page to the window size. JSON schema validation does not prove visual runtime compatibility.

## Microsoft format references

- [Report definition and native binding examples](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/report-definition)
- [BCApps native report.json](https://github.com/microsoft/BCApps/blob/main/src/Apps/W1/PowerBIReports/Power%20BI%20Files/Purchase%20app/Purchase%20app.Report/definition/report.json)
- [BCApps native cardVisual/Data example](https://github.com/microsoft/BCApps/blob/main/src/Apps/W1/PowerBIReports/Power%20BI%20Files/Purchase%20app/Purchase%20app.Report/definition/pages/15386889aed0b65c35cc/visuals/8d7c0c162083c130f329/visual.json)
- [Microsoft PBIR visual container schema](https://github.com/microsoft/json-schemas/blob/main/fabric/item/report/definition/visualContainer/2.0.0/schema.json)
- [Microsoft PBIR filter schema](https://github.com/microsoft/json-schemas/blob/main/fabric/item/report/definition/filterConfiguration/1.1.0/schema.json)
- [Microsoft theme schema release mapping](https://github.com/microsoft/powerbi-desktop-samples/blob/main/Report%20Theme%20JSON%20Schema/README.md)
