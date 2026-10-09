# ==========================================================
# TOTAL TV RATING CALCULATION
# ==========================================================

import pandas as pd
import os
from datetime import datetime, timedelta

# ==========================================================
# CONFIGURATION
# ==========================================================

import os

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

# Output folder
OUTPUT_FOLDER = os.path.join(
    BASE_DIR,
    "TV_Rating_Output"
)

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==========================================================
# FIND D-1 FILES
# ==========================================================

from datetime import datetime, timedelta

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
# READ FILES
# ==========================================================

statement_df = pd.read_csv(statement_file)

panel_df = pd.read_csv(panel_file)

print("\nStatement Rows :", len(statement_df))
print("Panel Rows     :", len(panel_df))

# ==========================================================
# STEP 2 - READ FILES & MERGE PANEL WEIGHT
# ==========================================================

print("\nReading files...")

# Read CSV files
statement_df = pd.read_csv(statement_file)
panel_df = pd.read_csv(panel_file)

print(f"Statement Records : {len(statement_df):,}")
print(f"Panel Records     : {len(panel_df):,}")

# ==========================================================
# CREATE Indi_id
# ==========================================================

# Statement File
statement_df["Indi_id"] = (
    statement_df["hhid"].astype(str).str.strip() +
    statement_df["member_id"].astype(str).str.strip()
)

# Panel File
panel_df["Indi_id"] = (
    panel_df["hhid"].astype(str).str.strip() +
    panel_df["member_code"].astype(str).str.strip()
)

# ==========================================================
# KEEP ONLY REQUIRED COLUMNS FROM PANEL
# ==========================================================

panel_weight = panel_df[[
    "Indi_id",
    "final_weight_scaled"
]].copy()

panel_weight.rename(
    columns={
        "final_weight_scaled": "Weight"
    },
    inplace=True
)

# ==========================================================
# MERGE WEIGHT TO STATEMENT
# ==========================================================

statement_df = statement_df.merge(
    panel_weight,
    on="Indi_id",
    how="left"
)

# ==========================================================
# CHECK MERGE
# ==========================================================

missing_weight = statement_df["Weight"].isna().sum()

print(f"Matched Records      : {(len(statement_df)-missing_weight):,}")
print(f"Missing Weights      : {missing_weight:,}")

if missing_weight > 0:
    print("WARNING : Some Indi_id values are not available in Panel File.")

print("\nMerge Completed Successfully.")

# ==========================================================
# STEP 3 - CREATE UNIQUE PERSON WEIGHT
# ==========================================================

print("\nCreating Unique Person Weight...")

# Initialize as numeric
statement_df["Unique_Person_Weight"] = 0.0

# First occurrence of each person
first_occurrence = ~statement_df["Indi_id"].duplicated()

# Copy weight only for first occurrence
statement_df.loc[first_occurrence, "Unique_Person_Weight"] = (
    statement_df.loc[first_occurrence, "Weight"]
)

unique_people = first_occurrence.sum()

print(f"Unique Persons : {unique_people:,}")
print("Unique Person Weight Created Successfully.")

# ==========================================================
# STEP 4 - CALCULATE OVERLAP SECONDS, IMPRESSIONS & REACH
# ==========================================================

print("\nCalculating TV Metrics...")

# ----------------------------------------------------------
# Overlap Seconds
# Formula:
# Overlap_Seconds = duration_seconds × Weight
# ----------------------------------------------------------

statement_df["Overlap_Seconds"] = (
    statement_df["duration_seconds"] * statement_df["Weight"]
)

# ----------------------------------------------------------
# Impressions
# Formula:
# SUM(Overlap_Seconds)
# ----------------------------------------------------------

impressions = statement_df["Overlap_Seconds"].sum()

# ----------------------------------------------------------
# Reach
# Formula:
# SUM(Unique_Person_Weight)
# ----------------------------------------------------------

reach = pd.to_numeric(
    statement_df["Unique_Person_Weight"],
    errors="coerce"
).sum()

# ----------------------------------------------------------
# Add Summary Columns
# (same value for every row)
# ----------------------------------------------------------

statement_df["Impressions"] = impressions
statement_df["Reach"] = reach

print(f"Impressions : {impressions:,.2f}")
print(f"Reach       : {reach:,.2f}")

print("\nStep 4 Completed Successfully.")

