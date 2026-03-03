"""
H1B sponsorship history checker using DOL public dataset.
Loads data/h1b_sponsors.csv at module level.
"""

import os
import warnings
import pandas as pd

# Load H1B sponsor data
_csv_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "h1b_sponsors.csv",
)

_df = None
try:
    _df = pd.read_csv(_csv_path)
    # Normalise column names (handle various CSV formats)
    _df.columns = [c.strip().upper().replace(" ", "_") for c in _df.columns]
    if "EMPLOYER_NAME" not in _df.columns:
        # Try common alternative names
        for col in _df.columns:
            if "EMPLOYER" in col or "COMPANY" in col or "NAME" in col:
                _df = _df.rename(columns={col: "EMPLOYER_NAME"})
                break
    if "INITIAL_APPROVALS" not in _df.columns:
        for col in _df.columns:
            if "INITIAL" in col and "APPROVAL" in col:
                _df = _df.rename(columns={col: "INITIAL_APPROVALS"})
                break
        if "INITIAL_APPROVALS" not in _df.columns:
            # Fallback — create a count column
            _df["INITIAL_APPROVALS"] = 1
except FileNotFoundError:
    _df = None
    warnings.warn(
        f"H1B sponsors CSV not found at {_csv_path}. "
        "Sponsorship checks will return 'data not available'."
    )
except Exception as e:
    _df = None
    warnings.warn(f"Error loading H1B sponsors CSV: {e}")


def check_sponsorship_history(company_name: str) -> dict:
    """
    Check if a company has H1B sponsorship history.
    Case-insensitive partial match on EMPLOYER_NAME.
    Returns dict with has_history, approvals, and message.
    """
    try:
        if _df is None or company_name is None:
            return {
                "has_history": False,
                "approvals": 0,
                "message": "Sponsorship data not available",
            }

        company_lower = company_name.strip().lower()
        if not company_lower:
            return {
                "has_history": False,
                "approvals": 0,
                "message": "No company name provided",
            }

        # Case-insensitive partial match
        mask = _df["EMPLOYER_NAME"].str.lower().str.contains(
            company_lower, na=False
        )
        matches = _df[mask]

        if matches.empty:
            return {
                "has_history": False,
                "approvals": 0,
                "message": f"No H1B history found for '{company_name}'",
            }

        total_approvals = int(
            matches["INITIAL_APPROVALS"].sum()
        )
        return {
            "has_history": True,
            "approvals": total_approvals,
            "message": f"{total_approvals} H1B approvals on record",
        }

    except Exception as e:
        print(f"[check_sponsorship_history] Error: {e}")
        return {
            "has_history": False,
            "approvals": 0,
            "message": f"Error checking sponsorship: {e}",
        }

