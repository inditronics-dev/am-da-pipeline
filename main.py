import subprocess
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


# ============================================================
# IMPORT DATE UTILITY
# ============================================================

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pipeline.date_utils import get_run_date


# ============================================================
# CONFIG: DEFINE YOUR PIPELINE ORDER HERE
# ============================================================

PIPELINE = [
    {
        "name": "Logo Sessions",
        "script": os.path.join("sessions", "logo", "01_sessions.py"),
        "check_file": None
    },
    {
        "name": "Logo Raw Events Storage",
        "script": os.path.join("sessions", "logo", "0.1_raw_events_storage.py"),
        "check_file": None
    },

    {
        "name": "Logo Household Sessions",
        "script": os.path.join("sessions", "logo", "0.3_HH_level_sessions.py"),
        "check_file": None
    },
    {
        "name": "FP files download",
        "script": os.path.join("sessions", "fp", "02_downloading_files.py"),
        "check_file": None
    },
    {
        "name": "correcting the data",
        "script": os.path.join("sessions", "fp", "03_all_scripts_1.py"),
        "check_file": None
    },
    {
        "name": "mapping the data",
        "script": os.path.join("sessions", "fp", "04_automatic_mapping_2.py"),
        "check_file": None
    },
    {
        "name": "merging the member declaration and viewership data for fp",
        "script": os.path.join("sessions", "fp", "05_merging_3.py"),
        "check_file": None
    },
    {
        "name": "household sessions for fp",
        "script": os.path.join("sessions", "fp", "06_sessions_4.py"),
        "check_file": None
    },
    {
        "name": "member sessions for fp",
        "script": os.path.join("sessions", "fp", "07_member_level_sessions_5.py"),
        "check_file": None
    },
    {
        "name": "cleaning",
        "script": os.path.join("sessions", "fp", "08_data_cleaning_6.py"),
        "check_file": None
    },
    {
        "name": "device_id and hhid mapping",
        "script": os.path.join("sessions", "Daily device_id hhid mapping", "0.2_daily_hhid_device_id_mapping.py"),
        "check_file": None
    },
    {
        "name": "cleaning for history file",
        "script": os.path.join("sessions", "merging", "09_member_rejuvenation_FP.py"),
        "check_file": None
    },
    {
        "name": "member rejuvenation",
        "script": os.path.join("sessions", "merging", "10_member_rejuvenation_logo.py"),
        "check_file": None
    },
    {
        "name": "now merging the rejuvenated logo and fp files",
        "script": os.path.join("sessions", "merging", "11_merging_after_rejuvenation.py"),
        "check_file": None
    },
    {
        "name": "cleaning for panel file",
        "script": os.path.join("for_panel_files", "12_data_cleaning.py"),
        "check_file": None
    },
    {
        "name": "3 rules",
        "script": os.path.join("statement_file", "13_qualifier_rules.py"),
        "check_file": None
    },
    {
        "name": "channel clipping",
        "script": os.path.join("statement_file", "14_channel_clipping.py"),
        "check_file": None
    },
    {
        "name": "statement file generation",
        "script": os.path.join("statement_file", "15_final_data_cleaning.py"),
        "check_file": None
    },
    {
        "name": "Panel file generation",
        "script": os.path.join("Panel", "16_panel.py"),
        "check_file": None
    },

    # ========================================================
    # VALIDATION STEPS
    # ========================================================

    {
        "name": "Logo Validation",
        "script": os.path.join("Validation", "Stage1_Logo_Checks.py"),
        "check_file": None
    },
    {
        "name": "FP Validation",
        "script": os.path.join("Validation", "Stage1_FP_Checks.py"),
        "check_file": None
    },
    {
        "name": "Data Processing Validation",
        "script": os.path.join(
            "Validation",
            "Stage2_Data_Processing_Checks.py"
        ),
        "check_file": None
    },
    {
        "name": "Members Updation Checks",
        "script": os.path.join(
            "Validation",
            "Stage2_Members_Updation_Checks.py"
        ),
        "check_file": None
    },
    {
        "name": "Merged Data Checks",
        "script": os.path.join(
            "Validation",
            "Stage2_Merged_Data_Checks.py"
        ),
        "check_file": None
    },
    {
        "name": "Data Cleaning For Panel Checks",
        "script": os.path.join(
            "Validation",
            "Stage2_Data_Cleaning_For_Panel_Checks.py"
        ),
        "check_file": None
    },
    {
        "name": "Panel Checks",
        "script": os.path.join(
            "Validation",
            "Panel_Validation_Checks.py"
        ),
        "check_file": None
    },
    {
        "name": "3 Rules, Channel Clipping & Statement Checks",
        "script": os.path.join(
            "Validation",
            "3rules_channel_clipping_statement.py"
        ),
        "check_file": None
    },
    
    {
        "name": "upload outputs to S3",
        "script": os.path.join(
            "pipeline",
            "17_upload_to_s3.py"
        ),
        "check_file": None
    }, 
    
    {
            "name": "Sending validation Mail",
            "script": os.path.join(
                "Validation",
                "sending_Mail.py"
            ),
            "check_file": None
    }
]


