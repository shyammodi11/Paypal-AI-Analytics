from backend.database.db import get_connection


# Only these database columns can be used for grouping.
ALLOWED_DIMENSIONS = {
    "complaint_category",
    "issue_nature",
    "platform",
    "rating",
    "app_version"
}


def get_distribution(
    dimension,
    platform=None,
    rating=None
):
    """
    Calculate the distribution of reviews across a selected dimension.

    Examples:
    - complaint_category
    - issue_nature
    - platform
    - rating
    - app_version
    """

    if dimension not in ALLOWED_DIMENSIONS:
        raise ValueError(
            f"Unsupported dimension: {dimension}"
        )

    conditions = []
    params = []

    if platform:
        conditions.append("LOWER(platform) = LOWER(?)")
        params.append(platform)

    if rating is not None:
        rating = int(rating)

        if rating not in [1, 2, 3, 4, 5]:
            raise ValueError("Rating must be between 1 and 5.")

        conditions.append("rating = ?")
        params.append(rating)

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    query = f"""
        SELECT
            COALESCE(
                CAST({dimension} AS TEXT),
                'Unknown / Missing'
            ) AS label,
            COUNT(*) AS review_count
        FROM reviews
        {where_clause}
        GROUP BY {dimension}
        ORDER BY review_count DESC
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            params
        ).fetchall()

    results = [
        {
            "label": row["label"],
            "review_count": row["review_count"]
        }
        for row in rows
    ]

    total = sum(
        item["review_count"]
        for item in results
    )

    for item in results:
        item["percentage"] = (
            round(item["review_count"] / total * 100, 2)
            if total else 0
        )

    return {
        "dimension": dimension,
        "total_reviews": total,
        "distribution": results
    }


def get_complaint_overview(platform=None):
    """
    Generate an overview of complaint categories
    and issue natures.
    """

    complaint_distribution = get_distribution(
        dimension="complaint_category",
        platform=platform
    )

    issue_distribution = get_distribution(
        dimension="issue_nature",
        platform=platform
    )

    return {
        "total_reviews": complaint_distribution["total_reviews"],
        "platform_filter": platform,
        "complaint_categories": complaint_distribution["distribution"],
        "issue_natures": issue_distribution["distribution"]
    }