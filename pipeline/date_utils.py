import os
import sys
from datetime import datetime, timedelta


def get_run_date(cli_date=None):
    """
    Determine the processing date for the pipeline.

    Priority:
    1. Date explicitly supplied to main.py
    2. RUN_DATE environment variable
    3. WORKFLOW_DATE environment variable
    4. D-1 if nothing is supplied

    Expected date format: YYYY-MM-DD
    """

    # ------------------------------------------------------------
    # 1. Date supplied directly to main.py
    # Example:
    # python main.py 2026-08-26
    # ------------------------------------------------------------
    run_date = cli_date

    # ------------------------------------------------------------
    # 2. Environment variables
    # ------------------------------------------------------------
    if not run_date:
        run_date = (
            os.environ.get("RUN_DATE")
            or os.environ.get("WORKFLOW_DATE")
        )

    # ------------------------------------------------------------
    # 3. Default to D-1
    # ------------------------------------------------------------
    if not run_date:
        run_date = (
            datetime.now() - timedelta(days=1)
        ).strftime("%Y-%m-%d")

    # ------------------------------------------------------------
    # 4. Validate date format
    # ------------------------------------------------------------
    try:
        datetime.strptime(run_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"Invalid run date: {run_date}. "
            f"Expected format YYYY-MM-DD."
        )

    return run_date

