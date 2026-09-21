"""Stage 2: print a read-only profile of the raw DLD transaction sample.

Run from the project folder with: python src/02_profile_data.py
This script writes no files and does not clean or remove any records.
"""

from pathlib import Path


# Locate the input relative to this script, even when run from another folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "dld_transactions_sample_2026_01.csv"

EXPECTED_COLUMNS = [
    "TRANSACTION_NUMBER", "INSTANCE_DATE", "GROUP_EN", "PROCEDURE_EN",
    "IS_OFFPLAN_EN", "IS_FREE_HOLD_EN", "USAGE_EN", "AREA_EN", "PROP_TYPE_EN",
    "PROP_SB_TYPE_EN", "TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA", "ROOMS_EN",
    "PARKING", "NEAREST_METRO_EN", "NEAREST_MALL_EN", "NEAREST_LANDMARK_EN",
    "TOTAL_BUYER", "TOTAL_SELLER", "MASTER_PROJECT_EN", "PROJECT_EN",
]
CATEGORICAL_COLUMNS = [
    "GROUP_EN", "PROCEDURE_EN", "IS_OFFPLAN_EN", "IS_FREE_HOLD_EN",
    "USAGE_EN", "PROP_TYPE_EN", "PROP_SB_TYPE_EN", "ROOMS_EN",
]
NUMERIC_COLUMNS = [
    "TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA", "TOTAL_BUYER", "TOTAL_SELLER",
]


def section(title):
    """Make each profiling section easy to find in terminal output."""
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def percentage(count, total):
    """Format percentages; an empty dataset has no meaningful denominator."""
    return f"{count / total * 100:.2f}%" if total else "N/A (no records)"


