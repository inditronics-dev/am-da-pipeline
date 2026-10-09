# ============================================================
# SEND VALIDATION REPORT EMAIL
# ============================================================

import os
import sys
import re
import smtplib
import pandas as pd
from email.message import EmailMessage
from datetime import datetime, timedelta
import time
import traceback

# ============================================================
# DYNAMIC RUN DATE
# ============================================================

RUN_DATE = os.environ.get("RUN_DATE")

if RUN_DATE:
    try:
        RUN_DATE = datetime.strptime(RUN_DATE, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            f"Invalid RUN_DATE format: {RUN_DATE}. "
            "Expected format: YYYY-MM-DD"
        )
else:
    RUN_DATE = (datetime.now() - timedelta(days=1)).date()

print(f"Processing Date: {RUN_DATE}")


# ============================================================
# DOWNLOAD WITH RETRY
# ============================================================

def download_with_retry(bucket, s3_key, local_file,
                        max_retry=30, wait_seconds=120):
    """
    Download a file from S3 with retry.

    max_retry=30
        Try up to 30 times.

    wait_seconds=120
        Wait 2 minutes between retries.
    """

    for attempt in range(1, max_retry + 1):

        print(f"\nAttempt {attempt}/{max_retry}")
        print(f"Checking : {s3_key}")

        success = download_file(
            bucket,
            s3_key,
            local_file
        )

        if success:
            print("[OK] File downloaded successfully.")
            return True

        print(f"File not available.")
        print(f"Waiting {wait_seconds} seconds...")

        time.sleep(wait_seconds)

    return False

# Get current file location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Add project root
sys.path.insert(0, PROJECT_ROOT)

# Add Total_Tv_ratings folder
sys.path.insert(0, os.path.join(PROJECT_ROOT, "Total_Tv_ratings"))

# Now import your project modules
from s3_utils import download_file
from Total_Tv_ratings.calculate_tv_kpi import calculate_tv_kpi

# ============================================================
# CONFIGURATION
# ============================================================

SENDER_EMAIL = "indi_dataops@inditronics.com"

# Store this as an environment variable
# Example (Windows CMD):
# set GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx

APP_PASSWORD = "jeft eidg wyhs axdi"

# Receiver (currently sending to yourself)
RECEIVER_EMAILS = [
    "kanchan.bishnoi@inditronics.com", "senthil.kumar@inditronics.com", "chandrashekhar.banda@inditronics.com", "aftab.momin@inditronics.com"
]


TEMP_FOLDER = os.path.join(SCRIPT_DIR, "temp")
os.makedirs(TEMP_FOLDER, exist_ok=True)

ATTACHMENT = os.path.join(
    TEMP_FOLDER,
    "Data Validation Check Completed.xlsx"
)


# ============================================================
# CHECK FILE
# ============================================================


if not APP_PASSWORD:
    raise ValueError(
        "GMAIL_APP_PASSWORD environment variable not found."
    )




# ============================================================
# DOWNLOAD LAST 5 DAYS & CALCULATE KPI
# ============================================================
def extract_hhids(txt_file):

    hhids = set()

    with open(txt_file, "r", encoding="utf-8") as f:

        for line in f:
            matches = re.findall(r'HH\d+', line.upper())
            hhids.update(matches)

    return hhids


BUCKET = "indi-analytics-output"

kpi_rows = []

panel_summary_html = ""


logo_detection = 0
fp_detection = 0

