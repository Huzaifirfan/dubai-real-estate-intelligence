"""Stage 3: clean a separate copy of the DLD sample and write a cleaning report.

Run with: python src/03_clean_transform_data.py
The raw CSV is read only. All changes happen in memory and in separate outputs.
"""

import hashlib
from pathlib import Path
import tempfile

try:
    import pandas as pd
except ImportError:
    raise SystemExit(
        "pandas is required. Activate your project environment, then run:\n"
        "python -m pip install -r requirements.txt"
    )


# Paths are based on this script, so running from another folder also works.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data/raw/dld_transactions_sample_2026_01.csv"
OUTPUT_PATH = PROJECT_ROOT / "data/processed/dld_transactions_clean_2026_01.csv"
REPORT_PATH = PROJECT_ROOT / "reports/stage3_cleaning_report.txt"

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
    "TRANSACTION_MONTH_NAME", "TRANSACTION_DAY", "TRANSACTION_DAY_NAME",
    "TRANSACTION_HOUR",
]


def file_hash(path):
    """Fingerprint file contents to verify that the raw CSV stays unchanged."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_output_paths():
    """Protect the raw file even if an output path is accidentally changed."""
    paths = [RAW_PATH, OUTPUT_PATH, REPORT_PATH]
    for position, first in enumerate(paths):
        for second in paths[position + 1:]:
            same_path = first.resolve() == second.resolve()
            # samefile also detects different names pointing to one hard-linked file.
            same_file = first.exists() and second.exists() and first.samefile(second)
            if same_path or same_file:
                raise ValueError("Raw data, cleaned data, and report paths must be separate files.")


def load_raw_data():
    """Try UTF-8 first, then Windows-1252 for older Windows CSV exports."""
    try:
        # Keep the same pandas loading conventions as Stages 1 and 2, including
        # standard missing markers. Malformed lines are never silently skipped.
        return pd.read_csv(RAW_PATH, encoding="utf-8", low_memory=False), "utf-8"
    except UnicodeDecodeError:
        print("UTF-8 decoding failed. Trying Windows-1252 (cp1252).")
        data = pd.read_csv(RAW_PATH, encoding="cp1252", low_memory=False)
        print("Fallback encoding used. Check official names, especially Arabic text, against the source.")
        return data, "cp1252 (fallback; original encoding not confirmed)"


def strip_text(value):
    """Trim strings and mark blank strings missing, preserving non-string values."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else pd.NA
    return value


def repeated_id_count(series):
    """Count additional occurrences after the first, excluding missing IDs."""
    return int((series.notna() & series.duplicated()).sum())


