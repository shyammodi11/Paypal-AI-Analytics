
import json
import pandas as pd


# ============================================================
# CLASSIFICATION DIMENSIONS
# ============================================================

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


# ============================================================
# HELPER: PARSE MULTI-LABEL CLASSIFICATIONS
# ============================================================

def parse_labels(value):
    """
    Convert a classification _all value into a clean list.

    Handles JSON strings, Python lists, missing values,
    and malformed JSON safely.
    """

    if isinstance(value, list):
        labels = value

    elif isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        try:
            labels = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []

    else:
        return []

    if not isinstance(labels, list):
        return []

    return list(dict.fromkeys(
        str(label).strip()
        for label in labels
        if label is not None and str(label).strip()
    ))


# ============================================================
# HELPER: GET REVIEW DENOMINATOR
# ============================================================

def get_review_count(df):
    """
    Return the number of unique reviews.

    Uses classification_id where available to avoid
    counting duplicate review records.
    """

    if "classification_id" in df.columns:
        return df["classification_id"].nunique()

    return len(df)


# ============================================================
# 1. PRIMARY CLASSIFICATION DISTRIBUTION
# ============================================================

def get_primary_distribution(
    df,
    dimension,
    include_unknown=True
):
    """
    Calculate the distribution of primary labels
    for a classification dimension.

    Each review contributes to exactly one primary label.
    """

    if dimension not in DIMENSIONS:
        raise ValueError(
            f"Unsupported dimension: {dimension}"
        )

    column = f"{dimension}_primary"

    if column not in df.columns:
        raise ValueError(
            f"Missing classification column: {column}"
        )

    denominator = get_review_count(df)

    if denominator == 0:
        return pd.DataFrame(
            columns=[
                "category",
                "review_count",
                "percentage"
            ]
        )

    working = df[
        ["classification_id", column]
        if "classification_id" in df.columns
        else [column]
    ].copy()

    working[column] = (
        working[column]
        .fillna("Unknown / Insufficient information")
        .astype(str)
        .str.strip()
    )

    working.loc[
        working[column] == "",
        column
    ] = "Unknown / Insufficient information"

    if not include_unknown:
        working = working[
            working[column]
            != "Unknown / Insufficient information"
        ]

    if "classification_id" in working.columns:
        working = working.drop_duplicates(
            subset=["classification_id"]
        )

    result = (
        working[column]
        .value_counts()
        .rename_axis("category")
        .reset_index(name="review_count")
    )

    result["percentage"] = (
        result["review_count"] / denominator * 100
    )

    return result


# ============================================================
# 2. MULTI-LABEL CLASSIFICATION DISTRIBUTION
# ============================================================

def get_multilabel_distribution(
    df,
    dimension,
    include_unknown=True
):
    """
    Calculate classification distribution using _all labels.

    A review may contribute to multiple categories.
    Counts are based on unique reviews per category.

    Percentages use the total number of reviews as
    denominator. Therefore, percentages can sum to
    more than 100%.
    """

    if dimension not in DIMENSIONS:
        raise ValueError(
            f"Unsupported dimension: {dimension}"
        )

    all_column = f"{dimension}_all"
    primary_column = f"{dimension}_primary"

    if all_column not in df.columns:
        raise ValueError(
            f"Missing classification column: {all_column}"
        )

    if primary_column not in df.columns:
        raise ValueError(
            f"Missing classification column: {primary_column}"
        )

    denominator = get_review_count(df)

    if denominator == 0:
        return pd.DataFrame(
            columns=[
                "category",
                "review_count",
                "percentage"
            ]
        )

    id_column = (
        "classification_id"
        if "classification_id" in df.columns
        else None
    )

    columns = [all_column, primary_column]

    if id_column:
        columns.insert(0, id_column)

    working = df[columns].copy()

    if not id_column:
        working["_review_id"] = range(len(working))
        id_column = "_review_id"

    records = []

    for _, row in working.iterrows():

        labels = parse_labels(row[all_column])

        # Fallback to primary classification when
        # the multi-label field is empty or unavailable.
        if not labels:
            primary = row[primary_column]

            if pd.notna(primary) and str(primary).strip():
                labels = [str(primary).strip()]

        labels = list(dict.fromkeys(labels))

        for label in labels:

            if (
                not include_unknown
                and label == "Unknown / Insufficient information"
            ):
                continue

            records.append({
                "classification_id": row[id_column],
                "category": label
            })

    if not records:
        return pd.DataFrame(
            columns=[
                "category",
                "review_count",
                "percentage"
            ]
        )

    label_df = pd.DataFrame(records)

    # A review should count only once per category.
    label_df = label_df.drop_duplicates(
        subset=["classification_id", "category"]
    )

    result = (
        label_df
        .groupby("category")["classification_id"]
        .nunique()
        .reset_index(name="review_count")
        .sort_values("review_count", ascending=False)
    )

    result["percentage"] = (
        result["review_count"] / denominator * 100
    )

    return result.reset_index(drop=True)


# ============================================================
# 3. CROSS-DIMENSIONAL ANALYSIS
# ============================================================

def get_cross_dimension_distribution(
    df,
    dimension_a,
    dimension_b,
    use_multilabel=False
):
    """
    Calculate relationships between two classification
    dimensions.

    Primary mode:
        Each review contributes to one category pair.

    Multi-label mode:
        A review may contribute to multiple category pairs.

    Counts represent unique reviews per category pair.
    """

    for dimension in [dimension_a, dimension_b]:

        if dimension not in DIMENSIONS:
            raise ValueError(
                f"Unsupported dimension: {dimension}"
            )

    suffix = "all" if use_multilabel else "primary"

    column_a = f"{dimension_a}_{suffix}"
    column_b = f"{dimension_b}_{suffix}"

    required_columns = [column_a, column_b]

    if "classification_id" in df.columns:
        required_columns.insert(0, "classification_id")

    for column in [column_a, column_b]:

        if column not in df.columns:
            raise ValueError(
                f"Missing classification column: {column}"
            )

    working = df[required_columns].copy()

    if "classification_id" not in working.columns:
        working["classification_id"] = range(len(working))

    records = []

    for _, row in working.iterrows():

        if use_multilabel:
            labels_a = parse_labels(row[column_a])
            labels_b = parse_labels(row[column_b])

        else:
            labels_a = (
                [str(row[column_a]).strip()]
                if pd.notna(row[column_a])
                and str(row[column_a]).strip()
                else []
            )

            labels_b = (
                [str(row[column_b]).strip()]
                if pd.notna(row[column_b])
                and str(row[column_b]).strip()
                else []
            )

        if not labels_a or not labels_b:
            continue

        for label_a in set(labels_a):
            for label_b in set(labels_b):

                records.append({
                    "classification_id": row["classification_id"],
                    "category_a": label_a,
                    "category_b": label_b
                })

    if not records:
        return pd.DataFrame(
            columns=[
                "category_a",
                "category_b",
                "review_count"
            ]
        )

    result = pd.DataFrame(records)

    result = result.drop_duplicates(
        subset=[
            "classification_id",
            "category_a",
            "category_b"
        ]
    )

    result = (
        result
        .groupby(
            ["category_a", "category_b"]
        )["classification_id"]
        .nunique()
        .reset_index(name="review_count")
        .sort_values("review_count", ascending=False)
    )

    return result.reset_index(drop=True)
