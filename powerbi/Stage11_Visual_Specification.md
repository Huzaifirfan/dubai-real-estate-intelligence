# Stage 11 visual specification

The existing Stage 10 PBIP is extended to exactly four analytical pages. All
pages use the unchanged Stage 10 theme, 1280 × 720 canvases, Segoe UI, a light
neutral background, dark navy text and restrained teal/gold accents.

## Shared layout and behavior

- Title at (24,16), subtitle at (24,57); data through 21 September 2026 and the
  partial-September warning remain visible at the upper right.
- Native page navigator at (24,86), width 1232, height 28. All four pages are
  listed; the selected page has a teal fill and white text. In Desktop edit mode,
  Ctrl+click activates a navigator button; report reading mode uses an ordinary click.
- Slicers start at y=128, height 64. Four equal KPI cards on each new page start at
  y=208, height 76. Chart/table panels start at y=300; notes occupy y=680.
- Executive Overview retains its original measures, fields, visuals, text and
  theme. Its data visuals move down 32 pixels to make room for navigation; chart
  heights reduce by 32 pixels so their lower edge and grain note stay in place.
- New-page slicers filter relevant data visuals. Chart/table selections use
  filtering instead of cross-highlighting. Charts do not filter slicer option
  lists. Filters are page-local; no unexpected cross-page synchronization is added.
- Charts expose useful existing measures in tooltips (sales records, distinct
  transaction numbers, median sale price per sqft and off-plan share as applicable).
- Month Name sorts by Month Number; Year Month sorts by Year Month Sort.

## Executive Overview — preserved

8 existing KPI cards, 4 existing charts, 5 existing slicers; 1 added navigator.
The original data-grain note is preserved verbatim. There is no market-value KPI.

## Market Trends — created

Subtitle: Dubai Property Sales Activity | 2026 YTD.

KPI cards: Sales Records; Previous Month Sales Records; MoM Sales Record Growth %;
Off-Plan Share.

| Visual | Type | Category / axis | Values |
|---|---|---|---|
| Monthly Sales Activity | Line | DimDate[Year Month] ascending | Sales Records |
| Monthly Off-Plan vs Ready | Clustered column | DimDate[Year Month] ascending | Off-Plan Sales Records; Ready Sales Records |
| Monthly Median Sale Price per Sqft | Line | DimDate[Year Month] ascending | Median Sale Price per Sqft |
| Monthly Residential Sales | Column | DimDate[Year Month] ascending | Residential Sales Records |

Slicers: AREA_EN, PROP_TYPE_EN, IS_OFFPLAN_EN.
Four charts in a two-by-two grid. September is explicitly partial, with coverage
through 21 September. Footer explains that MoM compares the latest selected month
with the full prior month. No forecast or day-normalized growth is presented.

## Area Intelligence — created

Subtitle: Sales Activity and Sale Price per Sqft by DLD Area.

KPI cards: Top Area by Sales Records; Sales Records; Median Sale Price per Sqft;
Off-Plan Share.

| Visual | Type | Definition |
|---|---|---|
| Top 15 Areas by Sales Records | Horizontal bar | AREA_EN; Sales Records descending; Top N 15 |
| Area Median Price per Sqft | Horizontal bar | AREA_EN; median descending; visual-level Valid Sale Price Records >= 30 |
| Area Sales Activity vs Median Price per Sqft | Table | AREA_EN, Sales Records, Median Sale Price per Sqft; sales descending |
| Area Detail Table | Table | AREA_EN, Sales Records, Distinct Sales Transaction Numbers, Off-Plan Sales Records, Ready Sales Records, Off-Plan Share, Median Sale Price per Sqft, Average Sale Price per Sqft; sales descending |

The requested table fallback is used for activity versus price. Two tables and
two charts are present. Tables support scrolling for complete area detail.
The 30-record rule affects only the pricing bar, not source records or the other
area visuals. Outliers are retained. Slicers: AREA_EN, PROP_TYPE_EN, IS_OFFPLAN_EN,
TRANSACTION_VALUE_BAND.

Source labels are preserved exactly. The semantic model's case-sensitive collation
keeps BUSINESS BAY and Business Bay (and other case-only variants) distinct. This
corrects the default engine's case-insensitive grouping without rewriting labels.

## Property & Pricing — created

Subtitle: Dubai Property Segment and Pricing Analysis.

KPI cards: Sales Records; Residential Share; Median Sale Price per Sqft;
Valid Sale Price Records.

Six horizontal bar charts in a three-by-two grid:

| Chart | Category | Value / filtering |
|---|---|---|
| Property Type Sales Mix | PROP_TYPE_EN | Sales Records |
| Top Property Subtypes | PROP_SB_TYPE_EN | Sales Records; Top N 10 |
| Transaction Value Bands | TRANSACTION_VALUE_BAND | Sales Records; logical band order |
| Property Size Bands | PROPERTY_SIZE_BAND | Sales Records; logical band order |
| Bedroom Analysis | BEDROOM_COUNT | Sales Records; exclude blanks only; numeric ascending |
| Median Sale Price per Sqft by Property Type | PROP_TYPE_EN | Median Sale Price per Sqft |

Slicers: PROP_TYPE_EN, PROP_SB_TYPE_EN, IS_OFFPLAN_EN, TRANSACTION_VALUE_BAND.
Bedroom zero is preserved (including studios); missing values are not invented.

Exact source band orders (spaces preserved):

- Under 500K; 500K - 1M; 1M - 2M; 2M - 5M; 5M - 10M; 10M+.
- Under 50 sqm; 50 - 100 sqm; 100 - 200 sqm; 200 - 500 sqm; 500+ sqm.

Two hidden Int64 Power Query helper columns supply SortByColumn metadata. The CSV
remains 41 columns; FactTransactions exposes 41 source columns plus these 2 helpers.

## Scope and evidence

New additions: 12 KPI cards, 12 charts, 2 tables, 11 slicers, 4 page navigators.
No new DAX measures are required; all 21 baseline definitions are reused.
Stage 11 evidence and final page screenshots are under `validation/stage11/`.
The build report distinguishes native refresh/render evidence from file checks.
No extra tooltip pages, forecasts, investment recommendations or market-value
aggregation is included. Transaction numbers are not treated as unique row keys.
