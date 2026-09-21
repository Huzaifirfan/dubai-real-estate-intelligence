"""Stage 4: assemble nine official source CSVs without cleaning their records.

Run: python src/04_build_2026_ytd_dataset.py
Source fields and duplicates are preserved. Parsed dates are separate sort keys,
so the output has only the original 22 columns, including original date text.
"""

import csv
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
YEAR = 2026
MONTHS = range(1, 10)
EXPECTED_COLUMN_COUNT = 22
SOURCES = [
    (month, PROJECT_ROOT / (
        "data/raw/dld_transactions_sample_2026_01.csv" if month == 1
        else f"data/external/2026_monthly/dld_transactions_2026_{month:02d}.csv"
    ))
    for month in MONTHS
]
OUTPUT_PATH = PROJECT_ROOT / "data/processed/dld_transactions_2026_ytd.csv"
REPORT_PATH = PROJECT_ROOT / "reports/stage4_ytd_assembly_report.txt"


def file_hash(path):
    """Read a SHA-256 fingerprint without changing the file."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_paths():
    """Require nine distinct sources and keep both outputs separate from them."""
    if len(SOURCES) != 9 or sorted(month for month, _ in SOURCES) != list(MONTHS):
        raise ValueError("Configure exactly nine sources, one for each month January through September.")
    paths = [path for _, path in SOURCES] + [OUTPUT_PATH, REPORT_PATH]
    for position, first in enumerate(paths):
        for second in paths[position + 1:]:
            aliases = first.resolve() == second.resolve()
            if first.exists() and second.exists():
                aliases = aliases or first.samefile(second)
            if aliases:
                raise ValueError(f"Paths must refer to separate files: {first} and {second}")


def date_text(value):
    return str(value) if pd.notna(value) else "N/A (no valid dates)"


def inspect_source(month, path):
    """Read one unchanged snapshot and collect its schema and month checks."""
    info = {"month": month, "path": path, "errors": [], "warnings": [], "schema_ok": False}
    try:
        # Hash the exact bytes that pandas will read, before parsing anything.
        content = path.read_bytes()
        info["bytes"] = len(content)
        info["hash_before"] = hashlib.sha256(content).hexdigest()
        try:
            text = content.decode("utf-8-sig")  # Also accepts a UTF-8 BOM.
            info["encoding"] = "UTF-8"
        except UnicodeDecodeError:
            text = content.decode("cp1252")
            info["encoding"] = "Windows-1252 fallback"
            info["warnings"].append(
                "Fallback encoding used; check official names, especially Arabic text, against the source."
            )

        # Read the literal header too: pandas normally renames duplicate or
        # blank headers. Stage 4 must detect these instead of silently accepting them.
        columns = next(csv.reader(io.StringIO(text)), [])
        info["columns"] = columns
        frame = pd.read_csv(
            io.StringIO(text), dtype="string", keep_default_na=False,
            na_filter=False, skip_blank_lines=False, low_memory=False,
        )
        if columns != list(frame.columns) or len(set(columns)) != len(columns):
            info["errors"].append("The header contains blank/duplicate names or pandas interpreted it differently.")
        if not isinstance(frame.index, pd.RangeIndex):
            info["errors"].append("Some rows have more fields than the header; an implicit CSV index was detected.")
        info["frame"] = frame
        info["rows"] = len(frame)

        # All fields stay as text, including numeric-looking values and blanks.
        # Only this separate Series is parsed; invalid dates are reported, kept
        # in the source records, and sorted last rather than replaced or deleted.
        if "INSTANCE_DATE" not in frame.columns:
            info["errors"].append("INSTANCE_DATE is missing, so dates cannot be validated.")
            return info
        date_values = frame["INSTANCE_DATE"]
        dates = pd.to_datetime(date_values, format="ISO8601", errors="coerce")
        info["dates"] = dates
        info["minimum"] = dates.min()
        info["maximum"] = dates.max()
        info["missing_dates"] = int(date_values.eq("").sum())
        info["invalid_dates"] = int((date_values.ne("") & dates.isna()).sum())
        expected_month = dates.dt.year.eq(YEAR) & dates.dt.month.eq(month)
        outside = dates.notna() & ~expected_month
        info["inside_month"] = int(expected_month.sum())
        info["outside_month"] = int(outside.sum())
        info["outside_dates"] = dates[outside].dt.strftime("%Y-%m-%d").value_counts().sort_index()
        info["represented_months"] = set(dates.dropna().dt.strftime("%Y-%m"))
        if info["outside_month"]:
            info["warnings"].append(
                f"{info['outside_month']:,} records fall outside expected month {YEAR}-{month:02d}; ALL are retained."
            )
        if dates.isna().any():
            info["warnings"].append(
                f"{info['missing_dates']:,} missing and {info['invalid_dates']:,} unparseable dates "
                "cannot be checked against the expected month; their records are retained."
            )
    except FileNotFoundError:
        info["errors"].append(f"Source file not found. Place the official CSV at: {path}")
    except UnicodeError:
        info["errors"].append("Cannot decode as UTF-8 or Windows-1252. Check the official export encoding.")
    except pd.errors.EmptyDataError:
        info["errors"].append("CSV is empty or has no readable header.")
    except (pd.errors.ParserError, csv.Error) as error:
        info["errors"].append(f"CSV parsing failed; check separators and quotation marks: {error}")
    except (OSError, ValueError, TypeError, AttributeError) as error:
        info["errors"].append(f"Could not read or validate this source: {error}")
    return info


def validate_schemas(records):
    """Compare every literal source header with January, including column order."""
    january = next(record for record in records if record["month"] == 1)
    expected = january.get("columns", [])
    january_ok = (
        len(expected) == EXPECTED_COLUMN_COUNT and len(set(expected)) == EXPECTED_COLUMN_COUNT
        and "INSTANCE_DATE" in expected and "TRANSACTION_NUMBER" in expected
        and "frame" in january
    )
    for record in records:
        actual = record.get("columns", [])
        if not january_ok:
            record["errors"].append("January must provide the original 22-column DLD schema; schema validation blocked.")
            continue
        missing = [column for column in expected if column not in actual]
        unexpected = [column for column in actual if column not in expected]
        order_differs = [column for column in actual if column in expected] != [
            column for column in expected if column in actual
        ]
        record["schema_differences"] = {
            "missing": missing, "unexpected": unexpected, "order_differs": order_differs,
        }
        record["schema_ok"] = actual == expected and "frame" in record and not record["errors"]
        if actual != expected:
            record["errors"].append(
                "Schema differs from January. No reordering, renaming, or column repair was performed."
            )
    return expected


def verify_source_hashes(records):
    """Hash every available source again after processing and record differences."""
    for record in records:
        if "hash_before" not in record:
            record["hash_unchanged"] = False
            continue
        try:
            record["hash_after"] = file_hash(record["path"])
            record["hash_unchanged"] = record["hash_before"] == record["hash_after"]
            if not record["hash_unchanged"]:
                record["errors"].append("SOURCE HASH CHANGED. The assembled CSV will not be published.")
        except OSError as error:
            record["hash_unchanged"] = False
            record["errors"].append(f"Cannot recheck source SHA-256: {error}")


def source_lines(info):
    """Use the same complete source details in the terminal and text report."""
    lines = [
        "", "-" * 72, f"Source: {info['path'].name}", f"Path: {info['path']}",
        f"Expected month: {YEAR}-{info['month']:02d}",
    ]
    if "bytes" in info:
        lines.append(f"File size: {info['bytes']:,} bytes")
    if "rows" in info:
        lines.append(f"Row count: {info['rows']:,}")
    columns = info.get("columns", [])
    lines.extend([f"Column count: {len(columns):,}", "Complete column names:"])
    lines.extend(f"  {number}. {column}" for number, column in enumerate(columns, 1))
    lines.append(f"Schema validation: {'PASS' if info['schema_ok'] else 'FAIL / unavailable'}")
    if "schema_differences" in info:
        differences = info["schema_differences"]
        lines.extend([
            "Missing columns: " + (", ".join(differences["missing"]) or "None"),
            "Unexpected columns: " + (", ".join(differences["unexpected"]) or "None"),
            f"Column order differs: {'YES' if differences['order_differs'] else 'No'}",
        ])
    if "dates" in info:
        lines.extend([
            f"Earliest INSTANCE_DATE / actual minimum date: {date_text(info['minimum'])}",
            f"Latest INSTANCE_DATE / actual maximum date: {date_text(info['maximum'])}",
            f"Records within expected month: {info['inside_month']:,}",
            f"Records outside expected month: {info['outside_month']:,}",
            f"Missing INSTANCE_DATE values: {info['missing_dates']:,}",
            f"Date conversion failures: {info['invalid_dates']:,}",
        ])
        if info["outside_month"]:
            lines.append("Outside-month dates and record counts:")
            lines.extend(f"  {day}: {count:,}" for day, count in info["outside_dates"].items())
    lines.extend([
        f"Input encoding: {info.get('encoding', 'Unavailable')}",
        f"SHA-256 before processing: {info.get('hash_before', 'Unavailable')}",
        f"SHA-256 after processing: {info.get('hash_after', 'Unavailable')}",
        f"Source hash unchanged: {'YES' if info.get('hash_unchanged') else 'NOT VERIFIED'}",
    ])
    lines.extend(f"WARNING: {message}" for message in info["warnings"])
    lines.extend(f"ERROR: {message}" for message in info["errors"])
    return lines


def combined_metrics(combined, dates):
    """Count records, duplicates, IDs, and empty fields without changing them."""
    ids = combined["TRANSACTION_NUMBER"]
    known_ids = ids[ids.notna() & ids.ne("")]
    return {
        "rows": len(combined), "columns": len(combined.columns),
        "duplicates": int(combined.duplicated().sum()),
        "unique_ids": int(known_ids.nunique()),
        "repeated_ids": int(known_ids.duplicated().sum()),
        "missing_ids": len(ids) - len(known_ids),
        "minimum": dates.min(), "maximum": dates.max(),
        "outside_ytd": int((dates.notna() & ~(dates.dt.year.eq(YEAR) & dates.dt.month.isin(MONTHS))).sum()),
        "missing": (combined.isna() | combined.eq("")).sum(),
    }


def report_text(records, expected, checks, metrics, errors):
    """Build an audit report, including actionable details if assembly is blocked."""
    warning_count = sum(len(record["warnings"]) for record in records)
    status = "FAILED - no new YTD CSV published" if errors else (
        "COMPLETE WITH WARNINGS" if warning_count else "COMPLETE"
    )
    lines = [
        "Dubai Real Estate Intelligence Platform",
        "Stage 4 - Official DLD 2026 Year-to-Date Dataset Assembly",
        "=" * 72, f"Status: {status}", f"Output CSV: {OUTPUT_PATH}",
        "Scope: the nine specified January-September source files only.",
        "Rows per month below refer to the source's expected month, not reassigned calendar months.",
        "A monthly file may cover only part of a month; no complete-month coverage is assumed.",
        "", "Rows per source month:",
    ]
    for record in records:
        rows = f"{record['rows']:,}" if "rows" in record else "Unavailable"
        lines.append(f"  {YEAR}-{record['month']:02d}: {rows} | {record['path'].name}")
    lines.append(f"Total rows before concatenation (readable sources): {sum(r.get('rows', 0) for r in records):,}")
    lines.extend(["", "Expected original column order from January:", ", ".join(expected) or "Unavailable"])
    lines.append(f"Schema validation result: {'PASS' if all(r['schema_ok'] for r in records) else 'FAIL'}")
    lines.append(f"Records outside expected source month: {sum(r.get('outside_month', 0) for r in records):,}")
    lines.append("Month mismatches are reported, not filtered, corrected, or reassigned.")
    if metrics:
        lines.extend([
            "", f"Total combined rows: {metrics['rows']:,}",
            f"Combined column count: {metrics['columns']:,}",
            f"Earliest INSTANCE_DATE: {date_text(metrics['minimum'])}",
            f"Latest INSTANCE_DATE: {date_text(metrics['maximum'])}",
            f"Records outside January-September 2026: {metrics['outside_ytd']:,}",
            f"Exact duplicate count: {metrics['duplicates']:,}",
            f"Unique TRANSACTION_NUMBER count: {metrics['unique_ids']:,}",
            f"Repeated TRANSACTION_NUMBER occurrences: {metrics['repeated_ids']:,}",
            f"Missing TRANSACTION_NUMBER values: {metrics['missing_ids']:,}",
            "Duplicate counts are additional occurrences after the first; no duplicates were removed.",
            "Repeated transaction numbers may legitimately represent multiple properties or records.",
            "", "Missing values per column in the combined dataset:",
            *[f"  {column}: {count:,}" for column, count in metrics["missing"].items()],
        ])
    else:
        lines.append("Combined metrics: unavailable because input validation blocked concatenation.")
    lines.extend([
        "", "Preservation conventions:",
        "All source fields were loaded as text, without stripping whitespace or changing numeric text.",
        "Missing-value counts describe blank CSV fields; literal NA strings and whitespace are preserved.",
        "Date parsing used separate validation/sort keys; original INSTANCE_DATE text is retained.",
        "No date columns or source labels were added. No missing values were filled or cleaned.",
        "The output is stably sorted by parsed INSTANCE_DATE, with unparseable/missing dates last.",
        "The pandas index is not exported. No work beyond Stage 4 was performed.",
        "", "Validation checks:",
        *[f"  {'PASS' if passed else 'FAIL'}: {label}" for label, passed in checks.items()],
        "", "Source files were not modified: " + (
            "CONFIRMED - all nine before/after SHA-256 hashes match."
            if len(records) == 9 and all(r.get("hash_unchanged") for r in records)
            else "NOT FULLY VERIFIED - see individual source details."
        ),
    ])
    if errors:
        lines.extend(["", "Blocking issues:", *[f"  - {error}" for error in errors]])
        lines.append("Any previously existing YTD output has been left untouched.")
    lines.extend(["", "ALL SOURCE FILES AND VALIDATION DETAILS"])
    for record in records:
        lines.extend(source_lines(record))
    return "\n".join(lines) + "\n"


def write_temporary(path, frame=None, text=None):
    """Write beside the final output so only complete files are published."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", suffix=".tmp", dir=path.parent, delete=False,
        ) as destination:
            temporary = Path(destination.name)
            if frame is not None:
                frame.to_csv(destination, index=False)
            else:
                destination.write(text)
        return temporary
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def main():
    """Inspect all sources, assemble only compatible data, and publish the audit."""
    temporary_csv = temporary_report = None
    try:
        validate_paths()
        records = []
        for month, path in SOURCES:
            print(f"Checking {YEAR}-{month:02d}: {path.name}")
            records.append(inspect_source(month, path))
        expected = validate_schemas(records)
        represented = set().union(*(r.get("represented_months", set()) for r in records))
        required_months = {f"{YEAR}-{month:02d}" for month in MONTHS}
        checks = {
            "Exactly nine monthly source files were successfully processed": len(records) == 9
            and all("frame" in r and "dates" in r and not r["errors"] for r in records),
            "All sources have January's original 22 columns in identical order": len(expected) == 22
            and all(r["schema_ok"] for r in records),
            "January through September are all represented by valid dates": required_months.issubset(represented),
            "Each source contains records from its expected month": all(r.get("inside_month", 0) > 0 for r in records),
        }
        errors = [f"{r['path'].name}: {error}" for r in records for error in r["errors"]]
        errors.extend(label for label, passed in checks.items() if not passed)
        metrics = None

        # Strict schema validation precedes concatenation. Even order-only
        # differences block assembly; this script does not repair source schemas.
        if not errors:
            combined = pd.concat([r["frame"] for r in records], ignore_index=True)
            dates = pd.concat([r["dates"] for r in records], ignore_index=True)
            total_source_rows = sum(r["rows"] for r in records)
            order = dates.sort_values(kind="stable", na_position="last").index
            combined = combined.loc[order].reset_index(drop=True)
            sorted_dates = dates.loc[order].reset_index(drop=True)
            checks.update({
                "Combined row count equals the sum of source row counts": len(combined) == total_source_rows,
                "Output contains exactly the 22 original columns and no derived columns": list(combined.columns) == expected,
                "Parsed dates are sorted ascending": sorted_dates.dropna().is_monotonic_increasing,
            })
            errors.extend(label for label, passed in checks.items() if not passed and label not in errors)
            metrics = combined_metrics(combined, sorted_dates)
            if not errors:
                temporary_csv = write_temporary(OUTPUT_PATH, frame=combined)

        # This happens after reading, concatenating, sorting, and writing the
        # temporary CSV. Changed source files block publication of the output.
        previous_errors = {(r["path"], error) for r in records for error in r["errors"]}
        verify_source_hashes(records)
        errors.extend(
            f"{r['path'].name}: {error}" for r in records for error in r["errors"]
            if (r["path"], error) not in previous_errors
        )
        checks["Every source SHA-256 hash is unchanged"] = all(r.get("hash_unchanged") for r in records)
        for record in records:
            print("\n".join(source_lines(record)))

        report = report_text(records, expected, checks, metrics, errors)
        temporary_report = write_temporary(REPORT_PATH, text=report)
        validate_paths()  # Recheck aliases before replacing any final output.
        if not errors:
            temporary_csv.replace(OUTPUT_PATH)
        temporary_report.replace(REPORT_PATH)

        print("\nSTAGE 4 YTD ASSEMBLY SUMMARY\n" + "=" * 72)
        if errors:
            print("Assembly stopped. No new combined CSV was published.")
            print(f"Read the reported source/schema problems in: {REPORT_PATH}")
            return 1
        print(f"Sources: {len(records):,} | Combined rows: {metrics['rows']:,} | Original columns: {metrics['columns']:,}")
        print(f"Date range: {date_text(metrics['minimum'])} through {date_text(metrics['maximum'])}")
        outside_count = sum(r["outside_month"] for r in records)
        print(f"Records outside their expected source month: {outside_count:,} (retained; see report)")
        print(f"Exact duplicate rows: {metrics['duplicates']:,} (retained)")
        print(f"Unique transaction numbers: {metrics['unique_ids']:,}")
        print(f"Additional repeated transaction-number occurrences: {metrics['repeated_ids']:,} (retained)")
        print("All required validation checks passed. All nine source hashes are unchanged.")
        print(f"Combined CSV: {OUTPUT_PATH}\nAssembly report: {REPORT_PATH}")
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Stage 4 could not be completed: {error}")
        print("Check source files, output paths, folder permissions, and available disk space.")
        return 1
    finally:
        # Only temporary output files created by this run can be removed here.
        for path in (temporary_csv, temporary_report):
            if path is not None:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
