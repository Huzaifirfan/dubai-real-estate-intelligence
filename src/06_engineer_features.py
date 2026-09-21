"""Stage 6: add analytics features without changing any existing source fields.

Run: python src/06_engineer_features.py
All rows and original column values are preserved, including repeated transaction
numbers, missing fields, and official category spelling/capitalization.
"""

import hashlib
import io
from pathlib import Path
import tempfile

try:
    import pandas as pd
except ImportError:
    raise SystemExit(
        "pandas is required. Activate your project environment, then run:\n"
        "python -m pip install -r requirements.txt"
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = PROJECT_ROOT / "data/processed/dld_transactions_2026_ytd_clean.csv"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/dld_transactions_2026_ytd_features.csv"
REPORT_PATH = PROJECT_ROOT / "reports/stage6_feature_engineering_report.txt"
SQFT_PER_SQM = 10.7639104167

SOURCE_COLUMNS = [
    "TRANSACTION_NUMBER", "INSTANCE_DATE", "GROUP_EN", "PROCEDURE_EN",
    "IS_OFFPLAN_EN", "IS_FREE_HOLD_EN", "USAGE_EN", "AREA_EN", "PROP_TYPE_EN",
    "PROP_SB_TYPE_EN", "TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA", "ROOMS_EN",
    "PARKING", "NEAREST_METRO_EN", "NEAREST_MALL_EN", "NEAREST_LANDMARK_EN",
    "TOTAL_BUYER", "TOTAL_SELLER", "MASTER_PROJECT_EN", "PROJECT_EN",
    "TRANSACTION_DATE", "TRANSACTION_YEAR", "TRANSACTION_MONTH",
    "TRANSACTION_MONTH_NAME", "TRANSACTION_QUARTER", "TRANSACTION_DAY",
    "TRANSACTION_DAY_NAME", "TRANSACTION_HOUR",
]
FEATURE_COLUMNS = [
    "IS_SALE_TRANSACTION", "IS_RESIDENTIAL_FLAG", "IS_OFFPLAN_FLAG",
    "IS_FREEHOLD_FLAG", "PROPERTY_SIZE_SQFT", "VALID_SALE_PRICE_METRIC",
    "SALE_PRICE_PER_SQM", "SALE_PRICE_PER_SQFT", "TRANSACTION_VALUE_BAND",
    "PROPERTY_SIZE_BAND", "BEDROOM_COUNT",
]
OFFPLAN_MAP = {"Off-Plan": 1, "Ready": 0}
FREEHOLD_MAP = {"Free Hold": 1, "Non Free Hold": 0}
BEDROOM_MAP = {"Studio": 0, **{f"{number} B/R": number for number in range(1, 8)}}

# Lower boundaries are inclusive; upper boundaries are exclusive.
# None means there is no boundary on that side.
VALUE_BANDS = [
    (None, 500000, "Under 500K"), (500000, 1000000, "500K - 1M"),
    (1000000, 2000000, "1M - 2M"), (2000000, 5000000, "2M - 5M"),
    (5000000, 10000000, "5M - 10M"), (10000000, None, "10M+"),
]
SIZE_BANDS = [
    (None, 50, "Under 50 sqm"), (50, 100, "50 - 100 sqm"),
    (100, 200, "100 - 200 sqm"), (200, 500, "200 - 500 sqm"),
    (500, None, "500+ sqm"),
]


def file_hash(path):
    """Calculate SHA-256 using read-only access to the file."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_paths():
    """Prevent either output from overwriting the input, including via aliases."""
    paths = [SOURCE_PATH, OUTPUT_PATH, REPORT_PATH]
    for position, first in enumerate(paths):
        for second in paths[position + 1:]:
            same_file = first.resolve() == second.resolve()
            if first.exists() and second.exists():
                same_file = same_file or first.samefile(second)
            if same_file:
                raise ValueError(f"Input and outputs must be separate files: {first} and {second}")


def load_source():
    """Fingerprint and read one snapshot, preserving all original CSV field text."""
    content = SOURCE_PATH.read_bytes()
    fingerprint = hashlib.sha256(content).hexdigest()
    options = dict(dtype="string", keep_default_na=False, na_filter=False,
                   skip_blank_lines=False, low_memory=False)
    try:
        data = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", **options)
        encoding = "UTF-8"
    except UnicodeDecodeError:
        print("UTF-8 decoding failed. Trying Windows-1252 (cp1252).")
        data = pd.read_csv(io.BytesIO(content), encoding="cp1252", **options)
        encoding = "Windows-1252 fallback; original encoding not confirmed"
        print("Check official category text against the source when fallback encoding is used.")
    # This retains literal categories such as 'NA', empty fields, date text,
    # numeric representations, and IDs exactly as they were stored in Stage 5.
    if not isinstance(data.index, pd.RangeIndex):
        raise ValueError("Extra CSV fields were interpreted as an index. Check the source header.")
    return data, fingerprint, encoding


def band_mask(values, lower, upper, eligible):
    """Return the rows belonging to one inclusive-lower/exclusive-upper band."""
    selected = values.notna() & eligible
    if lower is not None:
        selected &= values.ge(lower).fillna(False)
    if upper is not None:
        selected &= values.lt(upper).fillna(False)
    return selected


def assign_bands(values, definitions, eligible):
    """Leave ineligible values missing; never change the source numeric field."""
    bands = pd.Series(pd.NA, index=values.index, dtype="string")
    for lower, upper, label in definitions:
        bands.loc[band_mask(values, lower, upper, eligible)] = label
    return bands


def identifier_count(series):
    return int((series.notna() & series.ne("")).sum())


def engineer_features(source):
    """Append exactly eleven features, then validate preservation and mappings."""
    missing = [column for column in SOURCE_COLUMNS if column not in source.columns]
    unexpected = [column for column in source.columns if column not in SOURCE_COLUMNS]
    if missing or unexpected or not source.columns.is_unique:
        raise ValueError(
            "Expected the Stage 5 input with its 30 existing columns.\n"
            f"Missing columns: {', '.join(missing) or 'None'}\n"
            f"Unexpected columns: {', '.join(unexpected) or 'None'}\n"
            "No column names were changed."
        )

    output = source.copy()
    # These temporary numeric Series are for calculations only. The existing
    # TRANS_VALUE and ACTUAL_AREA columns in output remain completely unchanged.
    values = pd.to_numeric(source["TRANS_VALUE"], errors="coerce")
    areas = pd.to_numeric(source["ACTUAL_AREA"], errors="coerce")
    sales = source["GROUP_EN"].eq("Sales").fillna(False)
    residential = source["USAGE_EN"].eq("Residential").fillna(False)
    positive_area = areas.gt(0).fillna(False)
    valid_sale = sales & values.gt(0).fillna(False) & positive_area
    # fillna(False) above applies only to selection masks, not to DLD data.

    output["IS_SALE_TRANSACTION"] = sales.astype("Int8")
    output["IS_RESIDENTIAL_FLAG"] = residential.astype("Int8")
    output["IS_OFFPLAN_FLAG"] = source["IS_OFFPLAN_EN"].map(OFFPLAN_MAP).astype("Int8")
    output["IS_FREEHOLD_FLAG"] = source["IS_FREE_HOLD_EN"].map(FREEHOLD_MAP).astype("Int8")

    output["PROPERTY_SIZE_SQFT"] = pd.Series(pd.NA, index=source.index, dtype="Float64")
    output.loc[positive_area, "PROPERTY_SIZE_SQFT"] = areas.loc[positive_area] * SQFT_PER_SQM
    output["VALID_SALE_PRICE_METRIC"] = valid_sale.astype("Int8")

    # Restrict divisions to eligible Sales rows. Mortgages, Gifts, and any other
    # non-sale categories always retain missing sale price-per-area metrics.
    for column in ("SALE_PRICE_PER_SQM", "SALE_PRICE_PER_SQFT"):
        output[column] = pd.Series(pd.NA, index=source.index, dtype="Float64")
    output.loc[valid_sale, "SALE_PRICE_PER_SQM"] = values.loc[valid_sale] / areas.loc[valid_sale]
    output.loc[valid_sale, "SALE_PRICE_PER_SQFT"] = (
        values.loc[valid_sale] / output.loc[valid_sale, "PROPERTY_SIZE_SQFT"]
    )
    output["TRANSACTION_VALUE_BAND"] = assign_bands(values, VALUE_BANDS, values.notna())
    output["PROPERTY_SIZE_BAND"] = assign_bands(areas, SIZE_BANDS, positive_area)
    output["BEDROOM_COUNT"] = source["ROOMS_EN"].map(BEDROOM_MAP).astype("Int64")

    # Compare every source cell and its row position, not just aggregate counts.
    # This catches overwritten columns, lost records, and removed repeated IDs.
    unchanged_columns = output.loc[:, list(source.columns)].equals(source)
    checks = {
        "Output row count exactly equals input row count": len(output) == len(source),
        "All existing 30 columns retain their original names and order":
        list(output.columns[:len(source.columns)]) == list(source.columns),
        "All 11 Stage 6 features exist in the expected order":
        list(output.columns[len(source.columns):]) == FEATURE_COLUMNS,
        "Output has exactly 41 columns": len(output.columns) == len(SOURCE_COLUMNS) + len(FEATURE_COLUMNS),
        "No source column values were overwritten and no source rows were removed": unchanged_columns,
        "Source row order is unchanged": output.index.equals(source.index),
        "Transaction-number count and every repeated occurrence are unchanged":
        identifier_count(output["TRANSACTION_NUMBER"]) == identifier_count(source["TRANSACTION_NUMBER"])
        and output["TRANSACTION_NUMBER"].equals(source["TRANSACTION_NUMBER"]),
        "Sales flag uses only GROUP_EN": output["IS_SALE_TRANSACTION"].eq(sales.astype("Int8")).all(),
        "Residential flag follows USAGE_EN": output["IS_RESIDENTIAL_FLAG"].eq(residential.astype("Int8")).all(),
        "Sale price validity flag requires Sales and positive value/area":
        output["VALID_SALE_PRICE_METRIC"].eq(valid_sale.astype("Int8")).all(),
        "Sale price per sqm is populated exactly on valid sale rows":
        output["SALE_PRICE_PER_SQM"].notna().eq(valid_sale).all(),
        "Sale price per sqft is populated exactly on valid sale rows":
        output["SALE_PRICE_PER_SQFT"].notna().eq(valid_sale).all(),
        "No non-sale record has a sale price-per-area metric":
        output.loc[~sales, ["SALE_PRICE_PER_SQM", "SALE_PRICE_PER_SQFT"]].isna().all().all(),
        "Property size sqft is populated only for positive numeric area":
        output["PROPERTY_SIZE_SQFT"].notna().eq(positive_area).all(),
        "Property size sqft is positive whenever populated": output["PROPERTY_SIZE_SQFT"].dropna().gt(0).all(),
        "Bedroom counts follow only the defined mappings":
        output["BEDROOM_COUNT"].equals(source["ROOMS_EN"].map(BEDROOM_MAP).astype("Int64")),
        "Unexpected or missing bedroom categories have no guessed count":
        output.loc[~source["ROOMS_EN"].isin(BEDROOM_MAP), "BEDROOM_COUNT"].isna().all(),
    }
    for flag in ("IS_SALE_TRANSACTION", "IS_RESIDENTIAL_FLAG", "VALID_SALE_PRICE_METRIC"):
        checks[f"{flag} contains only 0/1 with no missing flags"] = output[flag].isin([0, 1]).all()
    for flag, column, mapping in (
        ("IS_OFFPLAN_FLAG", "IS_OFFPLAN_EN", OFFPLAN_MAP),
        ("IS_FREEHOLD_FLAG", "IS_FREE_HOLD_EN", FREEHOLD_MAP),
    ):
        checks[f"{flag} has defined 0/1 mappings; unknown values remain missing"] = (
            output[flag].dropna().isin([0, 1]).all()
            and output[flag].equals(source[column].map(mapping).astype("Int8"))
        )
    for column, numbers, definitions, eligible in (
        ("TRANSACTION_VALUE_BAND", values, VALUE_BANDS, values.notna()),
        ("PROPERTY_SIZE_BAND", areas, SIZE_BANDS, positive_area),
    ):
        checks[f"{column} has correct boundaries and missing-value rules"] = (
            output[column].notna().eq(eligible).all()
            and all(output[column].eq(label).fillna(False).eq(
                band_mask(numbers, lower, upper, eligible)
            ).all() for lower, upper, label in definitions)
        )
    failures = [label for label, passed in checks.items() if not passed]
    if failures:
        raise ValueError("Validation failed; outputs were not saved:\n- " + "\n- ".join(failures))

    numeric_issues = {}
    for column, numeric in (("TRANS_VALUE", values), ("ACTUAL_AREA", areas)):
        nonempty = source[column].notna() & source[column].ne("")
        numeric_issues[column] = int((nonempty & numeric.isna()).sum())
    return output, checks, numeric_issues


def format_number(value):
    return "N/A" if pd.isna(value) else f"{value:,.2f}"


def build_report(source, output, checks, numeric_issues, encoding, before, after):
    """Report engineering checks and descriptive statistics, without conclusions."""
    sales = int(output["IS_SALE_TRANSACTION"].sum())
    valid = int(output["VALID_SALE_PRICE_METRIC"].sum())
    lines = [
        "Dubai Real Estate Intelligence Platform",
        "Stage 6 - Analytics Feature Engineering",
        "=" * 72,
        f"Input file: {SOURCE_PATH}", f"Output file: {OUTPUT_PATH}",
        f"Input encoding: {encoding}", "Output encoding: UTF-8",
        f"Input rows: {len(source):,}", f"Output rows: {len(output):,}",
        f"Input columns: {len(source.columns):,}", f"Output columns: {len(output.columns):,}",
        "", "Complete list of Stage 6 features:", *[f"  - {column}" for column in FEATURE_COLUMNS],
        "", f"Total Sales records: {sales:,}", f"Total non-Sales records: {len(output) - sales:,}",
        f"Valid sale-price-metric records: {valid:,}",
        f"Records without a sale price metric (including non-Sales): {len(output) - valid:,}",
        f"Sales records where sale price metrics could not be calculated: {sales - valid:,}",
        "Non-Sales records are intentionally ineligible, regardless of their transaction value or area.",
        "", "Price-per-area statistics (validation/reporting only; no outliers removed or capped):",
    ]
    for column in ("SALE_PRICE_PER_SQM", "SALE_PRICE_PER_SQFT"):
        series = output[column]
        lines.extend([
            f"  {column}", f"    Minimum: {format_number(series.min())}",
            f"    Median: {format_number(series.median())}",
            f"    Mean: {format_number(series.mean())}", f"    Maximum: {format_number(series.max())}",
        ])
    lines.append("Statistics exclude missing metrics; report numbers are rounded to two decimal places only for display.")
    for column, definitions in (("TRANSACTION_VALUE_BAND", VALUE_BANDS), ("PROPERTY_SIZE_BAND", SIZE_BANDS)):
        lines.extend(["", f"Counts for {column}:"])
        lines.extend(f"  {label}: {output[column].eq(label).sum():,}" for _, _, label in definitions)
        lines.append(f"  Missing: {output[column].isna().sum():,}")
    lines.extend(["", "Counts for BEDROOM_COUNT:"])
    lines.extend(f"  {number}: {output['BEDROOM_COUNT'].eq(number).sum():,}" for number in range(8))
    lines.extend([
        f"  Missing / unmapped: {output['BEDROOM_COUNT'].isna().sum():,}",
        "Unrecognized room categories remain unchanged in ROOMS_EN and receive no guessed bedroom count.",
        "", "Residential vs non-residential:",
        f"  Residential: {output['IS_RESIDENTIAL_FLAG'].eq(1).sum():,}",
        f"  Non-residential / other: {output['IS_RESIDENTIAL_FLAG'].eq(0).sum():,}",
        "", "Off-plan vs ready:",
        f"  Off-Plan: {output['IS_OFFPLAN_FLAG'].eq(1).sum():,}",
        f"  Ready: {output['IS_OFFPLAN_FLAG'].eq(0).sum():,}",
        f"  Missing / unexpected category: {output['IS_OFFPLAN_FLAG'].isna().sum():,}",
        "", "Freehold vs non-freehold:",
        f"  Free Hold: {output['IS_FREEHOLD_FLAG'].eq(1).sum():,}",
        f"  Non Free Hold: {output['IS_FREEHOLD_FLAG'].eq(0).sum():,}",
        f"  Missing / unexpected category: {output['IS_FREEHOLD_FLAG'].isna().sum():,}",
        "", "Numeric interpretation issues in temporary calculation Series:",
        *[f"  {column}: {count:,}" for column, count in numeric_issues.items()],
        "The original numeric fields were not converted or overwritten in the exported source columns.",
        "", f"Square metres to square feet conversion factor: {SQFT_PER_SQM}",
        "Value bands use inclusive lower and exclusive upper boundaries, for all transaction groups.",
        "Size bands require positive ACTUAL_AREA. Bedrooms use only Studio and 1-7 B/R mappings.",
        "Sales status uses GROUP_EN only, never PROCEDURE_EN.",
        "Existing empty CSV fields, literal text such as NA, names, and date columns are preserved.",
        "", f"Source SHA-256 before processing: {before}", f"Source SHA-256 after processing: {after}",
        f"Source unchanged: {'YES - hashes match' if before == after else 'NO'}",
        "", "Validation results:",
        *[f"  {'PASS' if passed else 'FAIL'}: {label}" for label, passed in checks.items()],
        "", "All source rows, values, and repeated transaction numbers were retained.",
        "No existing missing DLD fields were filled. No rankings, predictions, or market conclusions were produced.",
        "Only the eleven requested Stage 6 features were added. The pandas index was not exported.",
    ])
    return "\n".join(lines) + "\n"


def save_outputs(source, output, checks, numeric_issues, encoding, before):
    """Stage complete UTF-8 files and verify the source before final publication."""
    validate_paths()
    if file_hash(SOURCE_PATH) != before:
        raise ValueError("The Stage 5 source changed during feature engineering. No outputs were saved.")
    temporary_paths = []
    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", suffix=".tmp", dir=OUTPUT_PATH.parent, delete=False,
        ) as destination:
            temporary_paths.append(Path(destination.name))
            output.to_csv(destination, index=False, na_rep="")
        after = file_hash(SOURCE_PATH)
        checks["Stage 5 source SHA-256 is unchanged"] = before == after
        if before != after:
            raise ValueError("The Stage 5 source changed during serialization. No outputs were published.")
        report = build_report(source, output, checks, numeric_issues, encoding, before, after)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp", dir=REPORT_PATH.parent, delete=False,
        ) as destination:
            temporary_paths.append(Path(destination.name))
            destination.write(report)
        validate_paths()
        if file_hash(SOURCE_PATH) != before:
            raise ValueError("The Stage 5 source changed before publication. No outputs were published.")
        temporary_paths[0].replace(OUTPUT_PATH)
        temporary_paths[1].replace(REPORT_PATH)
    finally:
        # This cleanup is limited to temporary output files created in this run.
        for path in temporary_paths:
            path.unlink(missing_ok=True)


def main():
    """Explain common problems clearly instead of showing a long traceback."""
    if not SOURCE_PATH.is_file():
        print("The Stage 5 cleaned YTD CSV was not found. Complete Stage 5 first.")
        print(f"Expected file: {SOURCE_PATH}")
        return 1
    try:
        validate_paths()
        source, before, encoding = load_source()
        output, checks, numeric_issues = engineer_features(source)
        save_outputs(source, output, checks, numeric_issues, encoding, before)
    except UnicodeError:
        print("The input cannot be decoded as UTF-8 or Windows-1252. Check the Stage 5 encoding.")
        return 1
    except pd.errors.EmptyDataError:
        print("The Stage 5 CSV is empty or has no readable header. Check the source file.")
        return 1
    except pd.errors.ParserError as error:
        print(f"The CSV could not be parsed: {error}")
        print("Check separators and quotation marks. No malformed rows were skipped.")
        return 1
    except OSError as error:
        print(f"A file could not be read or saved: {error}")
        print("Check file paths, folder permissions, and available disk space.")
        return 1
    except (ValueError, TypeError) as error:
        print(f"Stage 6 could not be completed: {error}")
        return 1

    print("\nSTAGE 6 FEATURE ENGINEERING SUMMARY\n" + "=" * 72)
    print(f"Input rows: {len(source):,}\nOutput rows: {len(output):,}")
    print(f"Columns before and after: {len(source.columns):,} -> {len(output.columns):,}")
    print(f"Sales records: {output['IS_SALE_TRANSACTION'].sum():,}")
    print(f"Valid sale price metric records: {output['VALID_SALE_PRICE_METRIC'].sum():,}")
    print(f"Median sale price per sqm: {format_number(output['SALE_PRICE_PER_SQM'].median())}")
    print(f"Median sale price per sqft: {format_number(output['SALE_PRICE_PER_SQFT'].median())}")
    print("Source unchanged: YES (SHA-256 verified).\nValidation status: PASS.")
    print(f"Features CSV: {OUTPUT_PATH}\nFeature report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
