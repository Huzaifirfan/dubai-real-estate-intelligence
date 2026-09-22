"""Stage 7: import the unchanged Stage 6 CSV into an EMPTY MySQL table.

First execute sql/01_create_mysql_schema.sql using your MySQL client.
Put MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE in .env.
Then run: python src/07_load_mysql.py

All batches use one InnoDB transaction: validation failures roll back this run.
This loader never creates, clears, drops, or replaces a database table.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import io
from pathlib import Path
import tempfile

try:
    import pandas as pd
    import pymysql  # Driver used by the SQLAlchemy mysql+pymysql URL.
    from dotenv import dotenv_values
    from sqlalchemy import MetaData, Table, create_engine, text
    from sqlalchemy.engine import URL
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.pool import NullPool
except ImportError:
    raise SystemExit("Activate the project environment and run: python -m pip install -r requirements.txt")


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "data/processed/dld_transactions_2026_ytd_features.csv"
ENV_PATH = ROOT / ".env"
REPORT_PATH = ROOT / "reports/stage7_mysql_load_report.txt"
DATABASE = "dubai_real_estate_intelligence"
TABLE_NAME = "dld_transactions_2026_ytd"
QUALIFIED_TABLE = f"`{DATABASE}`.`{TABLE_NAME}`"  # Fixed identifiers, never user SQL.
LOCK_NAME = "drei_stage7_dld_2026_ytd_import"
BATCH_SIZE = 5000
SCHEMA_HELP = "Execute sql/01_create_mysql_schema.sql in your MySQL client first, then rerun this loader."

EXPECTED_COLUMNS = [
    "TRANSACTION_NUMBER", "INSTANCE_DATE", "GROUP_EN", "PROCEDURE_EN",
    "IS_OFFPLAN_EN", "IS_FREE_HOLD_EN", "USAGE_EN", "AREA_EN", "PROP_TYPE_EN",
    "PROP_SB_TYPE_EN", "TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA", "ROOMS_EN",
    "PARKING", "NEAREST_METRO_EN", "NEAREST_MALL_EN", "NEAREST_LANDMARK_EN",
    "TOTAL_BUYER", "TOTAL_SELLER", "MASTER_PROJECT_EN", "PROJECT_EN",
    "TRANSACTION_DATE", "TRANSACTION_YEAR", "TRANSACTION_MONTH",
    "TRANSACTION_MONTH_NAME", "TRANSACTION_QUARTER", "TRANSACTION_DAY",
    "TRANSACTION_DAY_NAME", "TRANSACTION_HOUR", "IS_SALE_TRANSACTION",
    "IS_RESIDENTIAL_FLAG", "IS_OFFPLAN_FLAG", "IS_FREEHOLD_FLAG",
    "PROPERTY_SIZE_SQFT", "VALID_SALE_PRICE_METRIC", "SALE_PRICE_PER_SQM",
    "SALE_PRICE_PER_SQFT", "TRANSACTION_VALUE_BAND", "PROPERTY_SIZE_BAND", "BEDROOM_COUNT",
]
DECIMAL_COLUMNS = {
    "TRANS_VALUE", "PROCEDURE_AREA", "ACTUAL_AREA", "PROPERTY_SIZE_SQFT",
    "SALE_PRICE_PER_SQM", "SALE_PRICE_PER_SQFT",
}
INTEGER_TYPES = {
    "TOTAL_BUYER": "int", "TOTAL_SELLER": "int", "TRANSACTION_YEAR": "smallint",
    "TRANSACTION_MONTH": "tinyint", "TRANSACTION_DAY": "tinyint", "TRANSACTION_HOUR": "tinyint",
    "IS_SALE_TRANSACTION": "tinyint", "IS_RESIDENTIAL_FLAG": "tinyint",
    "IS_OFFPLAN_FLAG": "tinyint", "IS_FREEHOLD_FLAG": "tinyint",
    "VALID_SALE_PRICE_METRIC": "tinyint", "BEDROOM_COUNT": "tinyint",
}


class LoadStopped(Exception):
    """An expected validation problem, described without secret connection data."""


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_settings():
    """Use only this project's .env, without falling back to shell credentials."""
    if not ENV_PATH.is_file():
        raise LoadStopped(
            "The project .env file was not found. Create it with MYSQL_HOST, MYSQL_PORT, "
            "MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DATABASE. Never commit .env."
        )
    # Disable interpolation so passwords containing ${...} remain literal and
    # variables cannot silently obtain values from the shell environment.
    settings = dotenv_values(ENV_PATH, interpolate=False)
    required = ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]
    missing = [key for key in required if key not in settings or settings[key] is None
               or (key != "MYSQL_PASSWORD" and settings[key] == "")]
    if missing:
        raise LoadStopped("Missing .env settings: " + ", ".join(missing))
    if settings["MYSQL_DATABASE"] != DATABASE:
        raise LoadStopped(f"MYSQL_DATABASE must be {DATABASE} for this project.")
    try:
        port = int(settings["MYSQL_PORT"])
    except (ValueError, TypeError):
        raise LoadStopped("MYSQL_PORT must be an integer from 1 to 65535.") from None
    if not 1 <= port <= 65535:
        raise LoadStopped("MYSQL_PORT must be an integer from 1 to 65535.")
    settings["MYSQL_PORT"] = port
    return settings


