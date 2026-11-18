# =========================================================
# IMPORT LIBRARIES
# =========================================================
import subprocess
import os

# =========================================================
# DATE INPUT
# =========================================================
process_date = input(
    "\nEnter processing date (Example: 10-05-2026): "
).strip()

# =========================================================
# BASE PATH
# =========================================================
BASE_PATH = r"C:\Users\HP\Desktop\Data_Validation_Script"

# =========================================================
# SCRIPT FILES
# =========================================================
logo_script = os.path.join(
    BASE_PATH,
    "Stage1_Logo_Checks.py"
)

fp_script = os.path.join(
    BASE_PATH,
    "Stage1_FP_Checks.py"
)

data_processing_script = os.path.join(
    BASE_PATH,
    "Stage2_Data_Processing_Checks.py"
)

member_updation_script = os.path.join(
    BASE_PATH,
    "Stage2_Members_Updation_Checks.py"
)

merged_data_script = os.path.join(
    BASE_PATH,
    "Stage2_Merged_Data_Checks.py"
)

data_cleaning_script = os.path.join(
    BASE_PATH,
    "Stage2_Data_Cleaning_For_Panel_Checks.py"
)

panel_script = os.path.join(
    BASE_PATH,
    "Panel_Validation_Checks.py"
)

rules_script = os.path.join(
    BASE_PATH,
    "3rules_channel_clipping_statement.py"
)

# =========================================================
# RUN STAGE 1 - LOGO VALIDATION
# =========================================================
print("\n===================================")
print("RUNNING STAGE 1 - LOGO VALIDATION")
print("===================================\n")

subprocess.run(
    ["python", logo_script, process_date],
    check=True
)

print("\n===================================")
print("LOGO VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# RUN STAGE 1 - FP VALIDATION
# =========================================================
print("\n===================================")
print("RUNNING STAGE 1 - FP VALIDATION")
print("===================================\n")

subprocess.run(
    ["python", fp_script, process_date],
    check=True
)

print("\n===================================")
print("FP VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# RUN STAGE 2 - DATA PROCESSING
# =========================================================
print("\n===================================")
print("RUNNING STAGE 2 - DATA PROCESSING")
print("===================================\n")

subprocess.run(
    ["python", data_processing_script, process_date],
    check=True
)

print("\n===================================")
print("DATA PROCESSING VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# RUN STAGE 2 - MEMBERS UPDATION
# =========================================================
print("\n===================================")
print("RUNNING STAGE 2 - MEMBERS UPDATION")
print("===================================\n")

subprocess.run(
    ["python", member_updation_script, process_date],
    check=True
)

print("\n===================================")
print("MEMBERS UPDATION VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# RUN STAGE 2 - MERGED DATA CHECKS
# =========================================================
print("\n===================================")
print("RUNNING STAGE 2 - MERGED DATA CHECKS")
print("===================================\n")

subprocess.run(
    ["python", merged_data_script, process_date],
    check=True
)

print("\n===================================")
print("MERGED DATA VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# RUN STAGE 2 - DATA CLEANING FOR PANEL
# =========================================================
print("\n===================================")
print("RUNNING STAGE 2 - DATA CLEANING FOR PANEL")
print("===================================\n")

subprocess.run(
    ["python", data_cleaning_script, process_date],
    check=True
)

print("\n===================================")
print("DATA CLEANING FOR PANEL VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# RUN PANEL VALIDATION
# =========================================================
print("\n===================================")
print("RUNNING PANEL VALIDATION")
print("===================================\n")

subprocess.run(
    ["python", panel_script, process_date],
    check=True
)

print("\n===================================")
print("PANEL VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# RUN 3RULES VALIDATION
# =========================================================
print("\n===================================")
print("RUNNING 3RULES VALIDATION")
print("===================================\n")

subprocess.run(
    ["python", rules_script, process_date],
    check=True
)

print("\n===================================")
print("3RULES VALIDATION COMPLETED")
print("===================================\n")

# =========================================================
# FINAL MESSAGE
# =========================================================
print("\n===================================")
print("ALL VALIDATIONS COMPLETED")
print("===================================\n")