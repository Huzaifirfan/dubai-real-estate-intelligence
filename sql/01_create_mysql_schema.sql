-- Stage 7: run this file in MySQL Workbench or a MySQL client before the loader.
-- Requires MySQL 8.0+; the binary collation preserves distinctions between
-- official category spellings. No existing database/table is dropped or cleared.
CREATE DATABASE IF NOT EXISTS `dubai_real_estate_intelligence`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin;

USE `dubai_real_estate_intelligence`;

CREATE TABLE IF NOT EXISTS `dld_transactions_2026_ytd` (
    -- Technical database identifier only; it is not a source CSV column.
    `ROW_ID` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Original 22 DLD fields. Transaction numbers are deliberately NOT unique.
    `TRANSACTION_NUMBER` VARCHAR(64) NULL,
    `INSTANCE_DATE` DATETIME(6) NULL,
    `GROUP_EN` VARCHAR(64) NULL,
    `PROCEDURE_EN` VARCHAR(255) NULL,
    `IS_OFFPLAN_EN` VARCHAR(32) NULL,
    `IS_FREE_HOLD_EN` VARCHAR(32) NULL,
    `USAGE_EN` VARCHAR(64) NULL,
    `AREA_EN` VARCHAR(255) NULL,
    `PROP_TYPE_EN` VARCHAR(128) NULL,
    `PROP_SB_TYPE_EN` VARCHAR(128) NULL,
    `TRANS_VALUE` DECIMAL(24,2) NULL,
    `PROCEDURE_AREA` DECIMAL(24,2) NULL,
    `ACTUAL_AREA` DECIMAL(24,2) NULL,
    `ROOMS_EN` VARCHAR(64) NULL,
    -- Parking can contain long lists: the current CSV has up to 820 characters.
    `PARKING` VARCHAR(2048) NULL,
    `NEAREST_METRO_EN` VARCHAR(255) NULL,
    `NEAREST_MALL_EN` VARCHAR(255) NULL,
    `NEAREST_LANDMARK_EN` VARCHAR(255) NULL,
    `TOTAL_BUYER` INT NULL,
    `TOTAL_SELLER` INT NULL,
    `MASTER_PROJECT_EN` VARCHAR(512) NULL,
    `PROJECT_EN` VARCHAR(512) NULL,

    -- The eight existing Stage 5 date fields.
    `TRANSACTION_DATE` DATE NULL,
    `TRANSACTION_YEAR` SMALLINT NULL,
    `TRANSACTION_MONTH` TINYINT NULL,
    `TRANSACTION_MONTH_NAME` VARCHAR(16) NULL,
    `TRANSACTION_QUARTER` VARCHAR(2) NULL,
    `TRANSACTION_DAY` TINYINT NULL,
    `TRANSACTION_DAY_NAME` VARCHAR(16) NULL,
    `TRANSACTION_HOUR` TINYINT NULL,

    -- The eleven existing Stage 6 features. Decimal scales preserve all
    -- fractional digits currently present in the CSV; the loader rejects
    -- values that would require rounding or exceed the declared capacity.
    `IS_SALE_TRANSACTION` TINYINT NOT NULL,
    `IS_RESIDENTIAL_FLAG` TINYINT NOT NULL,
    `IS_OFFPLAN_FLAG` TINYINT NULL,
    `IS_FREEHOLD_FLAG` TINYINT NULL,
    `PROPERTY_SIZE_SQFT` DECIMAL(34,14) NULL,
    `VALID_SALE_PRICE_METRIC` TINYINT NOT NULL,
    `SALE_PRICE_PER_SQM` DECIMAL(36,16) NULL,
    `SALE_PRICE_PER_SQFT` DECIMAL(37,17) NULL,
    `TRANSACTION_VALUE_BAND` VARCHAR(32) NULL,
    `PROPERTY_SIZE_BAND` VARCHAR(32) NULL,
    `BEDROOM_COUNT` TINYINT NULL,

    -- Non-unique indexes help validation filters and later querying.
    KEY `idx_dld_instance_date` (`INSTANCE_DATE`),
    KEY `idx_dld_transaction_number` (`TRANSACTION_NUMBER`),
    KEY `idx_dld_area` (`AREA_EN`),
    KEY `idx_dld_group` (`GROUP_EN`),
    KEY `idx_dld_offplan` (`IS_OFFPLAN_EN`),
    KEY `idx_dld_property_type` (`PROP_TYPE_EN`)
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE=utf8mb4_0900_bin;

-- IF NOT EXISTS does not repair an existing incompatible table. The Python
-- loader validates its schema and will stop rather than change or clear it.
