# =========================================================
# STAGE 2 - DATA CLEANING FOR PANEL CHECKS
# =========================================================

# =========================================================
# IMPORT LIBRARIES
# =========================================================
import os
import sys
import pandas as pd

from datetime import datetime, timedelta

from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# =========================================================
# IMPORT CONFIG
# =========================================================
from file_path import *

# =========================================================
# PROCESS DATE
# =========================================================
run_date = (
    os.environ.get("RUN_DATE")
    or os.environ.get("WORKFLOW_DATE")
)

if not run_date:
    run_date = (
        datetime.now()
        - timedelta(days=1)
    ).strftime("%Y-%m-%d")

process_date = datetime.strptime(
    run_date,
    "%Y-%m-%d"
).strftime("%d-%m-%Y")

# =========================================================
# DATE FORMAT
# =========================================================
input_date = datetime.strptime(
    process_date,
    "%d-%m-%Y"
)

yyyy_mm_dd = input_date.strftime(
    "%Y-%m-%d"
)

# =========================================================
# FILE PATH
# =========================================================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

INPUT_FOLDER = os.path.join(
    BASE_DIR,
    "for_panel_files",
    "for_panel"
)

cleaned_file = os.path.join(
    INPUT_FOLDER,
    f"{yyyy_mm_dd}_cleaned.csv"
)

# =========================================================
# LOAD FILE
# =========================================================
df = pd.read_csv(
    cleaned_file
)

# =========================================================
# LOWER COLUMN NAMES
# =========================================================
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
)

# =========================================================
# LOAD EXCEL
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

if not os.path.exists(OUTPUT_FILE):

    shutil.copy2(
        VALIDATION_FILE,
        OUTPUT_FILE
    )

wb = load_workbook(
    OUTPUT_FILE
)

ws = wb["Sheet1"]

ws["D2"] = process_date

# =========================================================
# COLORS
# =========================================================
green_fill = PatternFill(
    start_color="90EE90",
    end_color="90EE90",
    fill_type="solid"
)

red_fill = PatternFill(
    start_color="FF9999",
    end_color="FF9999",
    fill_type="solid"
)

# =========================================================
# FIND VALIDATION ROW
# =========================================================
def find_validation_row(search_text):

    for row in ws.iter_rows():

        for cell in row:

            if cell.value is None:
                continue

            value = (
                str(cell.value)
                .replace("\n", " ")
                .strip()
                .lower()
            )

            if search_text.lower() in value:

                return cell.row

    return None

# =========================================================
# FIND ROWS
# =========================================================
ROW_1 = find_validation_row(
    "Ensure this channel IDs"
)

ROW_2 = find_validation_row(
    "Channel” column is “Others"
)

ROW_3 = find_validation_row(
    "Member_ID column"
)

ROW_4 = find_validation_row(
    "Duration_Seconds has no negative"
)

ROW_5 = find_validation_row(
    "no “0” duration"
)

# =========================================================
# UPDATE FUNCTION
# =========================================================
def update_validation(row, fail_list):

    print(f"row = {row}, type = {type(row)}")

    if row is None:
        raise ValueError("row is None")

    status_cell = ws.cell(
        row=row,
        column=4
    )

    remarks_cell = ws.cell(
        row=row,
        column=5
    )

    if len(fail_list) == 0:
        status_cell.value = "PASS"
        status_cell.fill = green_fill
        remarks_cell.value = ""
    else:
        status_cell.value = "FAIL"
        status_cell.fill = red_fill
        remarks_cell.value = " | ".join(fail_list)
# =========================================================
# VALIDATION 1
# REQUIRED CHANNEL IDS PRESENT
# =========================================================

channel_fail = []

required_channels = {
    1, 2, 3, 4, 5, 6, 7, 8,
    10, 11, 12, 13, 14, 15
}

available_channels = set(
    pd.to_numeric(
        df["channelid"],
        errors="coerce"
    )
    .dropna()
    .astype(int)
    .unique()
)

missing_channels = sorted(
    required_channels - available_channels
)

if len(missing_channels) > 0:

    channel_fail.append(
        "Missing Channel IDs=" +
        ",".join(map(str, missing_channels))
    )

# =========================================================
# VALIDATION 2
# OTHERS CHANNEL
# =========================================================
others_fail = []

others_rows = df[
    df["channel"]
    .astype(str)
    .str.strip()
    .str.lower()
    == "others"
]

if len(others_rows) > 0:

    others_fail.append(
        f"Others Rows="
        f"{len(others_rows)}"
    )

# =========================================================
# VALIDATION 3
# BLANK MEMBER_ID
# =========================================================
member_fail = []

blank_member_rows = df[
    (
        df["member_id"]
        .isna()
    )
    |
    (
        df["member_id"]
        .astype(str)
        .str.strip()
        == ""
    )
]

if len(blank_member_rows) > 0:

    member_fail.append(
        f"Blank Member_ID Rows="
        f"{len(blank_member_rows)}"
    )

# =========================================================
# VALIDATION 4
# NEGATIVE DURATION
# =========================================================
negative_fail = []

negative_rows = df[
    df["duration_seconds"] < 0
]

if len(negative_rows) > 0:

    negative_fail.append(
        f"Negative Duration Rows="
        f"{len(negative_rows)}"
    )

# =========================================================
# VALIDATION 5
# ZERO DURATION
# =========================================================
zero_fail = []

zero_rows = df[
    df["duration_seconds"] == 0
]

if len(zero_rows) > 0:

    zero_fail.append(
        f"Zero Duration Rows="
        f"{len(zero_rows)}"
    )

# =========================================================
# UPDATE EXCEL
# =========================================================
update_validation(
    ROW_1,
    channel_fail
)

update_validation(
    ROW_2,
    others_fail
)

update_validation(
    ROW_3,
    member_fail
)

update_validation(
    ROW_4,
    negative_fail
)

update_validation(
    ROW_5,
    zero_fail
)

# =========================================================
# SAVE FILE
# =========================================================
wb.save(
    OUTPUT_FILE
)

print("\n===================================")
print("DATA CLEANING FOR PANEL VALIDATION COMPLETED")
print("===================================\n")