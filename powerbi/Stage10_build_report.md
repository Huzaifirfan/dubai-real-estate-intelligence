# Stage 10 — Power BI recovery and build report

Project: Dubai Real Estate Intelligence Platform. Scope: Stage 10 only.

## Recovery finding and classification

The first verified inspection ran Git status, inspected `powerbi` and `reports` recursively, and searched the project including ignored files for Stage 10 artifacts. Git was clean at commit `e9b3401`. `powerbi` contained only the valid empty `.gitkeep`; `reports` contained the completed Stage 3–9 reports. No saved Stage 10 PBIP, semantic model, report, DAX, M, theme, specification, or build report was found. No partial, truncated, or corrupt Stage 10 artifact was found. The last saved checkpoint was Stage 9, so only missing Stage 10 work was added.

When the recovery request was repeated, the newly completed artifacts were reinspected and preserved. Work continued through validation and the missing recovery reports; the stage was not regenerated.

| Expected component | Initial state | Final state |
| --- | --- | --- |
| `Dubai_Real_Estate_Intelligence/Dubai_Real_Estate_Intelligence.pbip` | MISSING | COMPLETE |
| `Dubai_Real_Estate_Intelligence.SemanticModel` | MISSING | COMPLETE |
| `Dubai_Real_Estate_Intelligence.Report` | MISSING | COMPLETE |
| `Stage10_DAX_Measures.txt` | MISSING | COMPLETE |
| `Stage10_PowerQuery_M.txt` | MISSING | COMPLETE |
| `Stage10_Visual_Specification.md` | MISSING | COMPLETE |
| `dubai_real_estate_theme.json` | MISSING | COMPLETE |
| `Stage10_build_report.md` | MISSING | COMPLETE |
| `../reports/stage10_powerbi_build_report.txt` | MISSING | COMPLETE |

Already complete at the first inspection: Stages 1–9 and `.gitkeep`, all preserved. Partial existing Stage 10 files: none. Invalid existing Stage 10 files: none. Files deleted: none.

Targeted corrections during validation affected only new Stage 10 work:

- `SemanticModel/definition/model.tmdl`: removed the option that could silently return query errors as nulls.
- Four `visual.json` files (`kpi_sales_records`, `kpi_distinct_sales`, `kpi_valid_price`, `kpi_median_price`): disabled automatic display units after Desktop rendered both Sales-count cards as 120K. Counts now use zero decimals; the median uses two decimals.
- Validation evidence helpers received small reporting corrections. No source values or DAX results were changed to match reference values.

All nine requested components above were newly created during this recovery, together with a project-local `.gitignore`, registered theme resource, and validation evidence/scripts under `powerbi/validation`. Desktop subsequently saved native `.platform` files, diagram metadata, and an ignored local imported cache; its valid metadata was preserved. The complete file inventory is in `validation/stage10_artifact_inventory.json`.

## Real project and semantic model

Exact PBIP path:

```text
C:\Users\ssd\Desktop\D.A Projects\dubai-real-estate-intelligence\powerbi\Dubai_Real_Estate_Intelligence\Dubai_Real_Estate_Intelligence.pbip
```

This is a real native PBIP with PBIR report definitions and TMDL model definitions. The PBIP points to the report; `definition.pbir` points to the sibling semantic model. Both references resolve. The source-file parameter resolves to the existing CSV, and no credentials or placeholder data are embedded.

- `FactTransactions`: all 41 source columns; Desktop refresh loaded 159,223 rows.
- `DimDate`: 365 calendar dates covering 2026; Date, Year, Month Number, Month Name, Month Short, Year Month, Year Month Sort, Quarter. Month names and year-month labels have chronological sort columns.
- Relationship: `DimDate[Date]` **1 → \*** `FactTransactions[TRANSACTION_DATE]`; active; single-direction filtering from date to fact. Date is the date-table key. Transaction number is text and is not a row key.
- Exactly **21 DAX measures**, all on `FactTransactions`; all executed successfully in the live Desktop model.
- Sales measures use the exact `GROUP_EN = "Sales"` label. Price metrics additionally require `VALID_SALE_PRICE_METRIC = 1`. Shares use `DIVIDE`; category restrictions intersect slicer selections with `KEEPFILTERS`.
- `TRANS_VALUE` is hidden with no default summarization. No Total Sales Value, Total Market Value, or market-value SUM measure exists.

Power Query performs schema validation and type conversion without filtering rows, removing outliers, or normalizing source labels. `PARKING` remains text because it contains nonnumeric identifiers. The imported source CSV is not rewritten.

MoM compares the latest selected month at/before the data cutoff against the full prior calendar month. September has 7,919 Sales records versus August's 11,844, so the calculated change is approximately -33.14%; September is partial and this is not a like-for-like full-month comparison. No forecast or recommendation is produced.

## Executive Overview and theme

The native report contains one **Executive Overview** page at **1280 × 720 (16:9)**, with **8 KPI cards, 4 charts, 5 slicers**, and five textboxes. All requested title, subtitle, data-through label, partial-month warning, and transaction-grain note are included.

