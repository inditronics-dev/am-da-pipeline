# =========================================================
# IMPORT LIBRARIES
# =========================================================
import os
from datetime import datetime

# =========================================================
# BASE PATH
# =========================================================
BASE_PATH = r"C:\Users\HP\Desktop\Data_Validation_Script"

# =========================================================
# INPUT FOLDER
# =========================================================
INPUT_FOLDER = os.path.join(
    BASE_PATH,
    "Input_file"
)

# =========================================================
# FP OUTPUT FOLDER
# =========================================================
FP_BASE_FOLDER = BASE_PATH
# =========================================================
# EXCEL FILES
# =========================================================
VALIDATION_FILE = os.path.join(
    BASE_PATH,
    "Data Validation Check.xlsx"
)

OUTPUT_FILE = os.path.join(
    BASE_PATH,
    "Data_Validition_Update.xlsx"
)

# =========================================================
# GENERATE FILE PATHS
# =========================================================
def generate_file_paths(process_date):

    # -----------------------------------------------------
    # CONVERT DATE FORMAT
    # INPUT:
    # 10-05-2026
    # -----------------------------------------------------
    input_date = datetime.strptime(
        process_date,
        "%d-%m-%Y"
    )

    # -----------------------------------------------------
    # DATE FORMATS
    # -----------------------------------------------------
    dd_mm_yyyy = input_date.strftime("%d-%m-%Y")

    yyyy_mm_dd = input_date.strftime("%Y-%m-%d")

    # -----------------------------------------------------
    # PANEL FILE
    # -----------------------------------------------------
    panel_file = os.path.join(
        INPUT_FOLDER,
        f"{dd_mm_yyyy}_panel.csv"
    )

    # -----------------------------------------------------
    # 3 RULES
    # -----------------------------------------------------
    rules_input_file = os.path.join(
        INPUT_FOLDER,
        f"{yyyy_mm_dd}_cleaned.csv"
    )

    rules_output_file = os.path.join(
        INPUT_FOLDER,
        f"{dd_mm_yyyy}_ruled.csv"
    )

    # -----------------------------------------------------
    # CHANNEL CLIPPING
    # -----------------------------------------------------
    clipping_input_file = os.path.join(
        INPUT_FOLDER,
        f"{dd_mm_yyyy}_ruled.csv"
    )

    clipping_output_file = os.path.join(
        INPUT_FOLDER,
        f"{dd_mm_yyyy}_ruled_PROCESSED.csv"
    )

    # -----------------------------------------------------
    # STATEMENT FILES
    # -----------------------------------------------------
    statement_input_file = os.path.join(
        INPUT_FOLDER,
        f"{dd_mm_yyyy}_ruled_PROCESSED.csv"
    )

    statement_output_file = os.path.join(
        INPUT_FOLDER,
        f"{dd_mm_yyyy}_statement.csv"
    )
    # -----------------------------------------------------
    # LOGO FILE
    # -----------------------------------------------------
    logo_file = os.path.join(
        r"C:\Users\HP\Desktop\Data_Validation_Script\logo_fp_files",
        f"{yyyy_mm_dd}_memberwise.csv"
    )

    # -----------------------------------------------------
    # RETURN PATHS
    # -----------------------------------------------------
    return {
        "PANEL_FILE": panel_file,
        "RULES_INPUT_FILE": rules_input_file,
        "RULES_OUTPUT_FILE": rules_output_file,
        "CLIPPING_INPUT_FILE": clipping_input_file,
        "CLIPPING_OUTPUT_FILE": clipping_output_file,
        "STATEMENT_INPUT_FILE": statement_input_file,
        "STATEMENT_OUTPUT_FILE": statement_output_file,
        "LOGO_FILE": logo_file
    }

# =========================================================
# DATABASE CONFIG
# =========================================================
DB_HOST = "armenia-db-01.c960kiumy09x.ap-south-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "meter01"
DB_USER = "postgres"
DB_PASSWORD = "inditronics123"

# =========================================================
# VALIDATION CONFIG
# =========================================================
REMOVE_CHANNELS = [6, 9, 10, 13, 14, 15]

NATIONAL_CHANNELS = {
    'FirstNewsChannel',
    'PublicTV',
    'KentronTvHD',
    'ArmeniaTV',
    'ShantTV',
    'ATV'
}

VALID_MEMBER_IDS = {
    'M1', 'M2', 'M3', 'M4',
    'M5', 'M6', 'M7', 'M8'
}