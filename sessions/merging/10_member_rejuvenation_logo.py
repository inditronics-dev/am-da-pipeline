
# ============================================================
# FP MEMBER ATTRIBUTION ENGINE (AUTO D-1 VERSION)
# ============================================================

import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta
import psycopg2

# ============================================================
# PATH SETUP (UNCHANGED)
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

FP_INPUT_PATH = os.path.join(BASE_DIR, "sessions", "logo", "household_viewership_memberwise_output")

PANEL_FILE = os.path.join(BASE_DIR, "sessions", "merging", "HHID_Mapping_Script.xlsx")
CVF_FILE   = os.path.join(BASE_DIR, "sessions", "merging", "cvf_table.csv")
DIST_FILE  = os.path.join(BASE_DIR, "sessions", "merging", "distribution_table_backoff_completed.csv")

OUTPUT_PATH = os.path.join(BASE_DIR, "sessions", "merging", "sessions_with_rejuvenation")


# ============================================================
# DATABASE CONNECTION
# ============================================================

DB_HOST = "armenia-db-01.c960kiumy09x.ap-south-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "meter01"
DB_USER = "postgres"
DB_PASSWORD = "inditronics123"


# ============================================================
# DATABASE → HHID MAPPING EXCEL
# ============================================================

QUERY = """
WITH latest_households AS (
    SELECT DISTINCT ON (household_id)
        household_id,
        assigned_by,
        assigned_at
    FROM (
        SELECT DISTINCT ON (ma.meter_id)
            h.hhid AS household_id,
            ma.assigned_by,
            ma.assigned_at
        FROM meter_assignments ma
        JOIN meters m
            ON ma.meter_id = m.id
        JOIN households h
            ON ma.household_id = h.id
        WHERE m.meter_id >= 'IM000101'
          AND m.meter_id <= 'IM000600'
        ORDER BY ma.meter_id, ma.assigned_at DESC
    ) latest_per_meter
    ORDER BY household_id, assigned_at DESC
)
SELECT
    h.hhid,
    m.member_code,
    m.gender,
    h.city,
    h.region,
    DATE_PART('year', AGE(CURRENT_DATE, m.dob)) AS age,
    lh.assigned_by,
    lh.assigned_at
FROM latest_households lh
JOIN households h
    ON h.hhid = lh.household_id
JOIN members m
    ON h.id = m.household_id
ORDER BY
    h.hhid,
    m.member_code;
"""


def create_hhid_mapping_excel():
    """Fetch household/member data and create the mapping Excel."""

    print("Connecting to database...")

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    try:
        df = pd.read_sql_query(QUERY, conn)

    finally:
        conn.close()

    print("Database rows fetched:", len(df))

    # --------------------------------------------------------
    # AGE GROUP
    # --------------------------------------------------------
    def get_age_group(age):
        if pd.isna(age):
            return "Not Found"

        try:
            age = int(age)
        except (TypeError, ValueError):
            return "Not Found"

        if 0 <= age <= 19:
            return "0-19"
        elif 20 <= age <= 49:
            return "20-49"
        elif age >= 50:
            return "50+"
        else:
            return "Not Found"

    df["Age_Group"] = df["age"].apply(get_age_group)

    # --------------------------------------------------------
    # FAMILY SIZE
    # --------------------------------------------------------
    # Count members belonging to each HHID.
    # Example: HHID 1014 has M1, M2, M3, M4, M5 → 5
    df["Family_Size"] = (
        df.groupby("hhid")["member_code"]
          .transform("count")
    )

    # --------------------------------------------------------
    # FAMILY SIZE GROUP
    # --------------------------------------------------------
    def get_family_size_group(size):
        if pd.isna(size):
            return "Not Found"

        if size <= 2:
            return "Small"
        elif size <= 4:
            return "Medium"
        else:
            return "Large"

    df["Family_Size_Group"] = df["Family_Size"].apply(
        get_family_size_group
    )

    # --------------------------------------------------------
    # CITY GROUP
    # --------------------------------------------------------
    def get_city_group(region):
        if pd.isna(region) or str(region).strip() == "":
            return "Not Found"

        region = str(region).strip()

        if region == "Yerevan":
            return "Yerevan"
        elif region == "Not Found":
            return "Not Found"
        else:
            return "Rest of Armenia"

    df["City_Group"] = df["region"].apply(get_city_group)

    # --------------------------------------------------------
    # FINAL COLUMN ORDER
    # --------------------------------------------------------
    df = df[
        [
            "hhid",
            "member_code",
            "gender",
            "city",
            "region",
            "age",
            "assigned_by",
            "assigned_at",
            "Age_Group",
            "Family_Size",
            "Family_Size_Group",
            "City_Group"
        ]
    ]

    # --------------------------------------------------------
    # REMOVE TIMEZONE FROM ALL DATETIME COLUMNS FOR EXCEL
    # --------------------------------------------------------
    for col in df.columns:
        if pd.api.types.is_datetime64tz_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    # Save to the existing mapping Excel path
    df.to_excel(PANEL_FILE, index=False)

    print("HHID mapping Excel created:", PANEL_FILE)
    print("Mapping rows:", len(df))

    return df


