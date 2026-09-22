-- Dubai Real Estate Intelligence Platform
-- Stage 8: SQL Business Analysis | MySQL 8.4
-- Every statement is SELECT-only, including SELECT statements with CTEs.
-- Tables are fully qualified, so no default database or USE statement is needed.
-- Execute the file in MySQL Workbench or with a connected MySQL client.
--
-- READING THE RESULTS
-- A record is one imported row, not necessarily one distinct transaction.
-- COUNT(DISTINCT TRANSACTION_NUMBER) excludes NULL identifiers. Distinct counts
-- within different months/categories are not necessarily additive.
-- Averages and medians below describe RECORD distributions. Repeated IDs retain
-- their records and influence these statistics; these are not transaction-level
-- averages, property valuations, or ratios of summed transaction values/areas.
-- AVG/MIN/MAX ignore NULL. A missing result is not replaced with an invented 0.
-- Price-per-sqft statistics use Sales with VALID_SALE_PRICE_METRIC = 1 only.
-- Money is in AED and price-per-sqft is AED/sqft. Rounding affects output only.
-- Percentage denominators include all Sales records unless noted otherwise.
-- September 2026 is partial: source coverage ends on 2026-09-21.
-- All values, including extremes, remain in scope. Missing categories remain
-- visible unless a query explicitly limits its scope to named categories.
--
-- TOTAL SALES VALUE IS INTENTIONALLY OMITTED
-- Queries 02/03 test value consistency, missing values and group ambiguity.
-- Multiple values per ID make choosing MIN/MAX as a transaction total arbitrary.
-- Even identical values across lines do not prove whether they describe a whole
-- transaction or individual units. Source-grain documentation is needed before
-- choosing a defensible economic-value aggregation. No SUM(TRANS_VALUE) is used.
--
-- MySQL 8.4 syntax references:
-- https://dev.mysql.com/doc/refman/8.4/en/window-function-descriptions.html
-- https://dev.mysql.com/doc/refman/8.4/en/aggregate-functions.html


-- QUERY 01: Baseline counts for all imported records, including missing IDs.
SELECT 'QUERY 01 - DATASET BASELINE' AS ANALYSIS_SECTION;

SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_transaction_numbers,
    COUNT(*) - COUNT(TRANSACTION_NUMBER) AS missing_transaction_number_records,
    MIN(INSTANCE_DATE) AS earliest_instance_date,
    MAX(INSTANCE_DATE) AS latest_instance_date,
    COUNT(CASE WHEN GROUP_EN = 'Sales' THEN 1 END) AS sales_records,
    COUNT(CASE WHEN GROUP_EN = 'Mortgage' THEN 1 END) AS mortgage_records,
    COUNT(CASE WHEN GROUP_EN = 'Gifts' THEN 1 END) AS gifts_records,
    COUNT(CASE WHEN GROUP_EN <> 'Sales' OR GROUP_EN IS NULL THEN 1 END) AS non_sales_records,
    COUNT(CASE WHEN USAGE_EN = 'Residential' THEN 1 END) AS residential_records,
    COUNT(CASE WHEN USAGE_EN = 'Commercial' THEN 1 END) AS commercial_records,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Off-Plan' THEN 1 END) AS offplan_records,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Ready' THEN 1 END) AS ready_records
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd;


-- QUERY 02: Audit identifiers at their own grain without deleting their lines.
-- COUNT(DISTINCT ...) ignores NULL, so missing values are counted separately.
-- Additional occurrences are records beyond the first per non-NULL identifier.
SELECT 'QUERY 02 - TRANSACTION GRAIN AUDIT' AS ANALYSIS_SECTION;

