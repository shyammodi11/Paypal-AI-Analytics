from backend.tools.fraud_detection import (
    analyze_fraud_signals,
    find_fraud_candidates
)


# ============================================================
# TEST 1: UNAUTHORISED TRANSACTION
# ============================================================

print("\nTEST 1: Unauthorised Transaction")

result = analyze_fraud_signals(
    "Someone used my card without my permission."
)

print(result)

assert result["is_candidate"] is True
assert "unauthorized_transaction" in result["signal_types"]


# ============================================================
# TEST 2: ACCOUNT COMPROMISE
# ============================================================

print("\nTEST 2: Account Compromise")

result = analyze_fraud_signals(
    "My PayPal account was hacked and someone changed my password."
)

print(result)

assert result["is_candidate"] is True
assert "account_compromise" in result["signal_types"]


# ============================================================
# TEST 3: PHISHING / IMPERSONATION
# ============================================================

print("\nTEST 3: Phishing")

result = analyze_fraud_signals(
    "I received a fake PayPal email containing a suspicious link."
)

print(result)

assert result["is_candidate"] is True
assert "phishing_and_impersonation" in result["signal_types"]


# ============================================================
# TEST 4: NON-FRAUD REVIEW
# ============================================================

print("\nTEST 4: Ordinary Complaint")

result = analyze_fraud_signals(
    "The app is slow and customer support takes too long."
)

print(result)

assert result["is_candidate"] is False


# ============================================================
# TEST 5: CATEGORY-BASED CANDIDATE
# ============================================================

print("\nTEST 5: Fraud & Security Category")

result = analyze_fraud_signals(
    "PayPal is not providing good customer service.",
    complaint_category="Fraud & Security"
)

print(result)

assert result["is_candidate"] is True
assert result["category_match"] is True

# ============================================================
# TEST 6: PHONE NUMBER CHANGE IS NOT A TRANSACTION
# ============================================================

print("\nTEST 6: Account Change vs Unauthorised Transaction")

result = analyze_fraud_signals(
    "Someone changed my phone number without my permission."
)

print(result)

assert result["is_candidate"] is True
assert "account_compromise" in result["signal_types"]
assert "unauthorized_transaction" not in result["signal_types"]

# ============================================================
# TEST 7: DATABASE-LEVEL DETECTION
# ============================================================

print("\nTEST 7: Database Fraud Candidate Search")

result = find_fraud_candidates(limit=10)

print("Total candidates:", result["total_candidates"])
print("Returned:", result["returned_count"])
print("Triage summary:", result["triage_summary"])

for review in result["reviews"]:

    print("\nClassification ID:", review["classification_id"])
    print("Rating:", review["rating"])
    print("Category:", review["complaint_category"])
    print("Triage:", review["fraud_analysis"]["triage_level"])
    print("Signals:", review["fraud_analysis"]["signal_types"])
    print("Review:", review["review_text"][:250])


# ============================================================
# TEST 8: HIGH-PRIORITY FILTER
# ============================================================

print("\nTEST 8: High-Priority Candidates")

result = find_fraud_candidates(
    limit=10,
    triage_level="High"
)

print("High-priority candidates:", result["total_candidates"])


# ============================================================
# TEST 9: INVALID TRIAGE FILTER
# ============================================================

print("\nTEST 9: Invalid Triage Filter")

try:
    find_fraud_candidates(
        triage_level="Critical"
    )

except ValueError as error:
    print("Correctly handled:", error)


print("\nALL FRAUD DETECTION TESTS COMPLETED.")