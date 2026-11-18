import pandas as pd
import glob
import os
import re
from datetime import datetime, timedelta
from typing import List
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

# ============================================================
# CONFIG
# ============================================================

# Get project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# ============================================================
# DB CONFIG
# ============================================================

ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

run_date = os.environ.get("RUN_DATE")

if not run_date:
    run_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

run_date_obj = datetime.strptime(run_date, "%Y-%m-%d").date()

INPUT_DIR = os.path.join(BASE_DIR, "sessions", "merging", "Final_merged_file")
INPUT_PATTERN = "*.csv"
OUTPUT_DIR = os.path.join(BASE_DIR, "for_panel_files", "for_panel")

# The mapping workbook is stored alongside the merged files.
MAPPING_FILE = os.path.join(
    BASE_DIR,
    "sessions",
    "merging",
    "HHID_Mapping_Script.xlsx",
)

# Channel IDs to remove
CHANNELS_TO_REMOVE = {9, 99}

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# Helper: convert HH:MM:SS(.ms) to reporting-day seconds
# ============================================================

def time_to_seconds(t):
    try:
        if pd.isna(t):
            return None

        h, m, s = str(t).split(":")
        secs = int(h) * 3600 + int(m) * 60 + float(s)

        # Reporting day: 2 AM to 2 AM
        if secs < 7200:
            secs += 86400

        return int(secs)
    except Exception:
        return None


# ============================================================
# Calculate session duration
# ============================================================

def calculate_duration(df):
    if {"date", "start_time", "end_time"}.issubset(df.columns):
        df["start_dt"] = pd.to_datetime(
            df["date"].astype(str) + " " + df["start_time"].astype(str),
            errors="coerce",
        )

        df["end_dt"] = pd.to_datetime(
            df["date"].astype(str) + " " + df["end_time"].astype(str),
            errors="coerce",
        )

        # If the session crossed midnight
        df.loc[df["end_dt"] < df["start_dt"], "end_dt"] += timedelta(days=1)

        df["duration_seconds"] = (
            df["end_dt"] - df["start_dt"]
        ).dt.total_seconds()

        # Remove invalid durations
        df = df[df["duration_seconds"] > 0]

    return df


# ============================================================
# Shift values from s3_date to date and chname to channel
# ============================================================

