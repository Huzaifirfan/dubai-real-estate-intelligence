"""Stage 1: inspect the raw DLD sample without changing or saving its data."""

from pathlib import Path


# Resolve the project folder from this script, not the terminal's current folder.
# This lets you run the script from any location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "dld_transactions_sample_2026_01.csv"


def load_csv_with_fallback(file_path, pd):
    """Try UTF-8 first, then Windows-1252 for older Windows CSV exports."""
    try:
        # Keep pandas' normal type and missing-value detection. Read every row;
        # do not skip malformed lines or change anything in the source file.
        return pd.read_csv(file_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        print("UTF-8 decoding failed. Trying Windows-1252 (cp1252).")
        data = pd.read_csv(file_path, encoding="cp1252", low_memory=False)
        # A successful fallback does not prove that the text decoded correctly.
        # This matters especially for Arabic text in Dubai data.
        print(
            "Encoding note: Windows-1252 was used as a fallback. Check the preview "
            "against the official source, especially any Arabic text. "
            "Successful decoding does not confirm the original encoding."
        )
        return data


def main():
    """Load the sample read-only and print the requested raw-data checks."""
    # Check for the file before importing pandas, so beginners get a useful
    # placement message even if they have not installed dependencies yet.
    if not RAW_DATA_PATH.is_file():
        print("The official DLD sample CSV was not found.")
        print("Place your official Dubai Land Department sample in data/raw/.")
        print("Name the file exactly: dld_transactions_sample_2026_01.csv")
        print(f"Expected full path: {RAW_DATA_PATH}")
        print("Then run: python src/01_validate_raw_data.py")
        print("No data was downloaded, generated, or modified.")
        return 1

    try:
        import pandas as pd
    except ImportError:
        print("pandas is required to read the CSV.")
        print("From the project folder, install dependencies with:")
        print("python -m pip install -r requirements.txt")
        return 1

    try:
        file_size_bytes = RAW_DATA_PATH.stat().st_size
        data = load_csv_with_fallback(RAW_DATA_PATH, pd)
    except UnicodeError:
        print("The CSV could not be decoded using UTF-8 or Windows-1252.")
        print("Check the file's encoding with its official source or obtain a UTF-8 export.")
        print("The original file has not been changed.")
        return 1
    except pd.errors.EmptyDataError:
        print("The CSV is empty or has no readable columns. Check your official sample.")
        return 1
    except pd.errors.ParserError as error:
        print("The CSV could not be parsed. Check its delimiter and quotation marks.")
        print(f"Details: {error}")
        print("No rows were skipped and the original file has not been changed.")
        return 1
    except OSError as error:
        # Includes file access problems, such as missing read permissions.
        print(f"The CSV could not be opened: {error}")
        print("Check that the file exists and that you have permission to read it.")
        return 1

    # These checks describe the loaded data. They do not clean it, remove
    # duplicates, fill missing values, or write an output dataset.
    row_count, column_count = data.shape
    print("\nRaw-data validation (read-only)")
    print(f"File name: {RAW_DATA_PATH.name}")
    print(f"File size: {file_size_bytes:,} bytes ({file_size_bytes / 1024:.2f} KiB)")
    print(f"Number of rows: {row_count:,}")
    print(f"Number of columns: {column_count:,}")

    # Print names individually so long column lists are never truncated.
    print("\nComplete column names:")
    for number, column in enumerate(data.columns, start=1):
        print(f"{number}. {column}")

    print("\nFirst 5 rows:")
    print(data.head(5).to_string(index=False, max_colwidth=None))

    print("\npandas data types (inferred while loading):")
    print(data.dtypes.to_string())

    # duplicated() counts repeated full rows after their first occurrence.
    print(f"\nNumber of duplicate rows: {int(data.duplicated().sum()):,}")

    # isna() uses pandas' missing-value recognition, including empty fields
    # and standard markers such as NA. It does not alter the source data.
    missing_counts = data.isna().sum()
    print("\nMissing values for each column:")
    print(missing_counts.to_string())

    print("\nMissing-value percentage for each column:")
    if row_count == 0:
        # A header-only CSV has no rows, so a percentage is undefined.
        for column in data.columns:
            print(f"{column}: N/A (no data rows)")
    else:
        missing_percentages = missing_counts / row_count * 100
        print(missing_percentages.to_string(float_format=lambda value: f"{value:.2f}%"))

    print("\nValidation finished. The original CSV was not modified.")
    return 0


# Run main only when this file is executed directly, rather than imported.
if __name__ == "__main__":
    raise SystemExit(main())