# ==========================================================
# STEP 5 - CALCULATE ATS, REACH %, TOTAL TV RATING
# ==========================================================

print("\nCalculating Final TV Metrics...")

# ----------------------------------------------------------
# ATS (Seconds)
# Formula:
# ATS = Impressions / Reach
# ----------------------------------------------------------

ats_seconds = impressions / reach if reach > 0 else 0

# ----------------------------------------------------------
# Convert ATS Seconds to HH:MM:SS
# ----------------------------------------------------------

hours = int(ats_seconds // 3600)
minutes = int((ats_seconds % 3600) // 60)
seconds = int(round(ats_seconds % 60))

# Handle rounding case (e.g., 59.9 sec -> 60)
if seconds == 60:
    seconds = 0
    minutes += 1

if minutes == 60:
    minutes = 0
    hours += 1

ats_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# ----------------------------------------------------------
# Round Off Reach
# Excel:
# =ROUND((Reach/1000),2)
# ----------------------------------------------------------

round_off_reach = round(reach / 1000, 2)

# ----------------------------------------------------------
# Reach %
# Excel:
# =ROUND((RoundOffReach/3067400)*100000,2)
# ----------------------------------------------------------

reach_percent = round(
    (round_off_reach / POPULATION) * 100000,
    2
)

# ----------------------------------------------------------
# Total TV Rating
# Excel:
# =ROUND(((Impressions/86400)/3067400)*100,2)
# ----------------------------------------------------------

total_tv_rating = round(
    ((impressions / 86400) / POPULATION) * 100,
    2
)

# ----------------------------------------------------------
# Add Columns
# ----------------------------------------------------------

statement_df["ATS (Seconds)"] = ats_seconds
statement_df["ATS"] = ats_time
statement_df["Round off Reach"] = round_off_reach
statement_df["Reach %"] = reach_percent
statement_df["Total TV Rating"] = total_tv_rating

# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------

print(f"ATS (Seconds)     : {ats_seconds:.6f}")
print(f"ATS               : {ats_time}")
print(f"Round Off Reach   : {round_off_reach}")
print(f"Reach %           : {reach_percent}")
print(f"Total TV Rating   : {total_tv_rating}")

print("\nStep 5 Completed Successfully.")

# ==========================================================
# STEP 6 - SAVE OUTPUT TO EXCEL
# ==========================================================

print("\nSaving Output File...")

# ----------------------------------------------------------
# Statement Sheet
# ----------------------------------------------------------

output_columns = [
    "date",
    "hhid",
    "tv_set",
    "member_id",
    "channel",
    "start_time",
    "end_time",
    "duration",
    "duration_seconds",
    "type",
    "start_time_secs",
    "channelid",
    "Indi_id",
    "Weight",
    "Unique_Person_Weight",
    "Overlap_Seconds"
]

output_df = statement_df[output_columns].copy()

# ----------------------------------------------------------
# Summary Sheet
# ----------------------------------------------------------

summary_df = pd.DataFrame({
    "Metric": [
        "Impressions",
        "Reach",
        "ATS (Seconds)",
        "ATS",
        "Round off Reach",
        "Reach %",
        "Total TV Rating"
    ],
    "Value": [
        round(impressions, 2),
        round(reach, 2),
        round(ats_seconds, 6),
        ats_time,
        round_off_reach,
        reach_percent,
        total_tv_rating
    ]
})

# ----------------------------------------------------------
# Output File
# ----------------------------------------------------------

OUTPUT_FOLDER = SCRIPT_DIR

output_file = os.path.join(
    OUTPUT_FOLDER,
    f"{panel_date}_Total_TV_Rating.xlsx"
)

# ----------------------------------------------------------
# Save Excel
# ----------------------------------------------------------

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:

    # Sheet 1
    output_df.to_excel(
        writer,
        sheet_name="Statement",
        index=False
    )

    # Sheet 2
    summary_df.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

    # Formatting
    for sheet in writer.sheets.values():

        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        for column_cells in sheet.columns:

            max_length = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells
            )

            sheet.column_dimensions[
                column_cells[0].column_letter
            ].width = max_length + 3

print("\n==========================================")
print("TOTAL TV RATING COMPLETED SUCCESSFULLY")
print("==========================================")
print(f"Output File : {output_file}")