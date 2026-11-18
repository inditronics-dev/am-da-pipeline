# =========================================================
# STAGE 2 - MERGED DATA CHECKS
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
    run_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

process_date = datetime.strptime(
    run_date,
    "%Y-%m-%d"
).strftime("%d-%m-%Y")

# =========================================================
# DATE FORMATS
# =========================================================
input_date = datetime.strptime(
    process_date,
    "%d-%m-%Y"
)

dd_mm_yyyy = input_date.strftime(
    "%d-%m-%Y"
)

yyyy_mm_dd = input_date.strftime(
    "%Y-%m-%d"
)

# =========================================================
# PATHS
# =========================================================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

INPUT_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "merging",
    "sessions_with_rejuvenation"
)

OUTPUT_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "merging",
    "Final_merged_file"
)

# =========================================================
# FILES
# =========================================================
logo_before_file = os.path.join(
    INPUT_FOLDER,
    f"{yyyy_mm_dd}_Members_UpdatedLOGO.csv"
)

fp_before_file = os.path.join(
    INPUT_FOLDER,
    f"{yyyy_mm_dd}_Members_UpdatedFP.csv"
)

merged_file = os.path.join(
    OUTPUT_FOLDER,
    f"{yyyy_mm_dd}_Sessions.csv"
)

# =========================================================
# PRINT
# =========================================================
print("\n===================================")
print("STAGE 2 - MERGED DATA CHECKS")
print("===================================\n")

print(f"Logo Input  : {logo_before_file}")
print(f"FP Input    : {fp_before_file}")
print(f"Merged File : {merged_file}")

# =========================================================
# LOAD FILES
# =========================================================
logo_df = pd.read_csv(
    logo_before_file
)

fp_df = pd.read_csv(
    fp_before_file
)

merged_df = pd.read_csv(
    merged_file
)

# =========================================================
# LOWER COLUMN
# =========================================================
logo_df.columns = (
    logo_df.columns
    .str.strip()
    .str.lower()
)

fp_df.columns = (
    fp_df.columns
    .str.strip()
    .str.lower()
)

merged_df.columns = (
    merged_df.columns
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
# FIND ROW FUNCTION
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
    "Type column"
)

ROW_2 = find_validation_row(
    "Negative (-ve) values"
)

ROW_3 = find_validation_row(
    "no duplicate HHID"
)

ROW_5 = find_validation_row(
    "households lost during the merging"
)

merged_df["type"] = pd.to_numeric(
    merged_df["type"],
    errors="coerce"
)
# =========================================================
# VALIDATION 1
# TYPE CHECK
# =========================================================

type_fail = []

# Type column should not contain blanks
blank_type = merged_df["type"].isna().sum()

if blank_type > 0:

    type_fail.append(
        f"Blank Type={blank_type}"
    )

# Allowed Type values
allowed_types = {29, 42}

invalid_type = merged_df[
    ~merged_df["type"].isin(allowed_types)
]

if len(invalid_type) > 0:

    invalid_values = (
        invalid_type["type"]
        .drop_duplicates()
        .tolist()
    )

    type_fail.append(
        f"Invalid Types={invalid_values}"
    )

# Check Logo rows
logo_count = (
    merged_df["type"] == 29
).sum()

if logo_count == 0:

    type_fail.append(
        "No Logo (29) records found"
    )

# Check FP rows
fp_count = (
    merged_df["type"] == 42
).sum()

if fp_count == 0:

    type_fail.append(
        "No FP (42) records found"
    )

# =========================================================
# VALIDATION 2
# NEGATIVE DURATION
# =========================================================

negative_fail = []

# ---------------------------------------------------------
# Check for negative duration in both FP and LOGO data
# ---------------------------------------------------------
negative_rows = merged_df[
    merged_df["duration_seconds"] < 0
]

if len(negative_rows) > 0:

    negative_fail.append(
        f"Negative Duration Rows={len(negative_rows)}"
    )

    hhids = (
        negative_rows["hhid"]
        .drop_duplicates()
        .astype(str)
        .tolist()
    )

    negative_fail.append(
        "HHIDs=" + ", ".join(hhids[:20])
    )

    if len(hhids) > 20:
        negative_fail.append("...")
# =========================================================
# VALIDATION 3
# UNIQUE HHID CHECK
# =========================================================

duplicate_fail = []

# ---------------------------------------------------------
# UNIQUE HHIDs IN EACH TECHNOLOGY
# ---------------------------------------------------------
logo_hhids = set(
    merged_df[
        merged_df["type"] == 29
    ]["hhid"].dropna().astype(str)
)

fp_hhids = set(
    merged_df[
        merged_df["type"] == 42
    ]["hhid"].dropna().astype(str)
)

# ---------------------------------------------------------
# HHIDs PRESENT IN BOTH TECHNOLOGIES
# ---------------------------------------------------------
common_hhids = logo_hhids.intersection(fp_hhids)

if len(common_hhids) > 0:

    duplicate_fail.append(
        f"HHIDs present in both LOGO & FP = {len(common_hhids)}"
    )

    duplicate_fail.append(
        "HHIDs=" +
        ", ".join(sorted(list(common_hhids))[:20])
    )

    if len(common_hhids) > 20:

        duplicate_fail.append("...")



# =========================================================
# VALIDATION 4
# HOUSEHOLD LOSS CHECK
# =========================================================

household_fail = []

# ---------------------------------------------------------
# HHIDs BEFORE MERGING
# ---------------------------------------------------------
logo_hhids = set(
    logo_df["hhid"]
    .dropna()
    .astype(str)
)

fp_hhids = set(
    fp_df["hhid"]
    .dropna()
    .astype(str)
)

before_hhids = logo_hhids.union(fp_hhids)

# ---------------------------------------------------------
# COMMON HHIDs
# ---------------------------------------------------------
common_hhids = logo_hhids.intersection(fp_hhids)

# ---------------------------------------------------------
# HHIDs AFTER MERGING
# ---------------------------------------------------------
merged_hhids = set(
    merged_df["hhid"]
    .dropna()
    .astype(str)
)

# ---------------------------------------------------------
# LOST HHIDs
# ---------------------------------------------------------
lost_hhids = before_hhids - merged_hhids

# ---------------------------------------------------------
# LOST UNIQUE HHIDs
# ---------------------------------------------------------
invalid_lost = lost_hhids - common_hhids

if len(invalid_lost) > 0:

    household_fail.append(
        f"Invalid Lost HHIDs={len(invalid_lost)}"
    )

    household_fail.append(
        "HHIDs=" + ", ".join(sorted(list(invalid_lost))[:20])
    )

    if len(invalid_lost) > 20:

        household_fail.append("...")

# =========================================================
# UPDATE FUNCTION
# =========================================================
def update_validation(
    row,
    fail_list
):

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

        remarks_cell.value = (
            " | ".join(fail_list)
        )

# =========================================================
# UPDATE EXCEL
# =========================================================
update_validation(
    ROW_1,
    type_fail
)

update_validation(
    ROW_2,
    negative_fail
)

update_validation(
    ROW_3,
    duplicate_fail
)

update_validation(
    ROW_5,
    household_fail
)

# =========================================================
# SAVE
# =========================================================
wb.save(
    OUTPUT_FILE
)

print("\n===================================")
print("MERGED DATA VALIDATION COMPLETED")
print("===================================\n")