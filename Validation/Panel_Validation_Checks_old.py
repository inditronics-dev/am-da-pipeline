# ============================================
# INSTALL REQUIRED PACKAGES
# ============================================
# pip install pandas openpyxl psycopg2-binary

# ============================================
# IMPORT LIBRARIES
# ============================================
import pandas as pd
import psycopg2
import re
import sys
from file_path import *
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font

# ============================================
# VALID VALUES
# ============================================
VALID_REGIONS = [
    "Yerevan",
    "Vanadzor",
    "Artashat",
    "Hrazdan",
    "Gavar",
    "Gyumri",
    "Ashtarak",
    "Vagharshapat",
    "Ijevan",
    "Kapan",
    "Yeghegnadzor"
]

VALID_CITY_GROUPS = [
    "Yerevan",
    "Rest of Armenia"
]

CITY_TOTAL_POP = {

    "Yerevan": 1136300,

    "Rest of Armenia": 1931100

}
CITY_BENCHMARKS = {

    "Yerevan": {
    "POP_TOTAL": 1136300,
    "GENDER_TARGETS": {
        "Male": 0.44785,
        "Female": 0.55215
    },
    "POP_AGE_GENDER": {
        "3-17_Male": 0.07380,
        "18-20_Male": 0.01500,
        "21-29_Male": 0.04860,
        "30-39_Male": 0.06935,
        "40-49_Male": 0.06599,
        "50-59_Male": 0.05110,
        "60+_Male": 0.12401,

        "3-17_Female": 0.09099,
        "18-20_Female": 0.01849,
        "21-29_Female": 0.05992,
        "30-39_Female": 0.08550,
        "40-49_Female": 0.08136,
        "50-59_Female": 0.06300,
        "60+_Female": 0.15289
    }
 },


    "Rest_of_Armenia": {
    "POP_TOTAL": 1931100,
    "GENDER_TARGETS": {
        "Male": 0.48477,
        "Female": 0.51523
    },
    "POP_AGE_GENDER": {
        "3-17_Male": 0.10247,
        "18-20_Male": 0.01804,
        "21-29_Male": 0.04965,
        "30-39_Male": 0.07660,
        "40-49_Male": 0.06445,
        "50-59_Male": 0.05609,
        "60+_Male": 0.11748,

        "3-17_Female": 0.10890,
        "18-20_Female": 0.01917,
        "21-29_Female": 0.05277,
        "30-39_Female": 0.08141,
        "40-49_Female": 0.06850,
        "50-59_Female": 0.05961,
        "60+_Female": 0.12486
    }
 }
}

EXPECTED_TOTAL_POPULATION = 3067400


# ============================================
# GET DATE ARGUMENT
# ============================================
from datetime import datetime, timedelta

run_date = (
    os.environ.get("RUN_DATE")
    or os.environ.get("WORKFLOW_DATE")
)

if not run_date:
    run_date = (
        datetime.now() - timedelta(days=1)
    ).strftime("%Y-%m-%d")

process_date = datetime.strptime(
    run_date,
    "%Y-%m-%d"
).strftime("%d-%m-%Y")

# ============================================
# GENERATE FILE PATHS
# ============================================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

PANEL_FOLDER = os.path.join(
    BASE_DIR,
    "Panel",
    "Panel Files"
)

PANEL_FILE = os.path.join(
    PANEL_FOLDER,
    f"{process_date}_combined_weighted.csv"
)

# ============================================
# READ PANEL FILE
# ============================================
df = pd.read_csv(PANEL_FILE)

df.columns = df.columns.str.strip()

# ============================================
# CONNECT DATABASE
# ============================================
print("Connecting Database...")

DB_HOST = "armenia-db-01.c960kiumy09x.ap-south-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "meter01"
DB_USER = "postgres"
DB_PASSWORD = "inditronics123"

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

QUERY = """
 WITH latest_households AS (
    SELECT DISTINCT ON (household_id)
        household_id,
        assigned_by,
        assigned_at
    FROM (
        SELECT DISTINCT ON (ma.meter_id)
            h.hhid AS household_id,
            ma.assigned_by,
            ma.assigned_at
        FROM meter_assignments ma
        JOIN meters m
            ON ma.meter_id = m.id
        JOIN households h
            ON ma.household_id = h.id
        WHERE m.meter_id >= 'IM000101'
          AND m.meter_id <= 'IM000600'
        ORDER BY ma.meter_id, ma.assigned_at DESC
    ) latest_per_meter
    ORDER BY household_id, assigned_at DESC
)

SELECT
    h.hhid,
    m.member_code,
    m.gender,
    h.city,
    h.region,
    DATE_PART('year', AGE(CURRENT_DATE, m.dob)) AS age,
    lh.assigned_by,
    lh.assigned_at
FROM latest_households lh
JOIN households h
    ON h.hhid = lh.household_id
JOIN members m
    ON h.id = m.household_id
ORDER BY
    h.hhid,
    m.member_code;
"""

