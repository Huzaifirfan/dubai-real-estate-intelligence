# Stage 11 recovery and build report

Status: completed locally in Power BI Desktop; changes remain uncommitted.
Scope: Stage 11 only. No publication, commit, forecast or later-stage work.

## Recovery inspection

Branch: `main`. Baseline commit: `a63223c` — Add Stage 10 Power BI executive dashboard.
The original recovery inspection found a clean tree and Executive Overview only.
The latest continuation checkpoint found all four page definitions, the semantic
changes, two complete Stage 11 documents and successful native refresh evidence.
Both inspections are retained in `validation/stage11/recovery_baseline.json` and
`validation/stage11/continuation_checkpoint.json`.

| Component at latest continuation | Classification | Recovery action |
|---|---|---|
| PBIP, report/model references and JSON | COMPLETE | Preserved |
| Four page definitions and native page navigators | COMPLETE | Preserved |
| 21 DAX measures and date relationship | COMPLETE | Preserved |
| Hidden band-sort helpers and case-sensitive collation | COMPLETE | Preserved |
| Stage11_Advanced_DAX_Measures.txt | COMPLETE | Preserved |
| Stage11_Visual_Specification.md | COMPLETE | Preserved |
| Full native refresh, live DAX and source reconciliation | COMPLETE | Preserved |
| Final screenshots, native interaction check and protection audit | PARTIAL | Finished |
| Stage11_build_report.md | MISSING | Created |
| reports/stage11_powerbi_advanced_report.txt | MISSING | Created |
| Truncated/invalid report or model files | None found | No replacement/rebuild |

Before this continuation: four pages. After: the same four pages. Across Stage 11,
exactly three analytical pages were added to the one-page Stage 10 baseline.
No page or measure was rebuilt during the final continuation.

## Delivered project

`C:\Users\ssd\Desktop\D.A Projects\dubai-real-estate-intelligence\powerbi\Dubai_Real_Estate_Intelligence\Dubai_Real_Estate_Intelligence.pbip`

This is the existing real PBIP with native PBIR/TMDL definitions. Tables remain
FactTransactions and DimDate. FactTransactions has 41 original source columns and
2 hidden sorting helpers; DimDate has its original 8 columns. The source CSV
remains 41 columns. Desktop's internal row-number columns are not source fields.

Relationship: DimDate[Date] **1 → many** FactTransactions[TRANSACTION_DATE], active,
single direction. Existing DAX measures: **21**; new DAX measures: **0**. All 21
definitions are reused without changes, duplication or hard-coded reference metrics.

| Page | KPI cards | Charts | Tables | Slicers | Native render |
|---|---:|---:|---:|---:|---|
| Executive Overview | 8 | 4 | 0 | 5 | PASS |
| Market Trends | 4 | 4 | 0 | 3 | PASS |
| Area Intelligence | 4 | 2 | 2 | 4 | PASS |
| Property & Pricing | 4 | 6 | 0 | 4 | PASS |
| Stage 11 additions | **12** | **12** | **2** | **11** | PASS |

One native page navigator appears on each page, with the current page highlighted.
Native Ctrl+click navigation was exercised in Desktop edit mode. No extra tooltip
page or analytical page exists. The activity-versus-price comparison uses the
permitted table fallback. Area pricing bars require at least 30 valid price records
per area; this is a visual filter, not deletion of source records or outliers.

## Preserved behavior and necessary integration changes

- Executive Overview retains all original content, field bindings and measures.
  Its data visuals move down 32 pixels for the navigator; the four chart heights
  reduce by 32 pixels. Its data-grain note remains unchanged.
- The Stage 10 theme is unchanged. Titles, cards, slicers and restrained teal/gold
  chart colors are consistent across the four 16:9 pages.
- Month Name → Month Number and Year Month → Year Month Sort remain unchanged.
- TRANSACTION_VALUE_BAND_SORT and PROPERTY_SIZE_BAND_SORT are hidden Int64 columns
  added after the existing Power Query type-conversion step. SortByColumn supplies
  numeric order. Source labels, including spaces around hyphens, are untouched.
- `Latin1_General_100_CS_AS` model collation preserves case-only source labels.
  Default case-insensitive grouping merged official variants, so this integration
  change was necessary for Stage 11 area fidelity. All **251** sales-area counts
  now reconcile exactly to the CSV. BUSINESS BAY = 4,623; Business Bay = 208.
  Core market-wide Stage 10 metrics remain unchanged. Area-level groupings now
  correctly separate source variants; this is an intentional, documented difference.
- In-run polish repaired only the new slicers' inherited duplicate headers, the
  Valid Sale Price Records card's decimal display, categorical bedroom labels and
  new table column widths. No source field or existing measure was replaced.

## Native validation performed

Power BI Desktop **2.157.1354.0** opened the exact PBIP. A full refresh was executed
through TOM against the Desktop-owned local Analysis Services engine. Both M
partitions reached **Ready**, and live ADOMD queries evaluated all 21 measures.
This was real local Desktop/engine validation, not merely parsing generated files.

