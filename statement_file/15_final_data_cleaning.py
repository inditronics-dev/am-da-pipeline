import io
import os
import sys
import time
from datetime import datetime, timedelta

import boto3
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

SCRIPT_START = time.time()


def banner(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def mask(value):
    """Show only the first 4 chars of a secret so we can confirm it loaded."""
    if not value:
        return "NOT SET"
    return value[:4] + "*" * 8 + f" (len={len(value)})"


# ===============================
# STEP 1: LOAD .env
# ===============================
banner("STEP 1: LOADING .env")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
print(f"[INFO] SCRIPT_DIR : {SCRIPT_DIR}")
print(f"[INFO] BASE_DIR   : {BASE_DIR}")

env_path = os.path.join(BASE_DIR, ".env")
print(f"[INFO] Looking for .env at: {env_path}  -> exists: {os.path.exists(env_path)}")

loaded_base = load_dotenv(env_path)
loaded_cwd = load_dotenv()
print(f"[INFO] load_dotenv(BASE_DIR/.env) returned: {loaded_base}")
print(f"[INFO] load_dotenv(auto-find)      returned: {loaded_cwd}")

S3_BUCKET = os.getenv("S3_OUTPUT_BUCKET")
S3_PREFIX = os.getenv("S3_OUTPUT_PREFIX2", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_REGION = os.getenv("S3_REGION", "ap-south-1")  # note: no trailing comma

print(f"[INFO] S3_OUTPUT_BUCKET  : {S3_BUCKET}")
print(f"[INFO] S3_OUTPUT_PREFIX2 : {S3_PREFIX!r}")
print(f"[INFO] S3_ACCESS_KEY     : {mask(S3_ACCESS_KEY)}")
print(f"[INFO] S3_SECRET_KEY     : {mask(S3_SECRET_KEY)}")
print(f"[INFO] S3_REGION         : {S3_REGION!r}")

if not S3_BUCKET:
    print("[ERROR] S3_OUTPUT_BUCKET is not set in .env. Stopping.")
    sys.exit(1)
if not S3_ACCESS_KEY or not S3_SECRET_KEY:
    print("[ERROR] S3_ACCESS_KEY / S3_SECRET_KEY not found in .env. Stopping.")
    sys.exit(1)

# ===============================
# STEP 2: DATES AND FILE PATHS
# ===============================
banner("STEP 2: DATES AND FILE PATHS")

run_date_env = os.environ.get("RUN_DATE")
run_date = run_date_env

if not run_date:
    run_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"[INFO] RUN_DATE env not set -> defaulting to yesterday: {run_date}")
else:
    print(f"[INFO] RUN_DATE taken from env: {run_date}")

household_date_env = os.environ.get("HOUSEHOLD_DATE")
household_date = household_date_env or (
    datetime.now() - timedelta(days=1)
).strftime("%Y-%m-%d")
print(f"[INFO] Today               : {datetime.now().strftime('%Y-%m-%d')}")
print(f"[INFO] Household file date (d-1): {household_date}"
      f"{'  (from HOUSEHOLD_DATE env)' if household_date_env else ''}")

INPUT_FILE = os.path.join(BASE_DIR, "statement_file", "qualifier_output", f"{run_date}_ruled_PROCESSED.csv")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "statement_file", "statement")
OUTPUT_FILE_NAME = f"{run_date}_statement.csv"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
print(f"[INFO] INPUT_FILE    : {INPUT_FILE}")
print(f"[INFO] INPUT exists  : {os.path.exists(INPUT_FILE)}")
print(f"[INFO] OUTPUT_FOLDER : {OUTPUT_FOLDER}")
print(f"[INFO] OUTPUT_FILE   : {OUTPUT_FILE_NAME}")

# ===============================
# CHANNEL MAPPING
# ===============================
CHANNEL_MAP = {
    "Shant TV": 3, "ShantTV": 3,
    "MIR TV": 8, "MirTV": 8,
    "Boon Tv": 11, "BoonTV": 11,
    "Nur TV": 98, "NurTV": 98,
    "Shoghakat TV": 98,
    "1st TV channel": 2,
    "FirstNewsChannel": 1,
    "Nor Hayastan": 98, "NorHayastan": 98,
    "First News Channel": 1,
    "Public TV": 2, "PublicTV": 2,
    "Fast Sports": 98, "FastSports": 98,
    "Kentron Tv HD": 5, "KentronTVHD": 5,
    "Free News": 98, "FreeNews": 98,
    "Armenia TV": 4, "ArmeniaTV": 4,
    "TV 5": 12, "TV5": 12,
    "Dar 21 TV": 7, "Dar21TV": 7,
    "A TV": 15, "ATV": 15,
    "Others": 99
}


