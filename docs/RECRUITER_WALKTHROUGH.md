# Recruiter Walkthrough

Review the project in approximately **3–5 minutes**. The focus is reproducible analysis, clear business reporting and documented data-quality decisions.

| Time | Open | What to look for |
| --- | --- | --- |
| 0:00–0:30 | [README](../README.md) | Business questions, the Python → MySQL → Excel → Power BI workflow, and the January–21 September 2026 scope. September is partial. |
| 0:30–1:10 | [Executive Overview](../images/powerbi/executive_overview.png) | Sales activity, distinct transaction numbers, median price per sqft and the Off-Plan/Ready mix. The distinction between records and transaction numbers is deliberate. |
| 1:10–2:00 | [Market Trends](../images/powerbi/market_trends.png), [Area Intelligence](../images/powerbi/area_intelligence.png), [Property & Pricing](../images/powerbi/property_pricing.png) | Monthly comparisons, area activity/pricing, and property segments. These are native Desktop captures; some chart/table content requires scrolling in the report. |
| 2:00–2:50 | [SQL business analysis](../sql/03_business_analysis.sql) and [Stage 8 results](../reports/stage8_sql_business_analysis_report.txt) | Business queries, reconciliation and the transaction-grain audit. Repeated identifiers are investigated before defining market KPIs. |
| 2:50–3:30 | [Excel build report](../reports/stage9_excel_workbook_report.txt) and [workbook generator](../src/09_build_excel_workbook.py) | The validated seven-sheet workbook, eight KPI cards, four executive charts, full-data analysis tables, deterministic 5,000-row sample and data dictionary. |
| 3:30–4:30 | [Raw validation](../src/01_validate_raw_data.py), [YTD cleaning](../src/05_clean_2026_ytd.py), [feature engineering](../src/06_engineer_features.py) and [MySQL loader](../src/07_load_mysql.py) | Explicit checks, preservation of source labels, sales-only price metrics and an auditable path to the reporting layers. |

**Excel artifact status:** The earlier ZIP integrity issue was resolved by regeneration before recovery resumed. The current [workbook](../excel/Dubai_Real_Estate_Intelligence_2026_YTD.xlsx) opens programmatically and normally in native Microsoft Excel, and passes content and formula validation. Recovery preserved it unchanged; see the [Stage 12 report](../reports/stage12_portfolio_packaging_report.txt) for repair history and the native Excel result.

The strongest discussion point is the grain decision: Stage 8 found **772 repeated transaction numbers**, including **476 with multiple distinct transaction values**. The project intentionally excludes Total Sales Value and Total Market Value until the transaction grain can be reconciled.

For a deeper model review, open the [Power BI project](../powerbi/Dubai_Real_Estate_Intelligence/Dubai_Real_Estate_Intelligence.pbip) and follow the [README setup instructions](../README.md#how-to-run). A clean clone needs the local source dataset and an updated `SourceFile` parameter before refresh. The four pages reuse **21 DAX measures** across `FactTransactions` and `DimDate`.
