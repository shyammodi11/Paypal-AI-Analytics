
import json

from backend.database.db import get_connection


# ============================================================
# 1. SEARCH REVIEW EVIDENCE
# ============================================================

def search_review_evidence(
    keyword=None,
    complaint_category=None,
    issue_nature=None,
    platform=None,
    rating=None,
    app_version=None,
    limit=20,
    offset=0
):
    """
    Search customer reviews using keywords and filters.

    Returns matching reviews with their classification evidence.
    """

    # --------------------------------------------------------
    # Validate pagination
    # --------------------------------------------------------

    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")

    if not isinstance(offset, int) or offset < 0:
        raise ValueError("offset cannot be negative.")

    if rating is not None:
        rating = int(rating)

        if rating not in [1, 2, 3, 4, 5]:
            raise ValueError("rating must be between 1 and 5.")

    # --------------------------------------------------------
    # Build parameterised SQL query
    # --------------------------------------------------------

    conditions = []
    params = []

    if keyword and keyword.strip():
        conditions.append(
            "LOWER(review_text) LIKE LOWER(?)"
        )
        params.append(f"%{keyword.strip()}%")

    if complaint_category:
        conditions.append(
            "complaint_category = ?"
        )
        params.append(complaint_category)

    if issue_nature:
        conditions.append(
            "issue_nature = ?"
        )
        params.append(issue_nature)

    if platform:
        conditions.append(
            "LOWER(platform) = LOWER(?)"
        )
        params.append(platform)

    if rating is not None:
        conditions.append("rating = ?")
        params.append(rating)

    if app_version:
        conditions.append(
            "app_version LIKE ?"
        )
        params.append(f"%{app_version}%")

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    # --------------------------------------------------------
    # Execute search
    # --------------------------------------------------------

    with get_connection() as connection:

        total_matches = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM reviews
            {where_clause}
            """,
            params
        ).fetchone()[0]

        results = connection.execute(
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

            ORDER BY review_date DESC

            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        ).fetchall()

    reviews = [dict(row) for row in results]

    return {
        "total_matches": total_matches,
        "returned_count": len(reviews),
        "limit": limit,
        "offset": offset,
        "filters": {
            "keyword": keyword,
            "complaint_category": complaint_category,
            "issue_nature": issue_nature,
            "platform": platform,
            "rating": rating,
            "app_version": app_version
        },
        "reviews": reviews
    }


# ============================================================
# 2. RETRIEVE INDIVIDUAL REVIEW EVIDENCE
# ============================================================

def get_review_evidence(classification_id):
    """
    Retrieve one complete review using its classification ID.

    raw_data contains the original review fields and
    all available classification outputs.
    """

    if not classification_id:
        raise ValueError("classification_id is required.")

    with get_connection() as connection:

        result = connection.execute(
            """
            SELECT *
            FROM reviews
            WHERE classification_id = ?
            """,
            (classification_id,)
        ).fetchone()

    if result is None:
        return None

    review = dict(result)

    review["raw_data"] = json.loads(
        review.pop("raw_json")
    )

    return review