WITH transaction_grain AS (
    SELECT
        TRANSACTION_NUMBER,
        COUNT(*) AS record_count,
        COUNT(DISTINCT TRANS_VALUE) AS distinct_value_count,
        COUNT(DISTINCT GROUP_EN) AS distinct_group_count,
        COUNT(DISTINCT AREA_EN) AS distinct_area_count,
        COUNT(*) - COUNT(TRANS_VALUE) AS missing_value_records,
        COUNT(*) - COUNT(GROUP_EN) AS missing_group_records,
        COUNT(*) - COUNT(AREA_EN) AS missing_area_records
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
    WHERE TRANSACTION_NUMBER IS NOT NULL
    GROUP BY TRANSACTION_NUMBER
)
SELECT
    COUNT(CASE WHEN record_count > 1 THEN 1 END) AS repeated_transaction_numbers,
    COALESCE(SUM(record_count - 1), 0) AS additional_repeated_occurrences,
    COUNT(CASE WHEN distinct_value_count > 1 THEN 1 END) AS ids_with_multiple_values,
    COUNT(CASE WHEN distinct_group_count > 1 THEN 1 END) AS ids_with_multiple_groups,
    COUNT(CASE WHEN distinct_area_count > 1 THEN 1 END) AS ids_with_multiple_areas,
    COUNT(CASE WHEN missing_value_records > 0 THEN 1 END) AS ids_with_missing_values,
    COUNT(CASE WHEN missing_group_records > 0 THEN 1 END) AS ids_with_missing_groups,
    COUNT(CASE WHEN missing_area_records > 0 THEN 1 END) AS ids_with_missing_areas
FROM transaction_grain;

-- Up to 20 repeated IDs, ordered deterministically by record count and ID.
SELECT 'QUERY 02B - REPEATED TRANSACTION NUMBER SAMPLE' AS ANALYSIS_SECTION;

SELECT
    TRANSACTION_NUMBER AS transaction_number,
    COUNT(*) AS record_count,
    COUNT(DISTINCT TRANS_VALUE) AS distinct_trans_value_count,
    MIN(TRANS_VALUE) AS minimum_trans_value_aed,
    MAX(TRANS_VALUE) AS maximum_trans_value_aed,
    COUNT(DISTINCT AREA_EN) AS distinct_area_count,
    COUNT(DISTINCT GROUP_EN) AS distinct_group_count,
    COUNT(*) - COUNT(TRANS_VALUE) AS missing_trans_value_records
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE TRANSACTION_NUMBER IS NOT NULL
GROUP BY TRANSACTION_NUMBER
HAVING COUNT(*) > 1
ORDER BY record_count DESC, transaction_number
LIMIT 20;


-- QUERY 03: Diagnostic counts, not a claim that economic value is additive.
-- "Single value" means one distinct non-NULL value. The additional complete
-- value count distinguishes this from one known value mixed with NULL lines.
-- All-missing IDs, mixed transaction groups and missing IDs block assumptions.
SELECT 'QUERY 03 - TRANSACTION VALUE AGGREGATION SAFETY' AS ANALYSIS_SECTION;

WITH repeated_ids AS (
    SELECT
        TRANSACTION_NUMBER,
        COUNT(DISTINCT TRANS_VALUE) AS distinct_value_count,
        COUNT(*) - COUNT(TRANS_VALUE) AS missing_value_records,
        COUNT(DISTINCT GROUP_EN) AS distinct_group_count,
        COUNT(*) - COUNT(GROUP_EN) AS missing_group_records
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
    WHERE TRANSACTION_NUMBER IS NOT NULL
    GROUP BY TRANSACTION_NUMBER
    HAVING COUNT(*) > 1
)
SELECT
    COUNT(*) AS repeated_transaction_numbers,
    COUNT(CASE WHEN distinct_value_count = 1 THEN 1 END) AS repeated_ids_with_single_value,
    COUNT(CASE WHEN distinct_value_count > 1 THEN 1 END) AS repeated_ids_with_multiple_values,
    COUNT(CASE WHEN distinct_value_count = 0 THEN 1 END) AS repeated_ids_with_all_values_missing,
    COUNT(CASE WHEN missing_value_records > 0 THEN 1 END) AS repeated_ids_with_missing_values,
    COUNT(CASE WHEN distinct_value_count = 1 AND missing_value_records = 0 THEN 1 END)
        AS repeated_ids_with_one_complete_value,
    COUNT(CASE WHEN distinct_group_count > 1 THEN 1 END) AS repeated_ids_with_multiple_groups,
    COUNT(CASE WHEN missing_group_records > 0 THEN 1 END) AS repeated_ids_with_missing_groups,
    (SELECT COUNT(*)
     FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
     WHERE TRANSACTION_NUMBER IS NULL) AS records_without_transaction_number
