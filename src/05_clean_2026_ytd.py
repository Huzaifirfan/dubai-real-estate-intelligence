"""Stage 5: clean a separate copy of the Stage 4 YTD dataset.

Run from the project folder: python src/05_clean_2026_ytd.py
Only the cleaned CSV and Stage 5 report are written. No business metrics are
calculated, and the Stage 4 input and original monthly CSVs stay unchanged.
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


# Resolve paths from this file so the script also works from another folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = PROJECT_ROOT / "data/processed/dld_transactions_2026_ytd.csv"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/dld_transactions_2026_ytd_clean.csv"
REPORT_PATH = PROJECT_ROOT / "reports/stage5_ytd_cleaning_report.txt"
MONTHLY_SOURCE_PATHS = [
    PROJECT_ROOT / (
        "data/raw/dld_transactions_sample_2026_01.csv" if month == 1
        else f"data/external/2026_monthly/dld_transactions_2026_{month:02d}.csv"
    )
    for month in range(1, 10)
]

ORIGINAL_COLUMNS = [
    "TRANSACTION_NUMBER", "INSTANCE_DATE", "GROUP_EN", "PROCEDURE_EN",
    "IS_OFFPLAN_EN", "IS_FREE_HOLD_EN", "USAGE_EN", "AREA_EN", "PROP_TYPE_EN",
    "PROP_SB_TYPE_EN", "TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA", "ROOMS_EN",
    "PARKING", "NEAREST_METRO_EN", "NEAREST_MALL_EN", "NEAREST_LANDMARK_EN",
    "TOTAL_BUYER", "TOTAL_SELLER", "MASTER_PROJECT_EN", "PROJECT_EN",
]
NUMERIC_COLUMNS = [
    "TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA", "TOTAL_BUYER", "TOTAL_SELLER",
]
DERIVED_COLUMNS = [
    "TRANSACTION_DATE", "TRANSACTION_YEAR", "TRANSACTION_MONTH",
    "TRANSACTION_MONTH_NAME", "TRANSACTION_QUARTER", "TRANSACTION_DAY",
    "TRANSACTION_DAY_NAME", "TRANSACTION_HOUR",
]


def file_hash(path):
    """Fingerprint file bytes without opening the file for writing."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_output_paths():
    """Never allow an output to point to the Stage 4 or monthly source files."""
    protected = [SOURCE_PATH, *MONTHLY_SOURCE_PATHS]
    pairs = [(output, source) for output in (OUTPUT_PATH, REPORT_PATH) for source in protected]
    pairs.append((OUTPUT_PATH, REPORT_PATH))
    for first, second in pairs:
        same_file = first.resolve() == second.resolve()
        if first.exists() and second.exists():
            same_file = same_file or first.samefile(second)
        if same_file:
            raise ValueError(f"Source and output paths must be separate files: {first} and {second}")


def load_source():
    """Load a fingerprinted source snapshot as text before making any changes."""
    content = SOURCE_PATH.read_bytes()
    source_hash = hashlib.sha256(content).hexdigest()
    options = dict(dtype="string", keep_default_na=False, na_filter=False,
                   skip_blank_lines=False, low_memory=False)
    try:
        source = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", **options)
        encoding = "UTF-8"
    except UnicodeDecodeError:
        print("UTF-8 decoding failed. Trying Windows-1252 (cp1252).")
        source = pd.read_csv(io.BytesIO(content), encoding="cp1252", **options)
        encoding = "Windows-1252 fallback; original encoding not confirmed"
        print("Check official names, especially Arabic text, against the source when fallback encoding is used.")
    # Loading as strings preserves IDs, numeric text, and blanks until the
    # explicit cleaning rules below. No malformed lines are silently skipped.
    if not isinstance(source.index, pd.RangeIndex):
        raise ValueError("CSV rows contain extra fields that pandas interpreted as an index. Check the source header.")
    return source, source_hash, encoding


def strip_text(value):
    """Trim strings and mark empty strings missing without changing other values."""
    if isinstance(value, str):
        value = value.strip()
        return value if value else pd.NA
    return value


def known_ids(series):
    """Exclude already-missing/empty identifiers only when reporting counts."""
    return series[series.notna() & series.ne("")]