def load_csv(file_path, pd):
    """Read UTF-8 first, with the same Windows-1252 fallback as Stage 1."""
    try:
        # pandas infers types and recognizes standard missing markers, such as
        # empty fields and NA. No lines are skipped and no source file is edited.
        return pd.read_csv(file_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        print("UTF-8 decoding failed. Trying Windows-1252 (cp1252).")
        data = pd.read_csv(file_path, encoding="cp1252", low_memory=False)
        print(
            "Encoding note: fallback decoding does not confirm the original "
            "encoding. Check text against the source, especially Arabic text."
        )
        return data


def print_frequencies(series, row_count, pd, limit=None, include_missing=True):
    """Print counts without truncation, using all dataset rows for percentages."""
    # Missing values are retained as a category unless a named-item ranking is
    # requested. The display label below does not replace values in the data.
    counts = series.value_counts(dropna=not include_missing)
    if limit is not None:
        counts = counts.head(limit)
    if counts.empty:
        print("No values to report.")
        return

    labels = ["<MISSING>" if pd.isna(value) else str(value) for value in counts.index]
    width = max(5, max(len(label) for label in labels))
    print(f"{'Value':<{width}}  {'Records':>12}  {'% of all records':>18}")
    for label, count in zip(labels, counts):
        print(f"{label:<{width}}  {count:>12,}  {percentage(count, row_count):>18}")


def numeric_profile(series, pd):
    """Calculate statistics on the inferred numeric data without converting it."""
    count = int(series.count())
    result = {"count": count, "missing": int(series.isna().sum())}
    # Empty or all-missing columns still have meaningful counts. Their other
    # statistics are undefined, and are printed as N/A rather than zero.
    supported = count == 0 or (
        pd.api.types.is_numeric_dtype(series.dtype)
        and not pd.api.types.is_bool_dtype(series.dtype)
    )
    result["supported"] = supported
    for statistic in ("mean", "median", "min", "max", "std", "zero", "negative"):
        result[statistic] = None
    if not supported:
        return result
    if count:
        result.update(
            mean=series.mean(), median=series.median(), min=series.min(),
            max=series.max(), std=series.std(ddof=1),
        )
    result["zero"] = int(series.eq(0).sum())
    result["negative"] = int(series.lt(0).sum()) if count else 0
    return result


def format_stat(value, pd):
    """Use comma separators and two decimal places for numeric statistics."""
    return "N/A" if value is None or pd.isna(value) else f"{value:,.2f}"


def print_quality_checks(column, profile):
    """Report potential quality issues without correcting any values."""
    print(f"\n{column}")
    for label, key in (("Zero values", "zero"), ("Negative values", "negative")):
        value = profile[key]
        display = f"{value:,}" if value is not None else "N/A (non-numeric data)"
        print(f"  {label}: {display}")
    print(f"  Missing values: {profile['missing']:,}")


def profile_data(data, pd):
    """Print all requested sections; only the in-memory date column is parsed."""
    row_count, column_count = data.shape

    # Capture these checks BEFORE date parsing, so parsing cannot merge distinct
    # source date strings when counting unique values or exact duplicate rows.
    cardinality = data.nunique(dropna=True)
    exact_duplicates = int(data.duplicated().sum())
    transaction_ids = data["TRANSACTION_NUMBER"]
    # Only known transaction numbers participate in the repeated-ID count.
    # This mask is used for counting, not for removing rows from the DataFrame.
    repeated_ids = int((transaction_ids.notna() & transaction_ids.duplicated()).sum())
    unique_ids = int(transaction_ids.nunique(dropna=True))
    missing_ids = int(transaction_ids.isna().sum())
    missing_dates = int(data["INSTANCE_DATE"].isna().sum())

    section("1. DATASET DIMENSIONS")
    print(f"Records: {row_count:,}\nColumns: {column_count:,}")
    if row_count == 0:
        print("The CSV contains headers but no records. Undefined results show N/A.")

    section("2. DATE PROFILING — INSTANCE_DATE")
    # The source uses ISO dates (YYYY-MM-DD with optional time). Only this
    # in-memory column is converted. Unparseable entries become NaT here and
    # are counted explicitly; they are never written back to the CSV.
    data["INSTANCE_DATE"] = pd.to_datetime(
        data["INSTANCE_DATE"], format="ISO8601", errors="coerce"
    )
    dates = data["INSTANCE_DATE"]
    invalid_dates = int(dates.isna().sum()) - missing_dates
    earliest, latest = dates.min(), dates.max()
    date_count = int(dates.dt.normalize().nunique(dropna=True))
    print(f"Earliest INSTANCE_DATE: {earliest if pd.notna(earliest) else 'N/A'}")
    print(f"Latest INSTANCE_DATE: {latest if pd.notna(latest) else 'N/A'}")
    print(f"Unique calendar dates: {date_count:,}")
    print(f"Missing dates in the loaded CSV: {missing_dates:,}")
    print(f"Non-missing dates that could not be parsed as ISO dates: {invalid_dates:,}")
    print("Date range and calendar-date count use successfully parsed dates only.")

    section("3. CARDINALITY — EVERY COLUMN")
    print("Distinct non-missing values as loaded, before in-memory date parsing.")
    for column, count in cardinality.items():
        print(f"{column:<24} {count:>12,}")

    section("4. CATEGORICAL FREQUENCIES")
    print("Percentages use all records. <MISSING> is a display label only.")
    for column in CATEGORICAL_COLUMNS:
        print(f"\n{column}")
        print_frequencies(data[column], row_count, pd)

    section("5. AREA_EN — AREA PROFILING")
    unique_areas = int(cardinality["AREA_EN"])
    print(f"Unique non-missing areas: {unique_areas:,}")
    print("Top 20 named areas by number of records:")
    print_frequencies(data["AREA_EN"], row_count, pd, limit=20, include_missing=False)

    section("6. PROJECT_EN — PROJECT PROFILING")
    unique_projects = int(cardinality["PROJECT_EN"])
    missing_projects = int(data["PROJECT_EN"].isna().sum())
    print(f"Unique non-missing projects: {unique_projects:,}")
    print(f"Missing project names: {missing_projects:,} ({percentage(missing_projects, row_count)})")
    print("Top 20 named projects by number of records:")
    print_frequencies(data["PROJECT_EN"], row_count, pd, limit=20, include_missing=False)

    section("7. NUMERIC PROFILING")
    print("Count excludes missing values; other statistics use available numbers.")
    print("Standard deviation is the sample standard deviation (ddof=1).")
    print("Values are reported in the source units; no units are converted.")
    numeric_profiles = {}
    for column in NUMERIC_COLUMNS:
        profile = numeric_profile(data[column], pd)
        numeric_profiles[column] = profile
        print(f"\n{column}\n  Count: {profile['count']:,}")
        if not profile["supported"]:
            print("  This column contains non-numeric data; numeric statistics are unavailable.")
            print("  No values were converted, replaced, or removed.")
        for label, key in (
            ("Mean", "mean"), ("Median", "median"), ("Minimum", "min"),
            ("Maximum", "max"), ("Standard deviation", "std"),
        ):
            print(f"  {label}: {format_stat(profile[key], pd)}")

    section("8. TRANS_VALUE QUALITY CHECKS")
    print_quality_checks("TRANS_VALUE", numeric_profiles["TRANS_VALUE"])

    section("9. PROCEDURE_AREA AND ACTUAL_AREA QUALITY CHECKS")
    for column in ("PROCEDURE_AREA", "ACTUAL_AREA"):
        print_quality_checks(column, numeric_profiles[column])

    section("10. DUPLICATE ANALYSIS")
    print("Duplicate counts are additional occurrences after the first occurrence.")
    print(f"Exact duplicate rows across all loaded columns: {exact_duplicates:,}")
    print(f"Duplicate TRANSACTION_NUMBER count (non-missing): {repeated_ids:,}")
    print(f"Unique TRANSACTION_NUMBER count (non-missing): {unique_ids:,}")
    print(f"Missing TRANSACTION_NUMBER count: {missing_ids:,}")
    print("A transaction number may legitimately appear more than once.")
    print("Repeated transaction numbers are not automatically classified as bad data.")

    section("11. DATA PROFILING SUMMARY")
    print(f"- Dataset: {row_count:,} records and {column_count:,} columns.")
    if pd.notna(earliest):
        print(f"- Dates: {earliest} to {latest}; {date_count:,} unique calendar dates.")
    else:
        print("- Dates: no valid ISO dates available for a date range.")
    print(f"- Date completeness: {missing_dates:,} missing; {invalid_dates:,} unparseable.")
    print(f"- Coverage: {unique_areas:,} named areas and {unique_projects:,} named projects.")
    print(f"- Missing project names: {missing_projects:,} ({percentage(missing_projects, row_count)}).")
    print(f"- Exact duplicate rows: {exact_duplicates:,}; repeated transaction numbers: {repeated_ids:,}.")
    print(f"- Unique transaction numbers: {unique_ids:,}; missing transaction numbers: {missing_ids:,}.")
    print("  Repeated transaction numbers can be legitimate; no duplicates were removed.")
    for column in ("TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA"):
        profile = numeric_profiles[column]
        if profile["supported"]:
            print(
                f"- {column}: {profile['zero']:,} zero, {profile['negative']:,} negative, "
                f"{profile['missing']:,} missing values."
            )
        else:
            print(f"- {column}: numeric checks unavailable; {profile['missing']:,} missing values.")
    for column in NUMERIC_COLUMNS:
        if not numeric_profiles[column]["supported"]:
            print(f"- Numeric statistics unavailable for {column}: non-numeric data detected.")
    # Report constant-zero participant counts as observations, without guessing
    # why the source contains them or treating them as missing values.
    for column in ("TOTAL_BUYER", "TOTAL_SELLER"):
        profile = numeric_profiles[column]
        if profile["supported"] and profile["count"] and profile["zero"] == profile["count"]:
            print(f"- {column}: all {profile['count']:,} non-missing values are zero.")
    print("\nStage 2 complete. The raw CSV was not modified; no processed data was saved.")


def main():
    """Check the input and explain common problems without a long traceback."""
    if not RAW_DATA_PATH.is_file():
        print("The raw sample CSV was not found.")
        print("Place the official DLD sample in data/raw/ with this exact filename:")
        print("dld_transactions_sample_2026_01.csv")
        print(f"Expected full path: {RAW_DATA_PATH}")
        print("Then run: python src/02_profile_data.py")
        return 1

    try:
        import pandas as pd
    except ImportError:
        print("pandas is required. Activate your project environment, then run:")
        print("python -m pip install -r requirements.txt")
        return 1

    try:
        data = load_csv(RAW_DATA_PATH, pd)
    except UnicodeError:
        print("The CSV could not be decoded as UTF-8 or Windows-1252.")
        print("Check the source encoding or obtain a UTF-8 export from the official source.")
        return 1
    except pd.errors.EmptyDataError:
        print("The CSV is empty or has no readable header. Check the input file.")
        return 1
    except pd.errors.ParserError as error:
        print("The CSV could not be parsed. Check the delimiter and quotation marks.")
        print(f"Details: {error}\nNo malformed rows were skipped.")
        return 1
    except OSError as error:
        print(f"The CSV could not be opened: {error}")
        print("Check that the file exists and that you have permission to read it.")
        return 1

    missing_columns = [column for column in EXPECTED_COLUMNS if column not in data.columns]
    if missing_columns:
        print("The CSV is missing columns required for Stage 2:")
        for column in missing_columns:
            print(f"  - {column}")
        print("Check that you selected the expected sample with a comma-separated header.")
        print("The script has not renamed columns or changed the source file.")
        return 1

    print("Dubai Real Estate Intelligence Platform — Stage 2: Data Understanding and Profiling")
    print(f"Input: {RAW_DATA_PATH}")
    profile_data(data, pd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
