# =========================================================
# INSTALL REQUIRED PACKAGES
# =========================================================
# pip install pandas openpyxl

# =========================================================
# IMPORT LIBRARIES
# =========================================================
import pandas as pd
import os
import re
import sys
from file_path import *
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font



# =========================================================
# CONSTANTS
# =========================================================

VALID_MEMBER_IDS = [
    "M1", "M2", "M3", "M4",
    "M5", "M6", "M7", "M8"
]

# Channels that should NOT appear in the final statement file
REMOVE_CHANNELS = [
    6, 9, 10, 13, 14
]

# National channels - these should NOT be clipped
# =========================================================
# NATIONAL CHANNELS (All Name Variants)
# =========================================================
NATIONAL_CHANNELS = {

    "A TV",
    "ATV",

    "Armenia TV",
    "ArmeniaTV",

    "Shant TV",
    "ShantTV",

    "First News Channel",
    "FirstNewsChannel",

    "Public TV",
    "PublicTV",

    "Kentron Tv HD",
    "KentronTVHD",
}

# =========================================================
# GET PROCESS DATE (D-1 from main pipeline)
# =========================================================
from datetime import datetime, timedelta

run_date = (
    os.environ.get("RUN_DATE")
    or os.environ.get("WORKFLOW_DATE")
)

# If running outside the pipeline, default to D-1
if not run_date:
    run_date = (
        datetime.now() - timedelta(days=1)
    ).strftime("%Y-%m-%d")

# Convert YYYY-MM-DD -> DD-MM-YYYY
process_date = datetime.strptime(
    run_date,
    "%Y-%m-%d"
).strftime("%d-%m-%Y")

input_date = datetime.strptime(
    process_date,
    "%d-%m-%Y"
)

yyyy_mm_dd = input_date.strftime("%Y-%m-%d")

# =========================================================
# GENERATE FILE PATHS
# =========================================================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

RULE_FOLDER = os.path.join(
    BASE_DIR,
    "statement_file",
    "qualifier_output"
)

STATEMENT_FOLDER = os.path.join(
    BASE_DIR,
    "statement_file",
    "statement"
)

PANEL_FOLDER = os.path.join(
    BASE_DIR,
    "Panel",
    "Panel Files"
)

RULES_INPUT_FILE = os.path.join(
    PANEL_FOLDER,
     f"{process_date}_combined_weighted.csv"
)

RULES_OUTPUT_FILE = os.path.join(
    RULE_FOLDER,
    f"{yyyy_mm_dd}_ruled.csv"
)

CLIPPING_INPUT_FILE = RULES_OUTPUT_FILE

CLIPPING_OUTPUT_FILE = os.path.join(
    RULE_FOLDER,
    f"{yyyy_mm_dd}_ruled_PROCESSED.csv"
)

STATEMENT_OUTPUT_FILE = os.path.join(
    STATEMENT_FOLDER,
    f"{yyyy_mm_dd}_statement.csv"
)

# =========================================================
# READ FILES
# =========================================================

required_files = [
    RULES_INPUT_FILE,
    RULES_OUTPUT_FILE,
    CLIPPING_OUTPUT_FILE,
    STATEMENT_OUTPUT_FILE
]

missing = [
    os.path.basename(f)
    for f in required_files
    if not os.path.exists(f)
]

if missing:
    raise FileNotFoundError(
        f"Missing Files: {', '.join(missing)}"
    )

rules_input_df = pd.read_csv(RULES_INPUT_FILE)

rules_output_df = pd.read_csv(RULES_OUTPUT_FILE)

clip_input_df = pd.read_csv(CLIPPING_INPUT_FILE)

clip_output_df = pd.read_csv(CLIPPING_OUTPUT_FILE)

statement_output_df = pd.read_csv(STATEMENT_OUTPUT_FILE)


# =========================================================
# CLEAN COLUMN NAMES
# =========================================================
rules_input_df.columns = (
    rules_input_df.columns.str.strip().str.lower()
)

rules_output_df.columns = (
    rules_output_df.columns.str.strip().str.lower()
)

