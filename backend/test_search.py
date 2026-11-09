from backend.tools.review_search import (
    search_review_evidence,
    get_review_evidence
)


# ============================================================
# TEST 1: KEYWORD SEARCH
# ============================================================

print("\nTEST 1: Searching for 'refund'")

result = search_review_evidence(
    keyword="refund",
    limit=5
)

print("Total matches:", result["total_matches"])
print("Returned:", result["returned_count"])

for review in result["reviews"]:

    print("\nReview ID:", review["classification_id"])
    print("Rating:", review["rating"])
    print("Complaint:", review["complaint_category"])
    print("Text:", review["review_text"][:200])


# ============================================================
# TEST 2: COMPLAINT CATEGORY FILTER
# ============================================================

print("\n\nTEST 2: Customer Support complaints")

result = search_review_evidence(
    complaint_category="Customer Support",
    limit=5
)

print("Total matches:", result["total_matches"])

for review in result["reviews"]:
    print(review["review_text"][:150])


# ============================================================
# TEST 3: INDIVIDUAL REVIEW RETRIEVAL
# ============================================================

print("\n\nTEST 3: Individual review retrieval")

if result["reviews"]:

    classification_id = result["reviews"][0]["classification_id"]

    review = get_review_evidence(classification_id)

    print("Retrieved:", review is not None)
    print("Classification ID:", review["classification_id"])
    print("Original review:", review["raw_data"]["content"])
    print("Full classification fields:")
    print([
        key for key in review["raw_data"]
        if key.endswith("_primary")
    ])