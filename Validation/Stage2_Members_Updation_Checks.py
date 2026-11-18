# =========================================================
# STAGE 2 - MEMBERS UPDATION CHECKS
# =========================================================

# =========================================================
# IMPORT LIBRARIES
# =========================================================
import os
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


# =========================================================
# PATHS
# =========================================================
INPUT_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "logo",
    "household_viewership_memberwise_output"
)

FP_INPUT_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "fp",
    "output"
)

MEMBER_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "merging",
    "sessions_with_rejuvenation"
)

REFERENCE_FOLDER = os.path.join(
    BASE_DIR,
    "sessions",
    "merging"
)

CVF_FILE = os.path.join(
    REFERENCE_FOLDER,
    "cvf_table.csv"
)

DISTRIBUTION_FILE = os.path.join(
    REFERENCE_FOLDER,
    "distribution_table_backoff_completed.csv"
)

HHID_MAPPING_FILE = os.path.join(
    REFERENCE_FOLDER,
    "HHID_Mapping_Script.xlsx"
)


# =========================================================
# INPUT FILES
# =========================================================
logo_input = os.path.join(
    INPUT_FOLDER,
    f"{yyyy_mm_dd}_logo_sessions.csv"
)

fp_input = os.path.join(
    FP_INPUT_FOLDER,
    f"{yyyy_mm_dd}_fp_sessions.csv"
)

# =========================================================
# OUTPUT FILES
# =========================================================
logo_output = os.path.join(
    MEMBER_FOLDER,
    f"{yyyy_mm_dd}_Members_UpdatedLOGO.csv"
)

fp_output = os.path.join(
    MEMBER_FOLDER,
    f"{yyyy_mm_dd}_Members_UpdatedFP.csv"
)

# =========================================================
# READ CSV
# =========================================================
def read_csv_file(file_path):

    try:

        df = pd.read_csv(file_path)

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
        )

        return df

    except:

        return pd.DataFrame()

# =========================================================
# LOAD files
# =========================================================
logo_before = read_csv_file(logo_input)

fp_before = read_csv_file(fp_input)

logo_after = read_csv_file(logo_output)

fp_after = read_csv_file(fp_output)

# =========================================================
# VALIDATION 1
# REFERENCE FILE CHECK
# =========================================================

reference_fail = []

if not os.path.exists(CVF_FILE):
    reference_fail.append("CVF Table")

if not os.path.exists(DISTRIBUTION_FILE):
    reference_fail.append("Distribution Table")

if not os.path.exists(HHID_MAPPING_FILE):
    reference_fail.append("HHID Mapping File")

# =========================================================
# VALIDATION 2
# MEMBER UPDATION CHECK
# =========================================================