for i in range(7):

    target_date = RUN_DATE - timedelta(days=i)
    statement_date = target_date.strftime("%Y-%m-%d")
    panel_date = target_date.strftime("%d-%m-%Y")

    try:

        # S3 Keys
        statement_key = f"DA-Output/{panel_date}/statement/statement.csv"
        panel_key = f"DA-Output/{panel_date}/for_panel/Panel.csv"
        panel_summary_key = f"DA-Output/{panel_date}/for_panel/Panel_summary.csv"
        logo_key = f"DA-Output/{panel_date}/merging/Logo.txt"
        fp_key = f"DA-Output/{panel_date}/merging/FP.txt"

        validation_key = (
            f"DA-Output/{panel_date}/statement/"
            "Data Validation Check Completed.xlsx"
        )

        # Local files
        statement_file = os.path.join(
            TEMP_FOLDER,
            f"{statement_date}_statement.csv"
        )

        panel_file = os.path.join(
            TEMP_FOLDER,
            f"{panel_date}_combined_weighted.csv"
        )
        print("Statement Key:", statement_key)
        print("Panel Key:", panel_key)
        panel_summary_file = os.path.join(
            TEMP_FOLDER,
            f"{panel_date}_Panel_summary.csv"
        )
        # -------------------------------
        # Download Statement
        # -------------------------------
        if not download_with_retry(
            BUCKET,
            statement_key,
            statement_file
        ):
            raise RuntimeError(f"Unable to download {statement_key}")

        print(f"Statement exists: {os.path.exists(statement_file)}")
        print(statement_file)

        # -------------------------------
        # Download Panel
        # -------------------------------
        if not download_with_retry(
            BUCKET,
            panel_key,
            panel_file
        ):
            raise RuntimeError(f"Unable to download {panel_key}")

        print(f"Panel exists: {os.path.exists(panel_file)}")
        print(panel_file)

        logo_file = os.path.join(
            TEMP_FOLDER,
            f"{panel_date}_Logo.txt"
        )

        fp_file = os.path.join(
            TEMP_FOLDER,
            f"{panel_date}_FP.txt"
        )

        # Panel Summary
        if not download_with_retry(
            BUCKET,
            panel_summary_key,
            panel_summary_file
        ):
            raise RuntimeError(f"Unable to download {panel_summary_key}")

        print(f"Panel Summary exists: {os.path.exists(panel_summary_file)}")
        print(panel_summary_file)

        # Logo
        if not download_with_retry(
            BUCKET,
            logo_key,
            logo_file
        ):
            raise RuntimeError(f"Unable to download {logo_key}")

        # FP
        if not download_with_retry(
            BUCKET,
            fp_key,
            fp_file
        ):
            raise RuntimeError(f"Unable to download {fp_key}")

        if i == 0:

            # Download Validation Excel
            if not download_with_retry(
                BUCKET,
                validation_key,
                ATTACHMENT
            ):
                raise RuntimeError(
                    f"Unable to download {validation_key}"
                )

            print(f"Validation Excel exists: {os.path.exists(ATTACHMENT)}")
            # ============================================================
            # READ VALIDATION REPORT
            # ============================================================

            validation_df = pd.read_excel(ATTACHMENT)

            # Find PASS/FAIL column automatically
            status_col = None

            for col in validation_df.columns:
                if validation_df[col].astype(str).str.upper().isin(["PASS", "FAIL"]).any():
                    status_col = col
                    break

            if status_col is None:
                raise ValueError("PASS/FAIL column not found.")

            pass_count = (
                validation_df[status_col]
                .astype(str)
                .str.upper()
                .eq("PASS")
                .sum()
            )

            fail_df = validation_df[
                validation_df[status_col]
                .astype(str)
                .str.upper()
                == "FAIL"
            ]

            fail_count = len(fail_df)

            if fail_count > 0:
                fail_list = "<br>".join(
                    f"• {row.iloc[0]}"
                    for _, row in fail_df.iterrows()
                )
            else:
                fail_list = ""

            if os.path.exists(panel_summary_file):
                panel_summary_df = pd.read_csv(panel_summary_file)

                panel_summary_html = panel_summary_df.to_html(
                    index=False,
                    border=0,
                    classes="panel-summary",
                    justify="center",
                    escape=False
                )

            if os.path.exists(logo_file) and os.path.exists(fp_file):

                logo_hhids = extract_hhids(logo_file)
                fp_hhids = extract_hhids(fp_file)

                only_logo = logo_hhids - fp_hhids
                only_fp = fp_hhids - logo_hhids
                common = logo_hhids & fp_hhids

                logo_detection = len(common) + len(only_logo)
                fp_detection = len(only_fp)

                print("=" * 50)
                print("Logo Total :", len(logo_hhids))
                print("FP Total   :", len(fp_hhids))
                print("Only Logo  :", len(only_logo))
                print("Only FP    :", len(only_fp))
                print("Common     :", len(common))
                print("Logo Count :", logo_detection)
                print("FP Count   :", fp_detection)
                print("=" * 50)
       

        # Calculate KPI
        result = calculate_tv_kpi(
            statement_file,
            panel_file
        )

        # Store results
        kpi_rows.append({
            "Date": panel_date,
            "Rating": result["rating"],
            "Reach": result["round_off_reach"],
            "Reach%": result["reach_percent"],
            "ATS": result["ats"],
            "Universe": result["universe"]
        })

    except Exception as e:
        print(f"\nERROR for {panel_date}")
        traceback.print_exc()
        continue
if not kpi_rows:
    raise RuntimeError("No KPI data found for the last 7 days.")

# Sort oldest to newest (17 -> 21)
kpi_rows = sorted(
    kpi_rows,
    key=lambda x: datetime.strptime(x["Date"], "%d-%m-%Y")
)