FROM repeated_ids;


-- QUERY 04: Monthly Sales activity. The distinct-ID count accompanies records.
SELECT 'QUERY 04 - MONTHLY SALES ACTIVITY' AS ANALYSIS_SECTION;

SELECT
    TRANSACTION_YEAR AS transaction_year,
    TRANSACTION_MONTH AS transaction_month,
    TRANSACTION_MONTH_NAME AS transaction_month_name,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Off-Plan' THEN 1 END) AS offplan_sale_records,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Ready' THEN 1 END) AS ready_sale_records,
    COUNT(CASE WHEN USAGE_EN = 'Residential' THEN 1 END) AS residential_sale_records,
    CASE WHEN TRANSACTION_YEAR = 2026 AND TRANSACTION_MONTH = 9 THEN 1 ELSE 0 END
        AS IS_PARTIAL_MONTH
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales'
GROUP BY TRANSACTION_YEAR, TRANSACTION_MONTH, TRANSACTION_MONTH_NAME
ORDER BY transaction_year, transaction_month;


-- QUERY 05: Change in Sales RECORD counts, not transaction-value growth.
-- LAG reads the prior observed month. The month-number check prevents a gap
-- from being described as the immediately previous calendar month.
-- NULL growth means no comparable prior month or a zero prior denominator.
-- September's observed partial-month change is NOT a full-month comparison.
SELECT 'QUERY 05 - MONTH-OVER-MONTH SALES RECORD GROWTH' AS ANALYSIS_SECTION;

WITH monthly_sales AS (
    SELECT
        TRANSACTION_YEAR,
        TRANSACTION_MONTH,
        TRANSACTION_MONTH_NAME,
        COUNT(*) AS sale_records,
        COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
    WHERE GROUP_EN = 'Sales'
      AND TRANSACTION_YEAR IS NOT NULL
      AND TRANSACTION_MONTH IS NOT NULL
    GROUP BY TRANSACTION_YEAR, TRANSACTION_MONTH, TRANSACTION_MONTH_NAME
), previous_observations AS (
    SELECT
        monthly_sales.*,
        LAG(sale_records) OVER (ORDER BY TRANSACTION_YEAR, TRANSACTION_MONTH)
            AS previous_observed_sale_records,
        LAG(TRANSACTION_YEAR * 12 + TRANSACTION_MONTH)
            OVER (ORDER BY TRANSACTION_YEAR, TRANSACTION_MONTH) AS previous_month_number
    FROM monthly_sales
), comparable_months AS (
    SELECT
        previous_observations.*,
        CASE WHEN TRANSACTION_YEAR * 12 + TRANSACTION_MONTH - previous_month_number = 1
             THEN previous_observed_sale_records END AS previous_month_sale_records
    FROM previous_observations
)
SELECT
    TRANSACTION_YEAR AS transaction_year,
    TRANSACTION_MONTH AS transaction_month,
    TRANSACTION_MONTH_NAME AS transaction_month_name,
    sale_records AS sale_records,
    distinct_sale_transaction_numbers AS distinct_sale_transaction_numbers,
    previous_month_sale_records AS previous_month_sale_records,
    CAST(sale_records AS SIGNED) - CAST(previous_month_sale_records AS SIGNED)
        AS absolute_change,
    ROUND(100.0 * (CAST(sale_records AS SIGNED) - CAST(previous_month_sale_records AS SIGNED))
          / NULLIF(previous_month_sale_records, 0), 2) AS percentage_change,
    CASE WHEN TRANSACTION_YEAR = 2026 AND TRANSACTION_MONTH = 9 THEN 1 ELSE 0 END
        AS IS_PARTIAL_MONTH
FROM comparable_months
ORDER BY transaction_year, transaction_month;


