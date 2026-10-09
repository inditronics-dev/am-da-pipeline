import os
import zipfile
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# ==========================================================
# PATH CONFIG
# ==========================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_DIR = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..")
)

ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

# ==========================================================
# DATABASE CONFIG
# ==========================================================

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# ==========================================================
# D-1 REPORTING DATE
# ==========================================================

START_DATE = (
    datetime.now() - timedelta(days=1)
).strftime("%Y-%m-%d")

# ==========================================================
# OUTPUT DIRECTORY
# ==========================================================

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "sessions",
    "logo",
    "logo_events"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================================
# ARMENIA TIMEZONE
# ==========================================================

ARMENIA_TZ = pytz.timezone("Asia/Yerevan")

# ==========================================================
# CREATE REPORTING DAY
#
# Start : D-1 02:00:00
# End   : D 01:59:59
# ==========================================================

report_date = datetime.strptime(
    START_DATE,
    "%Y-%m-%d"
)

start_local = ARMENIA_TZ.localize(
    datetime.combine(
        report_date.date(),
        datetime.min.time()
    )
).replace(
    hour=2,  minute=0,  second=0
)

end_local = (
    start_local + timedelta(days=1) - timedelta(seconds=1)
)

# ==========================================================
# CREATED AT CUTOFF
# END + 6 HOURS
# ==========================================================

created_at_limit_utc = (
    end_local.astimezone(pytz.UTC)
    + timedelta(hours=6)
)

# Convert cutoff back to Armenia local time for display
created_at_limit_armenia = (
    created_at_limit_utc.astimezone(ARMENIA_TZ)
)

created_at_limit_str = created_at_limit_armenia.strftime(
    "%Y-%m-%d %H:%M:%S%z"
)

# ==========================================================
# CONVERT TO UTC EPOCH
# ==========================================================

start_epoch = int(
    start_local
    .astimezone(pytz.UTC)
    .timestamp()
)

end_epoch = int(
    end_local
    .astimezone(pytz.UTC)
    .timestamp()
)

# ==========================================================
# DISPLAY INFORMATION
# ==========================================================

print("\n" + "=" * 70)
print("DYNAMIC LOGO EVENTS EXTRACTION")
print("=" * 70)

print( f"Reporting Date (D-1) : {START_DATE}" )
print("\nArmenia Reporting Time")
print("-" * 70)

print(
    f"Start : "
    f"{start_local.strftime('%Y-%m-%d %H:%M:%S %Z (%z)')}"
)

print(
    f"End   : "
    f"{end_local.strftime('%Y-%m-%d %H:%M:%S %Z (%z)')}"
)

print("\nUTC Time")
print("-" * 70)

print(
    f"Start : "
    f"{start_local.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}"
)

print(
    f"End   : "
    f"{end_local.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}"
)

print("\nEpoch Timestamp")
print("-" * 70)
print(f"Start Epoch : {start_epoch}")
print(f"End Epoch   : {end_epoch}")
print("\nCreatedAt Cutoff")
print("-" * 70)
print( f"CreatedAt <= {created_at_limit_str}" )

print("\nOutput Directory")
print("-" * 70)
print(OUTPUT_DIR)
print("=" * 70)

# ==========================================================
# QUERY
# ==========================================================

query = f"""
SELECT v.*, e."createdAt"
FROM events_with_assigned_hhid v
INNER JOIN events e
    ON v.id = e.id
WHERE v.type IN ('29','30','23','3','4')
  AND v.timestamp BETWEEN {start_epoch} AND {end_epoch}
  AND e."createdAt" <= TIMESTAMPTZ '{created_at_limit_str}'
ORDER BY v.hhid ASC, v.timestamp ASC;
"""

# ==========================================================
# VALIDATE DATABASE CONFIG
# ==========================================================

required_db_values = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}

missing_values = [
    key
    for key, value in required_db_values.items()
    if not value
]

if missing_values:
    raise ValueError(
        "Missing database configuration in .env: "
        + ", ".join(missing_values)
    )

# ==========================================================
# CREATE DATABASE CONNECTION
# ==========================================================

engine = create_engine(
    f"postgresql+psycopg2://"
    f"{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ==========================================================
# FILE NAMES
# ==========================================================

date_for_filename = report_date.strftime("%d-%m-%Y")

csv_file = os.path.join(
    OUTPUT_DIR,
    f"{date_for_filename}_logo_events.csv"
)

zip_file = os.path.join(
    OUTPUT_DIR,
    f"{date_for_filename}_logo_events.zip"
)

# ==========================================================
# EXECUTE QUERY
# ==========================================================

try:

    print("\nConnecting to database...")

    with engine.connect() as connection:

        df = pd.read_sql(
            query,
            connection
        )

    print( f"Downloaded {len(df):,} rows." )

    print( f"Columns: {len(df.columns)}" )

    # ======================================================
    # SAVE CSV
    # ======================================================

    print("\nSaving CSV...")

    df.to_csv( csv_file, index=False )

    csv_size_mb = os.path.getsize(csv_file) / (
        1024 * 1024
    )

    print( f"CSV saved successfully: {csv_file}" )

    print(csv_file)

    print( f"CSV Size: {csv_size_mb:.2f} MB" )

    # ======================================================
    # CREATE ZIP
    # ======================================================

    print("\nCreating ZIP file...")

    with zipfile.ZipFile(
        zip_file,
        mode="w",
        compression=zipfile.ZIP_DEFLATED
    ) as zipf:

        zipf.write(
            csv_file,
            arcname=os.path.basename(csv_file)
        )

    zip_size_mb = os.path.getsize(zip_file) / (
        1024 * 1024
    )

    print( f"ZIP created successfully: {zip_file}" )

    print( f"ZIP Size: {zip_size_mb:.2f} MB" )

    # ======================================================
    # DELETE CSV AFTER SUCCESSFUL ZIP
    # ======================================================

    if os.path.exists(zip_file):

        os.remove(csv_file)

        print( "\nOriginal CSV deleted successfully." )

    # ======================================================
    # FINAL STATUS
    # ======================================================

    print("\n" + "=" * 70)
    print("PROCESS COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print( f"Reporting Date : {date_for_filename}" )

    print( f"Rows           : {len(df):,}" )

    print( f"CSV Size       : {csv_size_mb:.2f} MB" )       
    
    print( f"ZIP Size       : {zip_size_mb:.2f} MB" )

    print( f"Final File     : {zip_file}" )

    print("=" * 70)

except Exception as e:

    print("\n" + "=" * 70)
    print("PROCESS FAILED")
    print("=" * 70)

    print(
        f"Error: {e}"
    )

    # If CSV exists but ZIP was not successfully created,
    # keep the CSV so no downloaded data is lost.
    print(
        "\nCSV has NOT been deleted because the process failed."
    )

    print("=" * 70)

finally:

    engine.dispose()

    print("\nDatabase connection closed.")