# Create/update the mapping Excel before reading it
create_hhid_mapping_excel()

# ============================================================
# D-1 DATE (UNCHANGED)
# ============================================================

run_date = os.environ.get("RUN_DATE")

if not run_date:
    run_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
d1_date = datetime.strptime(run_date, "%Y-%m-%d")
date_str = d1_date.strftime("%Y-%m-%d")

print("Processing D-1 date:", date_str)

# ============================================================
# FILE FETCH (UNCHANGED)
# ============================================================

def get_file_from_folder(folder_path):
    if not os.path.exists(folder_path):
        raise ValueError(f"Folder not found: {folder_path}")

    for f in os.listdir(folder_path):
        if date_str in f:
            return os.path.join(folder_path, f)
    return None

INPUT_FILE = get_file_from_folder(FP_INPUT_PATH)

if not INPUT_FILE:
    raise ValueError(f"FP file not found for {date_str}")

# ============================================================
# OUTPUT SETUP (UNCHANGED)
# ============================================================

os.makedirs(OUTPUT_PATH, exist_ok=True)

OUTPUT_FILE = os.path.join(
    OUTPUT_PATH,
    f"{date_str}_Members_UpdatedLOGO.csv"
)

TXT_OUTPUT_FILE = OUTPUT_FILE.replace(".csv", ".txt")
SUMMARY_TXT_FILE = OUTPUT_FILE.replace(".csv", "_Summary.txt")

# ============================================================
# TIME BAND FUNCTION (UNCHANGED)
# ============================================================

def get_band_ranges(start, end):
    bands = []
    current = start

    while current < end:
        date = current.date()

        day_start = pd.Timestamp(f"{date} 06:00:00")
        prime_start = pd.Timestamp(f"{date} 18:00:00")
        next_midnight = pd.Timestamp(f"{date} 23:59:59") + pd.Timedelta(seconds=1)

        if current < day_start:
            band_end = min(day_start, end)
            band = "Late Night"
        elif current < prime_start:
            band_end = min(prime_start, end)
            band = "Day"
        else:
            band_end = min(next_midnight, end)
            band = "Prime"

        bands.append((current, band_end, band))
        current = band_end

    return bands

from decimal import Decimal, getcontext

getcontext().prec = 28

def deterministic_allocate(total_seconds, shares):

    shares = [Decimal(str(x)) for x in shares]

    total_share = sum(shares)

    if total_share == 0:
        return [0] * len(shares)

    raw = [
        (s / total_share) * Decimal(total_seconds)
        for s in shares
    ]

    alloc = [int(x) for x in raw]

    remaining = total_seconds - sum(alloc)

    remainders = sorted(
        [
            (raw[i] - Decimal(alloc[i]), i)
            for i in range(len(raw))
        ],
        reverse=True
    )

    for _, idx in remainders[:remaining]:
        alloc[idx] += 1

    return alloc

# ============================================================
# LOAD DATA (UNCHANGED)
# ============================================================

df = pd.read_csv(INPUT_FILE)
panel = pd.read_excel(PANEL_FILE)
cvf = pd.read_csv(CVF_FILE)
dist = pd.read_csv(DIST_FILE)

dist["Share"] = dist["Share"].round(5)
dist["New_Share"] = dist["New_Share"].round(5)

df.columns = df.columns.str.strip().str.lower()

# ============================================================
# CLEAN LOOKUPS (FROM NEW LOGIC)
# ============================================================

cvf = cvf[['City_Group','HH_Size_Group','Time_Band','CVF']].drop_duplicates()

panel = panel.rename(columns={
    'member_code': 'member_id',
    'Family_Size_Group': 'HH_Size_Group'
})

panel = panel[['hhid','member_id','Age_Group','gender','HH_Size_Group','City_Group']]

panel['Age_Group'] = panel['Age_Group'].astype(str).str.strip()
panel['gender'] = panel['gender'].astype(str).str.strip().str.capitalize()

dist = dist.rename(columns={'gende': 'gender'})
dist['Age_Group'] = dist['Age_Group'].astype(str).str.strip()
dist['gender'] = dist['gender'].astype(str).str.strip().str.capitalize()

panel = (
    panel
    .sort_values(
        ["hhid", "member_id"],
        kind="mergesort"
    )
    .reset_index(drop=True)
)

cvf = (
    cvf
    .sort_values(
        ["City_Group", "HH_Size_Group", "Time_Band"],
        kind="mergesort"
    )
    .reset_index(drop=True)
)