def load_input():
    """Load a fingerprinted snapshot without altering source fields or files."""
    if not SOURCE_PATH.is_file():
        raise LoadStopped(f"Stage 6 CSV not found: {SOURCE_PATH}. Complete Stage 6 first.")
    content = SOURCE_PATH.read_bytes()
    before = hashlib.sha256(content).hexdigest()
    # All fields initially remain strings. Empty CSV cells become SQL NULL only
    # in the insertion copy. Literal categories such as ROOMS_EN='NA' survive.
    frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype="string",
                        keep_default_na=False, na_filter=False, skip_blank_lines=False,
                        low_memory=False)
    missing = [column for column in EXPECTED_COLUMNS if column not in frame.columns]
    unexpected = [column for column in frame.columns if column not in EXPECTED_COLUMNS]
    if missing or unexpected or len(frame.columns) != 41 or not frame.columns.is_unique:
        raise LoadStopped(
            "Expected exactly the 41 Stage 6 columns.\n"
            f"Missing columns: {', '.join(missing) or 'None'}\n"
            f"Unexpected columns: {', '.join(unexpected) or 'None'}"
        )
    if not isinstance(frame.index, pd.RangeIndex):
        raise LoadStopped("CSV rows contain extra fields interpreted as an index. Check the CSV structure.")
    if frame.empty:
        raise LoadStopped("The CSV has no records. Nothing was imported.")
    print(f"CSV verified: {len(frame):,} rows and {len(frame.columns):,} columns.")
    return frame, before


def make_engine(settings):
    """URL.create safely handles special password characters without logging them."""
    url = URL.create(
        "mysql+pymysql", username=settings["MYSQL_USER"], password=settings["MYSQL_PASSWORD"],
        host=settings["MYSQL_HOST"], port=settings["MYSQL_PORT"], query={"charset": "utf8mb4"},
    )
    # Connect to the server first so a missing database receives a clear message.
    # NullPool closes the physical connection on exit, also releasing named locks.
    return create_engine(url, echo=False, hide_parameters=True, poolclass=NullPool,
                         connect_args={"connect_timeout": 10})