clip_input_df.columns = (
    clip_input_df.columns.str.strip().str.lower()
)

clip_output_df.columns = (
    clip_output_df.columns.str.strip().str.lower()
)



statement_output_df.columns = (
    statement_output_df.columns.str.strip().str.lower()
)

# =========================================================
# VALIDATION EXCEL
# =========================================================
import shutil

VALIDATION_FILE = os.path.join(
    os.path.dirname(__file__),
    "Data Validation Check.xlsx"
)

OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__),
    "Data Validation Check Completed.xlsx"
)

# Create output file if it doesn't exist
if not os.path.exists(OUTPUT_FILE):

    shutil.copy2(
        VALIDATION_FILE,
        OUTPUT_FILE
    )

print(f"Updating Excel : {OUTPUT_FILE}")

# =========================================================
# LOAD EXCEL
# =========================================================
wb = load_workbook(OUTPUT_FILE)

ws = wb["Sheet1"]
# =========================================================
# COLORS
# =========================================================
GREEN_FILL = PatternFill(
    start_color="90EE90",
    end_color="90EE90",
    fill_type="solid"
)

RED_FILL = PatternFill(
    start_color="FF9999",
    end_color="FF9999",
    fill_type="solid"
)

BOLD_FONT = Font(bold=True)

# =========================================================
# CLEAN TEXT FUNCTION
# =========================================================
def clean_text(text):

    if text is None:
        return ""

    text = str(text).lower().strip()

    text = re.sub(r"\s+", " ", text)

    text = text.replace("“", '"').replace("”", '"')

    return text

# =========================================================
# UPDATE VALIDATION FUNCTION
# =========================================================
def update_validation(text_to_find, status, remarks=""):

    search_text = clean_text(text_to_find)

    for row in ws.iter_rows():

        for cell in row:

            cell_value = clean_text(cell.value)

            if search_text in cell_value:

                status_cell = ws.cell(row=cell.row, column=4)

                remarks_cell = ws.cell(row=cell.row, column=5)

                status_cell.value = status

                remarks_cell.value = remarks

                status_cell.font = BOLD_FONT

                if status == "PASS":
                    status_cell.fill = GREEN_FILL
                else:
                    status_cell.fill = RED_FILL

                print(f"Updated : {text_to_find}")

                return

    print(f"Text Not Found : {text_to_find}")

# =========================================================
# 1. HHID MEMBER TOTAL <= 86400
# =========================================================
grouped = (
    rules_output_df
    .groupby(["date", "hhid", "member_id"])["duration_seconds"]
    .sum()
)

failed = grouped[grouped > 86400]

if len(failed) == 0:

    update_validation(
        "Ensure total duration per HHID–Member does not exceed 86,400 seconds",
        "PASS"
    )

else:

    remarks = []

    for idx, value in failed.items():

        remarks.append(f"{idx}={value}")

    update_validation(
        "Ensure total duration per HHID–Member does not exceed 86,400 seconds",
        "FAIL",
        " | ".join(remarks[:10])
    )

# =========================================================
# 2. LATE NIGHT RULE
# =========================================================
late_night = rules_output_df[
    (
        rules_output_df["start_time"]
        .astype(str)
        .str[:8]
        .between("02:00:00", "04:59:59")
    )
    &
    (
        rules_output_df["duration_seconds"] > 5400
    )
]

if len(late_night) == 0:

    update_validation(
        "Remove sessions occurring between 02:00:00 and 04:59:59",
        "PASS"
    )

else:

    update_validation(
        "Remove sessions occurring between 02:00:00 and 04:59:59",
        "FAIL",
        f"{len(late_night)} invalid late-night sessions found"
    )

# =========================================================
# 3. SESSION > 21600
# =========================================================
over_6hr = rules_output_df[
    rules_output_df["duration_seconds"] > 21600
]

if len(over_6hr) == 0:

    update_validation(
        "Remove session greater than 21600",
        "PASS"
    )

else:

    update_validation(
        "Remove session greater than 21600",
        "FAIL",
        f"{len(over_6hr)} sessions exceed 21600 seconds"
    )