def shift_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Shift s3_date to date and chname to channel before other processing."""
    print("    Shifting column values (s3_date to date, chname to channel)...")

    if "s3_date" in df.columns:
        if "date" in df.columns:
            s3_date_valid = (
                df["s3_date"].notna()
                & (df["s3_date"].astype(str).str.strip() != "")
            )
            df.loc[s3_date_valid, "date"] = df.loc[s3_date_valid, "s3_date"]
            print(
                f"       Shifted {s3_date_valid.sum()} value(s) "
                "from s3_date to date"
            )
        else:
            df["date"] = df["s3_date"]
            print(
                f"       Created date column with "
                f"{df['s3_date'].notna().sum()} value(s) from s3_date"
            )
    else:
        print("       s3_date column not found")

    if "chname" in df.columns:
        if "channel" in df.columns:
            chname_valid = (
                df["chname"].notna()
                & (df["chname"].astype(str).str.strip() != "")
            )
            df.loc[chname_valid, "channel"] = df.loc[chname_valid, "chname"]
            print(
                f"       Shifted {chname_valid.sum()} value(s) "
                "from chname to channel"
            )
        else:
            df["channel"] = df["chname"]
            print(
                f"       Created channel column with "
                f"{df['chname'].notna().sum()} value(s) from chname"
            )
    else:
        print("       chname column not found")

    return df


# ============================================================
# Channel mapping
# ============================================================

CHANNEL_MAP = {
    "Shant TV": 3,
    "ShantTV": 3,
    "MIR TV": 8,
    "MirTV": 8,
    "Boon Tv": 11,
    "BoonTV": 11,
    "Nur TV": 10,
    "NurTV": 10,
    "Shoghakat TV": 9,
    "1st TV channel": 2,
    "FirstNewsChannel": 1,
    "Nor Hayastan": 13,
    "NorHayastan": 13,
    "First News Channel": 1,
    "Public TV": 2,
    "PublicTV": 2,
    "Fast Sports": 6,
    "FastSports": 6,
    "Kentron Tv HD": 5,
    "KentronTVHD": 5,
    "Free News": 14,
    "FreeNews": 14,
    "Armenia TV": 4,
    "ArmeniaTV": 4,
    "TV 5": 12,
    "TV5": 12,
    "Dar 21 TV": 7,
    "Dar21TV": 7,
    "A TV": 15,
    "ATV": 15,
    "Others": 99,
}

CHANNEL_MAP_NORM = {key.strip().lower(): value for key, value in CHANNEL_MAP.items()}


# ============================================================
# File date utilities
# ============================================================

DATE_REGEX = re.compile(r"(\d{4}-\d{2}-\d{2})")


def extract_date_from_filename(filename: str):
    match = DATE_REGEX.search(filename)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def get_files_in_date_range(start_date, end_date) -> List[str]:
    files = glob.glob(os.path.join(INPUT_DIR, INPUT_PATTERN))
    selected = []

    for file_path in files:
        file_date = extract_date_from_filename(os.path.basename(file_path))
        if file_date and start_date <= file_date <= end_date:
            selected.append(file_path)

    return sorted(selected)


def prompt_date(prompt_text: str):
    while True:
        value = input(prompt_text).strip()
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD")


# ============================================================
# Household and member lookup utilities
# ============================================================

def normalize_id(series: pd.Series) -> pd.Series:
    """Normalize IDs for matching while preserving their string values."""
    return series.astype("string").str.strip().str.casefold()


def get_production_hhids() -> set[str]:
    engine = create_engine(
        URL.create(
            "postgresql+psycopg2",
            username=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
        )
    )

    query = text("""
        SELECT DISTINCT hhid
        FROM households
        WHERE current_status = 'PRODUCTION'
        ORDER BY hhid
    """)

    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            return {
                str(row.hhid).strip().casefold()
                for row in result
                if row.hhid is not None
            }
    finally:
        engine.dispose()


def get_under_3_member_keys(mapping_file: str) -> set[tuple[str, str]]:
    """
    Return normalized (hhid, member_code) pairs for mapped members younger
    than 3 years old.
    """
    if not os.path.isfile(mapping_file):
        raise FileNotFoundError(
            f"HHID mapping workbook not found: {mapping_file}"
        )

    mapping = pd.read_excel(mapping_file)

    required_columns = {"hhid", "member_code", "age"}
    missing_columns = required_columns - set(mapping.columns)
    if missing_columns:
        raise ValueError(
            "Missing required column(s) in mapping workbook: "
            f"{', '.join(sorted(missing_columns))}"
        )

    ages = pd.to_numeric(mapping["age"], errors="coerce")
    under_3 = mapping.loc[ages < 3, ["hhid", "member_code"]].dropna()

    return {
        (str(row.hhid).strip().casefold(),
         str(row.member_code).strip().casefold())
        for row in under_3.itertuples(index=False)
        if str(row.hhid).strip() and str(row.member_code).strip()
    }


# ============================================================
# Core processing
# ============================================================

def process_file(
    file_path: str,
    production_hhids: set[str],
    under_3_member_keys: set[tuple[str, str]],
):
    print(f"\nProcessing: {file_path}")

    df = pd.read_csv(file_path)
    original_rows = len(df)

    # Shift values before other processing
    df = shift_columns(df)

    # 1. Assign channel ID
    df["channelid"] = (
        df["channel"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(CHANNEL_MAP_NORM)
        .fillna(99)
        .astype(int)
    )

    # 2. Remove unwanted channel IDs
    removed_channel_count = df["channelid"].isin(CHANNELS_TO_REMOVE).sum()
    df = df[~df["channelid"].isin(CHANNELS_TO_REMOVE)]

    # 3. Add start_time_secs
    if "start_time" not in df.columns:
        raise ValueError("Missing 'start_time' column")

    df["start_time_secs"] = df["start_time"].apply(time_to_seconds)

    # 4. Remove empty member_id
    if "member_id" in df.columns:
        df = df.dropna(subset=["member_id"])
        df = df[df["member_id"].astype(str).str.strip() != ""]

    # 5. Keep only households currently in PRODUCTION
    if "hhid" not in df.columns:
        raise ValueError("Missing 'hhid' column in input CSV")

    df_hhid = normalize_id(df["hhid"])
    df = df[df_hhid.isin(production_hhids)]

    # 6. Remove rows for mapped members younger than 3
    if "member_id" not in df.columns:
        raise ValueError("Missing 'member_id' column in input CSV")

    df_hhid = normalize_id(df["hhid"])
    df_member = normalize_id(df["member_id"])
    row_keys = list(zip(df_hhid, df_member))

    under_3_mask = pd.Series(
        [key in under_3_member_keys for key in row_keys],
        index=df.index,
    )
    removed_under_3_count = int(under_3_mask.sum())
    df = df[~under_3_mask]

    # 7. Remove channel == "Others"
    df = df[df["channel"] != "Others"]

    cleaned_rows = len(df)

    # Output filename
    if "date" in df.columns and not df["date"].isna().all():
        first_date = df["date"].mode()[0]
        if isinstance(first_date, str):
            try:
                date_obj = datetime.strptime(first_date, "%Y-%m-%d")
                date_str = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                date_str = run_date
        else:
            date_str = run_date
    else:
        date_str = run_date

    output_file = os.path.join(OUTPUT_DIR, f"{date_str}_cleaned.csv")
    df.to_csv(output_file, index=False)

    print(
        f"Rows: {original_rows} -> {cleaned_rows} | "
        f"Removed channel rows: {removed_channel_count} | "
        f"Removed under-3 member rows: {removed_under_3_count} | "
        f"Saved: {output_file}"
    )


# ============================================================
# Main
# ============================================================

def main():
    print("\nAuto-processing D-1 files")

    target_date = run_date_obj
    target_date_str = run_date

    print(f"Target date: {target_date_str}")

    all_files = glob.glob(os.path.join(INPUT_DIR, INPUT_PATTERN))
    files = []

    print(f"\nChecking {len(all_files)} file(s) in {INPUT_DIR}")

    for file_path in all_files:
        filename = os.path.basename(file_path)
        print(f"   Found: {filename}")
        file_date = extract_date_from_filename(filename)

        if file_date == target_date:
            files.append(file_path)
            print(f"       Matched: {filename}")
        elif file_date:
            print(f"       Skipped (date: {file_date})")

    if not files:
        print(f"\nNo files found for {target_date_str}")
        print(f"Expected filename pattern: *{target_date_str}*.csv")
        return

    print(f"\n{len(files)} file(s) found for processing")

    production_hhids = get_production_hhids()
    print(f"Loaded {len(production_hhids)} PRODUCTION household ID(s)")

    under_3_member_keys = get_under_3_member_keys(MAPPING_FILE)
    print(f"Loaded {len(under_3_member_keys)} mapped member key(s) with age under 3")

    for file_path in sorted(files):
        process_file(file_path, production_hhids, under_3_member_keys)

    print(f"\nProcessing for {run_date} completed successfully.")


if __name__ == "__main__":
    main()