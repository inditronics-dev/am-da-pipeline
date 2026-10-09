# ============================================================
# STEP 1 – AUTO CITY PROCESSING (MINIMUM 5 INTAB RULE)
# ============================================================

import pandas as pd
import os
import re
import smtplib

from datetime import datetime, timedelta
from email.message import EmailMessage

import psycopg2
import yaml


# ============================================================
# DB CONFIG
# ============================================================

DB_HOST = "armenia-db-01.c960kiumy09x.ap-south-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "meter01"
DB_USER = "postgres"
DB_PASSWORD = "inditronics123"


# ============================================================
# INPUT / OUTPUT PATHS
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

INPUT_FOLDER = os.path.join(
    BASE_DIR,
    "for_panel_files",
    "for_panel"
)

OUTPUT_FOLDER = os.path.join(
    BASE_DIR,
    "Panel",
    "Panel Files"
)

# ============================================================
# EMAIL CONFIGURATION
# ============================================================

SENDER_EMAIL = "indi_dataops@inditronics.com"

# Gmail App Password
APP_PASSWORD = "jeft eidg wyhs axdi"

RECEIVER_EMAILS = [
    "senthil.kumar@inditronics.com"
]

# ============================================================
# QUERY
# ============================================================


# QUERY = """
# SELECT
#     h.hhid,
#     m.member_code,
#     m.gender,
#     region,
#     DATE_PART('year', AGE(CURRENT_DATE, m.dob)) AS age
# FROM households h
# JOIN members m
#     ON h.id = m.household_id
# """

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
# ============================================================
# CONNECTION FUNCTION
# ============================================================

def load_master_from_db():

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    members_all = pd.read_sql(QUERY, conn)

    conn.close()

    members_all.columns = (
        members_all.columns
        .str.lower()
        .str.strip()
    )

    return members_all

# ============================================================
# AGE LOGIC
# ============================================================

def weighted_group(age):
    if age <= 17: return "3-17"
    elif age <= 20: return "18-20"
    elif age <= 29: return "21-29"
    elif age <= 39: return "30-39"
    elif age <= 49: return "40-49"
    elif age <= 59: return "50-59"
    else: return "60+"


def reporting_group(age):
    if age <= 17: return "3-17"
    elif age <= 20: return "18-20"
    elif age <= 29: return "21-29"
    elif age <= 39: return "30-39"
    elif age <= 49: return "40-49"
    elif age <= 59: return "50-59"
    else: return "60+"

def sub_age_group(age):

    if 3 <= age <= 7:
        return "3-7"

    elif 8 <= age <= 12:
        return "8-12"

    elif 13 <= age <= 17:
        return "13-17"

    elif 18 <= age <= 19:
        return "18-19"

    elif age == 20:
        return "20"

    elif 21 <= age <= 24:
        return "21-24"

    elif age == 25:
        return "25"

    elif 26 <= age <= 29:
        return "26-29"

    elif age == 30:
        return "30"

    elif 31 <= age <= 34:
        return "31-34"

    elif age == 35:
        return "35"

    elif 36 <= age <= 39:
        return "36-39"

    elif age == 40:
        return "40"

    elif 41 <= age <= 44:
        return "41-44"

    elif age == 45:
        return "45"

    elif 46 <= age <= 49:
        return "46-49"

    elif age == 50:
        return "50"

    elif 51 <= age <= 54:
        return "51-54"

    elif age == 55:
        return "55"

    elif 56 <= age <= 59:
        return "56-59"

    elif age == 60:
        return "60"

    elif 61 <= age <= 64:
        return "61-64"

    elif age == 65:
        return "65"

    elif 66 <= age <= 69:
        return "66-69"

    elif age >= 70:
        return "70+"

    else:
        return None

# ============================================================
# REQUIRED WEIGHTING CELLS
# ============================================================

MAIN_AGE_GROUPS = [
    "3-17",
    "18-20",
    "21-29",
    "30-39",
    "40-49",
    "50-59",
    "60+"
]

SUB_AGE_GROUPS = [
    "3-7",
    "8-12",
    "13-17",
    "18-19",
    "20",
    "21-24",
    "25",
    "26-29",
    "30",
    "31-34",
    "35",
    "36-39",
    "40",
    "41-44",
    "45",
    "46-49",
    "50",
    "51-54",
    "55",
    "56-59",
    "60",
    "61-64",
    "65",
    "66-69",
    "70+"
]

GENDERS = [
    "Male",
    "Female"
]
# ============================================================
# REQUIRED MEMBERS PER SUB-AGE GROUP AND GENDER
# ============================================================

SUB_AGE_REQUIRED_COUNTS = {
    "3-7": 5,
    "8-12": 5,
    "13-17": 5,
    "18-19": 2,
    "20": 1,
    "21-24": 4,
    "25": 1,
    "26-29": 4,
    "30": 1,
    "31-34": 4,
    "35": 1,
    "36-39": 4,
    "40": 1,
    "41-44": 4,
    "45": 1,
    "46-49": 4,
    "50": 1,
    "51-54": 4,
    "55": 1,
    "56-59": 4,
    "60": 1,
    "61-64": 4,
    "65": 1,
    "66-69": 4,
    "70+": 10
}


# ============================================================
# CHECK AND SUPPLEMENT INDIVIDUAL MEMBERS
# ============================================================

def hhid_sort_key(hhid):
    """
    Sort HHIDs naturally:
    HH2 < HH10 < HH100
    """
    hhid_text = str(hhid).strip()

    digits = "".join(
        character for character in hhid_text
        if character.isdigit()
    )

    if digits:
        return (0, int(digits), hhid_text)

    return (1, hhid_text)

