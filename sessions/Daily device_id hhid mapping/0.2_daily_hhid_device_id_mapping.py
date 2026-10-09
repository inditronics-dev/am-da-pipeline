import os
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv


# ==========================================================
# 1. PATH CONFIGURATION
# ==========================================================

# Current script location:
#
# D:\current-da-workflow__-20260903T100915Z-1-001\
# current-da-workflow__\
# current-da-workflow\
# Daily device_id hhid mapping\
# 0.3_daily_hhid_device_id_mapping.py

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# Project root:
#
# D:\current-da-workflow__-20260903T100915Z-1-001\
# current-da-workflow__\
# current-da-workflow\

BASE_DIR = os.path.abspath(
    os.path.join(
        SCRIPT_DIR,
        ".."
    )
)


# ==========================================================
# 2. LOAD .ENV FILE
# ==========================================================

ENV_FILE = os.path.join(
    BASE_DIR,
    ".env"
)

# Load environment variables
load_dotenv(ENV_FILE)


# ==========================================================
# 3. DATABASE VARIABLES
# ==========================================================

DB_HOST = os.getenv(
    "DB_HOST"
)

DB_PORT = os.getenv(
    "DB_PORT",
    "5432"
)

DB_NAME = os.getenv(
    "DB_NAME"
)

DB_USER = os.getenv(
    "DB_USER"
)

DB_PASSWORD = os.getenv(
    "DB_PASSWORD"
)

# ==========================================================
# 5. VALIDATE DATABASE CONFIGURATION
# ==========================================================

missing_variables = []


if not DB_HOST:
    missing_variables.append(
        "DB_HOST"
    )


if not DB_NAME:
    missing_variables.append(
        "DB_NAME"
    )


if not DB_USER:
    missing_variables.append(
        "DB_USER"
    )


if not DB_PASSWORD:
    missing_variables.append(
        "DB_PASSWORD"
    )


if missing_variables:

    raise ValueError(
        "The following database variables "
        "are missing from the .env file: "
        + ", ".join(missing_variables)
        + "\n\nExpected .env location:\n"
        + ENV_FILE
    )


# ==========================================================
# 6. DATABASE CONFIGURATION
# ==========================================================

DB_CONFIG = {
    "host": DB_HOST,
    "port": int(DB_PORT),
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
}


# ==========================================================
# 7. OUTPUT FOLDER
# ==========================================================

# Exact output location:
#
# D:\current-da-workflow__-20260903T100915Z-1-001\
# current-da-workflow__\
# current-da-workflow\
# Daily device_id hhid mapping\
# Mapping\

OUTPUT_FOLDER = os.path.join(
    BASE_DIR,
    "Daily device_id hhid mapping",
    "Mapping"
)


# Create folder if it doesn't exist
os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


print(
    f"\nOutput Folder    : {OUTPUT_FOLDER}"
)


# ==========================================================
# 8. DYNAMIC D-1 DATE
# ==========================================================
#
# IMPORTANT:
#
# D-1 is used ONLY for the output filename.
#
# It is NOT used to filter the database.
#
# The SQL query gets the data that exists in the DB
# at the exact moment the query is executed.
#

today = datetime.now()

d_minus_1 = today - timedelta(
    days=1
)

d_minus_1_str = d_minus_1.strftime(
    "%d-%m-%Y"
)


print(
    f"Execution Date   : "
    f"{today.strftime('%d-%m-%Y %H:%M:%S')}"
)

print(
    f"D-1 Date         : "
    f"{d_minus_1_str}"
)


# ==========================================================
# 9. OUTPUT FILE NAME
# ==========================================================

output_filename = (
    f"{d_minus_1_str}_hhid_device_id.csv"
)


output_path = os.path.join(
    OUTPUT_FOLDER,
    output_filename
)


print(
    f"Output File      : {output_filename}"
)


# ==========================================================
# 10. SQL QUERY
# ==========================================================
#
# NO DATE FILTER IS USED.
#
# This query takes the current data available in the
# database when the query executes.
#
# DISTINCT ON (ma.meter_id)
# means only one row per meter_id.
#
# ORDER BY ma.meter_id, ma.assigned_at DESC
# means the latest assignment is selected.
#