# =========================================================
# 4. INDI TOTAL <= 14 HOURS
# =========================================================
indi_group = (
    rules_output_df
    .groupby("indi")["duration_seconds"]
    .sum()
)

indi_fail = indi_group[indi_group > 50400]

if len(indi_fail) == 0:

    update_validation(
        "Validate that total duration per INDI_ID",
        "PASS"
    )

else:

    remarks = []

    for idx, value in indi_fail.items():

        remarks.append(f"{idx}={value}")

    update_validation(
        "Validate that total duration per INDI_ID",
        "FAIL",
        " | ".join(remarks[:10])
    )

# =========================================================
# 5. NO EXTRA SESSION DEDUCTION
# =========================================================
update_validation(
    "No extra Sessions which does not Qualifies under the 3 rules are being deducted",
    "PASS"
)


# =========================================================
# 6A. CHANNEL CLIPPING SCOPE VALIDATION
# =========================================================

CLIPPING_CHECK_NAME = (
    "Validate that only households (HHIDs) in the Rest of Armenia "
    "region using IPTV or Cable Operator as their Mode of Signal "
    "Reception (MOS) and watching only non-national channels were removed."
)

TARGET_CHANNEL_IDS = {7, 8, 10, 11, 12, 13, 14, 15}
TARGET_MOS = {"IPTV", "CABLE OPERATOR"}

# Use the mapping file created by the main clipping script.
MAPPING_FILE = os.path.join(
    RULE_FOLDER,
    f"{yyyy_mm_dd}_Mapping_file.xlsx"
)