The first load encountered the old Stage 10 cache's collation incompatibility.
With Desktop closed, the existing ignored cache was preserved as
`.SemanticModel/.pbi/stage11_before_refresh.abf`; a fresh local cache was then
processed successfully. The existing PBIP/model definitions were extended in place.
The project was subsequently reopened successfully with the refreshed cache.

All four pages were visually inspected with data, without broken-visual, missing
field, query, relationship or theme errors. Native navigation and a Ready slicer
test were performed. Ready produced 38,042 sales records and 100% Ready Share;
charts responded. Clearing it restored the unfiltered baseline. Live DAX also
tested Ready and September filter contexts; September = 7,919 sales rows and
previous month = 11,844. Other slicer bindings and explicit filtering interactions
were structurally checked; exhaustive combinations of mouse interactions were
not tested.

| Unfiltered metric | Source and live Desktop result | Result |
|---|---:|---|
| Sales Records | 119,549 | PASS |
| Distinct Sales Transaction Numbers | 119,526 | PASS |
| Median Sale Price per Sqft | AED 1,716.7932418178125 (display 1,716.79) | PASS |
| Off-Plan Share | 68.17873842524822% (display 68.18%) | PASS |
| Ready Share | 31.821261574751775% (display 31.82%) | PASS |

All 159,223 source rows and 41 columns are retained. Coverage is 1 January through
21 September 2026. Each page displays coverage and the partial-September warning.
Market Trends also explains that MoM compares partial September with full August,
not equal day counts. Forecasts and day-normalized growth are not created.

## Evidence and source protection

Final native screenshots:

- [Executive Overview, filters cleared](validation/stage11/executive_overview_cleared.png)
- [Market Trends](validation/stage11/market_trends.png)
- [Area Intelligence](validation/stage11/area_intelligence.png)
- [Property & Pricing](validation/stage11/property_pricing.png)
- [Native Ready slicer test](validation/stage11/slicer_interaction.png)

Native refresh: `validation/stage11/desktop_refresh.json`.
Live DAX: `validation/stage11/live_dax_validation.json`.
Area/band/bedroom reconciliation: `validation/stage11/segment_reconciliation.json`.
File/source/schema checks: `validation/stage11/stage11_validation.json`.
Final render audit: `validation/stage11/desktop_render_validation.json`.
Exact file inventory: `validation/stage11/file_manifest.json`.

Source SHA-256 before:
`bb85cf21fa01480511257e3139061e78b9bbcc7bbe1d3b7cfe481bdcfc863db1`

Source SHA-256 after:
`bb85cf21fa01480511257e3139061e78b9bbcc7bbe1d3b7cfe481bdcfc863db1`

Source unchanged: **YES**. Baseline protection covers 114 files. Stages 1–9,
the Excel workbook, previous Python/SQL work, source CSV, Stage 10 documentation,
Stage 10 evidence and theme are unchanged. MySQL was not accessed or modified.
Only the documented Power BI integration changes affect Stage 10 project files.
The final protection audit and inventory enumerate each changed path.

The Stage 8 data-grain restriction remains in force: 772 transaction numbers
repeat; 476 repeated IDs have distinct TRANS_VALUE values. Transaction numbers
are not row keys. No Total Sales Value, Total Market Value or SUM(TRANS_VALUE)
market KPI was created. Outliers, missing bedrooms and official labels are retained.

## Known limits and opening guidance

- Validation applies to the installed Desktop version and this local source.
  Power BI Service publication and other Desktop versions were not tested.
- Microsoft's public visualContainer 2.12 schema URL returns HTTP 404. Available
  schemas, native TMDL parsing, real refresh, live DAX and Desktop rendering were
  checked; missing public schemas are recorded as a validation limitation.
- Some bars and tables scroll at this machine's 1024 × 768 display resolution.
  Full labels and additional rows remain accessible through tooltips/scrolling.
  The area comparison intentionally uses a table, not an unverified scatter chart.
- Number grouping follows the Windows locale (for example 1,19,549 = 119,549).
- The source parameter is local to this machine. On another machine, set SourceFile
  to the unchanged engineered CSV, then refresh. An old pre-collation Stage 10
  cache must not be reused with this model; preserve/rename it with Desktop closed
  if encountered. A clean clone has no tracked imported cache and requires refresh.
- No manual Desktop validation remains outstanding on this machine. Opening the
  exact PBIP above is the user's review step. Changes remain uncommitted on `main`.

Technical references: [Microsoft TMSL model metadata](https://learn.microsoft.com/en-us/analysis-services/tmsl/model-object-tmsl?view=sql-analysis-services-2025),
[Microsoft string storage and collation](https://learn.microsoft.com/en-us/analysis-services/tabular-models/string-storage-and-collation-in-tabular-models?view=sql-analysis-services-2025).
