# =========================================================
# STAGE 2 - DATA PROCESSING CHECKS
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
# GET PROCESS DATE (D-1 from main pipeline)
# =========================================================
run_date = (
    os.environ.get("RUN_DATE")
    or os.environ.get("WORKFLOW_DATE")
)

# If running outside the pipeline, default to D-1
if not run_date:
    run_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# Convert YYYY-MM-DD to DD-MM-YYYY
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

dd_mm_yyyy = input_date.strftime(
    "%d-%m-%Y"
)

yyyy_mm_dd = input_date.strftime(
    "%Y-%m-%d"
)

# =========================================================
# PROJECT ROOT
# =========================================================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

# =========================================================
# OUTPUT FOLDERS
# =========================================================
LOGO_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "logo",
    "household_viewership_memberwise_output"
)

FP_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "fp",
    "output"
)

print("\n===================================")
print("STAGE 2 - DATA PROCESSING CHECKS")
print("===================================\n")

print(f"Logo Folder : {LOGO_FOLDER}")
print(f"FP Folder   : {FP_FOLDER}")
print(f"OUTPUT_FILE = {OUTPUT_FILE}")

# =========================================================
# LOAD EXCEL
# =========================================================
import shutil

# =========================================================
# TEMPLATE AND OUTPUT FILE
# =========================================================
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
import shutil

# =========================================================
# TEMPLATE AND OUTPUT FILE
# =========================================================
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
import shutil

# =========================================================
# TEMPLATE AND OUTPUT FILE
# =========================================================
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

# Update processing date
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
# TODAY FILES
# =========================================================
logo_today_file = os.path.join(
    LOGO_FOLDER,
    f"{yyyy_mm_dd}_logo_sessions.csv"
)

fp_today_file = os.path.join(
    FP_FOLDER,
    f"{yyyy_mm_dd}_fp_sessions.csv"
)



# =========================================================
# VALIDATION
# =========================================================
status = "PASS"
remarks = []

# ---------------------------------------------------------
# CHECK FILES EXIST
# ---------------------------------------------------------
if not os.path.exists(logo_today_file):
    status = "FAIL"
    remarks.append("Logo file missing")

if not os.path.exists(fp_today_file):
    status = "FAIL"
    remarks.append("FP file missing")

# ---------------------------------------------------------
# CHECK NEGATIVE DURATION
# ---------------------------------------------------------
def check_negative_duration(file_path):

    df = pd.read_csv(file_path)

    return (df["duration_seconds"] < 0).sum()

if status == "PASS":

    logo_negative = check_negative_duration(
        logo_today_file
    )

    fp_negative = check_negative_duration(
        fp_today_file
    )

    if logo_negative > 0:

        status = "FAIL"

        remarks.append(
            f"Logo Negative Duration={logo_negative}"
        )

    if fp_negative > 0:

        status = "FAIL"

        remarks.append(
            f"FP Negative Duration={fp_negative}"
        )


# =========================================================
# FINAL REMARKS
# =========================================================
if status == "PASS":

    final_remark = (
        "Logo & FP files available. "
        "No negative duration values found."
    )

else:

    final_remark = " | ".join(remarks)

# =========================================================
# ROWS
# =========================================================
FILE_CHECK_ROW = 9
NEGATIVE_CHECK_ROW = 10

# =========================================================
# FILE EXISTENCE CHECK
# =========================================================
file_status = "PASS"
file_remarks = ""

if not os.path.exists(logo_today_file):
    file_status = "FAIL"
    file_remarks += "Logo file missing "

if not os.path.exists(fp_today_file):
    file_status = "FAIL"
    file_remarks += "FP file missing"

status_cell = ws.cell(row=FILE_CHECK_ROW, column=4)
remarks_cell = ws.cell(row=FILE_CHECK_ROW, column=5)

status_cell.value = file_status
remarks_cell.value = file_remarks if file_remarks else "Both files available"

status_cell.fill = green_fill if file_status == "PASS" else red_fill

# =========================================================
# NEGATIVE DURATION CHECK
# =========================================================
negative_status = "PASS"
negative_remarks = ""

if file_status == "PASS":

    logo_negative = check_negative_duration(logo_today_file)
    fp_negative = check_negative_duration(fp_today_file)

    if logo_negative > 0:
        negative_status = "FAIL"
        negative_remarks += f"Logo={logo_negative} "

    if fp_negative > 0:
        negative_status = "FAIL"
        negative_remarks += f"FP={fp_negative}"

status_cell = ws.cell(row=NEGATIVE_CHECK_ROW, column=4)
remarks_cell = ws.cell(row=NEGATIVE_CHECK_ROW, column=5)

status_cell.value = negative_status
remarks_cell.value = (
    negative_remarks
    if negative_remarks
    else "No negative duration values"
)

status_cell.fill = green_fill if negative_status == "PASS" else red_fill

# =========================================================
# SAVE FILE
# =========================================================
wb.save(
    OUTPUT_FILE
)

print("\nUpdated Rows 9 and 10")

print("\n===================================")
print("DATA PROCESSING VALIDATION COMPLETED")
print("===================================\n")