
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.config import DATABASE_PATH, PROJECT_DIR


# ============================================================
# 1. CONFIGURATION
# ============================================================

CSV_PATH = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "classified_reviews_full.csv"
)

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

CLASSIFICATION_COLUMNS = [
    f"{dimension}_{suffix}"
    for dimension in DIMENSIONS
    for suffix in ["primary", "all", "scores", "confidence"]
]

CSV_COLUMNS = [
    "classification_id",
    "complaint_category_primary",
    "issue_nature_primary"
] + [
    column for column in CLASSIFICATION_COLUMNS
    if column not in [
        "complaint_category_primary",
        "issue_nature_primary"
    ]
]


# ============================================================
# 2. VALUE NORMALISATION
# ============================================================

def is_missing(value):
    return value is None or pd.isna(value)


def clean_text(value):

    if is_missing(value):
        return None

    return str(value)


def clean_json_text(value):

    if is_missing(value):
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value, ensure_ascii=False, default=str)


def clean_confidence(value):

    if is_missing(value):
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# 3. VERIFY SOURCE AND DATABASE
# ============================================================

def validate_migration_source():

    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    df = pd.read_csv(
        CSV_PATH,
        usecols=CSV_COLUMNS,
        low_memory=False
    )

    if df["classification_id"].isna().any():
        raise ValueError("Missing classification IDs in CSV.")

    if df["classification_id"].duplicated().any():
        raise ValueError("Duplicate classification IDs in CSV.")

    df["classification_id"] = (
        df["classification_id"].astype(str)
    )

    with sqlite3.connect(DATABASE_PATH) as connection:

        db_df = pd.read_sql_query("""
            SELECT
                classification_id,
                complaint_category,
                issue_nature
            FROM reviews
        """, connection)

    db_df["classification_id"] = (
        db_df["classification_id"].astype(str)
    )

    if db_df["classification_id"].duplicated().any():
        raise ValueError("Duplicate IDs in SQLite reviews table.")

    if set(df["classification_id"]) != set(db_df["classification_id"]):
        raise ValueError("CSV and database IDs do not match.")

    comparison = df.merge(
        db_df,
        on="classification_id",
        how="inner",
        validate="one_to_one"
    )

    complaint_match = (
        comparison["complaint_category_primary"].fillna("").astype(str)
        ==
        comparison["complaint_category"].fillna("").astype(str)
    )

    issue_match = (
        comparison["issue_nature_primary"].fillna("").astype(str)
        ==
        comparison["issue_nature"].fillna("").astype(str)
    )

    if not complaint_match.all():
        raise ValueError("Complaint category mismatch detected.")

    if not issue_match.all():
        raise ValueError("Issue nature mismatch detected.")

    for dimension in DIMENSIONS:
        column = f"{dimension}_primary"

        if df[column].isna().any():
            raise ValueError(
                f"Missing primary classifications: {column}"
            )

    print("Source validation passed.")
    print("Records ready:", len(df))

    return df


# ============================================================
# 4. CREATE CLASSIFICATION TABLE
# ============================================================

def create_classification_table(connection):

    column_definitions = []

    for dimension in DIMENSIONS:

        column_definitions.extend([
            f"{dimension}_primary TEXT",
            f"{dimension}_all TEXT",
            f"{dimension}_scores TEXT",
            f"{dimension}_confidence REAL"
        ])

    schema = f"""
        CREATE TABLE IF NOT EXISTS review_classifications (

            classification_id TEXT PRIMARY KEY,

            {", ".join(column_definitions)},

            classification_schema_version TEXT,
            source_file TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (classification_id)
                REFERENCES reviews(classification_id)
        )
    """

    connection.execute(schema)


# ============================================================
# 5. PREPARE CLASSIFICATION RECORDS
# ============================================================

def prepare_records(df):

    records = []

    for _, row in df.iterrows():

        record = [str(row["classification_id"])]

        for dimension in DIMENSIONS:

            record.extend([
                clean_text(row[f"{dimension}_primary"]),
                clean_json_text(row[f"{dimension}_all"]),
                clean_json_text(row[f"{dimension}_scores"]),
                clean_confidence(row[f"{dimension}_confidence"])
            ])

        record.extend([
            "expanded-12-dimension-v1",
            CSV_PATH.name
        ])

        records.append(tuple(record))

    return records


# ============================================================
# 6. MIGRATE CLASSIFICATIONS
# ============================================================

def migrate():

    print("=" * 65)
    print("PAYPAL SENTINEL — EXPANDED CLASSIFICATION MIGRATION")
    print("=" * 65)

    # Validate before making any database changes
    df = validate_migration_source()

    # Create a timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = DATABASE_PATH.with_name(
        f"{DATABASE_PATH.stem}_backup_{timestamp}.db"
    )

    shutil.copy2(DATABASE_PATH, backup_path)

    print("\nDatabase backup created:")
    print(backup_path)

    columns = (
        ["classification_id"]
        + CLASSIFICATION_COLUMNS
        + ["classification_schema_version", "source_file"]
    )

    placeholders = ", ".join(["?"] * len(columns))
    column_names = ", ".join(columns)

    update_columns = [
        column for column in columns
        if column != "classification_id"
    ]

    update_clause = ", ".join(
        f"{column} = excluded.{column}"
        for column in update_columns
    )

    query = f"""
        INSERT INTO review_classifications (
            {column_names}
        )
        VALUES ({placeholders})

        ON CONFLICT(classification_id)
        DO UPDATE SET
            {update_clause},
            updated_at = CURRENT_TIMESTAMP
    """

    records = prepare_records(df)

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")

        create_classification_table(connection)

        connection.executemany(query, records)

        migrated_count = connection.execute("""
            SELECT COUNT(*)
            FROM review_classifications
        """).fetchone()[0]

        if migrated_count != len(df):

            raise RuntimeError(
                f"Migration count mismatch: "
                f"{migrated_count} != {len(df)}"
            )

        missing_ids = connection.execute("""
            SELECT COUNT(*)
            FROM reviews r
            LEFT JOIN review_classifications c
                ON r.classification_id = c.classification_id
            WHERE c.classification_id IS NULL
        """).fetchone()[0]

        if missing_ids != 0:
            raise RuntimeError(
                f"{missing_ids} reviews have no classifications."
            )

        connection.commit()

        print("\nMIGRATION SUCCESSFUL")
        print("=" * 65)
        print("Reviews in original table:", len(df))
        print("Classification records:", migrated_count)
        print("Missing classification records:", missing_ids)
        print("Dimensions migrated:", len(DIMENSIONS))
        print("Fields per dimension: 4")
        print("Total classification fields:", len(CLASSIFICATION_COLUMNS))

    except Exception:

        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# 7. EXECUTION
# ============================================================

if __name__ == "__main__":
    migrate()