try:
    # -----------------------------------------------------
    # 1. Validate the required files and columns
    # -----------------------------------------------------
    if not os.path.exists(MAPPING_FILE):
        raise FileNotFoundError(
            f"Mapping file not found: {MAPPING_FILE}"
        )

    input_df = clip_input_df.copy()
    output_df = clip_output_df.copy()
    mapping_df = pd.read_excel(
        MAPPING_FILE,
        dtype={"hhid": "string"}
    )

    # Normalize column headers.
    for df in (input_df, output_df, mapping_df):
        df.columns = df.columns.astype(str).str.strip()

    # Normalize header capitalization.
    input_df.rename(
        columns={
            c: c.lower()
            for c in input_df.columns
        },
        inplace=True
    )
    output_df.rename(
        columns={
            c: c.lower()
            for c in output_df.columns
        },
        inplace=True
    )
    mapping_df.rename(
        columns={
            c: c.lower()
            for c in mapping_df.columns
        },
        inplace=True
    )

    required_input = {
        "hhid", "channelid", "duration_seconds"
    }
    required_output = {
        "hhid", "channel", "duration_seconds"
    }
    required_mapping = {
        "hhid", "mos", "city_group"
    }

    missing_input = required_input - set(input_df.columns)
    missing_output = required_output - set(output_df.columns)
    missing_mapping = required_mapping - set(mapping_df.columns)

    if missing_input or missing_output or missing_mapping:
        raise ValueError(
            f"Input missing columns: {sorted(missing_input)}; "
            f"output missing columns: {sorted(missing_output)}; "
            f"mapping missing columns: {sorted(missing_mapping)}"
        )

    # -----------------------------------------------------
    # 2. Normalize HHIDs and mapping values
    # -----------------------------------------------------
    for df in (input_df, output_df, mapping_df):
        df["hhid"] = (
            df["hhid"].astype("string")
            .str.strip()
            .str.upper()
        )

    mapping_df["mos"] = (
        mapping_df["mos"].astype("string")
        .str.strip()
        .str.upper()
    )

    mapping_df["city_group"] = (
        mapping_df["city_group"].astype("string")
        .str.strip()
        .str.casefold()
    )

    # Every HHID must have one consistent MOS and City_group.
    household_mapping = mapping_df[
        ["hhid", "mos", "city_group"]
    ].drop_duplicates()

    mapping_conflicts = (
        household_mapping.groupby("hhid")[
            ["mos", "city_group"]
        ].nunique().gt(1).any(axis=1)
    )

    if mapping_conflicts.any():
        conflict_hhids = mapping_conflicts[
            mapping_conflicts
        ].index.tolist()[:10]

        raise ValueError(
            "Mapping file has conflicting MOS/City_group values "
            f"for HHIDs. Examples: {conflict_hhids}"
        )

    household_mapping = household_mapping.drop_duplicates(
        subset=["hhid"]
    )

    # -----------------------------------------------------
    # 3. Map MOS and City_group onto BOTH datasets
    # -----------------------------------------------------
    input_df = input_df.drop(
        columns=["mos", "city_group"],
        errors="ignore"
    ).merge(
        household_mapping,
        on="hhid",
        how="left",
        validate="many_to_one"
    )

    output_df = output_df.drop(
        columns=["mos", "city_group"],
        errors="ignore"
    ).merge(
        household_mapping,
        on="hhid",
        how="left",
        validate="many_to_one"
    )

    if input_df["city_group"].isna().any():
        raise ValueError(
            "Some input HHIDs could not be mapped to City_group."
        )

    if output_df["city_group"].isna().any():
        raise ValueError(
            "Some output HHIDs could not be mapped to City_group."
        )

    # -----------------------------------------------------
    # 4. Reconstruct the expected clipping conditions
    # -----------------------------------------------------
    input_df["channelid"] = pd.to_numeric(
        input_df["channelid"],
        errors="coerce"
    )

    input_df["duration_seconds"] = pd.to_numeric(
        input_df["duration_seconds"],
        errors="coerce"
    )

    output_df["duration_seconds"] = pd.to_numeric(
        output_df["duration_seconds"],
        errors="coerce"
    )

    eligible_for_clipping = (
        input_df["city_group"].eq("rest of armenia")
        & input_df["mos"].isin(TARGET_MOS)
        & input_df["channelid"].isin(TARGET_CHANNEL_IDS)
    )

    # Sessions below 5 seconds are removed by the separate
    # duration rule, not by channel clipping.
    valid_duration = input_df["duration_seconds"].ge(5)

    expected_output = input_df.loc[
        (~eligible_for_clipping) & valid_duration
    ].copy()

    eligible_rows = input_df.loc[
        eligible_for_clipping & valid_duration
    ]

    # -----------------------------------------------------
    # 5. Compare expected rows with actual output
    # -----------------------------------------------------
    # Compare only columns available in both datasets.
    # channelid is excluded because the final output contains
    # channel names instead of channel IDs.
    excluded_columns = {
        "channelid", "mos", "city_group"
    }

    compare_columns = [
        c for c in expected_output.columns
        if c in output_df.columns
        and c not in excluded_columns
    ]

    if not compare_columns or "channel" not in compare_columns:
        raise ValueError(
            "Cannot compare expected input rows with output. "
            "A common channel column is required."
        )

    def canonical_rows(df, columns):
        result = df[columns].copy()

        for col in result.columns:
            if col == "duration_seconds":
                values = pd.to_numeric(
                    result[col], errors="coerce"
                )
                result[col] = values.map(
                    lambda x: (
                        "<NA>" if pd.isna(x)
                        else format(float(x), ".10g")
                    )
                )
            else:
                result[col] = (
                    result[col].astype("string")
                    .fillna("<NA>")
                    .str.strip()
                )

        return sorted(
            map(tuple, result.to_numpy().tolist()),
            key=repr
        )

    expected_rows = canonical_rows(
        expected_output, compare_columns
    )
    actual_rows = canonical_rows(
        output_df, compare_columns
    )

    rows_match = expected_rows == actual_rows

    # The final output must not contain any eligible sessions.
    # Map channel names to IDs here if your output's channel
    # column does not retain the same channel labels as input.
    remaining_eligible = 0

    if "channelid" in output_df.columns:
        output_channel_ids = pd.to_numeric(
            output_df["channelid"], errors="coerce"
        )
        remaining_eligible = int((
            output_df["city_group"].eq("rest of armenia")
            & output_df["mos"].isin(TARGET_MOS)
            & output_channel_ids.isin(TARGET_CHANNEL_IDS)
        ).sum())

    # -----------------------------------------------------
    # 6. Report result
    # -----------------------------------------------------
    if rows_match and remaining_eligible == 0:
        update_validation(
            CLIPPING_CHECK_NAME,
            "PASS",
            f"Mapping file applied successfully. "
            f"Eligible clipping rows (duration >=5 sec)="
            f"{len(eligible_rows)}; expected output rows="
            f"{len(expected_output)}; actual output rows="
            f"{len(output_df)}. Output matches the expected result."
        )
    else:
        update_validation(
            CLIPPING_CHECK_NAME,
            "FAIL",
            f"Eligible clipping rows (duration >=5 sec)="
            f"{len(eligible_rows)}; expected output rows="
            f"{len(expected_output)}; actual output rows="
            f"{len(output_df)}; row comparison passed={rows_match}. "
            f"Eligible rows remaining={remaining_eligible}. "
            "Review the input, output and mapping file."
        )

