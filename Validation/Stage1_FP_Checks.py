# =========================================================
# STAGE 1 - FP CHECKS
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
# D-1 Date
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

# ---------------------------------------------------------
# PROCESS DATE
# Example:
# 10-05-2026
# ---------------------------------------------------------
dd_mm_yyyy = input_date.strftime("%d-%m-%Y")

# ---------------------------------------------------------
# FILE DATE
# Example:
# 2026-05-10
# ---------------------------------------------------------
yyyy_mm_dd = input_date.strftime("%Y-%m-%d")

# ---------------------------------------------------------
# NEXT DATE
# ---------------------------------------------------------
next_date = input_date + timedelta(days=1)

next_dd_mm_yyyy = next_date.strftime("%d-%m-%Y")

next_yyyy_mm_dd = next_date.strftime("%Y-%m-%d")

# ---------------------------------------------------------
# s3_date format
# Example:
# 5/10/2026
# ---------------------------------------------------------
expected_s3_date = f"{input_date.month}/{input_date.day}/{input_date.year}"

# =========================================================
# FP FOLDER
# =========================================================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

fp_folder = os.path.join(
    BASE_DIR,
    "sessions",
    "fp",
    "input_data"
)

print("\n===================================")
print("STAGE 1 - FP VALIDATION")
print("===================================\n")

print(f"FP Folder : {fp_folder}")

# =========================================================
# LOAD EXCEL
# =========================================================
VALIDATION_FILE = os.path.join(
    os.path.dirname(__file__),
    "Data Validation Check.xlsx"
)

OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__),
    "Data Validation Check Completed.xlsx"
)

import shutil

if not os.path.exists(OUTPUT_FILE):
    shutil.copy2(
        VALIDATION_FILE,
        OUTPUT_FILE
    )

wb = load_workbook(OUTPUT_FILE)

ws = wb["Sheet1"]

print("\nMerged Ranges:")
for merged in ws.merged_cells.ranges:
    print(merged)

# =========================================================
# DATE UPDATE
# =========================================================
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
# FIND FP ROW
# =========================================================
def find_validation_row(search_text):

    for row in ws.iter_rows():

        for cell in row:

            if cell.value is None:
                continue

            cell_value = (
                str(cell.value)
                .replace("\n", " ")
                .strip()
                .lower()
            )

            if search_text.lower() in cell_value:

                return cell.row

    return None

# =========================================================
# FP ROWS
# =========================================================
FP_FILE_ROW = 6

FP_S3_ROW = 7

# =========================================================
# EXPECTED FILES
# =========================================================
expected_files = []

# ---------------------------------------------------------
# SAME DAY 02 -> 23
# ---------------------------------------------------------
for hour in range(2, 24):

    expected_files.append(
        f"{yyyy_mm_dd}_{hour:02d}_matched.csv"
    )

# ---------------------------------------------------------
# NEXT DAY 00 -> 01
# ---------------------------------------------------------
for hour in range(0, 2):

    expected_files.append(
        f"{next_yyyy_mm_dd}_{hour:02d}_matched.csv"
    )

# =========================================================
# VALIDATION VARIABLES
# =========================================================
missing_files = []

low_size_files = []

s3_date_issues = []

s3_hour_issues = []