def clean_data(source):
    """Apply the authorized rules and validate the result entirely in memory."""
    missing = [column for column in ORIGINAL_COLUMNS if column not in source.columns]
    unexpected = [column for column in source.columns if column not in ORIGINAL_COLUMNS]
    if missing or unexpected or not source.columns.is_unique:
        raise ValueError(
            "Expected the Stage 4 CSV with only the 22 original DLD columns.\n"
            f"Missing columns: {', '.join(missing) or 'None'}\n"
            f"Unexpected columns: {', '.join(unexpected) or 'None'}\n"
            "No columns were renamed or repaired."
        )

    # Identify duplicates BEFORE trimming or coercing values. This prevents
    # invalid values becoming missing from making distinct source rows appear
    # identical. Only exact copies across all 22 original fields may be removed.
    duplicate_mask = source.duplicated(subset=ORIGINAL_COLUMNS, keep="first")
    cleaned = source.loc[~duplicate_mask].copy()
    retained_indices = cleaned.index.copy()
    original_ids = cleaned["TRANSACTION_NUMBER"].copy()
    duplicates_removed = int(duplicate_mask.sum())

    # This does not title-case names, change spelling, or fill missing values.
    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[column] = cleaned[column].map(strip_text)
    expected_ids = original_ids.map(strip_text)

    # Missing values before parsing and failed conversions are separate counts.
    # Failed dates become NaT in this copy, but their records are not deleted.
    date_values = cleaned["INSTANCE_DATE"].copy()
    missing_dates_before = int(date_values.isna().sum())
    cleaned["INSTANCE_DATE"] = pd.to_datetime(date_values, format="ISO8601", errors="coerce")
    dates = cleaned["INSTANCE_DATE"]
    date_failures = int((date_values.notna() & dates.isna()).sum())

    numeric_issues = {}
    for column in NUMERIC_COLUMNS:
        before = cleaned[column]
        converted = pd.to_numeric(before, errors="coerce")
        numeric_issues[column] = int((before.notna() & converted.isna()).sum())
        cleaned[column] = converted

    # Calendar attributes are the only new fields. Nullable integers preserve
    # missing dates and avoid writing a year such as 2026.0 into the CSV.
    cleaned["TRANSACTION_DATE"] = dates.dt.strftime("%Y-%m-%d")
    cleaned["TRANSACTION_YEAR"] = dates.dt.year.astype("Int64")
    cleaned["TRANSACTION_MONTH"] = dates.dt.month.astype("Int64")
    cleaned["TRANSACTION_MONTH_NAME"] = dates.dt.month_name()
    cleaned["TRANSACTION_QUARTER"] = "Q" + dates.dt.quarter.astype("Int64").astype("string")
    cleaned["TRANSACTION_DAY"] = dates.dt.day.astype("Int64")
    cleaned["TRANSACTION_DAY_NAME"] = dates.dt.day_name()
    cleaned["TRANSACTION_HOUR"] = dates.dt.hour.astype("Int64")

    # Stable sorting preserves source order when timestamps are equal. Missing
    # or unparseable dates remain in the dataset, placed after valid dates.
    cleaned = cleaned.sort_values("INSTANCE_DATE", kind="stable", na_position="last")
    remaining_duplicates = int(cleaned.duplicated(subset=ORIGINAL_COLUMNS).sum())
    aligned_ids = cleaned["TRANSACTION_NUMBER"].reindex(retained_indices)
    originally_present_ids = original_ids.notna() & original_ids.ne("")
    new_missing_ids = int((originally_present_ids & aligned_ids.isna()).sum())

    # Row indices still refer to the source here. Checking them verifies that
    # no record was discarded merely for a repeated ID or a conversion problem.
    checks = {
        "Cleaned rows do not exceed source rows": len(cleaned) <= len(source),
        "Only exact source duplicates were removed": len(cleaned) == len(source) - duplicates_removed,
        "Every nonduplicate source record is retained": cleaned.index.is_unique
        and cleaned.index.sort_values().equals(retained_indices.sort_values()),
        "All original 22 columns and their names/order are unchanged":
        list(cleaned.columns[:len(source.columns)]) == list(source.columns)
        and set(ORIGINAL_COLUMNS).issubset(cleaned.columns),
        "All eight derived date columns exist": set(DERIVED_COLUMNS).issubset(cleaned.columns),
        "No other columns were added": len(cleaned.columns) == len(ORIGINAL_COLUMNS) + len(DERIVED_COLUMNS),
        "No exact duplicates remain across the original 22 columns": remaining_duplicates == 0,
        "No new missing transaction numbers were introduced": new_missing_ids == 0,
        "Repeated transaction numbers are retained except in exact duplicate rows":
        aligned_ids.astype("string").equals(expected_ids.astype("string")),
        "All five numeric columns have numeric pandas types": all(
            pd.api.types.is_numeric_dtype(cleaned[column]) for column in NUMERIC_COLUMNS
        ),
        "Valid dates are sorted ascending": cleaned["INSTANCE_DATE"].dropna().is_monotonic_increasing,
        "Quarter values are Q1, Q2, Q3, Q4 or missing":
        cleaned["TRANSACTION_QUARTER"].dropna().isin(["Q1", "Q2", "Q3", "Q4"]).all(),
    }
    failures = [label for label, passed in checks.items() if not passed]
    if failures:
        message = "Validation failed; no outputs saved:\n- " + "\n- ".join(failures)
        if remaining_duplicates:
            message += (
                "\nTrimming or conversion created identical rows that were originally distinct. "
                "They were not deleted; this script removes only original exact duplicates."
            )
        raise ValueError(message)

    # Reset the index only after validating retained source rows. index=False
    # during export also ensures no pandas index becomes an extra CSV column.
    cleaned = cleaned.reset_index(drop=True)
    metrics = {
        "duplicates_removed": duplicates_removed,
        "missing_dates_before": missing_dates_before,
        "date_failures": date_failures,
        "numeric_issues": numeric_issues,
        "new_missing_ids": new_missing_ids,
        "remaining_duplicates": remaining_duplicates,
        "checks": checks,
    }
    return cleaned, metrics