def check_and_supplement_members(
    intab_members_df,
    region_master,
    group_name,
    process_date
):

    supplemented_members = []

    # --------------------------------------------------------
    # PREPARE INTAB DATA
    # --------------------------------------------------------

    intab_members_df = intab_members_df.copy()

    intab_members_df["Sex"] = (
        intab_members_df["gender"]
        .astype(str)
        .str.strip()
    )

    intab_members_df["Actual_age"] = intab_members_df["age"]

    intab_members_df["Weighted_Age_Group"] = (
        intab_members_df["Actual_age"]
        .apply(weighted_group)
    )

    intab_members_df["Sub_Age_Group"] = (
        intab_members_df["Actual_age"]
        .apply(sub_age_group)
    )

    # --------------------------------------------------------
    # PREPARE MASTER DATA
    # --------------------------------------------------------

    master_pool = region_master.copy()

    master_pool["Sex"] = (
        master_pool["gender"]
        .astype(str)
        .str.strip()
    )

    master_pool["Actual_age"] = master_pool["age"]

    master_pool["Weighted_Age_Group"] = (
        master_pool["Actual_age"]
        .apply(weighted_group)
    )

    master_pool["Sub_Age_Group"] = (
        master_pool["Actual_age"]
        .apply(sub_age_group)
    )

    # --------------------------------------------------------
    # EXISTING SELECTED MEMBERS
    # --------------------------------------------------------

    selected_member_keys = set(
        zip(
            intab_members_df["hhid"],
            intab_members_df["member_code"]
        )
    )

    # --------------------------------------------------------
    # CALCULATE MISSING SUB-AGE × GENDER REQUIREMENTS
    # --------------------------------------------------------

    missing_requirements = []

    for sub_group in SUB_AGE_GROUPS:

        required_count = SUB_AGE_REQUIRED_COUNTS.get(
            sub_group,
            0
        )

        for gender in GENDERS:

            existing_count = intab_members_df[
                (
                    intab_members_df["Sub_Age_Group"]
                    == sub_group
                )
                &
                (
                    intab_members_df["Sex"]
                    == gender
                )
            ].shape[0]

            shortage = max(
                required_count - existing_count,
                0
            )

            if shortage > 0:

                missing_requirements.append({
                    "Sub_Age_Group": sub_group,
                    "Gender": gender,
                    "Required": required_count,
                    "Existing": existing_count,
                    "Shortage": shortage
                })

    print(
        f"\n{group_name} - Missing detailed requirements:"
    )

    for requirement in missing_requirements:
        print(requirement)

    # --------------------------------------------------------
    # SELECT MEMBERS BY PRIORITY
    #
    # Priority 1:
    # Prefer one household that can satisfy multiple
    # missing requirements.
    #
    # Priority 2:
    # If the same member requirement is available in
    # multiple households, choose the smallest HHID.
    #
    # Only individual members are selected.
    # --------------------------------------------------------

    while True:

        # Recalculate remaining shortages
        remaining_requirements = []

        for sub_group in SUB_AGE_GROUPS:

            required_count = SUB_AGE_REQUIRED_COUNTS.get(
                sub_group,
                0
            )

            for gender in GENDERS:

                existing_count = intab_members_df[
                    (
                        intab_members_df["Sub_Age_Group"]
                        == sub_group
                    )
                    &
                    (
                        intab_members_df["Sex"]
                        == gender
                    )
                ].shape[0]

                shortage = max(
                    required_count - existing_count,
                    0
                )

                if shortage > 0:

                    remaining_requirements.append({
                        "Sub_Age_Group": sub_group,
                        "Gender": gender,
                        "Shortage": shortage
                    })

        if not remaining_requirements:
            break

        # ----------------------------------------------------
        # FIND AVAILABLE MEMBERS FOR MISSING REQUIREMENTS
        # ----------------------------------------------------

        available_candidates = master_pool[
            ~master_pool.apply(
                lambda row: (
                    row["hhid"],
                    row["member_code"]
                ) in selected_member_keys,
                axis=1
            )
        ].copy()

        available_candidates = available_candidates[
            available_candidates["Sub_Age_Group"].notna()
        ]

        # ----------------------------------------------------
        # FIND THE BEST HOUSEHOLD
        # ----------------------------------------------------

        best_hhid = None
        best_matches = set()
        best_hh_member_rows = None

        for hhid, household_df in available_candidates.groupby(
            "hhid"
        ):

            household_matches = set()

            for _, member in household_df.iterrows():

                requirement_key = (
                    member["Sub_Age_Group"],
                    member["Sex"]
                )

                for requirement in remaining_requirements:

                    required_key = (
                        requirement["Sub_Age_Group"],
                        requirement["Gender"]
                    )

                    if requirement_key == required_key:
                        household_matches.add(
                            requirement_key
                        )

            if not household_matches:
                continue

            # Priority 1:
            # Household matching more missing requirements wins
            if len(household_matches) > len(best_matches):

                best_hhid = hhid
                best_matches = household_matches
                best_hh_member_rows = household_df

            # Priority 2:
            # If equal number of matches, choose smallest HHID
            elif (
                len(household_matches)
                == len(best_matches)
                and best_hhid is not None
                and hhid_sort_key(hhid) < hhid_sort_key(best_hhid)
            ):

                best_hhid = hhid
                best_matches = household_matches
                best_hh_member_rows = household_df

        # ----------------------------------------------------
        # NO CANDIDATE AVAILABLE
        # ----------------------------------------------------

        if best_hhid is None:

            print(
                f"WARNING: Could not satisfy remaining "
                f"requirements for {group_name}: "
                f"{remaining_requirements}"
            )

            break

        # ----------------------------------------------------
        # SELECT ONLY REQUIRED MEMBERS FROM THIS HOUSEHOLD
        # ----------------------------------------------------

        selected_rows = []

        for requirement_key in sorted(best_matches):

            sub_group, gender = requirement_key

            # Find current shortage for this requirement
            current_count = intab_members_df[
                (
                    intab_members_df["Sub_Age_Group"]
                    == sub_group
                )
                &
                (
                    intab_members_df["Sex"]
                    == gender
                )
            ].shape[0]

            required_count = SUB_AGE_REQUIRED_COUNTS[
                sub_group
            ]

            shortage = max(
                required_count - current_count,
                0
            )

            if shortage <= 0:
                continue

            matching_members = best_hh_member_rows[
                (
                    best_hh_member_rows["Sub_Age_Group"]
                    == sub_group
                )
                &
                (
                    best_hh_member_rows["Sex"]
                    == gender
                )
            ].copy()

            # Sort members by member code for deterministic selection
            matching_members = matching_members.sort_values(
                by=["member_code"]
            )

            # Select only the number of members required
            selected_members = matching_members.head(shortage)

            for _, member in selected_members.iterrows():

                member_key = (
                    member["hhid"],
                    member["member_code"]
                )

                if member_key in selected_member_keys:
                    continue

                selected_rows.append(member)

                selected_member_keys.add(member_key)

        # ----------------------------------------------------
        # IF NO MEMBER WAS SELECTED, STOP TO AVOID INFINITE LOOP
        # ----------------------------------------------------

        if not selected_rows:

            print(
                f"WARNING: No individual members selected "
                f"for {group_name} from HHID {best_hhid}"
            )

            break

        # ----------------------------------------------------
        # APPEND ONLY SELECTED MEMBER ROWS
        # ----------------------------------------------------

        selected_members_df = pd.DataFrame(selected_rows)

        intab_members_df = pd.concat(
            [
                intab_members_df,
                selected_members_df
            ],
            ignore_index=True
        )

        # ----------------------------------------------------
        # WRITE ONE REPORT ROW PER SELECTED MEMBER
        # ----------------------------------------------------

        for _, member in selected_members_df.iterrows():

            member_requirement_name = (
                f"{member['Sub_Age_Group']}_{member['Sex']}"
            )

            supplemented_members.append({

                "Selection_Hierarchy": "1_Sub_Age_Individual",

                "Group": group_name,

                "HHID": member["hhid"],

                "Matched_Requirements": member_requirement_name,

                "Number_Requirements_Matched": 1,

                "Member_Code": member["member_code"],

                "Actual_Age": member["Actual_age"],

                "Age_Group": member["Weighted_Age_Group"],

                "Sub_Age_Group": member["Sub_Age_Group"],

                "Gender": member["Sex"],

                "Region": member["region"]

            })

    return (
        intab_members_df,
        supplemented_members
    )
# ============================================================
# MAIN FUNCTION
# ============================================================