# ===============================
# FUNCTION: FETCH HOUSEHOLD DETAILS FROM S3
# ===============================
def fetch_household_details(bucket, prefix, date_str):
    """
    Reads  s3://<bucket>/<prefix>/household-details/<date_str>/*.csv
    If several CSVs exist, the most recently modified one is used.
    """
    base_prefix = "/".join(p.strip("/") for p in [prefix, "household-details"] if p) + "/"
    key_prefix = base_prefix + date_str + "/"

    print("[S3] Creating boto3 client...")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
    )
    print("[S3] Client created.")

    print(f"[S3] Bucket     : {bucket}")
    print(f"[S3] Key prefix : {key_prefix}")
    print(f"[S3] Full path  : s3://{bucket}/{key_prefix}*.csv")

    # --- connectivity / permission check
    try:
        s3.head_bucket(Bucket=bucket)
        print("[S3] head_bucket OK -> bucket reachable and credentials accepted.")
    except NoCredentialsError:
        print("[ERROR] No AWS credentials found. Check your .env keys.")
        raise
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        print(f"[WARN] head_bucket failed ({code}): {e}. "
              f"Will still try listing (some roles lack HeadBucket permission).")

    # --- list objects
    print("[S3] Listing objects...")
    all_objects = []
    csv_objects = []
    pages = 0
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
            pages += 1
            for obj in page.get("Contents", []):
                all_objects.append(obj)
                if obj["Key"].lower().endswith(".csv"):
                    csv_objects.append(obj)
    except ClientError as e:
        print(f"[ERROR] Listing failed: {e}")
        raise

    print(f"[S3] Pages fetched       : {pages}")
    print(f"[S3] Objects under prefix: {len(all_objects)}")
    print(f"[S3] CSV objects found   : {len(csv_objects)}")

    for obj in sorted(csv_objects, key=lambda o: o["LastModified"]):
        print(f"[S3]    - {obj['Key']}  |  {obj['Size']:,} bytes  |  "
              f"modified {obj['LastModified']}")

    if not csv_objects:
        print(f"[ERROR] No CSV found at s3://{bucket}/{key_prefix}")
        # Help debugging: show which date folders actually exist
        print(f"[DEBUG] Listing available date folders under s3://{bucket}/{base_prefix} ...")
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=base_prefix, Delimiter="/")
            folders = [cp["Prefix"] for cp in resp.get("CommonPrefixes", [])]
            if folders:
                for f in folders[-15:]:
                    print(f"[DEBUG]    {f}")
                print(f"[DEBUG] (showing last {min(15, len(folders))} of {len(folders)} folders)")
            else:
                print("[DEBUG] No folders found under that prefix. "
                      "Check S3_OUTPUT_PREFIX2 and the 'household-details' folder name.")
        except ClientError as e:
            print(f"[DEBUG] Could not list parent prefix: {e}")
        raise FileNotFoundError(f"No CSV found at s3://{bucket}/{key_prefix}")

    latest = max(csv_objects, key=lambda o: o["LastModified"])
    if len(csv_objects) > 1:
        print(f"[WARN] {len(csv_objects)} CSVs found. Using the most recently modified one.")
    print(f"[S3] Selected file: s3://{bucket}/{latest['Key']}")

    print("[S3] Downloading...")
    t0 = time.time()
    body = s3.get_object(Bucket=bucket, Key=latest["Key"])["Body"].read()
    print(f"[S3] Downloaded {len(body):,} bytes in {time.time() - t0:.2f}s")

    hh = pd.read_csv(io.BytesIO(body))
    print(f"[S3] Parsed into DataFrame: {hh.shape[0]:,} rows x {hh.shape[1]} columns")
    print(f"[S3] Columns: {list(hh.columns)}")
    print("[S3] First 5 rows:")
    print(hh.head())
    return hh