def get_blank_hhids(df):

    blank_hhids = []

    for hhid, group in df.groupby("hhid"):

        member_values = (
            group["member_id"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        if all(
            x == "" or x.lower() == "nan"
            for x in member_values
        ):

            blank_hhids.append(hhid)

    return blank_hhids


logo_blank_before = get_blank_hhids(
    logo_before
)

fp_blank_before = get_blank_hhids(
    fp_before
)

validation1_fail = []


def validate_member_fill(
    blank_hhids,
    output_df,
    tech_name
):

    fail_list = []

    for hhid in blank_hhids:

        group = output_df[
            output_df["hhid"] == hhid
        ]

        if len(group) == 0:

            fail_list.append(
                f"{tech_name}-{hhid} (HHID Missing)"
            )

            continue

        member_values = (
            group["member_id"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        still_blank = all(
            x == "" or x.lower() == "nan"
            for x in member_values
        )

        if still_blank:

            fail_list.append(
                f"{tech_name}-{hhid}"
            )

    return fail_list


validation1_fail.extend(
    validate_member_fill(
        logo_blank_before,
        logo_after,
        "LOGO"
    )
)

validation1_fail.extend(
    validate_member_fill(
        fp_blank_before,
        fp_after,
        "FP"
    )
)

# =========================================================
# VALIDATION 3
# PANEL MEMBER COUNT (CVF)
# =========================================================

validation2_fail = []

if os.path.exists(CVF_FILE):

    cvf_df = pd.read_csv(CVF_FILE)

    cvf_df.columns = (
        cvf_df.columns
        .str.strip()
        .str.lower()
    )

    import math

    def validate_cvf(output_df, blank_hhids, tech_name):

        output_df.columns = (
            output_df.columns
            .str.strip()
            .str.lower()
        )

        mapping_df = pd.read_excel(HHID_MAPPING_FILE)

        mapping_df.columns = (
            mapping_df.columns
            .str.strip()
            .str.lower()
        )

        for hhid, group in output_df.groupby("hhid"):
            if hhid not in blank_hhids:
                    continue

            city = group.iloc[0]["city_group"]
            size = group.iloc[0]["hh_size_group"]
            band = group.iloc[0]["time_band"]

            cvf = pd.to_numeric(
                group.iloc[0]["cvf"],
                errors="coerce"
            )

            if pd.isna(cvf):
                validation2_fail.append(
                    f"{tech_name} | HHID={hhid} | CVF Missing"
                )
                continue

            assigned_members = (
                group["member_id"]
                .dropna()
                .astype(str)
                .nunique()
            )

            panel_members = mapping_df[
                mapping_df["hhid"] == hhid
            ]["member_code"].nunique()

            # Member count should never exceed panel members
            if assigned_members > panel_members:

                validation2_fail.append(
                    f"{tech_name} | HHID={hhid} | "
                    f"CVF={cvf} | "
                    f"Assigned={assigned_members} | "
                    f"PanelMembers={panel_members}"
                )

    validate_cvf(
    logo_after,
    logo_blank_before,
    "LOGO"
    )

    validate_cvf(
        fp_after,
        fp_blank_before,
        "FP"
    )

else:

    validation2_fail.append(
        "CVF Table Missing"
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

wb = load_workbook(OUTPUT_FILE)

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
# ROWS
# =========================================================
ROW_1 = 12
ROW_2 = 13
ROW_3 = 14

# =========================================================
# UPDATE VALIDATION 1
# =========================================================
status1 = ws.cell(
    row=ROW_1,
    column=4
)

remarks1 = ws.cell(
    row=ROW_1,
    column=5
)

if len(reference_fail) == 0:

    status1.value = "PASS"

    status1.fill = green_fill

    remarks1.value = ""

else:

    status1.value = "FAIL"

    status1.fill = red_fill

    remarks1.value = (
        ", ".join(reference_fail)
    )

# =========================================================
# UPDATE VALIDATION 2
# =========================================================
status2 = ws.cell(
    row=ROW_2,
    column=4
)

remarks2 = ws.cell(
    row=ROW_2,
    column=5
)

if len(validation1_fail) == 0:

    status2.value = "PASS"

    status2.fill = green_fill

    remarks2.value = ""

else:

    status2.value = "FAIL"

    status2.fill = red_fill


    remarks2.value = (
    ", ".join(validation1_fail)
    )

# =========================================================
# UPDATE VALIDATION 3
# =========================================================
status3 = ws.cell(
    row=ROW_3,
    column=4
)

remarks3 = ws.cell(
    row=ROW_3,
    column=5
)

if len(validation2_fail) == 0:

    status3.value = "PASS"

    status3.fill = green_fill

    remarks3.value = ""

else:

    status3.value = "FAIL"

    status3.fill = red_fill

    remarks3.value = (
        ", ".join(validation2_fail)
    )

# =========================================================
# SAVE
# =========================================================
wb.save(
    OUTPUT_FILE
)

print("\n===================================")
print("MEMBERS UPDATION VALIDATION COMPLETED")
print("===================================\n")