def run_step1(process_date, selected_cities):

    print(f"\nRunning Step-1 for {process_date}")

    process_dt = datetime.strptime(
        process_date,
        "%d-%m-%Y"
    )

    # ============================================================
    # INPUT CLEANED FILE
    # ============================================================

    process_date_obj = datetime.strptime(
        process_date,
        "%d-%m-%Y"
    )

    file_date = process_date_obj.strftime("%Y-%m-%d")

    expected_file = f"{file_date}_cleaned.csv"

    input_file = os.path.join(
        INPUT_FOLDER,
        expected_file
    )

    if not os.path.exists(input_file):

        raise Exception(
            f"Input cleaned file not found: {expected_file}"
        )

    print(f"Input file found: {expected_file}")

    # --------------------------------------------------------
    # RAW FILE DETECTION
    # --------------------------------------------------------

    expected_file = f"{file_date}_cleaned.csv"

    raw_file_path = os.path.join(
        INPUT_FOLDER,
        expected_file
    )

    if not os.path.exists(raw_file_path):
        raise Exception(
            f"File not found: {expected_file}"
        )

    print(f"Using raw file: {expected_file}")

    raw = pd.read_csv(raw_file_path)
    raw.columns = raw.columns.str.lower().str.strip()

    raw_unique_hhids = set(raw["hhid"].drop_duplicates())

    # --------------------------------------------------------
    # LOAD MASTER FROM DATA BASE
    # --------------------------------------------------------

    members_all = load_master_from_db()

    # ============================================================
    # OUTPUT DIRECTORY
    # ALL OUTPUT FILES SAVED DIRECTLY INSIDE Panel Files
    # ============================================================

    output_dir = OUTPUT_FOLDER

    os.makedirs(output_dir, exist_ok=True)

    # ========================================================
    # PROCESS EACH CITY
    # ========================================================

    YEREVAN_CITY = ["Yerevan"]

    REST_CITIES = [
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

    CITY_GROUPS = {
        "Yerevan": YEREVAN_CITY,
        "Rest_of_Armenia": REST_CITIES
    }
    # ============================================================
    # SUPPLEMENTATION REPORT DATA
    # ============================================================

    supplementation_report = {
        "Yerevan": [],
        "Rest_of_Armenia": []
    }
    summary_table = []

    for group_name, cities in CITY_GROUPS.items():


        region_master = members_all[
            members_all["region"].isin(cities)
        ].copy()

        region_master_hhids = set(region_master["hhid"])
        region_raw_hhids = raw_unique_hhids & region_master_hhids

        # ================= VIEWERSHIP =================

        viewership_df = raw[
            raw["hhid"].isin(region_raw_hhids)
        ]

        viewership_hh_count = len(region_raw_hhids)

        viewership_member_count = (
            viewership_df[["hhid", "member_id"]]
            .drop_duplicates()
            .shape[0]
        )

        # ================= INTAB (MINIMUM 5 RULE) =================

        intab_hhids = set()

        for city in cities:

            city_master = region_master[
                region_master["region"] == city
            ]

            city_master_hhids = set(city_master["hhid"])

            city_raw_hhids = raw_unique_hhids & city_master_hhids

            city_intab_hhids = set(city_raw_hhids)

            target_intab = min(
                max(5, len(city_raw_hhids)),
                len(city_master_hhids)
            )

            # Select the smallest HHIDs from the remaining database pool.
            # Raw HHIDs are already retained first.

            remaining_pool = sorted(
                city_master_hhids - city_intab_hhids,
                key=hhid_sort_key
            )

            needed_hhids = target_intab - len(city_intab_hhids)

            selected_extra_hhids = remaining_pool[:needed_hhids]

            city_intab_hhids.update(selected_extra_hhids)

            intab_hhids.update(city_intab_hhids)

        raw_hh_count = len(region_raw_hhids)
        intab_hh_count = len(intab_hhids)
        intab_members_df = region_master[
            region_master["hhid"].isin(intab_hhids)
        ].copy()
        # ============================================================
        # CHECK MISSING AGE / GENDER GROUPS
        # AND SUPPLEMENT FROM DATABASE
        # ============================================================

        intab_members_df, supplemented_members = (
            check_and_supplement_members(
                intab_members_df=intab_members_df,
                region_master=region_master,
                group_name=group_name,
                process_date=process_date
            )
        )
        intab_hh_count = intab_members_df["hhid"].nunique()
        # Store supplementation details for Excel report
        supplementation_report[group_name].extend(
            supplemented_members
        )

        intab_member_count = (
            intab_members_df[["hhid", "member_code"]]
            .drop_duplicates()
            .shape[0]
        )

        # ================= AGE + GROUP =================

        intab_members_df["Date"] = process_date
        intab_members_df["Sex"] = intab_members_df["gender"]
        intab_members_df["Actual_age"] = intab_members_df["age"]

        intab_members_df["City_Group"] = (
            "Yerevan"
            if group_name == "Yerevan"
            else "Rest of Armenia"
        )

        intab_members_df["Weighted_Age_Group"] = (
            intab_members_df["Actual_age"]
            .apply(weighted_group)
        )

        intab_members_df["Reporting_Age_Group"] = \
            intab_members_df["Actual_age"].apply(reporting_group)
        intab_members_df["Sub_Age_Group"] = \
            intab_members_df["Actual_age"].apply(sub_age_group)
        
        intab_members_df["HH_City"] = intab_members_df["region"]

        final_df = intab_members_df[
            [
                "Date", "hhid", "member_code", "Sex",
                "Actual_age", "Weighted_Age_Group",
                "Reporting_Age_Group","Sub_Age_Group",
                "City_Group", "HH_City"
            ]
        ]

        # ====================================================
        # CITY WISE SUMMARY FOR Excel SHEET
        # ====================================================

        if group_name == "Rest_of_Armenia":

            for city in cities:

                city_master = region_master[
                    region_master["region"] == city
                ]

                city_intab = intab_members_df[
                    intab_members_df["HH_City"] == city
                ]

                city_master_hhids = set(city_master["hhid"])

                city_raw_hhids = (
                    raw_unique_hhids &
                    city_master_hhids
                )

                city_viewership_df = raw[
                    raw["hhid"].isin(city_raw_hhids)
                ]

                city_intab_hh_count = city_intab["hhid"].nunique()

                city_intab_member_count = (
                    city_intab[
                        ["hhid", "member_code"]
                    ]
                    .drop_duplicates()
                    .shape[0]
                )

                city_viewership_hh_count = len(city_raw_hhids)

                city_viewership_member_count = (
                    city_viewership_df[
                        ["hhid", "member_id"]
                    ]
                    .drop_duplicates()
                    .shape[0]
                )

                city_master = members_all[
                    members_all["region"] == city
                ]

                installed_hh = city_master["hhid"].nunique()

                installed_members = (
                    city_master[
                        ["hhid", "member_code"]
                    ]
                    .drop_duplicates()
                    .shape[0]
                )

                summary_table.append([
                    city,
                    installed_hh,
                    installed_members,
                    city_intab_hh_count,
                    city_intab_member_count,
                    city_viewership_hh_count,
                    city_viewership_member_count
                ])
        
        final_df.to_csv(
            os.path.join(
                output_dir,
                f"{process_date}_{group_name}.csv"
            ),
            index=False
        )


        if group_name == "Yerevan":

            

            installed_hh = region_master["hhid"].nunique()

            installed_members = (
                region_master[
                    ["hhid", "member_code"]
                ]
                .drop_duplicates()
                .shape[0]
            )

            summary_table.append([
                group_name,
                installed_hh,
                installed_members,
                intab_hh_count,
                intab_member_count,
                viewership_hh_count,
                viewership_member_count
            ])

        print(f"{group_name} RAW:{raw_hh_count} | INTAB:{intab_hh_count}")

    print("\nSUMMARY TABLE")
    print(summary_table)
    # ============================================================
    # CREATE SUMMARY CSV
    # ============================================================

    summary_file = os.path.join(
        output_dir,
        f"{process_date}_Summary.csv"
    )

    summary_columns = [
        "Region",
        "Installed_HH",
        "Installed_Members",
        "Intab_HH",
        "Intab_Members",
        "Viewership_HH",
        "Viewership_Members"
    ]

    summary_df = pd.DataFrame(
        summary_table,
        columns=summary_columns
    )
    # ============================================================
    # APPLY REQUIRED CITY ORDER
    # ============================================================

    SUMMARY_CITY_ORDER = [
        "Artashat",
        "Ashtarak",
        "Gavar",
        "Gyumri",
        "Hrazdan",
        "Ijevan",
        "Kapan",
        "Vagharshapat",
        "Vanadzor",
        "Yeghegnadzor",
        "Yerevan"
    ]

    summary_df["Region"] = pd.Categorical(
        summary_df["Region"],
        categories=SUMMARY_CITY_ORDER,
        ordered=True
    )

    summary_df = summary_df.sort_values(
        by="Region"
    ).reset_index(drop=True)

    # Convert Region back to normal string
    summary_df["Region"] = summary_df["Region"].astype(str)

    # Add total row
    total_row = pd.DataFrame([{
        "Region": "Total",
        "Installed_HH": summary_df["Installed_HH"].sum(),
        "Installed_Members": summary_df["Installed_Members"].sum(),
        "Intab_HH": summary_df["Intab_HH"].sum(),
        "Intab_Members": summary_df["Intab_Members"].sum(),
        "Viewership_HH": summary_df["Viewership_HH"].sum(),
        "Viewership_Members": summary_df["Viewership_Members"].sum()
    }])

    summary_df = pd.concat(
        [summary_df, total_row],
        ignore_index=True
    )

    summary_df.to_csv(
        summary_file,
        index=False
    )

    print(f"Summary CSV created: {summary_file}")
    # ============================================================
    # CREATE SUPPLEMENTATION REPORT EXCEL
    # ============================================================

    report_file = os.path.join(
        output_dir,
        f"{process_date}_Supplementation_Report.xlsx"
    )


    with pd.ExcelWriter(
        report_file,
        engine="openpyxl"
    ) as writer:

        # --------------------------------------------------------
        # YEREVAN SHEET
        # --------------------------------------------------------

        yerevan_report = pd.DataFrame(
            supplementation_report["Yerevan"]
        )

        if yerevan_report.empty:

            yerevan_report = pd.DataFrame({
                "Status": [
                    "No supplementation required"
                ]
            })

        yerevan_report.to_excel(
            writer,
            sheet_name="Yerevan",
            index=False
        )


        # --------------------------------------------------------
        # REST OF ARMENIA SHEET
        # --------------------------------------------------------

        rest_report = pd.DataFrame(
            supplementation_report["Rest_of_Armenia"]
        )

        if rest_report.empty:

            rest_report = pd.DataFrame({
                "Status": [
                    "No supplementation required"
                ]
            })

        rest_report.to_excel(
            writer,
            sheet_name="Rest of Armenia",
            index=False
        )


    print(
        f"\nSupplementation report created: "
        f"{report_file}"
    )
    print("\nSTEP-1 COMPLETED SUCCESSFULLY")

# ============================================================
# STEP - 2 (RIM WEIGHT)
# ============================================================
# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "config.yaml"
)