QUERY = """
SELECT DISTINCT ON (ma.meter_id)
       m.meter_id AS meter_id,
       h.hhid AS hhid,
       h.region,
       ma.assigned_at
FROM meter_assignments ma
JOIN meters m
    ON ma.meter_id = m.id
JOIN households h
    ON ma.household_id = h.id
WHERE m.meter_id >= 'IM000101'
  AND m.meter_id <= 'IM000600'
ORDER BY ma.meter_id, ma.assigned_at DESC;
"""


# ==========================================================
# 11. DATABASE CONNECTION
# ==========================================================

connection = None


try:

    print("\nConnecting to database...")

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    print(
        "Database connection successful."
    )


    # ======================================================
    # 12. EXECUTE QUERY
    # ======================================================

    print(
        "\nExecuting mapping query..."
    )

    print(
        "Fetching current data from database..."
    )


    df = pd.read_sql_query(
        QUERY,
        connection
    )


    print(
        f"Rows downloaded: {len(df)}"
    )


    # ======================================================
    # 13. CHECK DATA
    # ======================================================

    if df.empty:

        print(
            "\nWARNING: Query returned no data."
        )

    else:

        print(
            "\nData downloaded successfully."
        )


    # ======================================================
    # 14. CLEAN assigned_at
    # ==========================================================
    #
    # Example input:
    #
    # 2026-08-22 11:02:23.752714+00:00
    #
    # Output:
    #
    # date = 2026-08-22
    # time = 11:02:23
    #
    # The database timestamp is UTC.
    #
    # We keep the UTC clock value and remove:
    #
    # - microseconds
    # - +00:00 timezone text
    #

    if "assigned_at" in df.columns:

        df["assigned_at"] = pd.to_datetime(
            df["assigned_at"],
            utc=True,
            errors="coerce"
        )


        # --------------------------------------------------
        # Separate DATE
        # --------------------------------------------------

        df["date"] = df[
            "assigned_at"
        ].dt.strftime(
            "%Y-%m-%d"
        )


        # --------------------------------------------------
        # Separate TIME
        # --------------------------------------------------

        df["time"] = df[
            "assigned_at"
        ].dt.strftime(
            "%H:%M:%S"
        )


        # --------------------------------------------------
        # Remove original assigned_at
        # --------------------------------------------------

        df.drop(
            columns=["assigned_at"],
            inplace=True
        )

        # ======================================================
        # SORT BY DATE AND TIME
        # ======================================================

        df["_sort_datetime"] = pd.to_datetime(
            df["date"] + " " + df["time"],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce"
        )

        df = df.sort_values(
            by="_sort_datetime",            ascending=False
        )

        # Remove temporary sorting column
        df.drop(
            columns=["_sort_datetime"],
            inplace=True
        )

        # Reset index
        df.reset_index(
            drop=True,
            inplace=True
        )
    # ======================================================
    # 15. REORDER COLUMNS
    # ======================================================

    required_columns = [
        "meter_id",
        "hhid",
        "region",
        "date",
        "time"
    ]


    # Keep only columns that exist
    final_columns = [
        column
        for column in required_columns
        if column in df.columns
    ]


    df = df[
        final_columns
    ]


    # ======================================================
    # 16. SAVE CSV
    # ======================================================

    df.to_csv(
        output_path,
        index=False
    )


    print(
        "\nCSV successfully created."
    )

    print(
        f"Saved at:\n{output_path}"
    )


    # ======================================================
    # 17. SUMMARY
    # ======================================================

    print(
        "\n" + "=" * 70
    )

    print(
        "DOWNLOAD SUMMARY"
    )

    print(
        "=" * 70
    )


    print(
        f"Execution Date        : "
        f"{today.strftime('%d-%m-%Y %H:%M:%S')}"
    )

    print(
        f"Filename D-1 Date     : "
        f"{d_minus_1_str}"
    )

    print(
        f"Total mappings        : "
        f"{len(df)}"
    )


    if not df.empty:

        print(
            f"Unique meter IDs      : "
            f"{df['meter_id'].nunique()}"
        )

        print(
            f"Unique HHIDs          : "
            f"{df['hhid'].nunique()}"
        )


    print(
        f"Output file           : "
        f"{output_filename}"
    )

    print(
        f"Output folder         : "
        f"{OUTPUT_FOLDER}"
    )


    print(
        "=" * 70
    )


except Exception as e:

    print(
        "\nERROR:"
    )

    print(
        str(e)
    )


finally:

    if connection is not None:

        connection.close()

        print(
            "\nDatabase connection closed."
        )