db_df = pd.read_sql(QUERY, conn)

conn.close()

db_df.columns = db_df.columns.str.strip()

# ============================================
# VALIDATION EXCEL
# ============================================
import shutil

VALIDATION_FILE = os.path.join(
    os.path.dirname(__file__),
    "Data Validation Check.xlsx"
)

OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__),
    "Data Validation Check Completed.xlsx"
)

# Create output file if not exists
if not os.path.exists(OUTPUT_FILE):
    shutil.copy2(
        VALIDATION_FILE,
        OUTPUT_FILE
    )

print(f"Updating Excel : {OUTPUT_FILE}")

# ============================================
# LOAD EXCEL
# ============================================
wb = load_workbook(OUTPUT_FILE)

ws = wb["Sheet1"]
# ============================================
# COLORS
# ============================================
GREEN_FILL = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")

RED_FILL = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")

BOLD_FONT = Font(bold=True)

# ============================================
# UPDATE FUNCTION
# ============================================
def update_validation(text_to_find, status, remarks=""):

    found = False

    for row in ws.iter_rows():

        for cell in row:

            if cell.value and text_to_find.lower() in str(cell.value).lower():

                status_cell = ws.cell(row=cell.row, column=4)
                remarks_cell = ws.cell(row=cell.row, column=5)

                status_cell.value = status
                remarks_cell.value = remarks

                status_cell.font = BOLD_FONT

                if status == "PASS":
                    status_cell.fill = GREEN_FILL
                else:
                    status_cell.fill = RED_FILL

                found = True

                print(f"Updated : {text_to_find}")

                return

    if not found:
        print(f"Text Not Found : {text_to_find}")

# ============================================
# 1. POPULATION VALIDATION
# ============================================
population_failures = []

region_population = (
    df.groupby("City_Group")["final_weight_scaled"]
    .sum()
    .round()
    .astype(int)
)

for region, expected_pop in CITY_TOTAL_POP.items():

    actual_pop = int(region_population.get(region, 0))

    if actual_pop != expected_pop:

        population_failures.append(
            f"{region}: Actual={actual_pop}, Expected={expected_pop}"
        )

total_population = int(round(df["final_weight_scaled"].sum()))

if total_population != EXPECTED_TOTAL_POPULATION:

    population_failures.append(
        f"Total Population: Actual={total_population}, Expected={EXPECTED_TOTAL_POPULATION}"
    )

if len(population_failures) == 0:

    update_validation(
        "Validate that final_weight_scaled equals to Armenia and region wise population ",
        "PASS"
    )

else:

    update_validation(
        "Validate that final_weight_scaled equals to Armenia and region wise population ",
        "FAIL",
        " | ".join(population_failures)
    )

# ============================================
# 2. HHID VALIDATION
# ============================================
hhid_counts = df.groupby("HH_City")["hhid"].nunique()

failed_regions = []

for region, count in hhid_counts.items():

    hhid_counts = (
    df.groupby("HH_City")["hhid"]
    .nunique()
    )

    failed_regions = []

    for region, count in hhid_counts.items():

        if count < 5:

            failed_regions.append(
                f"{region}={count}"
            )

    else:

        if count < 5:

            failed_regions.append(
                f"{region}={count}"
            )

if len(failed_regions) == 0:

    update_validation(
        "Ensure each region has a minimum of 5 HHIDs",
        "PASS"
    )

else:

    update_validation(
        "Ensure each region has a minimum of 5 HHIDs",
        "FAIL",
        ", ".join(failed_regions)
    )

# ============================================
# 3. HHID VALIDATION
# ============================================
hhid_counts = (
    df.groupby("HH_City")["hhid"]
    .nunique()
)

failed_regions = []

# Regions with fewer installed meters in DB
EXCEPTION_REGIONS = {
    "Yeghegnadzor": 1
}

for region, count in hhid_counts.items():

    if region in EXCEPTION_REGIONS:

        # Accept exactly the installed meter count
        if count != EXCEPTION_REGIONS[region]:

            failed_regions.append(
                f"{region}={count}"
            )

    else:

        if count < 5:

            failed_regions.append(
                f"{region}={count}"
            )

if len(failed_regions) == 0:

    update_validation(
        "Ensure each region has a minimum of 5 HHIDs",
        "PASS"
    )