def load_config():

    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_FILE}"
        )

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


CONFIG = load_config()


# ============================================================
# RAKING CONFIGURATION
# ============================================================

raking_config = CONFIG["raking"]

GENDER_COL = raking_config["columns"]["gender"]
AGE_COL = raking_config["columns"]["age"]
SUB_AGE_COL = raking_config["columns"]["sub_age"]

TOLERANCE = raking_config["tolerance"]
MAX_ITER = raking_config["max_iterations"]


# ============================================================
# CITY BENCHMARKS
# ============================================================

CITY_BENCHMARKS = CONFIG["city_benchmarks"]


# ============================================================
# CITY GROUP MAPPING
# ============================================================

CITY_GROUP_MAPPING = {
    "Yerevan": "Yerevan",
    "Rest of Armenia": "Rest_of_Armenia"
}

# ============================================================
# MAIN AGE x GENDER RAKING
# ============================================================

def rake_main_age_gender(df, city, weight_col="weight"):

    bench = CITY_BENCHMARKS[city]

    POP_AGE_GENDER = bench["POP_AGE_GENDER"]

    df = df.copy()

    # Create Main Age x Gender Key
    df["AGE_GENDER"] = (
        df["Reporting_Age_Group"].astype(str)
        + "_"
        + df["Sex"].astype(str)
    )

    iterations_used = 0

    for it in range(MAX_ITER):

        iterations_used = it + 1

        # Current distribution
        current_dist = (
            df.groupby("AGE_GENDER")[weight_col]
            .sum()
        )

        current_dist = (
            current_dist / current_dist.sum()
        )

        # Apply Main Age x Gender targets
        for cell, target in POP_AGE_GENDER.items():

            if cell in current_dist.index:

                df.loc[
                    df["AGE_GENDER"] == cell,
                    weight_col
                ] *= target / current_dist[cell]

        # Check convergence
        check_dist = (
            df.groupby("AGE_GENDER")[weight_col]
            .sum()
        )

        check_dist = (
            check_dist / check_dist.sum()
        )

        if all(
            abs(check_dist.get(cell, 0) - target)
            <= TOLERANCE
            for cell, target in POP_AGE_GENDER.items()
        ):
            break

    return df, iterations_used


# ============================================================
# SUB AGE x GENDER RAKING
# ============================================================

def rake_sub_age_gender(df, city, weight_col="weight"):

    bench = CITY_BENCHMARKS[city]

    SUB_POP_AGE_GENDER = (
        bench["SUB_AGE_GENDER_TARGETS"]
    )

    df = df.copy()

    # Create Sub Age x Gender Key
    df["SUB_AGE_GENDER"] = (
        "Age_group_"
        + df["Sub_Age_Group"].astype(str)
        + "_"
        + df["Sex"].astype(str)
    )

    iterations_used = 0

    for it in range(MAX_ITER):

        iterations_used = it + 1

        # Current distribution
        current_dist = (
            df.groupby("SUB_AGE_GENDER")[weight_col]
            .sum()
        )

        current_dist = (
            current_dist / current_dist.sum()
        )

        # Apply Sub Age x Gender targets
        for cell, target in SUB_POP_AGE_GENDER.items():

            if cell in current_dist.index:

                df.loc[
                    df["SUB_AGE_GENDER"] == cell,
                    weight_col
                ] *= target / current_dist[cell]

        # Check convergence
        check_dist = (
            df.groupby("SUB_AGE_GENDER")[weight_col]
            .sum()
        )

        check_dist = (
            check_dist / check_dist.sum()
        )

        if all(
            abs(check_dist.get(cell, 0) - target)
            <= TOLERANCE
            for cell, target
            in SUB_POP_AGE_GENDER.items()
        ):
            break

    return df, iterations_used


# ============================================================
# COMPLETE 3-PASS RAKING
# ============================================================