-- QUERY 06: Off-Plan versus Ready, retaining any other/missing category.
-- SUM(COUNT(*)) OVER () adds group record counts, never transaction values.
SELECT 'QUERY 06 - OFF-PLAN VS READY SALES' AS ANALYSIS_SECTION;

SELECT
    IS_OFFPLAN_EN AS is_offplan_en,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2)
        AS percentage_of_sale_records,
    COUNT(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END)
        AS populated_valid_price_records,
    ROUND(AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END), 2)
        AS average_sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales'
GROUP BY IS_OFFPLAN_EN
ORDER BY sale_records DESC, is_offplan_en;


-- QUERY 07: Property type activity and explicitly labelled arithmetic averages.
-- Average record value retains every non-NULL TRANS_VALUE, including extremes.
SELECT 'QUERY 07 - PROPERTY TYPE SALES' AS ANALYSIS_SECTION;

SELECT
    PROP_TYPE_EN AS prop_type_en,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2)
        AS percentage_of_sale_records,
    ROUND(AVG(TRANS_VALUE), 2) AS average_record_trans_value_aed,
    ROUND(AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END), 2)
        AS average_sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales'
GROUP BY PROP_TYPE_EN
ORDER BY sale_records DESC, prop_type_en;


-- QUERY 08: The 15 most frequent named subtypes. NULL subtype is excluded here.
SELECT 'QUERY 08 - PROPERTY SUBTYPE SALES' AS ANALYSIS_SECTION;

SELECT
    PROP_SB_TYPE_EN AS prop_sb_type_en,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    ROUND(AVG(TRANS_VALUE), 2) AS average_record_trans_value_aed,
    ROUND(AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END), 2)
        AS average_sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales' AND PROP_SB_TYPE_EN IS NOT NULL
GROUP BY PROP_SB_TYPE_EN
ORDER BY sale_records DESC, prop_sb_type_en
LIMIT 15;


-- QUERY 09: The 15 named areas with most Sales records, plus record price metrics.
-- Median: sort non-NULL valid prices and average the middle one/two positions.
-- ROW_ID breaks price ties without deleting records. LEFT JOIN retains areas
-- with activity but no eligible price observations; their median stays NULL.
SELECT 'QUERY 09 - TOP AREAS BY SALES ACTIVITY' AS ANALYSIS_SECTION;

WITH area_activity AS (
    SELECT
        AREA_EN,
        COUNT(*) AS sale_records,
        COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
        COUNT(CASE WHEN IS_OFFPLAN_EN = 'Off-Plan' THEN 1 END) AS offplan_sale_records,
        COUNT(CASE WHEN IS_OFFPLAN_EN = 'Ready' THEN 1 END) AS ready_sale_records,
        AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END)
            AS average_sale_price_per_sqft
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
    WHERE GROUP_EN = 'Sales' AND AREA_EN IS NOT NULL
    GROUP BY AREA_EN
), ordered_prices AS (
    SELECT
        AREA_EN,
        SALE_PRICE_PER_SQFT,
        ROW_NUMBER() OVER (PARTITION BY AREA_EN ORDER BY SALE_PRICE_PER_SQFT, ROW_ID)
            AS price_position,
        COUNT(*) OVER (PARTITION BY AREA_EN) AS price_count
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
    WHERE GROUP_EN = 'Sales' AND VALID_SALE_PRICE_METRIC = 1
      AND AREA_EN IS NOT NULL AND SALE_PRICE_PER_SQFT IS NOT NULL
), area_medians AS (
    SELECT AREA_EN, AVG(SALE_PRICE_PER_SQFT) AS median_sale_price_per_sqft
    FROM ordered_prices
    WHERE price_position IN (FLOOR((price_count + 1) / 2), FLOOR((price_count + 2) / 2))
    GROUP BY AREA_EN
)
SELECT
    activity.AREA_EN AS area_en,
    activity.sale_records AS sale_records,
    activity.distinct_sale_transaction_numbers AS distinct_sale_transaction_numbers,
    activity.offplan_sale_records AS offplan_sale_records,
    activity.ready_sale_records AS ready_sale_records,
    ROUND(activity.average_sale_price_per_sqft, 2) AS average_sale_price_per_sqft,
    ROUND(medians.median_sale_price_per_sqft, 2) AS median_sale_price_per_sqft