else:

    update_validation(
        "Ensure each region has a minimum of 5 HHIDs",
        "FAIL",
        ", ".join(failed_regions)
    )

# ============================================
# 4. HH_CITY VALIDATION
# ============================================

invalid_regions = sorted(
    set(df["HH_City"].dropna().astype(str).str.strip())
    - set(VALID_REGIONS)
)

if len(invalid_regions) == 0:

    update_validation(
        "Ensure that the HH_City column contains only",
        "PASS"
    )

else:

    update_validation(
        "Ensure that the HH_City column contains only",
        "FAIL",
        ", ".join(invalid_regions)
    )
# ============================================
# 4. CITY_GROUP VALIDATION
# ============================================
invalid_groups = sorted(
    set(df["City_Group"].dropna().astype(str).str.strip()) - set(VALID_CITY_GROUPS)
)

if len(invalid_groups) == 0:

    update_validation(
        "Ensure that the City_Group column contains only",
        "PASS"
    )

else:

    update_validation(
        "Ensure that the City_Group column contains only",
        "FAIL",
        ", ".join(invalid_groups)
    )

# ============================================
# 6. REGION × AGE × GENDER VALIDATION
# ============================================

validation_errors = []

for city, benchmark in CITY_BENCHMARKS.items():

    city_name = city.replace("_", " ")

    city_df = df[
        df["City_Group"].astype(str).str.strip() == city_name
    ]

    if city_df.empty:

        validation_errors.append(f"{city_name} : No records")
        continue

    grouped = (
        city_df
        .groupby(["Reporting_Age_Group", "Sex"])["final_weight_scaled"]
        .sum()
    )

    total = city_df["final_weight_scaled"].sum()

    for key, expected_ratio in benchmark["POP_AGE_GENDER"].items():

        age_group, gender = key.split("_", 1)

        actual_ratio = grouped.get((age_group, gender), 0) / total

        if abs(actual_ratio - expected_ratio) > 0.0001:

            validation_errors.append(
                f"{city_name}-{age_group}-{gender}"
            )

if len(validation_errors) == 0:

    update_validation(
        "Ensure that weights are applied to the correct Region × Age × Gender group",
        "PASS"
    )

else:

    update_validation(
        "Ensure that weights are applied to the correct Region × Age × Gender group",
        "FAIL",
        " | ".join(validation_errors[:10])
    )

# ============================================
# 5. AGE GROUP FORMAT VALIDATION
# ============================================
age_pattern = re.compile(r"^\d{1,2}-\d{1,2}$|^\d{1,2}\+$")

invalid_age_groups = []

unique_age_groups = (
    df["Reporting_Age_Group"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

for age_grp in unique_age_groups:

    if not age_pattern.match(age_grp):

        invalid_age_groups.append(age_grp)

if len(invalid_age_groups) == 0:

    update_validation(
        "Ensure that the age group is in the correct format.Example: “3-17” is the correct format.Check and ensure there are no incorrectly formatted values such as “17-Mar”",
        "PASS"
    )

else:

    update_validation(
        "Ensure that the age group is in the correct format.Example: “3-17” is the correct format.Check and ensure there are no incorrectly formatted values such as “17-Mar”",
        "FAIL",
        ", ".join(invalid_age_groups)
    )

# ============================================
# 6. HHID REGION MAPPING VALIDATION
# ============================================
panel_map = (
    df[["hhid", "HH_City"]]
    .drop_duplicates()
)

db_map = (
    db_df[["hhid", "region"]]
    .drop_duplicates()
)

merged = panel_map.merge(
    db_map,
    on="hhid",
    how="left"
)

mismatch_df = merged[
    merged["HH_City"].astype(str).str.strip().str.lower()
    !=
    merged["region"].astype(str).str.strip().str.lower()
]

if len(mismatch_df) == 0:

    update_validation(
        "Map HHIDs to the correct regions as per the database data",
        "PASS"
    )

else:

    mismatch_list = []

    for _, row in mismatch_df.iterrows():

        mismatch_list.append(
            f"{row['hhid']} FILE={row['HH_City']} DB={row['region']}"
        )

    update_validation(
        "Map HHIDs to the correct regions as per the database data",
        "FAIL",
        " | ".join(mismatch_list[:10])
    )

# ============================================
# SAVE OUTPUT
# ===========================================
print(f"Saving to : {OUTPUT_FILE}")

wb.save(OUTPUT_FILE)

print("\n======================================")
print("VALIDATION COMPLETED")
print("======================================")
print(f"Output File Saved : {OUTPUT_FILE}")
print("======================================")