from backend.tools.engineering_analytics import (
    analyze_engineering_signals,
    find_engineering_candidates
)


# ============================================================
# TEST 1: APP CRASH
# ============================================================

print("\nTEST 1: App Crash")

result = analyze_engineering_signals(
    "The PayPal app crashes every time I try to open it."
)

print(result)

assert result["is_candidate"] is True
assert "app_crash" in result["signal_types"]


# ============================================================
# TEST 2: PERFORMANCE
# ============================================================

print("\nTEST 2: Performance")

result = analyze_engineering_signals(
    "The application is extremely slow and keeps loading."
)

print(result)

assert result["is_candidate"] is True
assert "performance" in result["signal_types"]


# ============================================================
# TEST 3: LOGIN AND OTP
# ============================================================

print("\nTEST 3: Login and OTP")

result = analyze_engineering_signals(
    "I am not receiving the OTP verification code."
)

print(result)

assert result["is_candidate"] is True
assert "login_and_authentication" in result["signal_types"]


# ============================================================
# TEST 4: PAYMENT FAILURE
# ============================================================

print("\nTEST 4: Payment Failure")

result = analyze_engineering_signals(
    "My payment failed even though I have sufficient funds."
)

print(result)

assert result["is_candidate"] is True
assert "payment_and_transfer_failure" in result["signal_types"]


# ============================================================
# TEST 5: NOTIFICATION ISSUE
# ============================================================

print("\nTEST 5: Notifications")

result = analyze_engineering_signals(
    "I am not receiving notifications for payments."
)

print(result)

assert result["is_candidate"] is True
assert "notification_issues" in result["signal_types"]


# ============================================================
# TEST 6: UPDATE ISSUE
# ============================================================

print("\nTEST 6: App Update")

result = analyze_engineering_signals(
    "The new update broke the application."
)

print(result)

assert result["is_candidate"] is True
assert "app_update_and_compatibility" in result["signal_types"]


# ============================================================
# TEST 7: CLASSIFICATION-BASED CANDIDATE
# ============================================================

print("\nTEST 7: Classification-Based Candidate")

result = analyze_engineering_signals(
    "PayPal is frustrating.",
    issue_nature="Bug / Technical Defect"
)

print(result)

assert result["is_candidate"] is True
assert result["issue_match"] is True


# ============================================================
# TEST 8: ORDINARY REVIEW
# ============================================================

print("\nTEST 8: Ordinary Review")

result = analyze_engineering_signals(
    "I like using PayPal to send money to my family."
)

print(result)

assert result["is_candidate"] is False


# ============================================================
# TEST 9: DATABASE-LEVEL DETECTION
# ============================================================

print("\nTEST 9: Database Engineering Search")

result = find_engineering_candidates(limit=10)

print("Total candidates:", result["total_candidates"])
print("Returned:", result["returned_count"])
print("Triage summary:", result["triage_summary"])
print("Signal summary:", result["signal_summary"])
print("Version summary:", result["version_summary"])

for review in result["reviews"]:

    print("\nClassification ID:", review["classification_id"])
    print("Rating:", review["rating"])
    print("Platform:", review["platform"])
    print("Version:", review["app_version"])
    print("Issue nature:", review["issue_nature"])
    print("Signals:", review["engineering_analysis"]["signal_types"])
    print("Triage:", review["engineering_analysis"]["triage_level"])
    print("Review:", review["review_text"][:200])


# ============================================================
# TEST 10: PLATFORM FILTER
# ============================================================

print("\nTEST 10: Android Filter")

result = find_engineering_candidates(
    limit=5,
    platform="android"
)

print("Android candidates:", result["total_candidates"])


# ============================================================
# TEST 11: INVALID TRIAGE FILTER
# ============================================================

print("\nTEST 11: Invalid Triage")

try:
    find_engineering_candidates(
        triage_level="Critical"
    )

except ValueError as error:
    print("Correctly handled:", error)


print("\nALL ENGINEERING TESTS COMPLETED.")