def rake_dataframe(df, city):

    df = df.copy()

    POP_TOTAL = CITY_BENCHMARKS[city]["POP_TOTAL"]

    # --------------------------------------------------------
    # START WEIGHT
    # --------------------------------------------------------

    df["weight"] = 1.0

    # ========================================================
    # PASS 1
    # MAIN AGE x GENDER WEIGHTING
    # ========================================================

    print("\nPASS 1  MAIN AGE x GENDER WEIGHTING")

    df, main_iter_1 = rake_main_age_gender(
        df,
        city,
        "weight"
    )

    # Save for checking
    df["weight_after_main"] = df["weight"]

    # ========================================================
    # PASS 2
    # SUB AGE x GENDER FINE TUNING
    # ========================================================

    print("\nPASS 2  SUB AGE x GENDER FINE TUNING")

    df, sub_iter = rake_sub_age_gender(
        df,
        city,
        "weight"
    )

    # Save for checking
    df["weight_after_sub_age"] = df["weight"]

    # ========================================================
    # PASS 3
    # FINAL MAIN AGE x GENDER RECONCILIATION
    # ========================================================

    print("\nPASS 3  FINAL MAIN AGE x GENDER CHECK")

    df, main_iter_2 = rake_main_age_gender(
        df,
        city,
        "weight"
    )

    # ========================================================
    # FINAL WEIGHT
    # ========================================================

    df["final_weight"] = df["weight"]

    df["final_weight_scaled"] = (
        df["final_weight"]
        * (
            POP_TOTAL
            / df["final_weight"].sum()
        )
    )

    # ========================================================
    # ITERATION DETAILS
    # ========================================================

    df["main_raking_iterations_1"] = main_iter_1
    df["sub_age_raking_iterations"] = sub_iter
    df["main_raking_iterations_2"] = main_iter_2

    # ========================================================
    # REMOVE TEMPORARY WEIGHT
    # ========================================================

    df = df.drop(columns=["weight"])

    return df

# ============================================================
# MAIN FUNCTION
# ============================================================

def run_step2(process_date):

    folder_date = datetime.strptime(
        process_date, "%d-%m-%Y"
    ).strftime("%Y-%m-%d")

    input_dir = os.path.join(
    BASE_DIR,
    "Panel",
    "Panel Files"
    )

    # Save Step 2 outputs in the same folder as Step 1 outputs
    output_dir = input_dir

    os.makedirs(output_dir, exist_ok=True)
    files = [
    f"{process_date}_Rest_of_Armenia.csv",
    f"{process_date}_Yerevan.csv"
    ]

    missing_files = [
        fname
        for fname in files
        if not os.path.exists(os.path.join(input_dir, fname))
    ]

    if missing_files:
        raise FileNotFoundError(
            "The following Step 1 output files were not found:\n"
            + "\n".join(missing_files)
        )

    for fname in files:

        df = pd.read_csv(os.path.join(input_dir, fname))
        # Check Sub Age Group column
        if "Sub_Age_Group" not in df.columns:
            raise Exception(
                "Sub_Age_Group column not found. "
                "Please run updated Step 1 first."
            )

        city_group = (
            df["City_Group"]
            .dropna()
            .astype(str)
            .iloc[0]
        )

        if city_group not in CITY_GROUP_MAPPING:
            raise Exception(
                f"Unknown City_Group: {city_group}"
            )

        benchmark_key = CITY_GROUP_MAPPING[city_group]

        print(
            f"Processing: {fname} | "
            f"Benchmark: {benchmark_key}"
        )

        df_out = rake_dataframe(df, benchmark_key)

        # Add empty cols
        for col in ["SEC","HH_Income","HH_Education", "With_Child", "HH_Size"]:
            if col not in df_out.columns:
                df_out[col] = ""

        final_columns = [
            "Date",
            "hhid",
            "member_code",
            "Sex",
            "Actual_age",

            # Age Groups
            "Weighted_Age_Group",
            "Reporting_Age_Group",
            "Sub_Age_Group",

            # City
            "City_Group",
            "HH_City",

            # Raking Keys
            "AGE_GENDER",
            "SUB_AGE_GENDER",

            # Weight after each pass
            "weight_after_main",
            "weight_after_sub_age",

            # Final Weight
            "final_weight",
            "final_weight_scaled",

            # Iterations
            "main_raking_iterations_1",
            "sub_age_raking_iterations",
            "main_raking_iterations_2",

            # Other Variables
            "SEC",
            "HH_Income",
            "HH_Education",
            "With_Child",
            "HH_Size"
        ]

        df_out = df_out[final_columns]

        out_name = f"Raked_{fname.replace('.csv','.xlsx')}"

        df_out.to_excel(
            os.path.join(output_dir, out_name),
            index=False
        )

        print("Saved:", out_name)

    print("STEP 2 COMPLETED SUCCESSFULLY")
# ============================================================
# STEP 3 – COMBINE ALL STEP-2 FILES (PRODUCTION VERSION)
# ============================================================
# ============================================================
# AGE FIX FUNCTION (EXCEL SAFE)
# ============================================================

def clean_age(val):

    if pd.isna(val):
        return val

    # If Excel auto-converted to datetime
    if isinstance(val, pd.Timestamp):
        if val.month == 3:
            return "'3-" + str(val.day)

    val_str = str(val).strip()

    # If string like 14-Mar
    match = re.match(r"^(\d{1,2})-Mar", val_str, re.IGNORECASE)
    if match:
        day = match.group(1)
        return "'3-" + day

    return val_str


# ============================================================
# MAIN FUNCTION
# ============================================================

# ============================================================
# STEP 3 – COMBINE STEP-2 FILES
# ============================================================

def run_step3(process_date):

    print(f"\nRunning Step-3 Combine for {process_date}")

    # Same folder used by Step 1 and Step 2
    input_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "Panel Files"
    )

    # Step 3 output will also be saved in the same folder
    output_dir = input_dir

    os.makedirs(output_dir, exist_ok=True)

    # ========================================================
    # ONLY THESE TWO STEP-2 FILES WILL BE READ
    # ========================================================

    files = [
        f"Raked_{process_date}_Rest_of_Armenia.xlsx",
        f"Raked_{process_date}_Yerevan.xlsx"
    ]

    missing_files = [
        fname
        for fname in files
        if not os.path.exists(os.path.join(input_dir, fname))
    ]

    if missing_files:
        raise FileNotFoundError(
            "The following Step-2 input files were not found:\n"
            + "\n".join(missing_files)
        )

    all_dfs = []

    for fname in files:

        file_path = os.path.join(input_dir, fname)

        print("Reading Step-2 file:", file_path)

        df = pd.read_excel(file_path)

        if df.empty:
            raise Exception(
                f"Step-2 input file is empty: {fname}"
            )

        all_dfs.append(df)

    # ========================================================
    # COMBINE BOTH FILES
    # ========================================================

    final_df = pd.concat(
        all_dfs,
        ignore_index=True
    )

    # ========================================================
    # RENAME STEP-2 COLUMN
    # ========================================================

    if "main_raking_iterations_1" not in final_df.columns:
        raise Exception(
            "Required Step-2 column missing: "
            "main_raking_iterations_1"
        )

    final_df = final_df.rename(
        columns={
            "main_raking_iterations_1": "raking_iterations"
        }
    )

    # ========================================================
    # FORCE AGE FIX
    # ========================================================

    columns_to_fix = [
        "Weighted_Age_Group",
        "Reporting_Age_Group"
    ]

    for col in columns_to_fix:
        if col in final_df.columns:
            final_df[col] = final_df[col].apply(clean_age)

    # ========================================================
    # FINAL REQUIRED COLUMNS ONLY
    # ========================================================

    required_columns = [
        "Date",
        "hhid",
        "member_code",
        "Sex",
        "Actual_age",
        "Weighted_Age_Group",
        "Reporting_Age_Group",
        "Sub_Age_Group",
        "City_Group",
        "HH_City",
        "final_weight",
        "final_weight_scaled",
        "raking_iterations",
        "SEC",
        "HH_Income",
        "HH_Education",
        "With_Child",
        "HH_Size"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in final_df.columns
    ]

    if missing_columns:
        raise Exception(
            "Required columns missing from Step-2 files: "
            f"{missing_columns}"
        )

    # Keep only required columns in the exact order
    final_df = final_df[required_columns]

    # ========================================================
    # SAVE STEP-3 OUTPUT IN Panel Files
    # ========================================================

    output_file = os.path.join(
        output_dir,
        f"{process_date}_combined_weighted.csv"
    )

    final_df.to_csv(
        output_file,
        index=False
    )

    print("\nSTEP-3 COMPLETED SUCCESSFULLY")
    print("Total Rows:", len(final_df))
    print("Final Columns:", list(final_df.columns))
    print("Saved:", output_file)

    return output_file
