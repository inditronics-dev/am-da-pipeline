# ==========================================================
# TOTAL TV RATING CALCULATION
# ==========================================================

import pandas as pd
import os
from datetime import datetime, timedelta
from calculate_tv_kpi import calculate_tv_kpi

# ==========================================================
# CONFIGURATION
# ==========================================================


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# Population
POPULATION = 3067400


# Input folders
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

# ==========================================================
# FIND D-1 FILES
# ==========================================================


yesterday = datetime.now() - timedelta(days=1)

# Add these two lines
statement_date = yesterday.strftime("%Y-%m-%d")
panel_date = yesterday.strftime("%d-%m-%Y")

statement_file = os.path.join(
    STATEMENT_FOLDER,
    f"{yesterday.strftime('%Y-%m-%d')}_statement.csv"
)

panel_file = os.path.join(
    PANEL_FOLDER,
    f"{yesterday.strftime('%d-%m-%Y')}_combined_weighted.csv"
)

print("=" * 60)
print("Statement File :", statement_file)
print("Panel File     :", panel_file)
print("=" * 60)

# Check files exist
if not os.path.exists(statement_file):
    raise FileNotFoundError(f"Statement file not found:\n{statement_file}")

if not os.path.exists(panel_file):
    raise FileNotFoundError(f"Panel file not found:\n{panel_file}")


# ==========================================================
# CALCULATE TV KPI
# ==========================================================

result = calculate_tv_kpi(
    statement_file,
    panel_file
)


impressions = result["impressions"]
reach = result["reach"]
ats_seconds = result["ats_seconds"]
ats = result["ats"]
round_off_reach = result["round_off_reach"]
reach_percent = result["reach_percent"]
rating = result["rating"]
universe = result["universe"]

# Display Results
print("\n================ TV KPI =================")
print(f"Impressions      : {impressions:,.2f}")
print(f"Reach            : {reach:,.2f}")
print(f"ATS (Seconds)    : {ats_seconds:.6f}")
print(f"ATS              : {ats}")
print(f"Reach %          : {reach_percent}")
print(f"TV Rating        : {rating}")
print(f"Universe         : {universe:,}")
print("=========================================")