# ===============================
# FUNCTION: ADD TOTAL MEMBERS + FILTER SMALL REJUVENATED HOUSEHOLDS
# ===============================
def filter_small_rejuvenated(df, hh_df):
    required_hh_cols = {"HH Number", "Total Members"}
    missing = required_hh_cols - set(hh_df.columns)
    if missing:
        print(f"[ERROR] Household file is missing columns: {missing}")
        print(f"[ERROR] Available columns: {list(hh_df.columns)}")
        raise KeyError(f"Household file is missing columns: {missing}")

    for col in ("hhid", "Member_Status"):
        if col not in df.columns:
            print(f"[ERROR] Input file is missing column: {col}")
            print(f"[ERROR] Available columns: {list(df.columns)}")
            raise KeyError(f"Input file is missing column: {col}")
    print("[MERGE] Required columns present in both files.")

    # Lookup table: one row per HH Number
    lookup = hh_df[["HH Number", "Total Members"]].copy()
    lookup["HH Number"] = lookup["HH Number"].astype(str).str.strip()
    lookup["Total Members"] = pd.to_numeric(lookup["Total Members"], errors="coerce")

    print(f"[MERGE] Household rows              : {len(lookup):,}")
    print(f"[MERGE] Non-numeric Total Members   : {lookup['Total Members'].isna().sum():,}")
    dup_count = lookup["HH Number"].duplicated().sum()
    print(f"[MERGE] Duplicate HH Number rows    : {dup_count:,}"
          f"{'  (keeping last of each)' if dup_count else ''}")
    lookup = lookup.drop_duplicates(subset="HH Number", keep="last")
    print(f"[MERGE] Unique HH Numbers in lookup : {len(lookup):,}")

    # Key check
    hhid_key = df["hhid"].astype(str).str.strip()
    print(f"[MERGE] Sample input hhid values      : {hhid_key.head(5).tolist()}")
    print(f"[MERGE] Sample household HH Numbers   : {lookup['HH Number'].head(5).tolist()}")
    print(f"[MERGE] Unique hhid in input          : {hhid_key.nunique():,}")

    overlap = len(set(hhid_key.unique()) & set(lookup["HH Number"].unique()))
    print(f"[MERGE] hhid values found in HH Number: {overlap:,} of {hhid_key.nunique():,}")
    if overlap == 0:
        print("[WARN] ZERO overlap between hhid and HH Number! "
              "Check formats (leading zeros, prefixes, decimals like '123.0').")

    # Map
    df["Total Members"] = hhid_key.map(lookup.set_index("HH Number")["Total Members"])

    matched_rows = df["Total Members"].notna().sum()
    unmatched_rows = df["Total Members"].isna().sum()
    print(f"[MERGE] Input rows with Total Members : {matched_rows:,}")
    print(f"[MERGE] Input rows with NO match      : {unmatched_rows:,} (these are kept)")
    print("[MERGE] Total Members distribution (input rows):")
    print(df["Total Members"].value_counts(dropna=False).sort_index().head(15).to_string())

    # Member_Status overview
    print("[FILTER] Member_Status distribution before filtering:")
    print(df["Member_Status"].value_counts(dropna=False).to_string())

    is_rejuvenated = (
        df["Member_Status"].astype(str).str.strip().str.lower() == "rejuvenated"
    )
    is_small = df["Total Members"] < 3  # NaN < 3 is False -> unmatched rows kept
    to_remove = is_rejuvenated & is_small

    print(f"[FILTER] Rows with Member_Status == Rejuvenated   : {is_rejuvenated.sum():,}")
    print(f"[FILTER] Rows with Total Members < 3              : {is_small.sum():,}")
    print(f"[FILTER] Rows matching BOTH (will be removed)     : {to_remove.sum():,}")
    print(f"[FILTER] Unique households being removed          : "
          f"{df.loc[to_remove, 'hhid'].nunique():,}")

    if to_remove.any():
        print("[FILTER] Sample of rows being removed:")
        print(df.loc[to_remove, ["hhid", "Member_Status", "Total Members"]].drop_duplicates().head(10))

    before_rows = len(df)
    df = df[~to_remove].copy()
    print(f"[FILTER] Rows before: {before_rows:,} | after: {len(df):,} | "
          f"removed: {before_rows - len(df):,}")

    df = df.drop(columns=["Total Members", "Member_Status"])
    print("[FILTER] Dropped helper columns: Total Members, Member_Status")
    return df


# ===============================
# FUNCTION: POPULATE TV_SET
# ===============================
def populate_tv_set(df):
    df["tv_set"] = 1
    print(f"tv_set populated with value 1 for all {len(df):,} rows.")
    return df


# ===============================
# FUNCTION: TIME → SECONDS
# ===============================
def convert_time_to_seconds(time_str):
    h, m, s = map(int, time_str.split(":"))
    seconds = h * 3600 + m * 60 + s

    # If hour is 00 or 01 → next day continuation
    if h in [0, 1]:
        seconds += 86400

    return seconds


# ===============================
# STEP 3: FETCH HOUSEHOLD DETAILS (S3)
# ===============================
banner("STEP 3: FETCHING HOUSEHOLD DETAILS FROM S3")
household_df = fetch_household_details(S3_BUCKET, S3_PREFIX, household_date)
print("[OK] Household file fetched successfully from S3.")