FROM area_activity AS activity
LEFT JOIN area_medians AS medians ON activity.AREA_EN = medians.AREA_EN
ORDER BY activity.sale_records DESC, activity.AREA_EN
LIMIT 15;


-- QUERY 10: Named areas with at least 100 valid Sales records.
-- The threshold counts eligible records; populated_price_records separately
-- exposes any unexpected NULL prices among them. No outliers are removed.
-- Ordering uses the unrounded median so display rounding cannot change rank.
SELECT 'QUERY 10 - AREA PRICE BENCHMARK' AS ANALYSIS_SECTION;

WITH area_statistics AS (
    SELECT
        AREA_EN,
        COUNT(*) AS valid_sale_records,
        COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
        COUNT(SALE_PRICE_PER_SQFT) AS populated_price_records,
        AVG(SALE_PRICE_PER_SQFT) AS average_sale_price_per_sqft,
        MIN(SALE_PRICE_PER_SQFT) AS minimum_sale_price_per_sqft,
        MAX(SALE_PRICE_PER_SQFT) AS maximum_sale_price_per_sqft
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
    WHERE GROUP_EN = 'Sales' AND VALID_SALE_PRICE_METRIC = 1 AND AREA_EN IS NOT NULL
    GROUP BY AREA_EN
    HAVING COUNT(*) >= 100
), ordered_prices AS (
    SELECT
        records.AREA_EN,
        records.SALE_PRICE_PER_SQFT,
        ROW_NUMBER() OVER (
            PARTITION BY records.AREA_EN ORDER BY records.SALE_PRICE_PER_SQFT, records.ROW_ID
        ) AS price_position,
        COUNT(*) OVER (PARTITION BY records.AREA_EN) AS price_count
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd AS records
    INNER JOIN area_statistics AS areas ON records.AREA_EN = areas.AREA_EN
    WHERE records.GROUP_EN = 'Sales' AND records.VALID_SALE_PRICE_METRIC = 1
      AND records.SALE_PRICE_PER_SQFT IS NOT NULL
), area_medians AS (
    SELECT AREA_EN, AVG(SALE_PRICE_PER_SQFT) AS median_sale_price_per_sqft
    FROM ordered_prices
    WHERE price_position IN (FLOOR((price_count + 1) / 2), FLOOR((price_count + 2) / 2))
    GROUP BY AREA_EN
)
SELECT
    areas.AREA_EN AS area_en,
    areas.valid_sale_records AS valid_sale_records,
    areas.distinct_sale_transaction_numbers AS distinct_sale_transaction_numbers,
    areas.populated_price_records AS populated_price_records,
    ROUND(areas.average_sale_price_per_sqft, 2) AS average_sale_price_per_sqft,
    ROUND(medians.median_sale_price_per_sqft, 2) AS median_sale_price_per_sqft,
    ROUND(areas.minimum_sale_price_per_sqft, 2) AS minimum_sale_price_per_sqft,
    ROUND(areas.maximum_sale_price_per_sqft, 2) AS maximum_sale_price_per_sqft
FROM area_statistics AS areas
LEFT JOIN area_medians AS medians ON areas.AREA_EN = medians.AREA_EN
ORDER BY medians.median_sale_price_per_sqft DESC, areas.AREA_EN;


-- QUERY 11: Existing Sales value bands, logically ordered without relabelling.
-- Missing/unexpected bands remain visible after the six defined bands.
SELECT 'QUERY 11 - SALES VALUE BANDS' AS ANALYSIS_SECTION;