def date_text(value):
    return str(value) if pd.notna(value) else "N/A (no valid dates)"


def build_report(source, cleaned, metrics, encoding, hash_before, hash_after):
    """Describe changes and checks without calculating any business metrics."""
    ids = known_ids(cleaned["TRANSACTION_NUMBER"])
    lines = [
        "Dubai Real Estate Intelligence Platform",
        "Stage 5 - 2026 YTD Data Cleaning and Deduplication",
        "=" * 72,
        f"Source file: {SOURCE_PATH}", f"Output file: {OUTPUT_PATH}",
        f"Source encoding: {encoding}", "Output encoding: UTF-8",
        "", f"Source row count: {len(source):,}", f"Cleaned row count: {len(cleaned):,}",
        f"Exact duplicate rows removed: {metrics['duplicates_removed']:,}",
        "Duplicates identified across the original 22 source fields before trimming or conversion.",
        f"Source column count: {len(source.columns):,}",
        f"Cleaned column count: {len(cleaned.columns):,}",
        "Derived columns:", *[f"  - {column}" for column in DERIVED_COLUMNS],
        "", f"Earliest INSTANCE_DATE: {date_text(cleaned['INSTANCE_DATE'].min())}",
        f"Latest INSTANCE_DATE: {date_text(cleaned['INSTANCE_DATE'].max())}",
        f"Missing date values before parsing: {metrics['missing_dates_before']:,}",
        f"Date parsing failures: {metrics['date_failures']:,}",
        f"Missing date values after parsing: {cleaned['INSTANCE_DATE'].isna().sum():,}",
        "Missing/conversion counts above and below use retained rows after exact deduplication.",
        "Dates are parsed as ISO dates; failed conversions are retained as missing, not dropped.",
        "", "Numeric conversion issues (non-missing values converted to missing):",
        *[f"  {column}: {count:,}" for column, count in metrics["numeric_issues"].items()],
        "", "Missing values per column after cleaning:",
        *[f"  {column}: {count:,}" for column, count in cleaned.isna().sum().items()],
        "", f"Unique TRANSACTION_NUMBER count: {ids.nunique():,}",
        f"Repeated TRANSACTION_NUMBER occurrences retained: {ids.duplicated().sum():,}",
        f"Source repeated TRANSACTION_NUMBER occurrences: {known_ids(source['TRANSACTION_NUMBER']).duplicated().sum():,}",
        "Repeated counts are additional occurrences after the first, excluding missing identifiers.",
        "Repeated identifiers can represent multiple units, properties, or lines within one transaction.",
        "No record was removed merely because its transaction number appeared more than once.",
        f"New missing TRANSACTION_NUMBER values: {metrics['new_missing_ids']:,}",
        f"Remaining exact duplicate count: {metrics['remaining_duplicates']:,}",
        "", f"Source SHA-256 before processing: {hash_before}",
        f"Source SHA-256 after processing: {hash_after}",
        f"Stage 4 source unchanged: {'YES - hashes match' if hash_before == hash_after else 'NO'}",
        "The raw January and February-September external CSVs were not opened for writing.",
        "", "Validation results before publishing outputs:",
        *[f"  {'PASS' if passed else 'FAIL'}: {label}" for label, passed in metrics["checks"].items()],
        "", "Text was trimmed; empty/whitespace-only strings became missing values.",
        "Official column names, capitalization, and spelling were retained.",
        "Missing project, room, and master-project values were not filled or guessed.",
        "No outliers were removed, transaction values capped, or business metrics created.",
        "Dates sorted ascending; missing dates last; index reset and not exported.",
        "Work remains within Stage 5.",
    ]
    return "\n".join(lines) + "\n"


