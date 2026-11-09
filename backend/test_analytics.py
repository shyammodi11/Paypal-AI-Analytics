from backend.tools.complaint_analytics import (
    get_distribution,
    get_complaint_overview
)


# ============================================================
# TEST 1: COMPLAINT CATEGORY DISTRIBUTION
# ============================================================

print("\nTEST 1: Complaint Category Distribution")

result = get_distribution(
    dimension="complaint_category"
)

print("Total reviews:", result["total_reviews"])

for item in result["distribution"]:
    print(
        item["label"],
        "| Count:", item["review_count"],
        "| Percentage:", item["percentage"], "%"
    )


# ============================================================
# TEST 2: ISSUE NATURE DISTRIBUTION
# ============================================================

print("\nTEST 2: Issue Nature Distribution")

result = get_distribution(
    dimension="issue_nature"
)

print("Total reviews:", result["total_reviews"])

for item in result["distribution"]:
    print(
        item["label"],
        "| Count:", item["review_count"],
        "| Percentage:", item["percentage"], "%"
    )


# ============================================================
# TEST 3: PLATFORM DISTRIBUTION
# ============================================================

print("\nTEST 3: Platform Distribution")

result = get_distribution(
    dimension="platform"
)

for item in result["distribution"]:
    print(item)


# ============================================================
# TEST 4: FILTERED COMPLAINT OVERVIEW
# ============================================================

print("\nTEST 4: Complaint Overview")

result = get_complaint_overview()

print("Total reviews:", result["total_reviews"])
print("Complaint categories:", len(result["complaint_categories"]))
print("Issue natures:", len(result["issue_natures"]))


# ============================================================
# TEST 5: INVALID DIMENSION
# ============================================================

print("\nTEST 5: Invalid Dimension Handling")

try:
    get_distribution("customer_name")

except ValueError as error:
    print("Correctly handled:", error)


print("\nALL ANALYTICS TESTS COMPLETED.")