# ============================================================
# STEP 4 – FULL VALIDATION (CITY + GENDER + AGE BENCHMARKS)
# ============================================================

TOLERANCE = 0.0001  

# ============================================================
# OFFICIAL POPULATION TOTALS
# ============================================================

CITY_TOTAL_POP = {
    "Yerevan": 1136300,
    "Rest_of_Armenia": 1931100
}

# ============================================================
# BENCHMARK DISTRIBUTIONS
# ============================================================

CITY_BENCHMARKS = {

    "Yerevan": {
        "POP_TOTAL": 1136300,

        "GENDER_TARGETS": {
            "Male": 0.44785,
            "Female": 0.55215
        },

        "POP_AGE_GENDER": {
            "3-17_Male": 0.07015,
            "18-20_Male": 0.01515,
            "21-29_Male": 0.04907,
            "30-39_Male": 0.07003,
            "40-49_Male": 0.06663,
            "50-59_Male": 0.05160,
            "60+_Male": 0.12522,

            "3-17_Female": 0.08649,
            "18-20_Female": 0.01867,
            "21-29_Female": 0.06050,
            "30-39_Female": 0.08633,
            "40-49_Female": 0.08215,
            "50-59_Female": 0.06362,
            "60+_Female": 0.15438
        },

        "SUB_AGE_GENDER_TARGETS": {
            # Male
            "Age_group_3-7_Male": 0.01895,
            "Age_group_8-12_Male": 0.02570,
            "Age_group_13-17_Male": 0.02550,
            "Age_group_18-19_Male": 0.00990,
            "Age_group_20_Male": 0.00525,
            "Age_group_21-24_Male": 0.02100,
            "Age_group_25_Male": 0.00561,
            "Age_group_26-29_Male": 0.02246,
            "Age_group_30_Male": 0.00688,
            "Age_group_31-34_Male": 0.02753,
            "Age_group_35_Male": 0.00712,
            "Age_group_36-39_Male": 0.02849,
            "Age_group_40_Male": 0.00715,
            "Age_group_41-44_Male": 0.02859,
            "Age_group_45_Male": 0.00618,
            "Age_group_46-49_Male": 0.02472,
            "Age_group_50_Male": 0.00543,
            "Age_group_51-54_Male": 0.02172,
            "Age_group_55_Male": 0.00489,
            "Age_group_56-59_Male": 0.01956,
            "Age_group_60_Male": 0.00627,
            "Age_group_61-64_Male": 0.02507,
            "Age_group_65_Male": 0.00676,
            "Age_group_66-69_Male": 0.02704,
            "Age_group_70+_Male": 0.06009,

            # Female
            "Age_group_3-7_Female": 0.02337,
            "Age_group_8-12_Female": 0.03168,
            "Age_group_13-17_Female": 0.03144,
            "Age_group_18-19_Female": 0.01220,
            "Age_group_20_Female": 0.00647,
            "Age_group_21-24_Female": 0.02589,
            "Age_group_25_Female": 0.00692,
            "Age_group_26-29_Female": 0.02769,
            "Age_group_30_Female": 0.00849,
            "Age_group_31-34_Female": 0.03394,
            "Age_group_35_Female": 0.00878,
            "Age_group_36-39_Female": 0.03513,
            "Age_group_40_Female": 0.00881,
            "Age_group_41-44_Female": 0.03525,
            "Age_group_45_Female": 0.00762,
            "Age_group_46-49_Female": 0.03047,
            "Age_group_50_Female": 0.00669,
            "Age_group_51-54_Female": 0.02678,
            "Age_group_55_Female": 0.00603,
            "Age_group_56-59_Female": 0.02412,
            "Age_group_60_Female": 0.00773,
            "Age_group_61-64_Female": 0.03091,
            "Age_group_65_Female": 0.00833,
            "Age_group_66-69_Female": 0.03333,
            "Age_group_70+_Female": 0.07408
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
        },

        "SUB_AGE_GENDER_TARGETS": {
            # Male
            "Age_group_3-7_Male": 0.03405,
            "Age_group_8-12_Male": 0.03506,
            "Age_group_13-17_Male": 0.03336,
            "Age_group_18-19_Male": 0.01276,
            "Age_group_20_Male": 0.00528,
            "Age_group_21-24_Male": 0.02112,
            "Age_group_25_Male": 0.00571,
            "Age_group_26-29_Male": 0.02282,
            "Age_group_30_Male": 0.00744,
            "Age_group_31-34_Male": 0.02976,
            "Age_group_35_Male": 0.00788,
            "Age_group_36-39_Male": 0.03152,
            "Age_group_40_Male": 0.00704,
            "Age_group_41-44_Male": 0.02817,
            "Age_group_45_Male": 0.00585,
            "Age_group_46-49_Male": 0.02339,
            "Age_group_50_Male": 0.00533,
            "Age_group_51-54_Male": 0.02130,
            "Age_group_55_Male": 0.00589,
            "Age_group_56-59_Male": 0.02357,
            "Age_group_60_Male": 0.00751,
            "Age_group_61-64_Male": 0.03006,
            "Age_group_65_Male": 0.00681,
            "Age_group_66-69_Male": 0.02724,
            "Age_group_70+_Male": 0.04586,

            # Female
            "Age_group_3-7_Female": 0.03619,
            "Age_group_8-12_Female": 0.03726,
            "Age_group_13-17_Female": 0.03546,
            "Age_group_18-19_Female": 0.01356,
            "Age_group_20_Female": 0.00561,
            "Age_group_21-24_Female": 0.02245,
            "Age_group_25_Female": 0.00606,
            "Age_group_26-29_Female": 0.02426,
            "Age_group_30_Female": 0.00791,
            "Age_group_31-34_Female": 0.03163,
            "Age_group_35_Female": 0.00837,
            "Age_group_36-39_Female": 0.03350,
            "Age_group_40_Female": 0.00749,
            "Age_group_41-44_Female": 0.02994,
            "Age_group_45_Female": 0.00621,
            "Age_group_46-49_Female": 0.02486,
            "Age_group_50_Female": 0.00566,
            "Age_group_51-54_Female": 0.02264,
            "Age_group_55_Female": 0.00626,
            "Age_group_56-59_Female": 0.02505,
            "Age_group_60_Female": 0.00799,
            "Age_group_61-64_Female": 0.03195,
            "Age_group_65_Female": 0.00724,
            "Age_group_66-69_Female": 0.02895,
            "Age_group_70+_Female": 0.04874
        }
    }
}

