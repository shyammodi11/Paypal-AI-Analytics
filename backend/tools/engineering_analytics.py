import re
from collections import Counter

from backend.database.db import get_connection


# ============================================================
# 1. ENGINEERING SIGNAL TAXONOMY
# ============================================================

ENGINEERING_SIGNAL_RULES = {

    "app_crash": [
        r"\bapp crashes?\b",
        r"\bcrashed\b",
        r"\bkeeps crashing\b",
        r"\bapp closes?\b",
        r"\bcloses unexpectedly\b",
        r"\bforce close\b",
        r"\bkeeps closing\b",
        r"\bunexpectedly exits\b"
    ],

    "freezing_and_unresponsiveness": [
        r"\bfreezes?\b",
        r"\bfrozen\b",
        r"\bnot responding\b",
        r"\bstuck on (loading|screen|login)\b",
        r"\bhangs?\b",
        r"\bgets stuck\b"
    ],

    "performance": [
        r"\bvery slow\b",
        r"\bextremely slow\b",
        r"\bslow loading\b",
        r"\btakes forever to load\b",
        r"\blagging\b",
        r"\blags\b",
        r"\bperformance issue\b",
        r"\bloading endlessly\b",
        r"\bspinning (wheel|circle)\b"
    ],

    "login_and_authentication": [
        r"\bcannot log in\b",
        r"\bcan't log in\b",
        r"\bcannot login\b",
        r"\bcan't login\b",
        r"\bunable to log in\b",
        r"\bunable to login\b",
        r"\blogin failed\b",
        r"\bpassword not working\b",
        r"\botp\b",
        r"\bverification code\b",
        r"\bcode not received\b",
        r"\bnot receiving (the )?(code|otp)\b",
        r"\bverification failed\b",
        r"\b2.factor authentication\b"
    ],

    "payment_and_transfer_failure": [
        r"\bpayment failed\b",
        r"\bpayments? (is|are) failing\b",
        r"\bunable to pay\b",
        r"\bcannot pay\b",
        r"\bcan't pay\b",
        r"\btransfer failed\b",
        r"\btransfer (is )?not working\b",
        r"\bunable to transfer\b",
        r"\bmoney (is )?not sent\b",
        r"\btransaction failed\b",
        r"\bcheckout failed\b",
        r"\bdeclined unexpectedly\b"
    ],

    "notification_issues": [
        r"\bno notification\b",
        r"\bnotifications? not working\b",
        r"\bnot receiving notifications\b",
        r"\bnotification not received\b",
        r"\balerts? not working\b",
        r"\bno alert\b"
    ],

    "app_update_and_compatibility": [
        r"\bafter (the )?update\b",
        r"\bsince (the )?update\b",
        r"\bnew update\b",
        r"\bupdate broke\b",
        r"\bwon't update\b",
        r"\bupdate failed\b",
        r"\bincompatible\b",
        r"\bcompatibility issue\b"
    ],

    "ui_and_navigation": [
        r"\bbutton (doesn't|does not) work\b",
        r"\bbutton not working\b",
        r"\bcan't find\b",
        r"\bcannot find\b",
        r"\bmenu not working\b",
        r"\bscreen is blank\b",
        r"\bblank screen\b",
        r"\bpage not loading\b",
        r"\bcan't navigate\b",
        r"\bnavigation issue\b",
        r"\binterface is confusing\b"
    ]
}


# ============================================================
# 2. ENGINEERING CLASSIFICATION CATEGORIES
# ============================================================

ENGINEERING_RELEVANT_ISSUES = {
    "Bug / Technical Defect",
    "Performance Issue",
    "Logical / Functional Issue"
}

ENGINEERING_RELEVANT_COMPLAINTS = {
    "App Performance",
    "Login & Verification",
    "Payment Issues",
    "Bank & Card Issues"
}


# ============================================================
# 3. ANALYSE A SINGLE REVIEW
# ============================================================

