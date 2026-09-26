# Resume Project Entry

## A. One-line version

**Dubai Real Estate Intelligence Platform:** Built a Python, MySQL/SQL, Excel and Power BI analytics workflow for 159K+ official DLD records from 2026 YTD, with 21 DAX measures and four analytical pages.

## B. Two resume bullets

- Built a reproducible Python and MySQL/SQL workflow to validate, clean and analyze 159,223 official Dubai Land Department records across 41 source/analytical columns for January–21 September 2026.
- Developed Excel executive-workbook generation and four Power BI analytical pages using 21 DAX measures, with documented transaction-grain controls and partial-month disclosures.

## C. Three resume bullets

- Prepared 159,223 official DLD records for 2026 YTD using Python/Pandas, with schema checks, exact-duplicate removal, feature engineering and source-file SHA-256 validation.
- Loaded the engineered dataset into MySQL and wrote SQL business analysis; audited 772 repeated transaction numbers and excluded market-value totals pending transaction-grain reconciliation.
- Implemented a seven-sheet Excel workbook generator and four Power BI analytical pages with 21 DAX measures to present sales activity, area comparisons and property pricing.

## D. LinkedIn project description

Dubai Real Estate Intelligence Platform is an end-to-end analytics portfolio project using official Dubai Land Department transaction data. The workflow covers Python/Pandas preparation, MySQL loading, SQL business analysis, Excel executive-workbook generation and a Power BI semantic model with 21 DAX measures and four analytical pages.

The final dataset contains 159,223 records and 41 source/analytical columns, covering January through 21 September 2026. Analysis focuses on sales activity, Off-Plan/Ready share, median sale price per sqft, area comparisons and property segments. September is disclosed as a partial month.

Data-quality decisions are documented throughout. Transaction numbers are not assumed to be unique row keys, official labels and price outliers are retained, and market-value totals are intentionally excluded until transaction grain is reconciled. The repository includes scripts, queries, native Power BI screenshots and validation evidence.

## Accuracy notes

- Use **records**, not “159K unique transactions.” Sales Records and Distinct Sales Transaction Numbers are separate measures.
- Coverage ends on **21 September 2026**; this is not a complete September or full-year analysis.
- Excel statements describe the implemented generator and current workbook, validated programmatically and opened normally in native Microsoft Excel. The earlier ZIP integrity issue was resolved before recovery resumed; the [Stage 12 report](../reports/stage12_portfolio_packaging_report.txt) records repair history and the native Excel result.
- This is a portfolio project. Do not add claims of production deployment, measured business impact, investment advice or forecasting.
- Add your actual repository or portfolio link when publishing; no personal URL is assumed here.
