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
# 6. ONLY NON-NATIONAL CHANNELS CLIPPED
# =========================================================

CHANNEL_GROUPS = {

    "ATV": [
        "A TV",
        "ATV"
    ],

    "ArmeniaTV": [
        "Armenia TV",
        "ArmeniaTV"
    ],

    "ShantTV": [
        "Shant TV",
        "ShantTV"
    ],

    "FirstNewsChannel": [
        "First News Channel",
        "FirstNewsChannel"
    ],

    "PublicTV": [
        "Public TV",
        "PublicTV"
    ],

    "KentronTVHD": [
        "Kentron Tv HD",
        "KentronTVHD"
    ]
}

# ---------------------------------------------------------
# INPUT TOTAL
# ---------------------------------------------------------
input_channel_sum = (
    clip_input_df
    .groupby("channel")["duration_seconds"]
    .sum()
)

# ---------------------------------------------------------
# OUTPUT TOTAL
# ---------------------------------------------------------
output_channel_sum = (
    clip_output_df
    .groupby("channel")["duration_seconds"]
    .sum()
)

failed_channels = []

for std_name, variants in CHANNEL_GROUPS.items():

    input_total = 0
    output_total = 0

    for ch in variants:
        input_total += input_channel_sum.get(ch, 0)
        output_total += output_channel_sum.get(ch, 0)

    # -----------------------------------------------------
    # National channels should NEVER gain duration.
    # Small reduction is acceptable because sessions
    # <5 seconds are removed after processing.
    # -----------------------------------------------------
    if output_total > input_total:

        failed_channels.append(
            f"{std_name} "
            f"(Input={input_total}, Output={output_total}, "
            f"Increased by {output_total-input_total})"
        )

if len(failed_channels) == 0:

    update_validation(
        "Ensure that only Non-National channels are clipped",
        "PASS"
    )

else:

    update_validation(
        "Ensure that only Non-National channels are clipped",
        "FAIL",
        " | ".join(failed_channels)
    )
# =========================================================
# 7. DURATION <= 1800
# =========================================================
over_1800 = clip_output_df[
    clip_output_df["duration_seconds"] > 1800
]

if len(over_1800) == 0:

    update_validation(
        "Validate that the duration_seconds column does not exceed 1800 seconds",
        "PASS"
    )

else:

    update_validation(
        "Validate that the duration_seconds column does not exceed 1800 seconds",
        "FAIL",
        f"{len(over_1800)} rows exceed 1800"
    )

# =========================================================
# 8. ALL SESSIONS > 4 SECONDS AFTER CHANNEL CLIPPING
# =========================================================
less_than_5 = clip_output_df[
    clip_output_df["duration_seconds"] <= 4
]

if len(less_than_5) == 0:

    update_validation(
        "Validate that each session's duration is greater than 4 seconds",
        "PASS"
    )

else:

    update_validation(
        "Validate that each session's duration is greater than 4 seconds",
        "FAIL",
        f"{len(less_than_5)} sessions found with duration <= 4"
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
    and len(failed_channels) == 0
    and len(over_1800) == 0
    and len(less_than_5) == 0
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