# ==========================================================
# TOTAL TV RATING CALCULATION
# ==========================================================

import pandas as pd
import math


# ==========================================================

# CONFIGURATION
# ==========================================================

# Population
POPULATION = 3067400

def calculate_tv_kpi(statement_file, panel_file):

        # ==========================================================
        # STEP 2 - READ FILES & MERGE PANEL WEIGHT
        # ==========================================================

        print("\nReading files...")

        # Read CSV files
        statement_df = pd.read_csv(statement_file)
        panel_df = pd.read_csv(panel_file)

        # ==========================================================
        # UNIVERSE
        # ==========================================================

        universe = panel_df["final_weight_scaled"].sum()

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

        # Reach'000 (truncate to 2 decimals)
        round_off_reach = math.floor((reach / 1000) * 100) / 100

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

        # Rating (truncate to 2 decimals)
        raw_rating = ((impressions / 86400) / POPULATION) * 100
        total_tv_rating = math.floor(raw_rating * 100) / 100

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
        raw_rating = ((impressions / 86400) / POPULATION) * 100

        print("=" * 50)
        print("Date:", statement_df["date"].iloc[0])
        print(f"Impressions      : {impressions:.10f}")
        print(f"Population       : {POPULATION}")
        print(f"Raw Rating       : {raw_rating:.10f}")
        print(f"Rounded Rating   : {round(raw_rating, 2)}")
        print("=" * 50)
        print(f"Reach            : {reach:.10f}")
        print(f"Reach'000 Raw    : {reach/1000:.10f}")
        print(f"Reach'000 Round  : {round(reach/1000, 2)}")

        print("\nStep 5 Completed Successfully.")

        # ==========================================================
        # PREPARE OUTPUT DATA
        # ==========================================================

        print("\nPreparing Output Data...")

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

        return {
            "statement_df": output_df,
            "summary_df": summary_df,
            "impressions": impressions,
            "reach": reach,
            "ats_seconds": ats_seconds,
            "ats": ats_time,
            "round_off_reach": round_off_reach,
            "reach_percent": reach_percent,
            "rating": total_tv_rating,
            "universe": universe
        }