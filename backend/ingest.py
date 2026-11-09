
from backend.config import CLASSIFIED_REVIEWS_FILE
from backend.database.db import (
    initialize_database,
    upsert_reviews,
    get_database_summary
)

import pandas as pd


def main():

    print("=" * 55)
    print("PAYPAL SENTINEL — DATABASE INGESTION")
    print("=" * 55)

    # 1. Verify source file
    if not CLASSIFIED_REVIEWS_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {CLASSIFIED_REVIEWS_FILE}"
        )

    # 2. Load consolidated dataset
    df = pd.read_csv(CLASSIFIED_REVIEWS_FILE)

    print("Loaded dataset:", df.shape)

    # 3. Initialise database
    initialize_database()

    print("Database initialised.")

    # 4. Insert or update reviews
    processed = upsert_reviews(df)

    print("Records processed:", processed)

    # 5. Retrieve database summary
    summary = get_database_summary()

    print("\nDATABASE SUMMARY")
    print("-" * 55)

    print("Total reviews:", summary["total_reviews"])

    print("\nRatings:")
    print(summary["ratings"].to_string(index=False))

    print("\nComplaint categories:")
    print(summary["complaints"].to_string(index=False))

    print("\nIssue nature:")
    print(summary["issue_natures"].to_string(index=False))

    print("\nDATABASE INGESTION COMPLETED.")


if __name__ == "__main__":
    main()