dist = (
    dist
    .sort_values(
        [
            "City_Group",
            "HH_Size_Group",
            "Time_Band",
            "Age_Group",
            "gender"
        ],
        kind="mergesort"
    )
    .reset_index(drop=True)
)

# ============================================================
# TIME FIX (UNCHANGED)
# ============================================================

df['start_time'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['start_time'].astype(str))
df['end_time'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['end_time'].astype(str))

df.loc[df['end_time'] < df['start_time'], 'end_time'] += pd.Timedelta(days=1)

df['duration_seconds'] = (df['end_time'] - df['start_time']).dt.total_seconds().astype(int)
df = (
    df
    .sort_values(
        ["hhid", "start_time", "end_time"],
        kind="mergesort"
    )
    .reset_index(drop=True)
)

# ============================================================
# SPLIT INTO TIME BANDS (UNCHANGED)
# ============================================================

split_rows = []

for _, r in df.iterrows():
    splits = get_band_ranges(r['start_time'], r['end_time'])

    for s, e, band in splits:
        new_r = r.copy()
        new_r['start_time'] = s
        new_r['end_time'] = e
        new_r['duration_seconds'] = int((e - s).total_seconds())
        new_r['Time_Band'] = band
        split_rows.append(new_r)

df = pd.DataFrame(split_rows)

print("After split rows:", len(df))
# ============================================================
# IDENTIFY MISSING HHIDs (UNCHANGED)
# ============================================================

hh_missing_flag = df.groupby('hhid')['member_id'].apply(lambda x: x.isna().all())
missing_hhids = hh_missing_flag[hh_missing_flag].index

missing_df = df[df['hhid'].isin(missing_hhids)].copy()
valid_df = df[~df['hhid'].isin(missing_hhids)].copy()

# -----------------------------------------
# BEFORE ATTRIBUTION SUMMARY
# -----------------------------------------
hhids_blank_before = set(missing_hhids)
total_blank_before = len(hhids_blank_before)

# ============================================================
# ATTRIBUTION (REPLACED CORE LOGIC)
# ============================================================

output = []
member_time_tracker = {}

for _, r in missing_df.iterrows():

    start = r['start_time']
    end_time = r['end_time']
    hh = r['hhid']

    members = panel[panel['hhid'] == hh]
    members = (
    members
    .sort_values(
        "member_id",
        kind="mergesort"
    )
    .reset_index(drop=True)
    )

    if len(members) == 0:
        output.append(r)
        continue

    city = members['City_Group'].iloc[0]
    size = members['HH_Size_Group'].iloc[0]
    base_total = int(r['duration_seconds'])
    band = r['Time_Band']

    # CVF
    cvf_row = cvf[
        (cvf['City_Group'] == city) &
        (cvf['HH_Size_Group'] == size) &
        (cvf['Time_Band'] == band)
    ]

    cvf_val = round(float(cvf_row.iloc[0]["CVF"]), 2) if len(cvf_row) > 0 else 1.0
    expanded_total = int(base_total * cvf_val)

    # DISTRIBUTION
    d = dist[
        (dist.City_Group == city) &
        (dist.HH_Size_Group == size) &
        (dist.Time_Band == band)
    ]

    if len(d) == 0:
        m = members.iloc[0]
        fallback = r.copy()
        fallback['member_id'] = m['member_id']
        fallback['gender'] = m['gender']
        fallback['Age_Group'] = m['Age_Group']
        fallback['HH_Size_Group'] = size
        fallback['City_Group'] = city
        output.append(fallback)
        continue

    d = d.copy()
    d = (
    d
    .sort_values(
        ["Age_Group", "gender"],
        kind="mergesort"
    )
    .reset_index(drop=True)
    )
    d['New_Share'] = (d['New_Share'] / d['New_Share'].sum()).round(5)

    member_list, share_list, new_share_list = [], [], []

    for _, row_d in d.iterrows():
        seg_members = members[
            (members['Age_Group'] == row_d['Age_Group']) &
            (members['gender'] == row_d['gender'])
        ]

        for _, m in seg_members.iterrows():
            member_list.append(m)
            share_list.append(row_d.get('Share', row_d['New_Share']))
            new_share_list.append(row_d['New_Share'])

    if len(member_list) == 0:
        m = members.iloc[0]
        fallback = r.copy()
        fallback['member_id'] = m['member_id']
        fallback['gender'] = m['gender']
        fallback['Age_Group'] = m['Age_Group']
        fallback['HH_Size_Group'] = size
        fallback['City_Group'] = city
        output.append(fallback)
        continue

    temp_df = pd.DataFrame({
        'member': member_list,
        'share': share_list,
        'new_share': new_share_list
    })

    temp_df = temp_df[temp_df['new_share'] > 0]

    if len(temp_df) == 0:
        continue

    positive_count = len(temp_df)
    active_count = max(1, int(round(cvf_val)))
    active_count = min(active_count, positive_count)

    temp_df = (
    temp_df
    .sort_values(
        ["new_share", "share"],
        ascending=[False, False],
        kind="mergesort"
    )
    .reset_index(drop=True)
    )

    temp_df = temp_df.head(active_count)

    member_list = temp_df['member'].tolist()
    share_list = temp_df['share'].tolist()
    new_share_list = temp_df['new_share'].tolist()

    alloc = deterministic_allocate(
        expanded_total,
        new_share_list
    )

    rank_order = sorted(range(len(new_share_list)), key=lambda x: new_share_list[x], reverse=True)

    session_duration = int((end_time - start).total_seconds())

    for i in range(len(alloc)):

        dur = alloc[i]
        if dur <= 0:
            continue

        m = member_list[i]
        key = (hh, m['member_id'])

        current_total = member_time_tracker.get(key, 0)
        remaining_allowed = 86400 - current_total

        if remaining_allowed <= 0:
            continue

        final_sec = min(dur, remaining_allowed, session_duration)
        member_time_tracker[key] = current_total + final_sec

        rank = rank_order.index(i)

        if rank == 0:
            member_start, member_end = start, end_time
        else:
            
            member_key = str(m["member_id"])

            hash_value = int(
                hashlib.md5(member_key.encode("utf-8")).hexdigest(),
                16
            )

            shift = (hash_value % 60) * (
                -1 if hash_value % 2 == 0 else 1
            )
            center = start + timedelta(seconds=(session_duration / 2) + shift)

            member_start = center - timedelta(seconds=final_sec / 2)
            member_end = member_start + timedelta(seconds=final_sec)

            if member_start < start:
                member_start = start
                member_end = start + timedelta(seconds=final_sec)

            if member_end > end_time:
                member_end = end_time
                member_start = end_time - timedelta(seconds=final_sec)

        new_row = r.copy()

        new_row['start_time'] = member_start
        new_row['end_time'] = member_end

        actual_sec = int((member_end - member_start).total_seconds())

        new_row['duration_seconds'] = actual_sec
        new_row['duration'] = str(timedelta(seconds=actual_sec))

        new_row['member_id'] = m['member_id']
        new_row['gender'] = m['gender']
        new_row['Age_Group'] = m['Age_Group']
        new_row['HH_Size_Group'] = size
        new_row['City_Group'] = city
        new_row['Time_Band'] = band
        new_row['CVF'] = cvf_val
        new_row['Share'] = share_list[i]
        new_row['New_Share'] = new_share_list[i]

        output.append(new_row)