SELECT
    TRANSACTION_VALUE_BAND AS transaction_value_band,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2)
        AS percentage_of_sale_records
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales'
GROUP BY TRANSACTION_VALUE_BAND
ORDER BY CASE TRANSACTION_VALUE_BAND
    WHEN 'Under 500K' THEN 1
    WHEN '500K - 1M' THEN 2
    WHEN '1M - 2M' THEN 3
    WHEN '2M - 5M' THEN 4
    WHEN '5M - 10M' THEN 5
    WHEN '10M+' THEN 6
    ELSE 7
END, transaction_value_band;


-- QUERY 12: Existing property size bands. NULL bands are counted, not filled.
SELECT 'QUERY 12 - PROPERTY SIZE BANDS' AS ANALYSIS_SECTION;

SELECT
    PROPERTY_SIZE_BAND AS property_size_band,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2)
        AS percentage_of_sale_records,
    ROUND(AVG(TRANS_VALUE), 2) AS average_record_trans_value_aed,
    ROUND(AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END), 2)
        AS average_sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales'
GROUP BY PROPERTY_SIZE_BAND
ORDER BY CASE PROPERTY_SIZE_BAND
    WHEN 'Under 50 sqm' THEN 1
    WHEN '50 - 100 sqm' THEN 2
    WHEN '100 - 200 sqm' THEN 3
    WHEN '200 - 500 sqm' THEN 4
    WHEN '500+ sqm' THEN 5
    ELSE 6
END, property_size_band;


-- QUERY 13: Residential Sales with a known bedroom mapping; Studio is 0.
-- Unknown bedroom categories are excluded from this result, never guessed.
SELECT 'QUERY 13 - BEDROOM ANALYSIS' AS ANALYSIS_SECTION;

SELECT
    BEDROOM_COUNT AS bedroom_count,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    ROUND(AVG(TRANS_VALUE), 2) AS average_record_trans_value_aed,
    ROUND(AVG(PROPERTY_SIZE_SQFT), 2) AS average_property_size_sqft,
    ROUND(AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END), 2)
        AS average_sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales' AND USAGE_EN = 'Residential' AND BEDROOM_COUNT IS NOT NULL
GROUP BY BEDROOM_COUNT
ORDER BY bedroom_count;


-- QUERY 14: The 15 most active named projects by Sales records.
-- Grouping is by the official project-name text, not an invented project ID.
SELECT 'QUERY 14 - PROJECT ANALYSIS' AS ANALYSIS_SECTION;

SELECT
    PROJECT_EN AS project_en,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Off-Plan' THEN 1 END) AS offplan_sale_records,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Ready' THEN 1 END) AS ready_sale_records,
    ROUND(AVG(TRANS_VALUE), 2) AS average_record_trans_value_aed,
    ROUND(AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END), 2)
        AS average_sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales' AND PROJECT_EN IS NOT NULL
GROUP BY PROJECT_EN
ORDER BY sale_records DESC, project_en
LIMIT 15;


-- QUERY 15: High-value Sales records (at least AED 10 million), no value total.
-- The denominator is ALL Sales records, not only the high-value subset.
SELECT 'QUERY 15 - HIGH-VALUE SALES' AS ANALYSIS_SECTION;

SELECT
    COUNT(CASE WHEN TRANS_VALUE >= 10000000 THEN 1 END) AS high_value_sale_records,
    COUNT(DISTINCT CASE WHEN TRANS_VALUE >= 10000000 THEN TRANSACTION_NUMBER END)
        AS distinct_high_value_sale_transaction_numbers,
    ROUND(100.0 * COUNT(CASE WHEN TRANS_VALUE >= 10000000 THEN 1 END)
          / NULLIF(COUNT(*), 0), 2) AS percentage_of_sale_records
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales';

-- Individual records, not a deduplicated list of transactions or investments.
-- ROW_ID is shown solely to distinguish records with repeated transaction IDs.
SELECT 'QUERY 15B - TOP 20 HIGH-VALUE SALES RECORDS' AS ANALYSIS_SECTION;