def inspect_target(connection):
    """Require the existing non-destructive schema, including transaction support."""
    params = {"database": DATABASE, "table": TABLE_NAME}
    exists = connection.execute(text(
        "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=:database"
    ), params).scalar_one()
    if not exists:
        raise LoadStopped("The target database does not exist. " + SCHEMA_HELP)
    table_info = connection.execute(text(
        "SELECT ENGINE, TABLE_TYPE, TABLE_COLLATION FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA=:database AND TABLE_NAME=:table"
    ), params).mappings().one_or_none()
    if table_info is None:
        raise LoadStopped("The target table does not exist. " + SCHEMA_HELP)
    if table_info["ENGINE"] != "InnoDB" or table_info["TABLE_TYPE"] != "BASE TABLE":
        raise LoadStopped("The target must be an InnoDB table for rollback protection. " + SCHEMA_HELP)
    if table_info["TABLE_COLLATION"] != "utf8mb4_0900_bin":
        raise LoadStopped("The target collation differs from the supplied utf8mb4 schema. No table was altered.")
    rows = connection.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH, "
        "NUMERIC_PRECISION, NUMERIC_SCALE, DATETIME_PRECISION, COLUMN_KEY, EXTRA "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=:database AND TABLE_NAME=:table "
        "ORDER BY ORDINAL_POSITION"
    ), params).mappings().all()
    if [row["COLUMN_NAME"] for row in rows] != ["ROW_ID", *EXPECTED_COLUMNS]:
        raise LoadStopped("The table must have ROW_ID plus the 41 dataset columns in schema order. " + SCHEMA_HELP)
    metadata = {row["COLUMN_NAME"]: dict(row) for row in rows}
    row_id = metadata["ROW_ID"]
    if row_id["DATA_TYPE"] != "bigint" or row_id["COLUMN_KEY"] != "PRI" or "auto_increment" not in row_id["EXTRA"]:
        raise LoadStopped("ROW_ID must be BIGINT AUTO_INCREMENT PRIMARY KEY. " + SCHEMA_HELP)
    # Additional unique indexes could reject legitimate repeated transaction IDs.
    unique_indexes = connection.execute(text(
        "SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=:database "
        "AND TABLE_NAME=:table AND NON_UNIQUE=0 AND INDEX_NAME <> 'PRIMARY'"
    ), params).scalar_one()
    if unique_indexes:
        raise LoadStopped("Unexpected unique indexes could reject legitimate records. No table was changed.")
    for column in EXPECTED_COLUMNS:
        expected_type = ("decimal" if column in DECIMAL_COLUMNS else INTEGER_TYPES.get(column)
                         or {"INSTANCE_DATE": "datetime", "TRANSACTION_DATE": "date"}.get(column, "varchar"))
        if metadata[column]["DATA_TYPE"] != expected_type:
            raise LoadStopped(f"Incompatible MySQL type for {column}. " + SCHEMA_HELP)
    print("Target database and 42-column InnoDB table verified.")
    return metadata


def prepare_value(value, column, definition):
    """Adapt a value to its SQL type without guessing, rounding, or truncating."""
    if pd.isna(value) or value == "":
        if definition["IS_NULLABLE"] != "YES":
            raise ValueError("a missing value cannot enter a NOT NULL column")
        return None  # Python None is sent as SQL NULL, not the strings 'NaN'/'NaT'.
    kind = definition["DATA_TYPE"]
    if kind in {"decimal", "int", "smallint", "tinyint"}:
        number = Decimal(str(value))  # Never convert exact CSV decimals via float.
        if not number.is_finite():
            raise ValueError("non-finite numeric values cannot be stored in MySQL")
        if kind == "decimal":
            digits = list(number.as_tuple().digits)
            exponent = number.as_tuple().exponent
            # Trailing zeros do not require extra scale; all significant digits do.
            while digits and digits[-1] == 0:
                digits.pop()
                exponent += 1
            fractional_digits = max(-exponent, 0) if digits else 0
            integer_digits = max(number.adjusted() + 1, 0) if number else 0
            precision, scale = int(definition["NUMERIC_PRECISION"]), int(definition["NUMERIC_SCALE"])
            if fractional_digits > scale or integer_digits > precision - scale:
                raise ValueError("the DECIMAL definition would round or overflow this value")
            return number
        if number != number.to_integral_value():
            raise ValueError("a fractional value cannot be stored in an integer column")
        integer = int(number)
        bits = {"tinyint": 8, "smallint": 16, "int": 32}[kind]
        unsigned = "unsigned" in definition["COLUMN_TYPE"]
        low, high = (0, 2 ** bits - 1) if unsigned else (-2 ** (bits - 1), 2 ** (bits - 1) - 1)
        if not low <= integer <= high:
            raise ValueError("the value exceeds the integer type's capacity")
        return integer
    if kind == "datetime":
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is not None or timestamp.nanosecond:
            raise ValueError("timezone/nanosecond conversion would change the source timestamp")
        precision = int(definition["DATETIME_PRECISION"] or 0)
        if timestamp.microsecond % (10 ** (6 - precision)) or not 1000 <= timestamp.year <= 9999:
            raise ValueError("the DATETIME definition cannot preserve this timestamp")
        return timestamp.to_pydatetime()
    if kind == "date":
        parsed = date.fromisoformat(value)
        if parsed.year < 1000:
            raise ValueError("the date is outside MySQL DATE range")
        return parsed
    if len(value) > int(definition["CHARACTER_MAXIMUM_LENGTH"]):
        raise ValueError("text exceeds the VARCHAR capacity; truncation is not allowed")
    return value  # Official names, capitalization, whitespace, and literal NA stay intact.