# ============================================================
# FINAL OUTPUT (UNCHANGED)
# ============================================================

final_missing = pd.DataFrame(output)
final = pd.concat([valid_df, final_missing], ignore_index=True)

final['duration'] = final['duration_seconds'].apply(
    lambda x: str(timedelta(seconds=int(x)))
)

final['start_time'] = final['start_time'].dt.strftime('%H:%M:%S')
final['end_time'] = final['end_time'].dt.strftime('%H:%M:%S')

final = (
    final
    .sort_values(
        ["hhid", "start_time", "end_time", "member_id"],
        kind="mergesort"
    )
    .reset_index(drop=True)
)

# ============================================================
# SUMMARY REPORT
# ============================================================

# HHIDs still having all member_id blank
still_blank_flag = final.groupby("hhid")["member_id"].apply(lambda x: x.isna().all())
hhids_still_blank = set(still_blank_flag[still_blank_flag].index)

# HHIDs successfully filled
hhids_filled = hhids_blank_before - hhids_still_blank

with open(SUMMARY_TXT_FILE, "w", encoding="utf-8") as f:

    # -----------------------------------------
    # HHIDs 100% Blank Before
    # -----------------------------------------
    f.write(f"HHIDs 100% blank BEFORE : {len(hhids_blank_before)}\n")

    for hhid in sorted(hhids_blank_before):
        f.write(f"{hhid}\n")

    f.write(f"Total blank BEFORE      : {len(hhids_blank_before)}\n\n")

    # -----------------------------------------
    # HHIDs Filled
    # -----------------------------------------
    f.write(f"HHIDs FILLED            : {len(hhids_filled)}\n")

    for hhid in sorted(hhids_filled):
        f.write(f"{hhid}\n")

    f.write(f"Total filled            : {len(hhids_filled)}\n\n")

    # -----------------------------------------
    # HHIDs Still Blank
    # -----------------------------------------
    f.write(f"HHIDs STILL BLANK       : {len(hhids_still_blank)}\n")

    for hhid in sorted(hhids_still_blank):
        f.write(f"{hhid}\n")

    f.write(f"Total still blank       : {len(hhids_still_blank)}\n")

final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("FINAL DONE:", final.shape)



