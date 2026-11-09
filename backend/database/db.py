
import json
import sqlite3
import pandas as pd

from backend.config import DATABASE_PATH


# ============================================================
# 1. DATABASE CONNECTION
# ============================================================

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ============================================================
# 2. DATABASE INITIALISATION
# ============================================================

def initialize_database():

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS reviews (

                classification_id TEXT PRIMARY KEY,

                review_id TEXT,
                review_text TEXT,
                rating INTEGER,
                platform TEXT,
                review_date TEXT,
                app_version TEXT,

                complaint_category TEXT,
                issue_nature TEXT,

                raw_json TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        indexes = [
            """
            CREATE INDEX IF NOT EXISTS idx_rating
            ON reviews(rating)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_platform
            ON reviews(platform)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint
            ON reviews(complaint_category)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_issue_nature
            ON reviews(issue_nature)
            """
        ]

        for statement in indexes:
            connection.execute(statement)

        connection.commit()


# ============================================================
# 3. VALUE EXTRACTION
# ============================================================

def get_value(row, columns):

    for column in columns:

        if column not in row.index:
            continue

        value = row[column]

        if pd.isna(value):
            continue

        return value

    return None


def to_int(value):

    if value is None:
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


# ============================================================
# 4. INSERT OR UPDATE REVIEWS
# ============================================================

def upsert_reviews(df):

    if "classification_id" not in df.columns:
        raise ValueError("classification_id is required.")

    if df["classification_id"].isna().any():
        raise ValueError("Missing classification IDs.")

    if df["classification_id"].duplicated().any():
        raise ValueError("Duplicate classification IDs.")

    records = []

    for _, row in df.iterrows():

        raw_json = json.dumps(
            row.to_dict(),
            ensure_ascii=False,
            default=str
        )

        record = (

            str(row["classification_id"]),

            get_value(row, ["reviewId", "review_id"]),

            get_value(row, ["review_text", "content"]),

            to_int(get_value(row, ["review_rating", "score", "rating"])),

            get_value(row, ["android_or_ios", "platform"]),

            str(get_value(row, ["review_timestamp", "at", "review_date"]))
            if get_value(row, ["review_timestamp", "at", "review_date"]) is not None
            else None,

            get_value(row, ["reviewCreatedVersion", "app_version"]),

            get_value(row, ["complaint_category_primary"]),

            get_value(row, ["issue_nature_primary"]),

            raw_json
        )

        records.append(record)

    query = """
        INSERT INTO reviews (
            classification_id,
            review_id,
            review_text,
            rating,
            platform,
            review_date,
            app_version,
            complaint_category,
            issue_nature,
            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(classification_id)
        DO UPDATE SET

            review_id = excluded.review_id,
            review_text = excluded.review_text,
            rating = excluded.rating,
            platform = excluded.platform,
            review_date = excluded.review_date,
            app_version = excluded.app_version,
            complaint_category = excluded.complaint_category,
            issue_nature = excluded.issue_nature,
            raw_json = excluded.raw_json,
            updated_at = CURRENT_TIMESTAMP
    """

    with get_connection() as connection:
        connection.executemany(query, records)
        connection.commit()

    return len(records)


# ============================================================
# 5. RETRIEVE REVIEWS
# ============================================================

def get_all_reviews(limit=None):

    query = """
        SELECT *
        FROM reviews
        ORDER BY review_date DESC
    """

    params = ()

    if limit is not None:
        query += " LIMIT ?"
        params = (limit,)

    with get_connection() as connection:

        return pd.read_sql_query(
            query,
            connection,
            params=params
        )


# ============================================================
# 6. RETRIEVE ONE REVIEW
# ============================================================

def get_review_by_id(classification_id):

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
    review["raw_json"] = json.loads(review["raw_json"])

    return review


# ============================================================
# 7. SEARCH REVIEWS
# ============================================================

def search_reviews(
    keyword=None,
    complaint_category=None,
    issue_nature=None,
    platform=None,
    limit=100
):

    query = "SELECT * FROM reviews WHERE 1=1"
    params = []

    if keyword:
        query += " AND review_text LIKE ?"
        params.append(f"%{keyword}%")

    if complaint_category:
        query += " AND complaint_category = ?"
        params.append(complaint_category)

    if issue_nature:
        query += " AND issue_nature = ?"
        params.append(issue_nature)

    if platform:
        query += " AND platform = ?"
        params.append(platform)

    query += " ORDER BY review_date DESC LIMIT ?"
    params.append(limit)

    with get_connection() as connection:

        return pd.read_sql_query(
            query,
            connection,
            params=params
        )


# ============================================================
# 8. DATABASE SUMMARY
# ============================================================

def get_database_summary():

    with get_connection() as connection:

        total_reviews = connection.execute(
            "SELECT COUNT(*) FROM reviews"
        ).fetchone()[0]

        ratings = pd.read_sql_query(
            """
            SELECT rating, COUNT(*) AS review_count
            FROM reviews
            GROUP BY rating
            ORDER BY rating
            """,
            connection
        )

        complaints = pd.read_sql_query(
            """
            SELECT complaint_category,
                   COUNT(*) AS review_count
            FROM reviews
            GROUP BY complaint_category
            ORDER BY review_count DESC
            """,
            connection
        )

        issue_natures = pd.read_sql_query(
            """
            SELECT issue_nature,
                   COUNT(*) AS review_count
            FROM reviews
            GROUP BY issue_nature
            ORDER BY review_count DESC
            """,
            connection
        )

    return {
        "total_reviews": total_reviews,
        "ratings": ratings,
        "complaints": complaints,
        "issue_natures": issue_natures
    }