def prepare_frame(source, metadata):
    """Build a separate insertion DataFrame with Python date/Decimal/int/None values."""
    columns = {}
    for column in EXPECTED_COLUMNS:
        converted = []
        for position, value in enumerate(source[column], start=2):
            try:
                converted.append(prepare_value(value, column, metadata[column]))
            except (ValueError, TypeError, InvalidOperation, OverflowError):
                raise LoadStopped(
                    f"CSV record near line {position:,}, column {column}, cannot be represented "
                    "without changing its value. Check the value and schema; no rows were imported."
                ) from None
        # object dtype avoids converting nullable integers/Decimals back to floats.
        columns[column] = pd.Series(converted, index=source.index, dtype=object)
    return pd.DataFrame(columns, index=source.index)


def csv_metrics(frame):
    """Calculate comparison values from this CSV rather than fixed reference counts."""
    dates = frame["INSTANCE_DATE"].dropna()
    sales = frame["GROUP_EN"].eq("Sales")
    return {
        "rows": len(frame), "columns": len(frame.columns) + 1,
        "minimum": dates.min() if len(dates) else None,
        "maximum": dates.max() if len(dates) else None,
        "unique_ids": int(frame["TRANSACTION_NUMBER"].nunique(dropna=True)),
        "sales": int(sales.sum()), "non_sales": int((~sales).sum()),
        "valid_prices": int(frame["VALID_SALE_PRICE_METRIC"].eq(1).sum()),
        "null_sqm": int(frame["SALE_PRICE_PER_SQM"].isna().sum()),
        "duplicate_row_ids": 0,
        "literal_na_rooms": int(frame["ROOMS_EN"].eq("NA").sum()),
    }


def mysql_metrics(connection):
    """Validate the inserted rows while the transaction can still be rolled back."""
    result = dict(connection.execute(text(f"""
        SELECT COUNT(*) AS rows_count,
               MIN(INSTANCE_DATE) AS minimum_date, MAX(INSTANCE_DATE) AS maximum_date,
               COUNT(DISTINCT TRANSACTION_NUMBER) AS unique_ids,
               COALESCE(SUM(CASE WHEN GROUP_EN='Sales' THEN 1 ELSE 0 END),0) AS sales,
               COALESCE(SUM(CASE WHEN GROUP_EN='Sales' THEN 0 ELSE 1 END),0) AS non_sales,
               COALESCE(SUM(CASE WHEN VALID_SALE_PRICE_METRIC=1 THEN 1 ELSE 0 END),0) AS valid_prices,
               COALESCE(SUM(CASE WHEN SALE_PRICE_PER_SQM IS NULL THEN 1 ELSE 0 END),0) AS null_sqm,
               COUNT(*) - COUNT(DISTINCT ROW_ID) AS duplicate_row_ids,
               COALESCE(SUM(CASE WHEN ROOMS_EN='NA' THEN 1 ELSE 0 END),0) AS literal_na_rooms
        FROM {QUALIFIED_TABLE}
    """)).mappings().one())
    columns = connection.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=:database AND TABLE_NAME=:table"
    ), {"database": DATABASE, "table": TABLE_NAME}).scalar_one()
    return {
        "rows": int(result.pop("rows_count")), "columns": int(columns),
        "minimum": result.pop("minimum_date"), "maximum": result.pop("maximum_date"),
        **{key: int(value) for key, value in result.items()},
    }


