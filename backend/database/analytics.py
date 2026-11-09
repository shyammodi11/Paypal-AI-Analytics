
import sqlite3
import pandas as pd

from backend.config import DATABASE_PATH


DIMENSIONS = [
    "business_context",
    "stakeholder",
    "business_operation",
    "request_intent",
    "business_impact",
    "product_module",
    "product_feature",
    "workflow_stage",
    "reported_symptom",
    "review_sentiment",
    "complaint_category",
    "issue_nature"
]


def get_analytics_reviews():

    classification_columns = []

    for dimension in DIMENSIONS:
        for suffix in [
            "primary",
            "all",
            "scores",
            "confidence"
        ]:
            classification_columns.append(
                f"c.{dimension}_{suffix}"
            )

    select_columns = [
        "r.*",
        *classification_columns
    ]

    query = f"""
        SELECT
            {", ".join(select_columns)}
        FROM reviews r

        INNER JOIN review_classifications c
            ON r.classification_id = c.classification_id

        ORDER BY r.review_date DESC
    """

    with sqlite3.connect(DATABASE_PATH) as connection:
        df = pd.read_sql_query(query, connection)

    return df


def get_analytics_summary():

    query = """
        SELECT
            COUNT(*) AS total_reviews,
            COUNT(DISTINCT r.classification_id) AS unique_reviews,
            MIN(r.review_date) AS earliest_review,
            MAX(r.review_date) AS latest_review,
            COUNT(DISTINCT r.app_version) AS app_versions,
            COUNT(DISTINCT r.platform) AS platforms

        FROM reviews r

        INNER JOIN review_classifications c
            ON r.classification_id = c.classification_id
    """

    with sqlite3.connect(DATABASE_PATH) as connection:
        result = pd.read_sql_query(query, connection)

    return result.iloc[0].to_dict()