# Header row
header = "".join(
    f"<th>{row['Date']}</th>"
    for row in kpi_rows
)

# Rating row
rating_row = "".join(
    f"<td>{row['Rating']:.2f}</td>"
    for row in kpi_rows
)

# Reach row
reach_row = "".join(
    f"<td>{row['Reach']:.2f}</td>"
    for row in kpi_rows
)

# Reach % row
reach_percent_row = "".join(
    f"<td>{row['Reach%']:.2f}</td>"
    for row in kpi_rows
)

# ATS row
ats_row = "".join(
    f"<td>{row['ATS']}</td>"
    for row in kpi_rows
)

universe_row = "".join(
    f"<td>{row['Universe']:,.0f}</td>"
    for row in kpi_rows
)

# ============================================================
# CREATE EMAIL
# ============================================================

report_date = RUN_DATE.strftime("%d-%m-%Y")

msg = EmailMessage()

msg["Subject"] = f"Validation, InTAB and Panel Completed - {report_date}"
msg["From"] = SENDER_EMAIL
msg["To"] = ", ".join(RECEIVER_EMAILS)

html = f"""
<html>
<head>
<style>

table {{
    border-collapse: collapse;
}}

.panel-summary {{
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 13px;
    width: auto;
    margin-top: 10px;
}}

.panel-summary th {{
    background-color: #f2f2f2;
    border: 1px solid #bfbfbf;
    padding: 6px 10px;
    text-align: center;
    font-weight: bold;
}}

.panel-summary td {{
    border: 1px solid #bfbfbf;
    padding: 6px 10px;
    text-align: center;
    vertical-align: middle;
}}

.panel-summary td:first-child {{
    text-align: left;
}}

.panel-summary tr:last-child td {{
    background-color: #f2f2f2;
    font-weight: bold;
}}

.kpi-table {{
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 13px;
    margin-top: 10px;
}}

.kpi-table th {{
    background-color: #f2f2f2;
    border: 1px solid #bfbfbf;
    padding: 6px 10px;
    text-align: center;
    font-weight: bold;
}}

.kpi-table td {{
    border: 1px solid #bfbfbf;
    padding: 6px 10px;
    text-align: center;
    vertical-align: middle;
}}

.kpi-table td:first-child {{
    background-color: #f2f2f2;
    font-weight: bold;
    text-align: left;
}}

</style>
</head>
<H3> Dear Team,</H3>
<h3>Total TV KPI</h3>
<p>Please find below the Total TV KPI summary for the last 7 reporting days</p>

<table class="kpi-table">

<tr>
    <th>Metric</th>
    {header}
</tr>

<tr>
    <td>Rating</td>
    {rating_row}
</tr>

<tr>
    <td>Reach'000</td>
    {reach_row}
</tr>

<tr>
    <td>Reach%</td>
    {reach_percent_row}
</tr>

<tr>
    <td>ATS</td>
    {ats_row}
</tr>

<tr>
    <td>Universe</td>
    {universe_row}
</tr>

</table>

<br><br>

<h3>Viewership Attribution</h3>

<p>
Please find the Viewership Attribution details for <b>{report_date}</b>, below.
</p>

<p>
We added <b>{logo_detection}</b> Households for Logo Detection and
<b>{fp_detection}</b> Households for FP Detection using viewership attribution.
</p>

<br><br>
<h3>Validation Summary</h3>

<p>
<b>PASS :</b> {pass_count}<br>
<b>FAIL :</b> {fail_count}
</p>

{"<p><b>Failed Validations:</b><br>" + fail_list + "</p>" if fail_count > 0 else "<p>All validation checks passed successfully.</p>"}
<br>

<h3>INTAB for {report_date}</h3>


{panel_summary_html}

<br>

<br>

<br>


<p>Please find the attached INTAB and validation report.</p>

<p>
Generated On:
{datetime.now().strftime("%d-%b-%Y %I:%M:%S %p")}
</p>

<p>
Regards,<br>
Indi_DataOps
</p>

</body>
</html>
"""

msg.set_content("Please view this email in HTML format.")
msg.add_alternative(html, subtype="html")
# ============================================================
# ATTACH FILE
# ============================================================
with open(ATTACHMENT, "rb") as f:
    msg.add_attachment(
        f.read(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(ATTACHMENT),
    )

# ============================================================
# SEND EMAIL
# ============================================================

print("Sending email...")

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(SENDER_EMAIL, APP_PASSWORD)
    smtp.send_message(msg)

print("Email sent successfully.")