# ============================================================
# MAIN FUNCTION
# ============================================================

def run_full_validation(process_date):

    print(f"\nRunning Full Validation for {process_date}")

    # =========================================================
    # STEP 4 INPUT PATH
    # =========================================================

    input_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "Panel Files"
    )

    combined_path = os.path.join(
        input_dir,
        f"{process_date}_combined_weighted.csv"
    )

    if not os.path.exists(combined_path):
        raise Exception("Combined file not found.")

    df = pd.read_csv(combined_path)
    if df.empty:
        raise Exception("Combined weighted CSV is empty.")

    required_columns = [
        "City_Group",
        "Sex",
        "Reporting_Age_Group",
        "Sub_Age_Group",
        "final_weight_scaled"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise Exception(
            f"Missing required columns: {missing_columns}"
        )

    df["final_weight_scaled"] = pd.to_numeric(
        df["final_weight_scaled"],
        errors="coerce"
    )

    if df["final_weight_scaled"].isna().any():
        raise Exception(
            "final_weight_scaled contains null or non-numeric values."
        )

    if (df["final_weight_scaled"] < 0).any():
        raise Exception(
            "final_weight_scaled contains negative values."
        )

    df["City_Group"] = (
        df["City_Group"]
        .astype(str)
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )

    # =========================================================
    # CITY TOTAL VALIDATION
    # =========================================================

    city_results = []
    present_cities = set(df["City_Group"])

    for city, pop in CITY_TOTAL_POP.items():

        if city not in present_cities:
            city_results.append({
                "City": city,
                "Expected_Population": pop,
                "Weighted_Sum": 0,
                "Difference": -pop,
                "Difference_%": -100,
                "Status": "MISSING"
            })
            continue

        city_df = df[
            df["City_Group"] == city
        ].copy()

        city_sum = city_df["final_weight_scaled"].sum()

        diff = city_sum - pop
        pct_diff = (diff / pop) * 100

        status = "PASS" if abs(diff) <= 1 else "FAIL"

        city_results.append({
            "City": city,
            "Expected_Population": pop,
            "Weighted_Sum": round(city_sum, 2),
            "Difference": round(diff, 2),
            "Difference_%": round(pct_diff, 4),
            "Status": status
        })

    city_validation_df = pd.DataFrame(city_results)

        

    # =========================================================
    # GENDER + AGE BENCHMARK VALIDATION
    # =========================================================

    benchmark_results = []

    for city in CITY_TOTAL_POP.keys():

        city_df = df[
            df["City_Group"]
            .str.replace(" ", "_")
            == city
        ].copy()

        if len(city_df) == 0:
            continue

        city_df["Weighted_Age_Group"] = (
        city_df["Weighted_Age_Group"]
        .astype(str)
        .replace({
            "14-Mar": "3-14",
            "Mar-14": "3-14"
        })
        )

        total_weight = city_df["final_weight_scaled"].sum()
        if total_weight <= 0:
            benchmark_results.append({
                "City": city,
                "Dimension": "All",
                "Category": "Total Weight",
                "Expected": 1,
                "Observed": 0,
                "Difference": -1,
                "Status": "FAIL"
            })
            continue

        # =========================================================
        # GENDER VALIDATION
        # =========================================================

        gender_dist = (
            city_df.groupby("Sex")["final_weight_scaled"]
            .sum()
        )

        gender_dist = gender_dist / total_weight

        for gender, expected in CITY_BENCHMARKS[city]["GENDER_TARGETS"].items():

            observed = gender_dist.get(gender, 0)

            diff = observed - expected

            status = (
                "PASS"
                if abs(diff) <= TOLERANCE
                else "FAIL"
            )

            benchmark_results.append({
                "City": city,
                "Dimension": "Gender",
                "Category": gender,
                "Expected": round(expected, 5),
                "Observed": round(observed, 5),
                "Difference": round(diff, 5),
                "Status": status
            })

        city_df["AGE_GENDER"] = (
        city_df["Reporting_Age_Group"].astype(str)
        + "_"
        + city_df["Sex"].astype(str)
        )

        ag_dist = (
            city_df.groupby("AGE_GENDER")["final_weight_scaled"]
            .sum()
        )

        ag_dist = ag_dist / total_weight

        for cell, expected in CITY_BENCHMARKS[city]["POP_AGE_GENDER"].items():

            observed = ag_dist.get(cell, 0)

            diff = observed - expected

            status = (
                "PASS"
                if abs(diff) <= TOLERANCE
                else "FAIL"
            )

            benchmark_results.append({
                "City": city,
                "Dimension": "Age_Gender",
                "Category": cell,
                "Expected": round(expected, 5),
                "Observed": round(observed, 5),
                "Difference": round(diff, 5),
                "Status": status
            })
        # =========================================================
        # SUB-AGE GROUP + GENDER VALIDATION
        # =========================================================

        city_df["SUB_AGE_GENDER"] = (
            "Age_group_"
            + city_df["Sub_Age_Group"].astype(str).str.strip()
            + "_"
            + city_df["Sex"].astype(str).str.strip()
        )

        sub_age_gender_dist = (
            city_df.groupby("SUB_AGE_GENDER")["final_weight_scaled"]
            .sum()
        )

        sub_age_gender_dist = (
            sub_age_gender_dist / total_weight
        )

        for cell, expected in CITY_BENCHMARKS[city][
            "SUB_AGE_GENDER_TARGETS"
        ].items():

            observed = sub_age_gender_dist.get(cell, 0)

            diff = observed - expected

            status = (
                "PASS"
                if abs(diff) <= TOLERANCE
                else "FAIL"
            )

            benchmark_results.append({
                "City": city,
                "Dimension": "Sub_Age_Gender",
                "Category": cell,
                "Expected": round(expected, 5),
                "Observed": round(observed, 5),
                "Difference": round(diff, 5),
                "Status": status
            })

    benchmark_validation_df = pd.DataFrame(benchmark_results)
    # =========================================================
    # STEP 4 OUTPUT PATH
    # =========================================================

    validation_dir = input_dir

    txt_path = os.path.join(
        validation_dir,
        f"{process_date}_full_validation_report.txt"
    )

    with open(txt_path, "w", encoding="utf-8") as f:

        f.write("=============================================\n")
        f.write("RIM ENGINE – FULL VALIDATION REPORT\n")
        f.write("=============================================\n\n")
        f.write(f"Process Date : {process_date}\n")
        f.write(f"Generated On : {datetime.now()}\n\n")

        f.write("===== CITY TOTAL VALIDATION =====\n\n")
        f.write(city_validation_df.to_string(index=False))
        f.write("\n\n")

        f.write("===== GENDER + MAIN AGE + SUB-AGE BENCHMARK VALIDATION =====\n\n")
        f.write(benchmark_validation_df.to_string(index=False))
        f.write("\n\n")

    print("Validation report saved:", txt_path)

    return city_validation_df, benchmark_validation_df
# =========================================================
# E-MAIL FUNCTION
# =========================================================

# ============================================================
# SEND EMAIL WITH ALL FOUR OUTPUT FILES
# ============================================================

def send_email(process_date):

    # --------------------------------------------------------
    # FILE PATHS
    # --------------------------------------------------------

    summary_file = os.path.join(
        OUTPUT_FOLDER,
        f"{process_date}_Summary.csv"
    )

    supplementation_file = os.path.join(
        OUTPUT_FOLDER,
        f"{process_date}_Supplementation_Report.xlsx"
    )

    combined_file = os.path.join(
        OUTPUT_FOLDER,
        f"{process_date}_combined_weighted.csv"
    )

    validation_file = os.path.join(
        OUTPUT_FOLDER,
        f"{process_date}_full_validation_report.txt"
    )

    files_to_attach = [
        summary_file,
        supplementation_file,
        combined_file,
        validation_file
    ]

    # --------------------------------------------------------
    # CHECK ALL FOUR FILES
    # --------------------------------------------------------

    missing_files = [
        file_path
        for file_path in files_to_attach
        if not os.path.exists(file_path)
    ]

    if missing_files:
        raise FileNotFoundError(
            "The following email attachment files were not found:\n"
            + "\n".join(missing_files)
        )

    # --------------------------------------------------------
    # CREATE EMAIL
    # --------------------------------------------------------

    msg = EmailMessage()

    msg["Subject"] = (
        f"Panel Output - {process_date}"
    )

    msg["From"] = SENDER_EMAIL

    msg["To"] = ", ".join(RECEIVER_EMAILS)

    msg.set_content(
        f"""Hi Senthil,

Please find attached the panel output files for {process_date}.

Attachments:

1. {process_date}_Summary.csv
2. {process_date}_Supplementation_Report.xlsx
3. {process_date}_combined_weighted.csv
4. {process_date}_full_validation_report.txt

Regards,
Panel Automation
"""
    )

    # --------------------------------------------------------
    # ATTACH ALL FOUR FILES
    # --------------------------------------------------------

    for file_path in files_to_attach:

        with open(file_path, "rb") as f:

            file_data = f.read()

        file_name = os.path.basename(file_path)

        if file_path.lower().endswith(".xlsx"):

            maintype = "application"
            subtype = (
                "vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            )

        elif file_path.lower().endswith(".csv"):

            maintype = "text"
            subtype = "csv"

        elif file_path.lower().endswith(".txt"):

            maintype = "text"
            subtype = "plain"

        else:

            maintype = "application"
            subtype = "octet-stream"

        msg.add_attachment(
            file_data,
            maintype=maintype,
            subtype=subtype,
            filename=file_name
        )

    # --------------------------------------------------------
    # SEND EMAIL THROUGH GMAIL
    # --------------------------------------------------------

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465
    ) as smtp:

        smtp.login(
            SENDER_EMAIL,
            APP_PASSWORD
        )

        smtp.send_message(msg)

    print("\nEMAIL SENT SUCCESSFULLY")
# ============================================================
# SCRIPT EXECUTION
# ============================================================

if __name__ == "__main__":

    try:

        print("\n" + "=" * 70)
        print("PANEL AUTOMATION STARTED")
        print("=" * 70)

        # ----------------------------------------------------
        # PROCESS DATE
        # ----------------------------------------------------

        process_date = (
            datetime.now() - timedelta(days=1)
        ).strftime("%d-%m-%Y")

        print(f"\nProcess Date: {process_date}")

        # ----------------------------------------------------
        # SELECT CITIES
        # ----------------------------------------------------

        selected_cities = [
            "Yerevan",
            "Rest_of_Armenia"
        ]

        print(f"Selected Cities: {selected_cities}")

        # ----------------------------------------------------
        # STEP 1
        # ----------------------------------------------------

        print("\n" + "=" * 70)
        print("STEP 1 STARTED")
        print("=" * 70)

        step1_result = run_step1(
            process_date=process_date,
            selected_cities=selected_cities
        )

        print("\nSTEP 1 COMPLETED SUCCESSFULLY")

        # ----------------------------------------------------
        # STEP 2
        # IMPORTANT:
        # run_step2 accepts only process_date
        # ----------------------------------------------------

        print("\n" + "=" * 70)
        print("STEP 2 STARTED")
        print("=" * 70)

        step2_result = run_step2(
            process_date=process_date
        )

        print("\nSTEP 2 COMPLETED SUCCESSFULLY")

        # ----------------------------------------------------
        # STEP 3
        # IMPORTANT:
        # run_step3 accepts only process_date
        # ----------------------------------------------------

        print("\n" + "=" * 70)
        print("STEP 3 STARTED")
        print("=" * 70)

        step3_result = run_step3(
            process_date=process_date
        )

        print("\nSTEP 3 COMPLETED SUCCESSFULLY")

        # ----------------------------------------------------
        # STEP 4
        # IMPORTANT:
        # run_full_validation accepts only process_date
        # ----------------------------------------------------

        print("\n" + "=" * 70)
        print("STEP 4 STARTED")
        print("=" * 70)

        validation_result = run_full_validation(
            process_date=process_date
        )

        print("\nSTEP 4 COMPLETED SUCCESSFULLY")

        # ----------------------------------------------------
        # CHECK EXPECTED OUTPUT FILES
        # ----------------------------------------------------

        summary_file = os.path.join(
            OUTPUT_FOLDER,
            f"{process_date}_Summary.csv"
        )

        supplementation_file = os.path.join(
            OUTPUT_FOLDER,
            f"{process_date}_Supplementation_Report.xlsx"
        )

        combined_file = os.path.join(
            OUTPUT_FOLDER,
            f"{process_date}_combined_weighted.csv"
        )

        validation_file = os.path.join(
            OUTPUT_FOLDER,
            f"{process_date}_full_validation_report.txt"
        )

        expected_output_files = [
            summary_file,
            supplementation_file,
            combined_file,
            validation_file
        ]

        print("\n" + "=" * 70)
        print("CHECKING OUTPUT FILES")
        print("=" * 70)

        missing_files = []

        for file_path in expected_output_files:

            if os.path.exists(file_path):

                file_size = os.path.getsize(file_path)

                print(
                    f"FOUND: {os.path.basename(file_path)} "
                    f"({file_size:,} bytes)"
                )

            else:

                missing_files.append(file_path)

                print(
                    f"MISSING: {os.path.basename(file_path)}"
                )

        if missing_files:

            raise FileNotFoundError(
                "The following expected output files are missing:\n"
                + "\n".join(missing_files)
            )

        print("\nAll four output files are available.")

        # ----------------------------------------------------
        # SEND EMAIL
        # ----------------------------------------------------

        print("\n" + "=" * 70)
        print("EMAIL PROCESS STARTED")
        print("=" * 70)

        send_email(process_date)

        print("\nEMAIL SENT SUCCESSFULLY")

        # ----------------------------------------------------
        # FINAL SUCCESS
        # ----------------------------------------------------

        print("\n" + "=" * 70)
        print("PANEL AUTOMATION COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print(f"\nProcess Date: {process_date}")

        print("\nGenerated Files:")

        for file_path in expected_output_files:
            print(f" - {os.path.basename(file_path)}")

        print("\nEmail Status: SENT")
        print("=" * 70)

    except Exception as e:

        print("\n" + "=" * 70)
        print("PANEL AUTOMATION FAILED")
        print("=" * 70)

        print(f"\nError: {str(e)}")

        import traceback

        traceback.print_exc()

        print("\nEmail Status: NOT SENT")
        print("=" * 70)

        raise