SELECT
    ROW_ID AS row_id,
    TRANSACTION_NUMBER AS transaction_number,
    INSTANCE_DATE AS instance_date,
    AREA_EN AS area_en,
    PROJECT_EN AS project_en,
    PROP_TYPE_EN AS prop_type_en,
    PROP_SB_TYPE_EN AS prop_sb_type_en,
    IS_OFFPLAN_EN AS is_offplan_en,
    TRANS_VALUE AS trans_value_aed,
    ACTUAL_AREA AS actual_area_sqm,
    CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END
        AS sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales' AND TRANS_VALUE >= 10000000
ORDER BY TRANS_VALUE DESC, ROW_ID
LIMIT 20;


-- QUERY 16: Monthly Off-Plan record share; unknown categories stay in denominator.
-- September remains explicitly marked as partial, with no extrapolation.
SELECT 'QUERY 16 - MONTHLY OFF-PLAN SHARE' AS ANALYSIS_SECTION;

SELECT
    TRANSACTION_YEAR AS transaction_year,
    TRANSACTION_MONTH AS transaction_month,
    TRANSACTION_MONTH_NAME AS transaction_month_name,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Off-Plan' THEN 1 END) AS offplan_sale_records,
    COUNT(CASE WHEN IS_OFFPLAN_EN = 'Ready' THEN 1 END) AS ready_sale_records,
    ROUND(100.0 * COUNT(CASE WHEN IS_OFFPLAN_EN = 'Off-Plan' THEN 1 END)
          / NULLIF(COUNT(*), 0), 2) AS offplan_share_percentage,
    CASE WHEN TRANSACTION_YEAR = 2026 AND TRANSACTION_MONTH = 9 THEN 1 ELSE 0 END
        AS IS_PARTIAL_MONTH
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales'
GROUP BY TRANSACTION_YEAR, TRANSACTION_MONTH, TRANSACTION_MONTH_NAME
ORDER BY transaction_year, transaction_month;


-- QUERY 17: Official freehold categories for Sales, including NULL if present.
SELECT 'QUERY 17 - FREEHOLD ANALYSIS' AS ANALYSIS_SECTION;

SELECT
    IS_FREE_HOLD_EN AS is_free_hold_en,
    COUNT(*) AS sale_records,
    COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_sale_transaction_numbers,
    ROUND(AVG(TRANS_VALUE), 2) AS average_record_trans_value_aed,
    ROUND(AVG(CASE WHEN VALID_SALE_PRICE_METRIC = 1 THEN SALE_PRICE_PER_SQFT END), 2)
        AS average_sale_price_per_sqft
FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
WHERE GROUP_EN = 'Sales'
GROUP BY IS_FREE_HOLD_EN
ORDER BY sale_records DESC, is_free_hold_en;


-- QUERY 18: Read-only quality checks across all records.
-- Non-Sales normally have missing sale-price metrics. Report those separately
-- from Sales problems, and distinguish zero/negative values from missing ones.
-- Exact duplicates are compared across ALL 22 original DLD columns, excluding
-- ROW_ID and all derived features. NULLs group together without filling data.
-- This grouping is deliberately more expensive than an identifier-only check.
SELECT 'QUERY 18 - DATA QUALITY CHECK' AS ANALYSIS_SECTION;