def clean_data(raw):
    """Apply only the authorized rules and validate before any output is saved."""
    missing_columns = [column for column in ORIGINAL_COLUMNS if column not in raw.columns]
    if missing_columns:
        raise ValueError("Required original columns are missing: " + ", ".join(missing_columns))
    if any(column in raw.columns for column in DERIVED_COLUMNS):
        raise ValueError("The input already has derived date columns. Use the original raw CSV.")

    # This is the ONLY row-removal operation. It compares every original column
    # BEFORE whitespace trimming or conversion, and keeps the first occurrence.
    duplicate_mask = raw.duplicated(keep="first")
    cleaned = raw.loc[~duplicate_mask].copy()
    retained_indices = cleaned.index.copy()
    ids_before_cleaning = cleaned["TRANSACTION_NUMBER"].copy()
    duplicates_removed = int(duplicate_mask.sum())

    # Preserve capitalization and spelling. Only surrounding whitespace and
    # completely blank strings change; existing missing values are not filled.
    text_columns = cleaned.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        cleaned[column] = cleaned[column].map(strip_text)
    expected_ids = ids_before_cleaning.map(strip_text)

    # Count parsing failures separately from values already missing. Failed
    # dates become NaT in this copy; their rows remain in the output.
    dates_before = cleaned["INSTANCE_DATE"].copy()
    cleaned["INSTANCE_DATE"] = pd.to_datetime(
        dates_before, format="ISO8601", errors="coerce"
    )
    dates = cleaned["INSTANCE_DATE"]
    date_failures = int((dates_before.notna() & dates.isna()).sum())

    # Derived calendar attributes use the parsed timestamp, without changing
    # its timezone. Nullable integers keep missing dates blank rather than
    # creating a guessed year/month/day or writing values like 2026.0.
    cleaned["TRANSACTION_DATE"] = dates.dt.strftime("%Y-%m-%d")
    cleaned["TRANSACTION_YEAR"] = dates.dt.year.astype("Int64")
    cleaned["TRANSACTION_MONTH"] = dates.dt.month.astype("Int64")
    cleaned["TRANSACTION_MONTH_NAME"] = dates.dt.month_name()
    cleaned["TRANSACTION_DAY"] = dates.dt.day.astype("Int64")
    cleaned["TRANSACTION_DAY_NAME"] = dates.dt.day_name()
    cleaned["TRANSACTION_HOUR"] = dates.dt.hour.astype("Int64")

    # Invalid numeric text becomes missing only in the cleaned copy. Count each
    # newly missing value; never fill, cap, or discard numeric observations.
    numeric_issues = {}
    for column in NUMERIC_COLUMNS:
        before = cleaned[column]
        converted = pd.to_numeric(before, errors="coerce")
        numeric_issues[column] = int((before.notna() & converted.isna()).sum())
        cleaned[column] = converted

    # Stable sorting keeps the source order for equal timestamps. Failed or
    # missing dates stay in the dataset and appear at the end.
    cleaned = cleaned.sort_values("INSTANCE_DATE", kind="stable", na_position="last")

    # Validate using source row indices before resetting them. This proves
    # every nonduplicate source record is still present, even for repeated IDs.
    remaining_duplicates = int(cleaned.duplicated(subset=list(raw.columns)).sum())
    aligned_ids = cleaned["TRANSACTION_NUMBER"].reindex(retained_indices)
    newly_missing_ids = int((ids_before_cleaning.notna() & aligned_ids.isna()).sum())
    checks = {
        "Cleaned rows must not exceed raw rows": len(cleaned) <= len(raw),
        "Only exact duplicate source rows may be removed": len(cleaned) == len(raw) - duplicates_removed,
        "All retained source rows must remain": cleaned.index.is_unique
        and cleaned.index.sort_values().equals(retained_indices.sort_values()),
        "No exact duplicates may remain": remaining_duplicates == 0,
        "Transaction numbers must not gain missing values": newly_missing_ids == 0,
        "All original columns must remain in their original order": list(cleaned.columns[:len(raw.columns)])
        == list(raw.columns),
        "All original DLD columns must exist": set(ORIGINAL_COLUMNS).issubset(cleaned.columns),
        "All derived date columns must exist": set(DERIVED_COLUMNS).issubset(cleaned.columns),
        "All transaction numbers must be retained apart from whitespace trimming":
        aligned_ids.astype("string").equals(expected_ids.astype("string")),
        "All required numeric columns must be numeric": all(
            pd.api.types.is_numeric_dtype(cleaned[column]) for column in NUMERIC_COLUMNS
        ),
        "Valid timestamps must be sorted ascending": cleaned["INSTANCE_DATE"].dropna().is_monotonic_increasing,
    }
    failed = [message for message, passed in checks.items() if not passed]
    if failed:
        detail = "\n- ".join(failed)
        if remaining_duplicates:
            detail += (
                "\nTrimming or conversion made previously distinct rows identical. "
                "They were NOT removed: only original exact duplicates may be deleted."
            )
        raise ValueError("Validation failed; outputs were not saved:\n- " + detail)

    # The old pandas row index is not a business field and must not be exported.
    cleaned = cleaned.reset_index(drop=True)
    metrics = {
        "duplicates_removed": duplicates_removed,
        "date_failures": date_failures,
        "numeric_issues": numeric_issues,
        "remaining_duplicates": remaining_duplicates,
        "newly_missing_ids": newly_missing_ids,
        "checks": checks,
    }
    return cleaned, metrics


def build_report(raw, cleaned, metrics, encoding, raw_hash):
    """Build a plain-text audit report using dynamically calculated counts."""
    minimum = cleaned["INSTANCE_DATE"].min()
    maximum = cleaned["INSTANCE_DATE"].max()
    lines = [
        "Dubai Real Estate Intelligence Platform",
        "Stage 3 - Data Cleaning and Safe Transformation",
        "=" * 72,
        f"Raw file name: {RAW_PATH.name}",
        f"Raw path: {RAW_PATH}",
        f"Output file name: {OUTPUT_PATH.name}",
        f"Output path: {OUTPUT_PATH}",
        f"Input encoding: {encoding}",
        "Output encoding: UTF-8",
        f"Raw SHA-256: {raw_hash}",
        "Raw-file protection: separate output paths; raw fingerprint verified before saving.",
        "",
        f"Raw row count: {len(raw):,}",
        f"Cleaned row count: {len(cleaned):,}",
        f"Exact duplicates removed: {metrics['duplicates_removed']:,}",
        "Duplicates compared across all original columns BEFORE transformations.",
        f"Raw column count: {len(raw.columns):,}",
        f"Cleaned column count: {len(cleaned.columns):,}",
        "New derived columns:",
        *[f"  - {column}" for column in DERIVED_COLUMNS],
        "",
        f"Date conversion failures: {metrics['date_failures']:,}",
        "Failures count non-missing values after trimming that could not be parsed.",
        "Dates use ISO format; rows with missing or failed dates remain, sorted last.",
        "Numeric conversion issues (non-missing values converted to missing):",
        *[f"  {column}: {count:,}" for column, count in metrics["numeric_issues"].items()],
        "",
        "Missing-value counts after cleaning:",
        *[f"  {column}: {count:,}" for column, count in cleaned.isna().sum().items()],
        "",
        "Repeated TRANSACTION_NUMBER values retained: YES.",
        "Every source row remains except exact duplicate rows across all original columns.",
        "Repeated transaction numbers may legitimately represent multiple properties or records.",
        "Repeated counts below mean additional occurrences after the first, excluding missing IDs.",
        f"Raw repeated TRANSACTION_NUMBER count: {repeated_id_count(raw['TRANSACTION_NUMBER']):,}",
        f"Cleaned repeated TRANSACTION_NUMBER count: {repeated_id_count(cleaned['TRANSACTION_NUMBER']):,}",
        f"Unique TRANSACTION_NUMBER count: {cleaned['TRANSACTION_NUMBER'].nunique(dropna=True):,}",
        f"Newly missing TRANSACTION_NUMBER values: {metrics['newly_missing_ids']:,}",
        f"Remaining exact duplicate count: {metrics['remaining_duplicates']:,}",
        f"Minimum INSTANCE_DATE: {minimum if pd.notna(minimum) else 'N/A'}",
        f"Maximum INSTANCE_DATE: {maximum if pd.notna(maximum) else 'N/A'}",
        "",
        "Validation checks before saving:",
        *[f"  PASS: {message}" for message in metrics["checks"]],
        "",
        "Original column names, official name capitalization, and spelling were retained.",
        "Missing values were preserved; no property details were invented or filled.",
        "No outliers or high-value records were removed or capped.",
        "TOTAL_BUYER and TOTAL_SELLER were retained, including their zero values.",
        "Index reset; pandas index not saved as a CSV column.",
        "No price-per-square-metre calculation or work beyond Stage 3 was performed.",
    ]
    return "\n".join(lines) + "\n"