LOG_FILE = os.path.join("pipeline", "pipeline_log.txt")


# ============================================================
# FUNCTION: LOGGING
# ============================================================

def log(message):
    log_dir = os.path.dirname(LOG_FILE)

    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")


# ============================================================
# FUNCTION: RUN SCRIPT
# ============================================================

def run_step(step, step_index, run_id, broadcast, run_date):

    broadcast(
        step_index,
        f"\nRunning: {step['name']}\n"
    )

    start_time = datetime.now()

    from dashboard.models import (
        create_step,
        update_step_status,
        append_step_log,
        update_run_status
    )

    step_id = create_step(
        run_id,
        step_index,
        step["name"]
    )

    script_path = os.path.abspath(step["script"])

    # ------------------------------------------------------------
    # Check script exists
    # ------------------------------------------------------------

    if not os.path.exists(script_path):

        msg = f"Script not found: {script_path}\n"

        append_step_log(step_id, msg)
        broadcast(step_index, msg, is_error=True)

        update_step_status(
            step_id,
            "Failed"
        )

        update_run_status(
            run_id,
            "Failed",
            error_message=f"Script not found: {step['script']}"
        )

        raise Exception(msg)

    # ------------------------------------------------------------
    # Prepare environment
    # ------------------------------------------------------------

    env = os.environ.copy()

    # IMPORTANT:
    # Every child script receives the SAME processing date.
    env["RUN_DATE"] = run_date
    env["WORKFLOW_DATE"] = run_date

    # ------------------------------------------------------------
    # Start subprocess
    # ------------------------------------------------------------

    process = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.path.abspath(os.path.dirname(__file__)),
        env=env
    )

    log_buffer = []
    BUFFER_SIZE = 50

    # ------------------------------------------------------------
    # Read process output
    # ------------------------------------------------------------

    for line in iter(process.stdout.readline, ''):

        log_buffer.append(line)

        if len(log_buffer) >= BUFFER_SIZE:

            chunk = "".join(log_buffer)

            append_step_log(
                step_id,
                chunk
            )

            broadcast(
                step_index,
                chunk
            )

            log_buffer = []

    # ------------------------------------------------------------
    # Flush remaining output
    # ------------------------------------------------------------

    if log_buffer:

        chunk = "".join(log_buffer)

        append_step_log(
            step_id,
            chunk
        )

        broadcast(
            step_index,
            chunk
        )

    process.stdout.close()

    return_code = process.wait()

    end_time = datetime.now()
    duration = end_time - start_time

    log(
        f"{step['name']} | "
        f"Run Date: {run_date} | "
        f"Start: {start_time} | "
        f"End: {end_time} | "
        f"Duration: {duration} | "
        f"Code: {return_code}"
    )

    # ------------------------------------------------------------
    # Handle failure
    # ------------------------------------------------------------

    if return_code != 0:

        msg = (
            f"Step failed with exit code "
            f"{return_code}\n"
        )

        append_step_log(
            step_id,
            msg
        )

        broadcast(
            step_index,
            msg,
            is_error=True
        )

        update_step_status(
            step_id,
            "Failed"
        )

        update_run_status(
            run_id,
            "Failed",
            error_message=f"Step '{step['name']}' failed."
        )

        raise Exception(
            f"Script failed: {script_path}"
        )

    # ------------------------------------------------------------
    # Check expected output
    # ------------------------------------------------------------

    if step["check_file"]:

        check_path = os.path.abspath(
            step["check_file"]
        )

        if not os.path.exists(check_path):

            msg = (
                f"Expected output not found: "
                f"{check_path}\n"
            )

            append_step_log(
                step_id,
                msg
            )

            broadcast(
                step_index,
                msg,
                is_error=True
            )

            update_step_status(
                step_id,
                "Failed"
            )

            update_run_status(
                run_id,
                "Failed",
                error_message=(
                    f"Expected output missing "
                    f"for '{step['name']}'"
                )
            )

            raise Exception(msg)

    # ------------------------------------------------------------
    # Success
    # ------------------------------------------------------------

    update_step_status(
        step_id,
        "Success"
    )

    broadcast(
        step_index,
        f"Completed: {step['name']}\n"
    )


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":

    from dashboard.models import (
        init_db,
        create_run,
        update_run_status,
        get_run_details
    )

    import urllib.request
    import json

    # ------------------------------------------------------------
    # GET PROCESSING DATE
    # ------------------------------------------------------------

    # If running:
    #
    # python main.py 2026-08-26
    #
    # run_date = 2026-08-26
    #
    # If running:
    #
    # python main.py
    #
    # run_date = D-1

    cli_date = None

    if len(sys.argv) > 1:
        cli_date = sys.argv[1]

    try:

        run_date = get_run_date(
            cli_date
        )

    except ValueError as e:

        print(f"ERROR: {e}")
        sys.exit(1)

    # ------------------------------------------------------------
    # SET ENVIRONMENT FOR ALL CHILD PROCESSES
    # ------------------------------------------------------------

    os.environ["RUN_DATE"] = run_date
    os.environ["WORKFLOW_DATE"] = run_date

    # ------------------------------------------------------------
    # INITIALIZE DATABASE
    # ------------------------------------------------------------

    sys.path.insert(
        0,
        os.path.abspath(
            os.path.dirname(__file__)
        )
    )

    init_db()

    # ------------------------------------------------------------
    # CREATE PIPELINE RUN
    # ------------------------------------------------------------

    run_id = create_run(
        run_date,
        trigger_type="manual" if cli_date else "cron"
    )

    # ------------------------------------------------------------
    # BROADCAST
    # ------------------------------------------------------------

    def broadcast(
        step_index,
        message,
        is_error=False
    ):

        print(
            message,
            end=""
        )

        sys.stdout.flush()

        payload = json.dumps({
            "run_id": run_id,
            "step_index": step_index,
            "message": message,
            "is_error": is_error
        }).encode("utf-8")

        try:

            req = urllib.request.Request(
                "http://127.0.0.1:5000/api/workflow/broadcast",
                data=payload,
                headers={
                    "Content-Type": "application/json"
                },
                method="POST"
            )

            with urllib.request.urlopen(
                req,
                timeout=0.5
            ):
                pass

        except Exception:
            pass

    # ------------------------------------------------------------
    # START PIPELINE
    # ------------------------------------------------------------

    broadcast(
        -1,
        f"\nStarting Pipeline Execution\n"
        f"Processing Date: {run_date}\n\n"
    )

    try:

        # ========================================================
        # PARALLEL: Step 0 and Step 1
        # ========================================================

        with ThreadPoolExecutor(
            max_workers=2
        ) as executor:

            future_1 = executor.submit(
                run_step,
                PIPELINE[0],
                0,
                run_id,
                broadcast,
                run_date
            )

            future_2 = executor.submit(
                run_step,
                PIPELINE[1],
                1,
                run_id,
                broadcast,
                run_date
            )

            future_1.result()
            future_2.result()

        # ========================================================
        # SEQUENTIAL: Remaining steps
        # ========================================================

        for i in range(
            2,
            len(PIPELINE)
        ):

            run_step(
                PIPELINE[i],
                i,
                run_id,
                broadcast,
                run_date
            )

        # --------------------------------------------------------
        # SUCCESS
        # --------------------------------------------------------

        update_run_status(
            run_id,
            "Success"
        )

        broadcast(
            -1,
            "\nPipeline completed successfully!"
        )

    except Exception as e:

        run_details = get_run_details(
            run_id
        )

        if (
            run_details
            and run_details.get("status") == "Running"
        ):

            update_run_status(
                run_id,
                "Failed",
                error_message=str(e)
            )

        broadcast(
            -1,
            f"\nPipeline stopped due to error: "
            f"{str(e)}\n"
        )