# =========================================================
# CHECK FILES
# =========================================================
for file_name in expected_files:

    file_path = os.path.join(
        fp_folder,
        file_name
    )

    # -----------------------------------------------------
    # FILE EXIST CHECK
    # -----------------------------------------------------
    if not os.path.exists(file_path):

        missing_files.append(file_name)

        continue

    # -----------------------------------------------------
    # FILE SIZE CHECK
    # -----------------------------------------------------
    file_size_kb = round(
        os.path.getsize(file_path) / 1024,
        2
    )

    if file_size_kb < 100:

        low_size_files.append(
            f"{file_name} ({file_size_kb} KB)"
        )

    # -----------------------------------------------------
    # READ CSV
    # -----------------------------------------------------
    try:

        df = pd.read_csv(
            file_path
        )

    except Exception as e:

        s3_date_issues.append(
            f"Read Error : {file_name}"
        )

        continue

    # -----------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # -----------------------------------------------------
    required_cols = [
        "s3_date",
        "s3_hour"
    ]

    missing_cols = [
        col for col in required_cols
        if col not in df.columns
    ]

    if missing_cols:

        s3_date_issues.append(
            f"Missing Columns in {file_name}"
        )

        continue
    # -----------------------------------------------------
    # CHECK s3_date
    # -----------------------------------------------------
    try:

        expected_file_date = file_name.split("_")[0]

        parsed_dates = pd.to_datetime(
            df["s3_date"],
            errors="coerce"
        )

        parsed_dates = parsed_dates.dt.strftime(
            "%Y-%m-%d"
        )

        invalid_dates = parsed_dates[
            parsed_dates != expected_file_date
        ]

        if len(invalid_dates) > 0:

            s3_date_issues.append(file_name)

    except:

        s3_date_issues.append(file_name)
   
    # -----------------------------------------------------
    # CHECK s3_hour
    # -----------------------------------------------------
    expected_hour = file_name.split("_")[1]

    unique_hours = (
        df["s3_hour"]
        .astype(str)
        .str.zfill(2)
        .unique()
    )

    if not all(
        x == expected_hour
        for x in unique_hours
    ):

        s3_hour_issues.append(file_name)

# =========================================================
# FINAL STATUS
# =========================================================
fail_reasons = []

# ---------------------------------------------------------
# MISSING FILES
# ---------------------------------------------------------
if missing_files:

    fail_reasons.append(
        "Missing : " +
        ", ".join(missing_files)
    )

# ---------------------------------------------------------
# LOW SIZE
# ---------------------------------------------------------
if low_size_files:

    fail_reasons.append(
        "Low Size : " +
        ", ".join(low_size_files)
    )

# ---------------------------------------------------------
# s3_date ISSUE
# ---------------------------------------------------------
if s3_date_issues:

    fail_reasons.append(
        "s3_date mismatch : " +
        ", ".join(s3_date_issues)
    )

# ---------------------------------------------------------
# s3_hour ISSUE
# ---------------------------------------------------------
if s3_hour_issues:

    fail_reasons.append(
        "s3_hour mismatch : " +
        ", ".join(s3_hour_issues)
    )

# =========================================================
# VALIDATION 1
# FILE EXIST + FILE SIZE
# =========================================================
file_fail_reasons = []

if missing_files:

    file_fail_reasons.append(
        "Missing : " +
        ", ".join(missing_files)
    )

if low_size_files:

    file_fail_reasons.append(
        "Low Size : " +
        ", ".join(low_size_files)
    )

status_cell_1 = ws.cell(
    row=FP_FILE_ROW,
    column=4
)

remarks_cell_1 = ws.cell(
    row=FP_FILE_ROW,
    column=5
)

if len(file_fail_reasons) == 0:

    status_cell_1.value = "PASS"

    status_cell_1.fill = green_fill

    remarks_cell_1.value = "24 Files Validated"

else:

    status_cell_1.value = "FAIL"

    status_cell_1.fill = red_fill

    remarks_cell_1.value = " | ".join(
        file_fail_reasons
    )

# =========================================================
# VALIDATION 2
# s3_date + s3_hour
# =========================================================
s3_fail_reasons = []

if s3_date_issues:

    s3_fail_reasons.append(
        "s3_date mismatch : " +
        ", ".join(s3_date_issues)
    )

if s3_hour_issues:

    s3_fail_reasons.append(
        "s3_hour mismatch : " +
        ", ".join(s3_hour_issues)
    )

status_cell_2 = ws.cell(
    row=FP_S3_ROW,
    column=4
)

remarks_cell_2 = ws.cell(
    row=FP_S3_ROW,
    column=5
)

if len(s3_fail_reasons) == 0:

    status_cell_2.value = "PASS"

    status_cell_2.fill = green_fill

    remarks_cell_2.value = "All s3 values matched"

else:

    status_cell_2.value = "FAIL"

    status_cell_2.fill = red_fill

    remarks_cell_2.value = " | ".join(
        s3_fail_reasons
    )

# =========================================================
# SAVE OUTPUT
# =========================================================
wb.save(OUTPUT_FILE)

print("\n===================================")
print("FP VALIDATION COMPLETED")
print("===================================\n")