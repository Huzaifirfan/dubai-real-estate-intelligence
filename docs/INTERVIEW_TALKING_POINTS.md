# Interview Talking Points

These answers describe the implemented project. Adapt the wording to your own voice and add personal motivation only where it reflects your experience.

## Tell me about this project.

This project analyzes official Dubai Land Department transaction data from January through 21 September 2026. Python validates, cleans and engineers a 159,223-record, 41-column dataset; MySQL and SQL support business analysis; Excel generation and a four-page Power BI report present the results. The model contains 21 DAX measures. September is explicitly treated as a partial month.

## Why did you choose Dubai real estate?

Dubai real estate provides a useful analytical case because the official transaction data supports questions about activity, location, property characteristics and pricing. It also requires careful decisions about transaction grain and source labels. That is the project's analytical rationale; any personal reason should come from your own experience.

## Why did you use Python?

Python makes the preparation steps repeatable. Pandas supports schema checks, profiling, exact-duplicate removal, monthly assembly and feature creation. The scripts preserve raw inputs and produce validation evidence, including row counts and SHA-256 checks. Python also creates the Excel reporting package with openpyxl.

## Why MySQL?

MySQL provides a typed relational layer for the engineered data and a place to validate the load independently. The SQL analysis then expresses monthly, area and property-segment questions as reviewable queries. It also supports the transaction-number audit before those results become dashboard KPIs.

## Why both Excel and Power BI?

Excel provides a familiar executive workbook with analysis tables, a data dictionary and a deterministic inspection sample. Power BI adds a semantic model, reusable measures, slicers and four analytical pages. Both reporting layers use the same engineered source. The current Excel workbook passes programmatic checks for seven sheets, eight KPI cards and four executive charts, and opens normally in native Microsoft Excel. Its earlier ZIP integrity issue was resolved before recovery resumed; the [Stage 12 report](../reports/stage12_portfolio_packaging_report.txt) records the native Excel result.

## What data-quality problems did you encounter?

The project handles exact duplicate rows, repeated transaction identifiers, missing fields, price outliers and capitalization variants in official labels. Exact duplicates are removed; legitimate non-identical rows with repeated identifiers are retained. Missing bedrooms are not invented, labels are preserved, and outliers are not silently discarded. Price-per-area measures use valid Sales records.

## Why didn't you calculate Total Sales Value?

`TRANSACTION_NUMBER` is not a unique row key. Stage 8 found 772 repeated numbers, and 476 of those identifiers had multiple distinct `TRANS_VALUE` values. Summing rows or arbitrarily choosing one value per identifier would not establish a reliable market total. Total Sales Value, Total Market Value and a market KPI based on `SUM(TRANS_VALUE)` are therefore intentionally excluded pending grain reconciliation.

## How did you validate the data?

Validation runs across layers: source schema and date coverage, duplicate and missing-value checks, row-count reconciliation, source-file hashes, MySQL load checks and SQL audits. Stage 9 records workbook and formula checks. Stage 12 recovery verified the repaired workbook, including all 205,000 sample cells against the source; the [recovery report](../reports/stage12_portfolio_packaging_report.txt) separately records the native Excel result. Stages 10–11 record native Power BI model parsing, refresh, all 21 live DAX measures, source reconciliation, rendered pages and selected slicer tests. Those records distinguish structural checks from native application validation.

## What was the hardest part?

A central challenge was preserving the meaning of a record across tools. A repeated transaction number does not automatically mean a duplicate row, and default case-insensitive grouping can merge distinct official area labels. The project documents the grain restriction and uses a case-sensitive Power BI model so area counts reconcile to the source.

## How would you scale this project?

The next steps would be automated monthly ingestion, explicit schema-change checks, incremental loading and validation reports for each new period. Power BI Service deployment and scheduled refresh would require a tested refresh setup. These are future improvements; the current project is a local portfolio implementation.

## What would you improve with more historical data?

More history would support full-year and like-for-like month comparisons and help distinguish recurring seasonal patterns from a single YTD snapshot. I would first reconcile transaction grain and introduce a reviewed semantic area mapping while retaining original labels. Partial-period comparisons would continue to be disclosed.

Evidence: [stage summary](PROJECT_STAGE_SUMMARY.md), [Stage 8 SQL report](../reports/stage8_sql_business_analysis_report.txt), [Stage 9 Excel report](../reports/stage9_excel_workbook_report.txt) and [Stage 11 Power BI report](../reports/stage11_powerbi_advanced_report.txt).