def build_report(source, actual, expected, batches, before, after, checks, server_info):
    lines = [
        "Dubai Real Estate Intelligence Platform",
        "Stage 7 - MySQL Database Setup and Data Import Pipeline",
        "=" * 72, "Status: SUCCESS - import committed after validation",
        f"MySQL server version: {server_info[0]}", f"MySQL distribution: {server_info[1]}",
        f"Database name: {DATABASE}", f"Table name: {TABLE_NAME}",
        f"CSV source: {SOURCE_PATH}", f"Source rows: {len(source):,}",
        f"Source columns: {len(source.columns):,}", f"MySQL rows after import: {actual['rows']:,}",
        f"MySQL column count: {actual['columns']:,}", f"Number of batches used: {batches:,}",
        f"Maximum rows per batch: {BATCH_SIZE:,}",
        f"Earliest INSTANCE_DATE: {actual['minimum']}", f"Latest INSTANCE_DATE: {actual['maximum']}",
        f"Unique transaction numbers: {actual['unique_ids']:,}", f"Sales count: {actual['sales']:,}",
        f"Non-Sales count: {actual['non_sales']:,}", f"Valid sale-price-metric count: {actual['valid_prices']:,}",
        f"NULL SALE_PRICE_PER_SQM count: {actual['null_sqm']:,}",
        f"Duplicate ROW_ID count: {actual['duplicate_row_ids']:,}",
        f"Literal NA room categories preserved: {actual['literal_na_rooms']:,}",
        "", f"Source SHA-256 before processing: {before}", f"Source SHA-256 after processing: {after}",
        f"Source unchanged: {'YES - hashes match' if before == after else 'NO'}",
        "", "CSV-derived expected values compared with MySQL (column expectation includes ROW_ID):",
        *[f"  {key}: Expected={expected[key]} | MySQL={actual[key]}" for key in expected],
        "", "Validation results:", *[f"  {'PASS' if passed else 'FAIL'}: {label}" for label, passed in checks.items()],
        "", "ROW_ID was excluded from inserts and generated by MySQL.",
        "The table was empty before this import. Repeated transaction numbers were retained.",
        "All batches were inserted in one InnoDB transaction; no table was cleared or replaced.",
        "Source blanks/NaN/NaT become SQL NULL; literal category text such as NA is preserved.",
        "Decimal values were parsed from strings without float conversion or rounding.",
        "Only Stage 7 setup, import, and validation were performed. No credentials are included here.",
    ]
    return "\n".join(lines) + "\n"


def safe_database_error(error):
    """Never print a connection URL, password, SQL parameters, or raw DB exception."""
    original = getattr(error, "orig", None)
    code = original.args[0] if original is not None and original.args and isinstance(original.args[0], int) else None
    explanations = {
        1045: "Authentication failed. Check MYSQL_USER and MYSQL_PASSWORD in .env.",
        1044: "The MySQL account lacks permission for this database.",
        1049: "The target database is missing. " + SCHEMA_HELP,
        1146: "The target table is missing. " + SCHEMA_HELP,
        2003: "Cannot reach MySQL. Check the server, MYSQL_HOST, and MYSQL_PORT.",
        2006: "The MySQL connection closed. Check server availability and packet limits.",
        2013: "The MySQL connection was lost. Check server availability before retrying.",
        1205: "MySQL timed out waiting for a lock. Retry after the other operation finishes.",
        1213: "MySQL detected a transaction deadlock. Retry after the other operation finishes.",
    }
    return explanations.get(code, f"MySQL operation failed (driver error code {code or 'unavailable'}). Check server permissions and schema.")