Charts are Monthly Sales Activity, Off-Plan vs Ready Sales, Top 10 Areas by Sales Activity, and Property Type Sales Mix. The Top 10 chart uses a native TopN filter over Sales row counts, not distinct transaction IDs. Slicers use AREA_EN, PROP_TYPE_EN, IS_OFFPLAN_EN, TRANSACTION_VALUE_BAND, and DimDate[Month Name].

The light neutral/navy/teal/gold theme passes Microsoft's theme schema for installed Desktop 2.157. Its registered resource has identical JSON content; Desktop changed its whitespace when saving. The external theme was preserved byte-for-byte. All visual rectangles are within the page and do not overlap.

The report has been opened and rendered in Power BI Desktop; a real window capture is recorded in `validation/desktop_window_final.png`. This is not a simulated dashboard image.

## Validation completed

Evidence is explicitly separated by method:

1. **Local source checks:** 159,223 rows, 41 columns; coverage 2026-01-01 through 2026-09-21; no malformed rows. Reconfirmed 772 repeated transaction numbers and 476 repeated IDs with multiple distinct transaction values.
2. **File validation:** all 31 originally authored project/report/theme JSON artifacts passed their published Microsoft schemas. After Desktop's native save, all 34 JSON artifacts parse; 21 declared public schemas validate. Nine chart/slicer definitions now reference Desktop-generated visualContainer 2.12.0, whose Microsoft public schema endpoint and official GitHub path return HTTP 404. External validation of those nine final definitions is unavailable, not claimed as passed. Four native manifest/diagram files have no schema declaration; their JSON/references and Desktop loading are checked. No empty project artifacts or broken model/report references were found. All 33 inspected direct report field bindings resolve to real model columns/measures. No embedded credentials or placeholders were found.
3. **Native model validation:** installed `Microsoft.PowerBI.Tabular` TMDL deserializer accepts the model and resolves tables, measures, sort columns, and relationship metadata.
4. **Power BI Desktop 2.157.1354.0:** opened the PBIP; refreshed both M partitions successfully through the project's local Analysis Services model; both tables reached Ready. Live DAX evaluated all 21 measures. Monthly counts and Ready/September filter tests passed.
5. **Visual review:** actual Desktop capture shows the page, KPI cards, charts, slicers, warning, and note. The specific numeric display issue was repaired and the project reopened for review.

| Core metric | Source calculation | Live Desktop DAX | Result |
| --- | ---: | ---: | --- |
| Sales Records | 119,549 | 119,549 | PASS |
| Distinct Sales Transaction Numbers | 119,526 | 119,526 | PASS |
| Median Sale Price per Sqft | AED 1,716.7932418178125 | AED 1,716.7932418178125 | PASS |
| Off-Plan Share | 68.17873842524822% | 68.17873842524822% | PASS |
| Ready Share | 31.821261574751775% | 31.821261574751775% | PASS |

Other confirmed results: Valid Sale Price Records 119,549; Residential Share 97.34%; Top Area Madinat Al Mataar (11,950 Sales records).

Evidence: `validation/recovery_baseline.json`, `validation/stage10_validation.json`, `validation/native_model_validation.json`, `validation/desktop_refresh.json`, `validation/live_dax_validation.json`, and the Desktop captures. Validation scripts are retained for repeatability; cached Microsoft schemas and their URLs are recorded locally.

## Source protection and scope

Source: `data/processed/dld_transactions_2026_ytd_features.csv` (51,605,147 bytes).

SHA-256 before:

```text
bb85cf21fa01480511257e3139061e78b9bbcc7bbe1d3b7cfe481bdcfc863db1
```

SHA-256 after:

```text
bb85cf21fa01480511257e3139061e78b9bbcc7bbe1d3b7cfe481bdcfc863db1
```

**Source unchanged: YES.** All 35 baseline-protected files retain their hashes, including the Excel workbook, previous scripts and SQL, previous reports, and source CSV. No MySQL operation was performed. No Stage 1–9 file was modified. No commit was created. Work remains within Stage 10.

## Remaining Desktop checks and Git status

Open the exact PBIP above. If the local imported cache is not available when reopened, choose **Home → Refresh**; the read-only CSV refresh has already succeeded here. Save locally if you want Desktop to retain its imported cache. No sign-in or publishing is required.

Opening, refresh, DAX execution, and baseline rendering have been tested. Full final-format validation outside Desktop is limited by the unpublished visualContainer 2.12.0 schema described above; Desktop-written definitions were not downgraded just to make an external check pass. A complete mouse/keyboard interaction matrix across all five slicers, every TopN tie case, accessibility, and every display scaling has not been tested. Review those as final usability checks in Desktop; they are not claimed as completed. The fixed 2026 snapshot text must be updated if the source is replaced in a future stage.

Final Git status contains only untracked Stage 10 additions under `powerbi` and `reports/stage10_powerbi_build_report.txt`; tracked diff is empty. The exact status is saved in `validation/git_status_final.txt`. Nothing is staged or committed.