def save_outputs(source, cleaned, metrics, encoding, hash_before):
    """Stage complete outputs, then verify the input hash before publishing."""
    validate_output_paths()
    temporary_paths = []
    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", suffix=".tmp", dir=OUTPUT_PATH.parent, delete=False,
        ) as destination:
            temporary_paths.append(Path(destination.name))
            cleaned.to_csv(destination, index=False, na_rep="")

        # All cleaning and CSV serialization have finished. Compare the current
        # input bytes against the snapshot pandas originally read.
        hash_after = file_hash(SOURCE_PATH)
        metrics["checks"]["Stage 4 source SHA-256 is unchanged"] = hash_before == hash_after
        if hash_before != hash_after:
            raise ValueError("The Stage 4 source changed during processing. No outputs were published.")
        report = build_report(source, cleaned, metrics, encoding, hash_before, hash_after)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp", dir=REPORT_PATH.parent, delete=False,
        ) as destination:
            temporary_paths.append(Path(destination.name))
            destination.write(report)

        validate_output_paths()
        if file_hash(SOURCE_PATH) != hash_before:
            raise ValueError("The Stage 4 source changed before publication. No outputs were published.")
        # Replace only the two designated output paths, never any source path.
        temporary_paths[0].replace(OUTPUT_PATH)
        temporary_paths[1].replace(REPORT_PATH)
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)


def main():
    """Run Stage 5 and provide clear guidance for common file problems."""
    if not SOURCE_PATH.is_file():
        print("The Stage 4 combined YTD CSV was not found. Complete Stage 4 first.")
        print(f"Expected file: {SOURCE_PATH}")
        return 1
    try:
        validate_output_paths()
        source, hash_before, encoding = load_source()
        cleaned, metrics = clean_data(source)
        save_outputs(source, cleaned, metrics, encoding, hash_before)
    except UnicodeError:
        print("Cannot decode the input as UTF-8 or Windows-1252. Check the Stage 4 CSV encoding.")
        return 1
    except pd.errors.EmptyDataError:
        print("The Stage 4 CSV is empty or has no readable header. Check the input file.")
        return 1
    except pd.errors.ParserError as error:
        print(f"The CSV could not be parsed: {error}")
        print("Check the separator and quotation marks. No malformed rows were skipped.")
        return 1
    except OSError as error:
        print(f"A file could not be read or saved: {error}")
        print("Check the paths, folder permissions, and available disk space.")
        return 1
    except (ValueError, TypeError) as error:
        print(f"Stage 5 could not be completed: {error}")
        return 1

    ids = known_ids(cleaned["TRANSACTION_NUMBER"])
    print("\nSTAGE 5 YTD CLEANING SUMMARY\n" + "=" * 72)
    print(f"Source rows: {len(source):,}\nCleaned rows: {len(cleaned):,}")
    print(f"Exact duplicates removed: {metrics['duplicates_removed']:,}")
    print(f"Columns before and after: {len(source.columns):,} -> {len(cleaned.columns):,}")
    print(f"Date range: {date_text(cleaned['INSTANCE_DATE'].min())} through {date_text(cleaned['INSTANCE_DATE'].max())}")
    print(f"Unique transaction numbers: {ids.nunique():,}")
    print(f"Additional repeated transaction-number occurrences retained: {ids.duplicated().sum():,}")
    print(f"Remaining exact duplicates: {metrics['remaining_duplicates']:,}")
    print(f"Missing dates before parsing: {metrics['missing_dates_before']:,}")
    print(f"Date parsing failures: {metrics['date_failures']:,}")
    print("Numeric conversion issues:")
    for column, count in metrics["numeric_issues"].items():
        print(f"  {column}: {count:,}")
    print("Source unchanged: YES (SHA-256 verified). All validation checks passed.")
    print(f"Cleaned CSV: {OUTPUT_PATH}\nCleaning report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