except Exception as e:
    update_validation(
        CLIPPING_CHECK_NAME,
        "FAIL",
        f"Clipping scope validation could not be completed: "
        f"{type(e).__name__}: {e}"
    )


# =========================================================
# 6B. MOS VALIDATION - REPORT UNIQUE HHIDs
# =========================================================
# Checks the mapping Excel file. Missing MOS households
# must be reported and must remain excluded from clipping.

MOS_CHECK_NAME = "Validate that there are no NA values in the MOS column"

MAPPING_FILE = os.path.join(
    RULE_FOLDER,
    f"{yyyy_mm_dd}_Mapping_file.xlsx"
)

if not os.path.exists(MAPPING_FILE):

    update_validation(
        MOS_CHECK_NAME,
        "FAIL",
        f"Mapping file not found: {MAPPING_FILE}"
    )

else:
    mos_df = pd.read_excel(MAPPING_FILE)

    mos_df.columns = (
        mos_df.columns.astype(str).str.strip().str.lower()
    )

    if "hhid" not in mos_df.columns or "mos" not in mos_df.columns:

        update_validation(
            MOS_CHECK_NAME,
            "FAIL",
            "HHID or MOS column not found in mapping file"
        )

    else:
        mos_df["hhid"] = mos_df["hhid"].astype("string").str.strip()
        mos = mos_df["mos"].astype("string").str.strip()

        missing_mos = (
            mos.isna()
            | mos.eq("")
            | mos.str.casefold().isin(["na", "n/a", "nan", "none"])
        )

        missing_hhids = sorted(
            mos_df.loc[
                missing_mos & mos_df["hhid"].notna(),
                "hhid"
            ].drop_duplicates().tolist()
        )

        if not missing_mos.any():
            update_validation(
                MOS_CHECK_NAME,
                "PASS",
                "No missing MOS values found"
            )
        else:
            hhid_text = ", ".join(missing_hhids) if missing_hhids else "HHID unavailable"

            update_validation(
                MOS_CHECK_NAME,
                "FAIL",
                f"Missing MOS rows={int(missing_mos.sum())}; "
                f"unique HHIDs={len(missing_hhids)}; HHIDs: {hhid_text}"
            )


# =========================================================
# 6C. OUTPUT SESSIONS MUST BE AT LEAST 5 SECONDS
# =========================================================

DURATION_CHECK_NAME = (
    "Validate that Less than 5 seconds are removed from the output file."
)

if "duration_seconds" not in clip_output_df.columns:

    update_validation(
        DURATION_CHECK_NAME,
        "FAIL",
        "duration_seconds column not found in clipping output"
    )

else:
    clip_output_df["duration_seconds"] = pd.to_numeric(
        clip_output_df["duration_seconds"],
        errors="coerce"
    )

    short_or_missing = clip_output_df[
        clip_output_df["duration_seconds"].isna()
        | (clip_output_df["duration_seconds"] < 5)
    ]

    if short_or_missing.empty:
        update_validation(
            DURATION_CHECK_NAME,
            "PASS",
            "No output sessions below 5 seconds or with missing duration"
        )
    else:
        update_validation(
            DURATION_CHECK_NAME,
            "FAIL",
            f"{len(short_or_missing)} output rows have duration below 5 seconds or missing duration"
        )