# ===============================
# STEP 4: READ INPUT FILE
# ===============================
banner("STEP 4: READING INPUT FILE")
if not os.path.exists(INPUT_FILE):
    print(f"[ERROR] Input file not found: {INPUT_FILE}")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE)
print(f"[INPUT] Loaded {len(df):,} rows x {df.shape[1]} columns")
print(f"[INPUT] Columns: {list(df.columns)}")
print("[INPUT] First 5 rows:")
print(df.head())
print(f"[INPUT] Null counts (non-zero only):")
nulls = df.isna().sum()
print(nulls[nulls > 0].to_string() if (nulls > 0).any() else "none")

# ===============================
# STEP 5: MAP TOTAL MEMBERS + DROP SMALL REJUVENATED HOUSEHOLDS
# ===============================
banner("STEP 5: MAP TOTAL MEMBERS + FILTER SMALL REJUVENATED HOUSEHOLDS")
df = filter_small_rejuvenated(df, household_df)
print(f"[OK] Rows remaining after household filter: {len(df):,}")
print(f"[OK] Columns now: {list(df.columns)}")

# ===============================
# STEP 6: START TIME → SECONDS
# ===============================
banner("STEP 6: START TIME -> SECONDS")
if "start_time_secs" in df.columns:
    print("[INFO] Existing start_time_secs column found -> dropping and recalculating.")
    df = df.drop(columns=["start_time_secs"])

df["start_time_secs"] = df["start_time"].apply(convert_time_to_seconds)

print("Start time converted to seconds.")
print(df[["start_time", "start_time_secs"]].head())
print(f"[INFO] start_time_secs min: {df['start_time_secs'].min():,} | "
      f"max: {df['start_time_secs'].max():,}")

# ===============================
# STEP 7: CLEAN + MAP CHANNEL
# ===============================
banner("STEP 7: CLEAN + MAP CHANNEL")
df["channel"] = df["channel"].astype(str).str.strip()

df["channelid"] = df["channel"].map(CHANNEL_MAP)

unmapped = df.loc[df["channelid"].isna(), "channel"].value_counts()
print(f"[INFO] Rows with unmapped channel (will become 99): {int(unmapped.sum()):,}")
if len(unmapped):
    print("[INFO] Unmapped channel names:")
    print(unmapped.to_string())

# Fill unknown as 99
df["channelid"] = df["channelid"].fillna(99).astype(int)

print("Channel mapping completed.")
print("[INFO] channelid distribution:")
print(df["channelid"].value_counts().sort_index().to_string())

# ===============================
# STEP 8: REMOVE UNWANTED CHANNELIDS
# ===============================
banner("STEP 8: REMOVE UNWANTED CHANNELIDS")
initial_rows = len(df)

df = df[~df["channelid"].isin([])]

print(f"Rows removed: {initial_rows - len(df)}")
print(f"[INFO] Rows remaining: {len(df):,}")

# ===============================
# STEP 9: REMOVE SESSIONS LESS THAN 5 SEC
# ===============================
banner("STEP 9: REMOVE SESSIONS < 5 SEC")
if "duration_seconds" in df.columns:

    before_rows = len(df)

    df = df[df["duration_seconds"].fillna(0) >= 5]

    print(
        f"Rows removed (duration_seconds < 5 sec): "
        f"{before_rows - len(df):,}"
    )
    print(f"[INFO] Rows remaining: {len(df):,}")

else:
    print("duration_seconds column not found. Skipping filter.")

# ===============================
# STEP 10: DATE FORMAT CONVERSION
# ===============================
banner("STEP 10: DATE FORMAT CONVERSION")
print(f"[INFO] Sample date values before: {df['date'].head(3).tolist()}")
df["date"] = pd.to_datetime(df["date"], errors="coerce")
bad_dates = df["date"].isna().sum()
print(f"[INFO] Unparseable dates (NaT): {bad_dates:,}")
df["date"] = df["date"].dt.strftime("%-m/%-d/%Y")

print("Date format conversion complete.")
print(f"[INFO] Sample date values after : {df['date'].head(3).tolist()}")

# ===============================
# STEP 11: POPULATE TV_SET
# ===============================
banner("STEP 11: POPULATE TV_SET")
df = populate_tv_set(df)

# ===============================
# STEP 12: SAVE OUTPUT
# ===============================
banner("STEP 12: SAVE OUTPUT")
output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE_NAME)
df.to_csv(output_path, index=False)

print("Final file saved at:", output_path)
print(f"[OK] Final shape  : {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"[OK] Final columns: {list(df.columns)}")
print(f"[OK] File size    : {os.path.getsize(output_path):,} bytes")
print("[OK] Final 5 rows:")
print(df.head())

banner(f"DONE in {time.time() - SCRIPT_START:.1f}s")