
import pandas as pd

from backend.analytics.classification_analytics import (
    DIMENSIONS,
    parse_labels
)


# ============================================================
# DATE PREPARATION
# ============================================================

FREQUENCIES = {
    "daily": "D",
    "weekly": "W",
    "monthly": "MS"
}


def prepare_temporal_data(df):
    """
    Return a copy with valid UTC review dates and
    a timezone-naive timestamp for period grouping.
    """

    if "review_date" not in df.columns:
        raise ValueError("Missing review_date column.")

    working = df.copy()

    working["review_date"] = pd.to_datetime(
        working["review_date"],
        utc=True,
        errors="coerce"
    )

    working = working.dropna(
        subset=["review_date"]
    )

    # Convert to UTC, then remove timezone for period grouping.
    working["period_timestamp"] = (
        working["review_date"]
        .dt.tz_convert("UTC")
        .dt.tz_localize(None)
    )

    if "classification_id" not in working.columns:
        working["classification_id"] = range(len(working))

    return working


def get_period_start(series, frequency):
    """
    Convert timestamps into daily, weekly or monthly
    period-start timestamps.
    """

    if frequency not in FREQUENCIES:
        raise ValueError(
            "frequency must be daily, weekly or monthly."
        )

    if frequency == "daily":
        return series.dt.floor("D")

    if frequency == "weekly":
        return (
            series.dt.to_period("W")
            .dt.start_time
        )

    return (
        series.dt.to_period("M")
        .dt.start_time
    )


# ============================================================
# 1. REVIEW VOLUME OVER TIME
# ============================================================

def get_review_volume_trend(
    df,
    frequency="monthly"
):
    """
    Count unique reviews per daily, weekly or monthly period.
    """

    working = prepare_temporal_data(df)

    if working.empty:
        return pd.DataFrame(
            columns=["period", "review_count"]
        )

    working["period"] = get_period_start(
        working["period_timestamp"],
        frequency
    )

    result = (
        working
        .groupby("period")["classification_id"]
        .nunique()
        .reset_index(name="review_count")
        .sort_values("period")
    )

    return result.reset_index(drop=True)


# ============================================================
# 2. CLASSIFICATION TRENDS OVER TIME
# ============================================================

def get_dimension_trend(
    df,
    dimension,
    frequency="monthly",
    label_mode="primary",
    top_n=10
):
    """
    Track classification categories over time.

    label_mode:
        primary - one primary category per review
        all     - all available labels per review

    Counts represent unique reviews per period/category.
    """

    if dimension not in DIMENSIONS:
        raise ValueError(
            f"Unsupported dimension: {dimension}"
        )

    if label_mode not in ["primary", "all"]:
        raise ValueError(
            "label_mode must be 'primary' or 'all'."
        )

    working = prepare_temporal_data(df)

    if working.empty:
        return pd.DataFrame(
            columns=[
                "period",
                "category",
                "review_count"
            ]
        )

    column = f"{dimension}_{label_mode}"

    if column not in working.columns:
        raise ValueError(
            f"Missing classification column: {column}"
        )

    working["period"] = get_period_start(
        working["period_timestamp"],
        frequency
    )

    records = []

    for _, row in working.iterrows():

        value = row[column]

        if label_mode == "all":
            labels = parse_labels(value)

            if not labels and dimension + "_primary" in working.columns:
                primary = row[dimension + "_primary"]

                if pd.notna(primary) and str(primary).strip():
                    labels = [str(primary).strip()]

        else:
            labels = (
                [str(value).strip()]
                if pd.notna(value) and str(value).strip()
                else []
            )

        for label in set(labels):

            records.append({
                "classification_id": row["classification_id"],
                "period": row["period"],
                "category": label
            })

    if not records:
        return pd.DataFrame(
            columns=[
                "period",
                "category",
                "review_count"
            ]
        )

    label_df = pd.DataFrame(records).drop_duplicates(
        subset=[
            "classification_id",
            "period",
            "category"
        ]
    )

    # Select the most common categories across the
    # complete selected dataset.
    top_categories = (
        label_df.groupby("category")["classification_id"]
        .nunique()
        .nlargest(top_n)
        .index
    )

    label_df = label_df[
        label_df["category"].isin(top_categories)
    ]

    result = (
        label_df
        .groupby(["period", "category"])["classification_id"]
        .nunique()
        .reset_index(name="review_count")
        .sort_values(["period", "review_count"], ascending=[True, False])
    )

    return result.reset_index(drop=True)


# ============================================================
# 3. APP VERSION TRENDS OVER TIME
# ============================================================

def get_app_version_trend(
    df,
    frequency="monthly",
    top_n=10,
    include_missing=False
):
    """
    Track review volume by app version over time.

    This describes review volume, not defect rates or
    evidence that a version caused a reported issue.
    """

    if "app_version" not in df.columns:
        raise ValueError("Missing app_version column.")

    working = prepare_temporal_data(df)

    if working.empty:
        return pd.DataFrame(
            columns=[
                "period",
                "app_version",
                "review_count"
            ]
        )

    working["app_version"] = (
        working["app_version"]
        .fillna("Unknown / Missing")
        .astype(str)
        .str.strip()
    )

    working.loc[
        working["app_version"] == "",
        "app_version"
    ] = "Unknown / Missing"

    if not include_missing:
        working = working[
            working["app_version"] != "Unknown / Missing"
        ]

    if working.empty:
        return pd.DataFrame(
            columns=[
                "period",
                "app_version",
                "review_count"
            ]
        )

    working["period"] = get_period_start(
        working["period_timestamp"],
        frequency
    )

    top_versions = (
        working.groupby("app_version")["classification_id"]
        .nunique()
        .nlargest(top_n)
        .index
    )

    working = working[
        working["app_version"].isin(top_versions)
    ]

    result = (
        working
        .groupby(["period", "app_version"])["classification_id"]
        .nunique()
        .reset_index(name="review_count")
        .sort_values(["period", "review_count"], ascending=[True, False])
    )

    return result.reset_index(drop=True)