def analyze_engineering_signals(
    review_text,
    complaint_category=None,
    issue_nature=None
):
    """
    Identify potential engineering-related symptoms.

    Signals are based on customer-reported text and
    existing classification outputs.

    This does not confirm a software defect or root cause.
    """

    text = str(review_text or "").lower()

    matched_signals = []

    for signal_type, patterns in ENGINEERING_SIGNAL_RULES.items():

        matched_patterns = [
            pattern
            for pattern in patterns
            if re.search(pattern, text)
        ]

        if matched_patterns:
            matched_signals.append({
                "signal_type": signal_type,
                "matched_patterns": matched_patterns
            })

    issue_match = (
        issue_nature in ENGINEERING_RELEVANT_ISSUES
    )

    complaint_match = (
        complaint_category in ENGINEERING_RELEVANT_COMPLAINTS
    )

    is_candidate = (
        len(matched_signals) > 0
        or issue_match
        or complaint_match
    )

    if not is_candidate:
        return {
            "is_candidate": False,
            "signal_types": [],
            "matched_signals": [],
            "issue_match": False,
            "complaint_match": False,
            "triage_level": "Not flagged"
        }

    signal_types = [
        item["signal_type"]
        for item in matched_signals
    ]

    # Triage is a prioritisation heuristic,
    # not a measure of verified technical severity.

    high_priority_signals = {
        "app_crash",
        "payment_and_transfer_failure"
    }

    if any(
        signal in high_priority_signals
        for signal in signal_types
    ):
        triage_level = "High"

    elif len(signal_types) >= 2:
        triage_level = "Medium"

    elif len(signal_types) == 1:
        triage_level = "Medium"

    else:
        triage_level = "Review Required"

    return {
        "is_candidate": True,
        "signal_types": signal_types,
        "matched_signals": matched_signals,
        "issue_match": issue_match,
        "complaint_match": complaint_match,
        "triage_level": triage_level
    }


# ============================================================
# 4. FIND ENGINEERING CANDIDATES IN DATABASE
# ============================================================

def find_engineering_candidates(
    limit=50,
    offset=0,
    triage_level=None,
    app_version=None,
    platform=None
):
    """
    Retrieve reviews with potential engineering symptoms.

    Optional filters:
    - triage_level
    - app_version
    - platform
    """

    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    if not isinstance(offset, int) or offset < 0:
        raise ValueError("offset cannot be negative.")

    allowed_triage_levels = [
        "High",
        "Medium",
        "Review Required"
    ]

    if (
        triage_level is not None
        and triage_level not in allowed_triage_levels
    ):
        raise ValueError("Invalid triage level.")

    conditions = []
    params = []

    if app_version:
        conditions.append("app_version LIKE ?")
        params.append(f"%{app_version}%")

    if platform:
        conditions.append("LOWER(platform) = LOWER(?)")
        params.append(platform)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    with get_connection() as connection:

        rows = connection.execute(
            f"""
            SELECT
                classification_id,
                review_id,
                review_text,
                rating,
                platform,
                review_date,
                app_version,
                complaint_category,
                issue_nature
            FROM reviews
            {where_clause}
            """,
            params
        ).fetchall()

    candidates = []

    for row in rows:

        review = dict(row)

        analysis = analyze_engineering_signals(
            review_text=review["review_text"],
            complaint_category=review["complaint_category"],
            issue_nature=review["issue_nature"]
        )

        if not analysis["is_candidate"]:
            continue

        if (
            triage_level is not None
            and analysis["triage_level"] != triage_level
        ):
            continue

        review["engineering_analysis"] = analysis

        candidates.append(review)

    triage_order = {
        "High": 0,
        "Medium": 1,
        "Review Required": 2
    }

    candidates.sort(
        key=lambda item: (
            triage_order[item["engineering_analysis"]["triage_level"]],
            item["review_date"] or ""
        )
    )

    total_matches = len(candidates)

    # Summary is calculated across all matching candidates,
    # not just the current page.
    triage_summary = {
        level: sum(
            1 for item in candidates
            if item["engineering_analysis"]["triage_level"] == level
        )
        for level in allowed_triage_levels
    }

    signal_summary = Counter()

    version_summary = Counter()

    for item in candidates:

        for signal in item["engineering_analysis"]["signal_types"]:
            signal_summary[signal] += 1

        version = item["app_version"] or "Unknown / Missing"
        version_summary[version] += 1

    return {
        "total_candidates": total_matches,
        "returned_count": min(limit, max(0, total_matches - offset)),
        "limit": limit,
        "offset": offset,
        "filters": {
            "triage_level": triage_level,
            "app_version": app_version,
            "platform": platform
        },
        "triage_summary": triage_summary,
        "signal_summary": dict(signal_summary.most_common()),
        "version_summary": dict(version_summary.most_common(15)),
        "reviews": candidates[offset:offset + limit],
        "disclaimer": (
            "These are customer-reported technical symptoms and "
            "classification-based candidates. They do not establish "
            "confirmed software defects or backend root causes."
        )
    }