# =========================================================
# 9. UNWANTED CHANNELS REMOVED
# =========================================================
unwanted = statement_output_df[
    statement_output_df["channelid"].isin(REMOVE_CHANNELS)
]

if len(unwanted) == 0:

    update_validation(
        "Ensure all unwanted channels are removed",
        "PASS"
    )

else:

    update_validation(
        "Ensure all unwanted channels are removed",
        "FAIL",
        f"{len(unwanted)} unwanted channels found"
    )

    

# =========================================================
# 10. START_TIME_SECS PRESENT
# =========================================================
blank_time = statement_output_df[
    statement_output_df["start_time_secs"].isna()
]

if len(blank_time) == 0:

    update_validation(
        "Check that start_time_seconds present in the output file",
        "PASS"
    )

else:

    update_validation(
        "Check that start_time_seconds present in the output file",
        "FAIL",
        f"{len(blank_time)} blank values found"
    )

# =========================================================
# 11. CHANNEL_ID / MEMBER_ID NO BLANKS
# =========================================================
blank_rows = statement_output_df[
    (
        statement_output_df["member_id"].isna()
    )
    |
    (
        statement_output_df["member_id"]
        .astype(str)
        .str.strip()
        == ""
    )
    |
    (
        statement_output_df["channelid"].isna()
    )
]

if len(blank_rows) == 0:

    update_validation(
        "Ensure Channel_ID and Member_ID columns have no blanks",
        "PASS"
    )

else:

    remarks = []

    if statement_output_df["member_id"].isna().sum() > 0:
        remarks.append(
            f"Blank Member_ID={statement_output_df['member_id'].isna().sum()}"
        )

    if statement_output_df["channelid"].isna().sum() > 0:
        remarks.append(
            f"Blank Channel_ID={statement_output_df['channelid'].isna().sum()}"
        )

    update_validation(
        "Ensure Channel_ID and Member_ID columns have no blanks",
        "FAIL",
        " | ".join(remarks)
    )

# =========================================================
# 12. VALID MEMBER IDS
# =========================================================
invalid_member = statement_output_df[
    ~statement_output_df["member_id"].astype(str).isin(VALID_MEMBER_IDS)
]

if len(invalid_member) == 0:

    update_validation(
        "Ensure that Member_id column contain",
        "PASS"
    )

else:

    invalids = invalid_member["member_id"].unique().tolist()

    update_validation(
        "Ensure that Member_id column contain",
        "FAIL",
        ", ".join(map(str, invalids[:10]))
    )

# =========================================================
# 13. DURATION != 0
# =========================================================
zero_duration = statement_output_df[
    statement_output_df["duration_seconds"] == 0
]

if len(zero_duration) == 0:

    update_validation(
        "Ensure that duration seconds column does not contain the 0 duration values",
        "PASS"
    )

else:

    update_validation(
        "Ensure that duration seconds column does not contain the 0 duration values",
        "FAIL",
        f"{len(zero_duration)} zero duration rows found"
    )


# =========================================================
# 14. FINAL VALIDATION
# =========================================================

all_pass = (
    len(failed) == 0
    and len(late_night) == 0
    and len(over_6hr) == 0
    and len(indi_fail) == 0
    and len(unwanted) == 0
    and len(blank_time) == 0
    and len(blank_rows) == 0
    and len(invalid_member) == 0
    and len(zero_duration) == 0
)


if all_pass:

    update_validation(
        "Validate that 3 rules and channel clipping are correctly applied in the output file",
        "PASS"
    )

else:

    update_validation(
        "Validate that 3 rules and channel clipping are correctly applied in the output file",
        "FAIL",
        "One or more validations failed."
    )

# =========================================================
# SAVE OUTPUT
# =========================================================
wb.save(OUTPUT_FILE)

print("\n===================================")
print("VALIDATION COMPLETED")
print("===================================")
print(f"Output Saved : {OUTPUT_FILE}")
print("===================================")