def save_outputs(cleaned, report, raw_hash):
    """Prepare complete output files before replacing the final output paths."""
    check_output_paths()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_paths = []
    try:
        # Temporary files live beside their destinations. Replacement avoids
        # leaving a partially written CSV at the final path if writing fails.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", suffix=".tmp",
            dir=OUTPUT_PATH.parent, delete=False,
        ) as output:
            temporary_paths.append(Path(output.name))
            cleaned.to_csv(output, index=False, na_rep="")
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp",
            dir=REPORT_PATH.parent, delete=False,
        ) as output:
            temporary_paths.append(Path(output.name))
            output.write(report)

        # Check the raw file again just before publishing the two outputs.
        if file_hash(RAW_PATH) != raw_hash:
            raise ValueError("The raw file changed during this run. Outputs were not saved; check the input.")
        temporary_paths[0].replace(OUTPUT_PATH)
        temporary_paths[1].replace(REPORT_PATH)
    finally:
        # Remove only temporary files created by this function, never raw data.
        for path in temporary_paths:
            path.unlink(missing_ok=True)


def main():
    """Run the workflow and explain common input or permission problems."""
    if not RAW_PATH.is_file():
        print("The raw sample CSV was not found. Place the official sample at:")
        print(RAW_PATH)
        return 1

    try:
        check_output_paths()
        original_hash = file_hash(RAW_PATH)
        raw, encoding = load_raw_data()
        cleaned, metrics = clean_data(raw)
        report = build_report(raw, cleaned, metrics, encoding, original_hash)
        save_outputs(cleaned, report, original_hash)
        if file_hash(RAW_PATH) != original_hash:
            raise ValueError("The raw-file fingerprint changed. Check whether another program edited the input.")
    except UnicodeError:
        print("The CSV could not be decoded as UTF-8 or Windows-1252.")
        print("Check the official source encoding or obtain a UTF-8 export.")
        return 1
    except pd.errors.EmptyDataError:
        print("The raw CSV is empty or has no readable header. Check the source file.")
        return 1
    except pd.errors.ParserError as error:
        print("The CSV could not be parsed. Check its delimiter and quotation marks.")
        print(f"Details: {error}. No malformed rows were skipped.")
        return 1
    except OSError as error:
        print(f"A file could not be read or saved: {error}")
        print("Check folder permissions and available disk space, then run the script again.")
        return 1
    except (ValueError, TypeError) as error:
        print(f"Stage 3 could not be completed: {error}")
        return 1

    print("\nSTAGE 3 CLEANING SUMMARY")
    print("=" * 72)
    print(f"Rows: {len(raw):,} raw -> {len(cleaned):,} cleaned")
    print(f"Exact duplicate rows removed: {metrics['duplicates_removed']:,}")
    print(f"Columns: {len(raw.columns):,} original -> {len(cleaned.columns):,} cleaned")
    print(f"Date conversion failures: {metrics['date_failures']:,}")
    print("Numeric conversion issues:")
    for column, count in metrics["numeric_issues"].items():
        print(f"  {column}: {count:,}")
    print(f"Repeated transaction-number occurrences retained: {repeated_id_count(cleaned['TRANSACTION_NUMBER']):,}")
    print(f"Unique transaction numbers: {cleaned['TRANSACTION_NUMBER'].nunique(dropna=True):,}")
    print(f"Remaining exact duplicates: {metrics['remaining_duplicates']:,}")
    print("All validation checks passed. Raw CSV unchanged (SHA-256 verified).")
    print(f"Cleaned CSV: {OUTPUT_PATH}")
    print(f"Cleaning report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