WITH original_record_groups AS (
    SELECT COUNT(*) AS matching_record_count
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
    GROUP BY
        TRANSACTION_NUMBER, INSTANCE_DATE, GROUP_EN, PROCEDURE_EN,
        IS_OFFPLAN_EN, IS_FREE_HOLD_EN, USAGE_EN, AREA_EN,
        PROP_TYPE_EN, PROP_SB_TYPE_EN, TRANS_VALUE, PROCEDURE_AREA,
        ACTUAL_AREA, ROOMS_EN, PARKING, NEAREST_METRO_EN,
        NEAREST_MALL_EN, NEAREST_LANDMARK_EN, TOTAL_BUYER, TOTAL_SELLER,
        MASTER_PROJECT_EN, PROJECT_EN
    HAVING COUNT(*) > 1
), duplicate_summary AS (
    SELECT
        COUNT(*) AS exact_duplicate_original_record_groups,
        COALESCE(SUM(matching_record_count - 1), 0) AS additional_exact_duplicate_original_records
    FROM original_record_groups
), quality_summary AS (
    SELECT
        COUNT(*) AS total_records,
        COUNT(DISTINCT TRANSACTION_NUMBER) AS distinct_transaction_numbers,
        COUNT(*) - COUNT(TRANSACTION_NUMBER) AS null_transaction_number_records,
        COUNT(*) - COUNT(INSTANCE_DATE) AS null_instance_date_records,
        COUNT(*) - COUNT(PROJECT_EN) AS null_project_name_records,
        COUNT(*) - COUNT(ROOMS_EN) AS null_room_category_records,
        COUNT(*) - COUNT(MASTER_PROJECT_EN) AS null_master_project_name_records,
        COUNT(*) - COUNT(SALE_PRICE_PER_SQFT) AS null_sale_price_per_sqft_records,
        COUNT(CASE WHEN VALID_SALE_PRICE_METRIC <> 1 OR VALID_SALE_PRICE_METRIC IS NULL
                        OR SALE_PRICE_PER_SQFT IS NULL THEN 1 END)
            AS ineligible_or_missing_price_metric_records,
        COUNT(CASE WHEN GROUP_EN = 'Sales'
                    AND (VALID_SALE_PRICE_METRIC <> 1 OR VALID_SALE_PRICE_METRIC IS NULL
                         OR SALE_PRICE_PER_SQFT IS NULL) THEN 1 END)
            AS sales_with_invalid_or_missing_price_metric,
        COUNT(CASE WHEN (GROUP_EN <> 'Sales' OR GROUP_EN IS NULL)
                    AND SALE_PRICE_PER_SQFT IS NULL THEN 1 END)
            AS non_sales_with_expected_null_price_metric,
        COUNT(CASE WHEN (GROUP_EN <> 'Sales' OR GROUP_EN IS NULL)
                    AND (SALE_PRICE_PER_SQFT IS NOT NULL OR SALE_PRICE_PER_SQM IS NOT NULL)
                   THEN 1 END) AS non_sales_with_unexpected_price_metrics,
        COUNT(CASE WHEN TRANS_VALUE <= 0 THEN 1 END) AS non_positive_trans_value_records,
        COUNT(*) - COUNT(TRANS_VALUE) AS null_trans_value_records,
        COUNT(CASE WHEN ACTUAL_AREA <= 0 THEN 1 END) AS non_positive_actual_area_records,
        COUNT(*) - COUNT(ACTUAL_AREA) AS null_actual_area_records
    FROM dubai_real_estate_intelligence.dld_transactions_2026_ytd
)
SELECT
    quality.total_records AS total_records,
    quality.distinct_transaction_numbers AS distinct_transaction_numbers,
    quality.null_transaction_number_records AS null_transaction_number_records,
    quality.null_instance_date_records AS null_instance_date_records,
    quality.null_project_name_records AS null_project_name_records,
    quality.null_room_category_records AS null_room_category_records,
    quality.null_master_project_name_records AS null_master_project_name_records,
    quality.null_sale_price_per_sqft_records AS null_sale_price_per_sqft_records,
    quality.ineligible_or_missing_price_metric_records AS ineligible_or_missing_price_metric_records,
    quality.sales_with_invalid_or_missing_price_metric AS sales_with_invalid_or_missing_price_metric,
    quality.non_sales_with_expected_null_price_metric AS non_sales_with_expected_null_price_metric,
    quality.non_sales_with_unexpected_price_metrics AS non_sales_with_unexpected_price_metrics,
    duplicates.exact_duplicate_original_record_groups AS exact_duplicate_original_record_groups,
    duplicates.additional_exact_duplicate_original_records AS additional_exact_duplicate_original_records,
    quality.non_positive_trans_value_records AS non_positive_trans_value_records,
    quality.null_trans_value_records AS null_trans_value_records,
    quality.non_positive_actual_area_records AS non_positive_actual_area_records,
    quality.null_actual_area_records AS null_actual_area_records
FROM quality_summary AS quality
CROSS JOIN duplicate_summary AS duplicates;