def main():
    engine = None
    temporary_report = None
    committed = False
    try:
        for protected in (SOURCE_PATH, ENV_PATH):
            if REPORT_PATH.resolve() == protected.resolve() or (
                REPORT_PATH.exists() and protected.exists() and REPORT_PATH.samefile(protected)
            ):
                raise LoadStopped("The report path must not point to a source or credential file.")
        settings = read_settings()
        source, before = load_input()
        engine = make_engine(settings)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("MySQL connection successful. Credentials were not displayed.")
            server_info = connection.execute(text("SELECT VERSION(), @@version_comment")).one()
            print(f"MySQL server: {server_info[0]} ({server_info[1]}).")
            metadata = inspect_target(connection)
            # Enable strict storage behavior for this session only; do not alter
            # the server configuration or allow silent MySQL truncation.
            modes = connection.execute(text("SELECT @@SESSION.sql_mode")).scalar_one().split(",")
            if not {"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}.intersection(modes):
                connection.execute(text("SET SESSION sql_mode=:modes"), {"modes": ",".join(modes + ["STRICT_ALL_TABLES"])})
            table = Table(TABLE_NAME, MetaData(), schema=DATABASE, autoload_with=connection)
            locked = connection.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": LOCK_NAME}).scalar_one()
            if locked != 1:
                raise LoadStopped("Another loader holds the import lock. No data was inserted.")
            connection.commit()  # Finish metadata reads; named locks survive commit.
            try:
                # One transaction covers the empty-table guard, all batches, and
                # post-load checks. Any exception before commit rolls back this run.
                with connection.begin():
                    current_rows = connection.execute(text(f"SELECT COUNT(*) FROM {QUALIFIED_TABLE}")).scalar_one()
                    if current_rows != 0:
                        raise LoadStopped(
                            f"Import stopped: the target table already contains {current_rows:,} rows. "
                            "This prevents duplicate imports. Nothing was appended, truncated, or dropped."
                        )
                    print("Target table is empty. Preparing values without rounding or truncation...")
                    prepared = prepare_frame(source, metadata)
                    expected = csv_metrics(prepared)
                    batches = 0
                    for start in range(0, len(prepared), BATCH_SIZE):
                        stop = min(start + BATCH_SIZE, len(prepared))
                        print(f"Loading rows {start + 1:,}-{stop:,}...", flush=True)
                        # ROW_ID is absent. SQLAlchemy/PyMySQL receive bounded
                        # executemany batches, rather than a 159k-row SQL string.
                        connection.execute(table.insert(), prepared.iloc[start:stop].to_dict(orient="records"))
                        batches += 1
                        if connection.exec_driver_sql("SHOW WARNINGS").fetchone() is not None:
                            raise LoadStopped("MySQL reported a storage warning; the import will be rolled back rather than accept changed values.")
                    actual = mysql_metrics(connection)
                    after = file_hash(SOURCE_PATH)
                    checks = {
                        "Input has exactly the 41 expected columns": set(source.columns) == set(EXPECTED_COLUMNS) and len(source.columns) == 41,
                        "Target table was empty before insertion": current_rows == 0,
                        "Every source value fits its SQL type without rounding or truncation": len(prepared) == len(source),
                        **{f"MySQL {key} matches CSV-derived expectation": actual[key] == expected[key] for key in expected},
                        "Source CSV SHA-256 is unchanged": before == after,
                    }
                    failures = [label for label, passed in checks.items() if not passed]
                    if failures:
                        raise LoadStopped("Post-load validation failed; rolling back:\n- " + "\n- ".join(failures))
                    report = build_report(source, actual, expected, batches, before, after, checks, server_info)
                    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tmp", dir=REPORT_PATH.parent, delete=False) as destination:
                        temporary_report = Path(destination.name)
                        destination.write(report)
                    if file_hash(SOURCE_PATH) != before:
                        raise LoadStopped("The source changed before commit. The import will be rolled back.")
                committed = True
            finally:
                # NullPool also closes the underlying connection if this cleanup
                # fails, releasing the server's session-level import lock.
                try:
                    if connection.in_transaction():
                        connection.rollback()
                    connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": LOCK_NAME})
                    connection.commit()
                except SQLAlchemyError:
                    pass
        temporary_report.replace(REPORT_PATH)
        print("\nSTAGE 7 MYSQL LOAD SUMMARY\n" + "=" * 72)
        print(f"Database: {DATABASE}\nTable: {TABLE_NAME}")
        print(f"CSV rows: {len(source):,} | MySQL rows: {actual['rows']:,}")
        print(f"MySQL columns: {actual['columns']:,} (ROW_ID + 41 dataset columns)")
        print(f"Batches: {batches:,}\nDate range: {actual['minimum']} through {actual['maximum']}")
        print(f"Unique transaction numbers: {actual['unique_ids']:,}")
        print(f"Sales: {actual['sales']:,} | Non-Sales: {actual['non_sales']:,}")
        print(f"Valid price metrics: {actual['valid_prices']:,} | NULL price per sqm: {actual['null_sqm']:,}")
        print("Source unchanged: YES (SHA-256 verified). Validation: PASS. Import committed.")
        print(f"Report: {REPORT_PATH}")
        return 0
    except LoadStopped as error:
        print(str(error))
    except SQLAlchemyError as error:
        print(safe_database_error(error))
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError):
        print("The Stage 6 CSV could not be read as UTF-8 CSV. Check its header and format; no source values were changed.")
    except OSError:
        print("A required file could not be read or written. Check paths, permissions, and disk space.")
    except (ValueError, TypeError, InvalidOperation):
        print("A setting or CSV value could not be represented safely. Check .env keys and the Stage 6 schema.")
    finally:
        if engine is not None:
            engine.dispose()
        if temporary_report is not None:
            temporary_report.unlink(missing_ok=True)
    if committed:
        print("The database import was committed, but the report could not be published. The nonempty-table guard will prevent another import.")
    else:
        print("No import was committed by this run. Existing table data was not cleared or replaced.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
