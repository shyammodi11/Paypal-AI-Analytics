import re

from backend.database.db import get_connection


# ============================================================
# 1. FRAUD AND SECURITY SIGNAL TAXONOMY
# ============================================================

FRAUD_SIGNAL_RULES = {

    "unauthorized_transaction": [
    r"unauthori[sz]ed.{0,30}(payment|charge|transaction|purchase|withdrawal)",
    r"(payment|charge|transaction|purchase|withdrawal).{0,30}unauthori[sz]ed",
    r"(payment|charge|transaction|purchase).{0,50}without my permission",
    r"(payment|charge|transaction|purchase).{0,50}without my consent",
    r"without my permission.{0,50}(payment|charge|transaction|purchase)",
    r"without my consent.{0,50}(payment|charge|transaction|purchase)",
    r"i did not make this transaction",
    r"i didn't make this transaction",
    r"i never made this payment",
    r"i never authorized",
    r"transaction.{0,30}(not mine|don't recognize|do not recognize)",
    r"payment.{0,30}(not mine|don't recognize|do not recognize)",
    r"someone used my (credit|debit)? ?card",
    r"someone made (a )?(payment|purchase|transaction)"
    ],

    "account_compromise": [
        r"my account (was )?hacked",
        r"someone hacked my account",
        r"someone accessed my account",
        r"account takeover",
        r"account was compromised",
        r"my account has been compromised",
        r"someone changed my (password|email|phone)",
        r"login from an unknown device",
        r"someone logged into my account"
    ],

    "phishing_and_impersonation": [
        r"\bphishing\b",
        r"\bphishing email\b",
        r"\bscammer\b",
        r"\bscam(?:med|ming)?\b",
        r"fake paypal",
        r"pretending to be paypal",
        r"impersonat(?:e|ed|ing|ion)",
        r"suspicious link",
        r"asked me for my password",
        r"fake payment confirmation"
    ],

    "identity_or_payment_compromise": [
        r"identity theft",
        r"stolen identity",
        r"stolen (credit|debit) card",
        r"card details (were )?stolen",
        r"my card was compromised",
        r"my bank details were stolen",
        r"someone stole my (money|funds)",
        r"money was taken from my account"
    ],

    "suspicious_activity": [
        r"suspicious activity",
        r"suspicious transaction",
        r"unknown transaction",
        r"unrecognized transaction",
        r"unrecognised transaction",
        r"unknown payment",
        r"unexpected charge",
        r"charge i did not make"
    ]
}


# ============================================================
# 2. ANALYSE A SINGLE REVIEW
# ============================================================

def analyze_fraud_signals(
    review_text,
    complaint_category=None
):
    """
    Identify potential fraud/security signals in review text.

    This function identifies customer-reported indicators.
    It does not verify actual fraud.
    """

    text = str(review_text or "").lower()

    matched_signals = []

    for signal_type, patterns in FRAUD_SIGNAL_RULES.items():

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

    category_match = (
        complaint_category == "Fraud & Security"
    )

    # A review can be included through its category
    # or through an explicit text-based signal.
    is_candidate = (
        category_match or len(matched_signals) > 0
    )

    if not is_candidate:
        return {
            "is_candidate": False,
            "signal_types": [],
            "matched_signals": [],
            "category_match": False,
            "triage_level": "Not flagged"
        }

    signal_types = [
        item["signal_type"]
        for item in matched_signals
    ]

    # Triage levels are prioritisation heuristics,
    # not probabilities or verified fraud severity.
    if (
        "unauthorized_transaction" in signal_types
        or "account_compromise" in signal_types
        or "identity_or_payment_compromise" in signal_types
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
        "category_match": category_match,
        "triage_level": triage_level
    }


# ============================================================
# 3. FIND FRAUD / SECURITY CANDIDATES IN DATABASE
# ============================================================

def find_fraud_candidates(
    limit=50,
    offset=0,
    triage_level=None
):
    """
    Retrieve reviews containing potential fraud/security signals.

    Includes:
    - Fraud & Security category reviews
    - Reviews with explicit fraud/security text indicators

    Returns original review evidence and transparent reasons.
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

    with get_connection() as connection:

        rows = connection.execute(
            """
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
            """
        ).fetchall()

    candidates = []

    for row in rows:

        review = dict(row)

        analysis = analyze_fraud_signals(
            review_text=review["review_text"],
            complaint_category=review["complaint_category"]
        )

        if not analysis["is_candidate"]:
            continue

        if (
            triage_level is not None
            and analysis["triage_level"] != triage_level
        ):
            continue

        review["fraud_analysis"] = analysis

        candidates.append(review)

    # Prioritise high-triage candidates, then medium.
    triage_order = {
        "High": 0,
        "Medium": 1,
        "Review Required": 2
    }

    candidates.sort(
        key=lambda item: (
            triage_order[item["fraud_analysis"]["triage_level"]],
            item["review_date"] or ""
        ),
        reverse=False
    )

    total_matches = len(candidates)

    paginated_candidates = candidates[
        offset:offset + limit
    ]

    return {
        "total_candidates": total_matches,
        "returned_count": len(paginated_candidates),
        "limit": limit,
        "offset": offset,
        "triage_filter": triage_level,
        "triage_summary": {
            level: sum(
                1 for item in candidates
                if item["fraud_analysis"]["triage_level"] == level
            )
            for level in allowed_triage_levels
        },
        "reviews": paginated_candidates,
        "disclaimer": (
            "These are customer-reported potential fraud or "
            "security signals. They are not verified fraud events."
        )
    }