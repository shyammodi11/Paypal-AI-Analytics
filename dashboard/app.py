
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# 1. PROJECT IMPORTS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.db import get_all_reviews
from backend.tools.fraud_detection import find_fraud_candidates
from backend.tools.engineering_analytics import find_engineering_candidates
from backend.agents.supervisor_agent import (
    route_question,
    build_agent_questions,
    execute_selected_agents,
    consolidate_responses
)

from backend.database.analytics import get_analytics_reviews
from dashboard.analytics.advanced_analytics import render_advanced_analytics


# ============================================================
# 2. PAGE CONFIGURATION AND STYLING
# ============================================================

st.set_page_config(
    page_title="PayPal Sentinel | Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1600px;
    }

    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.07);
        border: 1px solid rgba(128, 128, 128, 0.16);
        padding: 15px;
        border-radius: 10px;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
    }

    .agent-description {
        color: #808080;
        font-size: 0.92rem;
        margin-top: -8px;
    }

    .small-note {
        color: #808080;
        font-size: 0.8rem;
    }

    .section-gap {
        padding-top: 0.7rem;
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. CONSTANTS
# ============================================================

UNKNOWN = "Unknown / Insufficient information"

AGENT_LABELS = {
    "complaint": "Complaint Intelligence",
    "fraud": "Fraud Intelligence",
    "engineering": "Engineering Intelligence"
}

FRAUD_LABELS = {
    "unauthorized_transaction": "Unauthorized Transaction",
    "account_compromise": "Account Compromise",
    "phishing_and_impersonation": "Phishing & Impersonation",
    "identity_or_payment_compromise": "Identity / Payment Compromise",
    "suspicious_activity": "Suspicious Activity"
}

ENGINEERING_LABELS = {
    "app_crash": "App Crash",
    "freezing_and_unresponsiveness": "Freezing & Unresponsiveness",
    "performance": "Performance",
    "login_and_authentication": "Login & Authentication",
    "payment_and_transfer_failure": "Payment & Transfer Failure",
    "notification_issues": "Notification Issues",
    "app_update_and_compatibility": "App Update & Compatibility",
    "ui_and_navigation": "UI & Navigation"
}


# ============================================================
# 4. DATA LOADING AND CACHING
# ============================================================

@st.cache_data(ttl=300)
def load_reviews():

    df = get_all_reviews()

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    df["review_date"] = pd.to_datetime(
        df["review_date"],
        utc=True,
        errors="coerce"
    )

    df["rating"] = pd.to_numeric(
        df["rating"],
        errors="coerce"
    )

    for column in [
        "platform",
        "app_version",
        "complaint_category",
        "issue_nature",
        "review_text",
        "classification_id",
        "review_id"
    ]:

        if column in df.columns:
            df[column] = df[column].fillna("Unknown / Missing")

    return df

@st.cache_data(ttl=300)
def load_expanded_analytics():

    df = get_analytics_reviews()

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    df["review_date"] = pd.to_datetime(
        df["review_date"],
        utc=True,
        errors="coerce"
    )

    df["rating"] = pd.to_numeric(
        df["rating"],
        errors="coerce"
    )

    return df

@st.cache_data(ttl=300)
def load_all_fraud_candidates():

    all_reviews = []
    offset = 0
    batch_size = 200
    total = None

    while True:

        result = find_fraud_candidates(
            limit=batch_size,
            offset=offset
        )

        if total is None:
            total = result["total_candidates"]

        batch = result.get("reviews", [])

        if not batch:
            break

        all_reviews.extend(batch)
        offset += len(batch)

        if offset >= total:
            break

    return {
        "total_candidates": total or 0,
        "reviews": all_reviews
    }


@st.cache_data(ttl=300)
def load_all_engineering_candidates():

    all_reviews = []
    offset = 0
    batch_size = 200
    total = None

    while True:

        result = find_engineering_candidates(
            limit=batch_size,
            offset=offset
        )

        if total is None:
            total = result["total_candidates"]

        batch = result.get("reviews", [])

        if not batch:
            break

        all_reviews.extend(batch)
        offset += len(batch)

        if offset >= total:
            break

    return {
        "total_candidates": total or 0,
        "reviews": all_reviews
    }


# ============================================================
# 5. REUSABLE ANALYTICS FUNCTIONS
# ============================================================

def distribution_table(series, label_name):

    result = (
        series.fillna("Unknown / Missing")
        .value_counts()
        .rename_axis(label_name)
        .reset_index(name="Review Count")
    )

    result["Percentage"] = (
        result["Review Count"] / max(result["Review Count"].sum(), 1) * 100
    ).round(2)

    return result


def bar_chart(data, x, y, title, horizontal=False):

    if horizontal:

        fig = px.bar(
            data.sort_values(y),
            x=y,
            y=x,
            orientation="h",
            text=y,
            title=title
        )

        fig.update_layout(
            height=max(350, len(data) * 35),
            yaxis_title=None,
            xaxis_title="Reviews"
        )

    else:

        fig = px.bar(
            data,
            x=x,
            y=y,
            text=y,
            title=title
        )

        fig.update_layout(height=400)

    fig.update_traces(textposition="outside")

    fig.update_layout(
        margin=dict(l=10, r=20, t=55, b=20),
        title_x=0.02
    )

    return fig


def metric_row(items):

    columns = st.columns(len(items))

    for column, (label, value, help_text) in zip(columns, items):

        column.metric(
            label,
            value,
            help=help_text
        )


def prepare_candidate_dataframe(records, analysis_key):

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    if df.empty:
        return df

    df["review_date"] = pd.to_datetime(
        df["review_date"],
        utc=True,
        errors="coerce"
    )

    for column in [
        "platform",
        "app_version",
        "complaint_category",
        "issue_nature",
        "review_text"
    ]:
        if column in df.columns:
            df[column] = df[column].fillna("Unknown / Missing")

    df["rating"] = pd.to_numeric(
        df["rating"],
        errors="coerce"
    )

    df["analysis"] = df[analysis_key]

    df["triage_level"] = df["analysis"].apply(
        lambda x: x.get("triage_level", "Unknown")
        if isinstance(x, dict) else "Unknown"
    )

    df["signal_types"] = df["analysis"].apply(
        lambda x: x.get("signal_types", [])
        if isinstance(x, dict) else []
    )

    df["matched_signals"] = df["analysis"].apply(
        lambda x: x.get("matched_signals", [])
        if isinstance(x, dict) else []
    )

    df["explicit_text_match"] = df["matched_signals"].apply(
        lambda x: len(x) > 0
    )

    return df


def apply_candidate_filters(
    candidates,
    start_date,
    end_date,
    platforms,
    ratings,
    versions
):

    if candidates.empty:
        return candidates

    result = candidates.copy()

    result = result[
        result["review_date"].dt.date.between(start_date, end_date)
    ]

    result = result[result["platform"].isin(platforms)]
    result = result[result["rating"].isin(ratings)]
    result = result[result["app_version"].isin(versions)]

    return result


def display_evidence_table(df, columns, height=400):

    if df.empty:
        st.info("No matching evidence found.")
        return

    available = [c for c in columns if c in df.columns]

    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        height=height
    )


def display_review_detail(row, analysis_key=None):

    st.markdown("**Original customer review**")
    st.write(row.get("review_text", "Review text unavailable."))

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Rating", str(row.get("rating", "N/A")))
    c2.metric("Platform", str(row.get("platform", "N/A")))
    c3.metric("App Version", str(row.get("app_version", "N/A")))
    c4.metric("Triage", str(row.get("triage_level", "N/A")))

    if "complaint_category" in row:
        st.write(
            "**Complaint category:**",
            row.get("complaint_category")
        )

    if "issue_nature" in row:
        st.write(
            "**Issue nature:**",
            row.get("issue_nature")
        )

    st.caption(
        f"Classification ID: {row.get('classification_id', 'N/A')}"
    )

    if analysis_key:

        analysis = row.get(analysis_key, {})

        st.markdown("**Detected signal types**")

        signals = analysis.get("signal_types", [])

        if signals:
            st.write(
                ", ".join(
                    FRAUD_LABELS.get(s, s.replace("_", " ").title())
                    if analysis_key == "fraud_analysis"
                    else ENGINEERING_LABELS.get(
                        s, s.replace("_", " ").title()
                    )
                    for s in signals
                )
            )
        else:
            st.write("No explicit signal type available.")

        st.markdown("**Matched detection rules**")

        matched = analysis.get("matched_signals", [])

        if matched:

            for item in matched:

                st.code(
                    "\n".join(item.get("matched_patterns", [])),
                    language="text"
                )

        else:

            st.info(
                "No explicit text pattern was matched. "
                "This candidate was identified through classification "
                "or category-based evidence."
            )


# ============================================================
# 6. LOAD DATA
# ============================================================

with st.spinner("Loading PayPal Sentinel intelligence data..."):

    reviews = load_reviews()

    if reviews.empty:
        st.error("No reviews available in the database.")
        st.stop()

    fraud_data = load_all_fraud_candidates()
    engineering_data = load_all_engineering_candidates()

fraud_df = prepare_candidate_dataframe(
    fraud_data["reviews"],
    "fraud_analysis"
)

engineering_df = prepare_candidate_dataframe(
    engineering_data["reviews"],
    "engineering_analysis"
)


# ============================================================
# 7. HEADER
# ============================================================

st.title("🛡️ PayPal Sentinel")

st.markdown(
    "Customer Complaint · Fraud Intelligence · Engineering Analytics"
)

valid_dates = reviews["review_date"].dropna()

earliest_date = valid_dates.min().date()
latest_date = valid_dates.max().date()

st.caption(
    f"Analysed dataset: {earliest_date} to {latest_date} | "
    f"Last available review: {latest_date} | "
    f"{len(reviews):,} records"
)


# ============================================================
# 8. SHARED FILTERS
# ============================================================

with st.sidebar:

    st.title("Investigation Filters")

    st.caption("Shared filters apply to all four intelligence tabs.")

    date_range = st.date_input(
        "Review date range",
        value=(earliest_date, latest_date),
        min_value=earliest_date,
        max_value=latest_date,
        key="global_dates"
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = earliest_date, latest_date

    platform_options = sorted(reviews["platform"].unique().tolist())

    selected_platforms = st.multiselect(
        "Platform",
        platform_options,
        default=platform_options,
        key="global_platforms"
    )

    rating_options = sorted(
        reviews["rating"].dropna().astype(int).unique().tolist()
    )

    selected_ratings = st.multiselect(
        "Rating",
        rating_options,
        default=rating_options,
        key="global_ratings"
    )

    version_options = sorted(
        reviews["app_version"].unique().tolist()
    )

    selected_versions = st.multiselect(
        "App version",
        version_options,
        default=version_options,
        key="global_versions"
    )

    st.divider()

    st.caption(
        "Candidate scans are cached for five minutes. "
        "Use the refresh button to reload data."
    )

    if st.button("↻ Refresh data", use_container_width=True):

        st.cache_data.clear()
        st.rerun()


# ============================================================
# 9. APPLY SHARED FILTERS
# ============================================================

filtered_reviews = reviews.copy()

filtered_reviews = filtered_reviews[
    filtered_reviews["review_date"].dt.date.between(
        start_date, end_date
    )
]

filtered_reviews = filtered_reviews[
    filtered_reviews["platform"].isin(selected_platforms)
    & filtered_reviews["rating"].isin(selected_ratings)
    & filtered_reviews["app_version"].isin(selected_versions)
]


# ============================================================
# 10. ADVANCED ANALYTICS DATA
# ============================================================

analytics_reviews = load_expanded_analytics()

filtered_analytics = analytics_reviews.copy()

if not filtered_analytics.empty:
    filtered_analytics = filtered_analytics[
        filtered_analytics["review_date"].dt.date.between(
            start_date, end_date
        )
    ]

    filtered_analytics = filtered_analytics[
        filtered_analytics["platform"].isin(selected_platforms)
        & filtered_analytics["rating"].isin(selected_ratings)
        & filtered_analytics["app_version"].isin(selected_versions)
    ]


# ============================================================
# 11. FILTER FRAUD AND ENGINEERING CANDIDATES
# ============================================================

filtered_fraud = apply_candidate_filters(
    fraud_df,
    start_date,
    end_date,
    selected_platforms,
    selected_ratings,
    selected_versions
)

filtered_engineering = apply_candidate_filters(
    engineering_df,
    start_date,
    end_date,
    selected_platforms,
    selected_ratings,
    selected_versions
)


# ============================================================
# 12. MAIN NAVIGATION
# ============================================================

complaint_tab, fraud_tab, engineering_tab, analytics_tab = st.tabs([
    "💬 Complaint Intelligence",
    "🛡️ Fraud Intelligence",
    "⚙️ Engineering Intelligence",
    "📊 Advanced Analytics"
])


# ============================================================
# 11. COMPLAINT INTELLIGENCE TAB
# ============================================================

with complaint_tab:

    st.header("Complaint Intelligence Agent")

    st.markdown(
        '<p class="agent-description">'
        'Analyses customer complaints, issue categories and '
        'business-impact patterns across customer reviews.'
        '</p>',
        unsafe_allow_html=True
    )

    total = len(filtered_reviews)

    known_category = filtered_reviews[
        filtered_reviews["complaint_category"] != UNKNOWN
    ]

    unknown_category = filtered_reviews[
        filtered_reviews["complaint_category"] == UNKNOWN
    ]

    known_issue = filtered_reviews[
        filtered_reviews["issue_nature"] != UNKNOWN
    ]

    metric_row([
        ("Reviews in scope", f"{total:,}", "After shared filters"),
        ("Classified complaints", f"{len(known_category):,}", None),
        ("Unclassified complaints", f"{len(unknown_category):,}", None),
        (
            "Issue nature identified",
            f"{len(known_issue):,}",
            "Non-unknown issue classifications"
        )
    ])

    if filtered_reviews.empty:

        st.warning("No reviews match the selected filters.")

    else:

        st.divider()

        # Complaint categories and issue nature

        st.subheader("Complaint & Issue Distribution")

        col1, col2 = st.columns(2)

        with col1:

            complaint_dist = distribution_table(
                filtered_reviews["complaint_category"],
                "Complaint Category"
            )

            st.plotly_chart(
                bar_chart(
                    complaint_dist,
                    "Complaint Category",
                    "Review Count",
                    "Complaint Category Distribution",
                    horizontal=True
                ),
                use_container_width=True
            )

            st.dataframe(
                complaint_dist,
                use_container_width=True,
                hide_index=True
            )

        with col2:

            issue_dist = distribution_table(
                filtered_reviews["issue_nature"],
                "Issue Nature"
            )

            st.plotly_chart(
                bar_chart(
                    issue_dist,
                    "Issue Nature",
                    "Review Count",
                    "Issue Nature Distribution",
                    horizontal=True
                ),
                use_container_width=True
            )

            st.dataframe(
                issue_dist,
                use_container_width=True,
                hide_index=True
            )

        # Category and issue cross-analysis

        st.divider()

        st.subheader("Complaint Category × Issue Nature")

        cross = pd.crosstab(
            filtered_reviews["complaint_category"],
            filtered_reviews["issue_nature"]
        )

        heatmap = px.imshow(
            cross,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues",
            title="Review Count Across Complaint and Issue Dimensions"
        )

        heatmap.update_layout(
            height=550,
            xaxis_title="Issue Nature",
            yaxis_title="Complaint Category"
        )

        st.plotly_chart(
            heatmap,
            use_container_width=True
        )

        st.caption(
            "Counts represent reviews classified across two different "
            "dimensions. Do not add percentages from different dimensions "
            "together."
        )

        # Rating and platform breakdown

        st.divider()

        st.subheader("Customer Experience Analysis")

        col1, col2 = st.columns(2)

        with col1:

            rating_category = pd.crosstab(
                filtered_reviews["complaint_category"],
                filtered_reviews["rating"]
            )

            rating_category = rating_category.reset_index().melt(
                id_vars="complaint_category",
                var_name="Rating",
                value_name="Review Count"
            )

            fig = px.bar(
                rating_category,
                x="complaint_category",
                y="Review Count",
                color="Rating",
                barmode="stack",
                title="Rating Composition by Complaint Category"
            )

            fig.update_layout(
                height=450,
                xaxis_title=None
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:

            platform_category = pd.crosstab(
                filtered_reviews["complaint_category"],
                filtered_reviews["platform"]
            )

            platform_category = platform_category.reset_index().melt(
                id_vars="complaint_category",
                var_name="Platform",
                value_name="Review Count"
            )

            fig = px.bar(
                platform_category,
                x="complaint_category",
                y="Review Count",
                color="Platform",
                barmode="group",
                title="Platform Comparison by Complaint Category"
            )

            fig.update_layout(
                height=450,
                xaxis_title=None
            )

            st.plotly_chart(fig, use_container_width=True)

        # Review trends

        st.divider()

        st.subheader("Review Activity Over Time")

        trend_df = filtered_reviews.dropna(
            subset=["review_date"]
        ).copy()

        trend_df["Review Month"] = (
            trend_df["review_date"].dt.to_period("M").astype(str)
        )

        monthly = (
            trend_df.groupby(
                ["Review Month", "complaint_category"]
            )
            .size()
            .reset_index(name="Review Count")
        )

        trend_fig = px.line(
            monthly,
            x="Review Month",
            y="Review Count",
            color="complaint_category",
            markers=True,
            title="Monthly Complaint Activity"
        )

        trend_fig.update_layout(height=450)

        st.plotly_chart(
            trend_fig,
            use_container_width=True
        )

        # App versions

        st.divider()

        st.subheader("App Version Analysis")

        version_dist = distribution_table(
            filtered_reviews["app_version"],
            "App Version"
        )

        version_dist = version_dist.head(20)

        st.plotly_chart(
            bar_chart(
                version_dist,
                "App Version",
                "Review Count",
                "Top 20 App Versions by Review Volume",
                horizontal=True
            ),
            use_container_width=True
        )

        # Complaint evidence explorer

        st.divider()

        st.subheader("Complaint Evidence Explorer")

        complaint_filter = st.selectbox(
            "Select complaint category",
            ["All"] + sorted(
                filtered_reviews["complaint_category"].unique().tolist()
            ),
            key="complaint_evidence_filter"
        )

        issue_filter = st.selectbox(
            "Select issue nature",
            ["All"] + sorted(
                filtered_reviews["issue_nature"].unique().tolist()
            ),
            key="complaint_issue_filter"
        )

        complaint_evidence = filtered_reviews.copy()

        if complaint_filter != "All":
            complaint_evidence = complaint_evidence[
                complaint_evidence["complaint_category"] == complaint_filter
            ]

        if issue_filter != "All":
            complaint_evidence = complaint_evidence[
                complaint_evidence["issue_nature"] == issue_filter
            ]

        complaint_keyword = st.text_input(
            "Search complaint review text",
            key="complaint_keyword",
            placeholder="Search refunds, payments, customer support..."
        )

        if complaint_keyword.strip():

            complaint_evidence = complaint_evidence[
                complaint_evidence["review_text"].str.contains(
                    complaint_keyword,
                    case=False,
                    regex=False,
                    na=False
                )
            ]

        st.caption(
            f"{len(complaint_evidence):,} matching reviews"
        )

        display_evidence_table(
            complaint_evidence.sort_values(
                "review_date",
                ascending=False
            ),
            [
                "classification_id",
                "rating",
                "platform",
                "review_date",
                "app_version",
                "complaint_category",
                "issue_nature",
                "review_text"
            ]
        )

        if not complaint_evidence.empty:

            selected_id = st.selectbox(
                "Inspect individual complaint",
                complaint_evidence["classification_id"].astype(str).tolist(),
                key="complaint_selected_id"
            )

            selected_row = complaint_evidence[
                complaint_evidence["classification_id"].astype(str)
                == selected_id
            ].iloc[0]

            with st.expander("Full customer review", expanded=True):
                display_review_detail(selected_row)


# ============================================================
# 12. FRAUD INTELLIGENCE TAB
# ============================================================

with fraud_tab:

    st.header("Fraud Intelligence Agent")

    st.markdown(
        '<p class="agent-description">'
        'Identifies customer-reported potential fraud, security '
        'and suspicious activity signals using rule-based detection '
        'and complaint classification.'
        '</p>',
        unsafe_allow_html=True
    )

    fraud_triage = filtered_fraud["triage_level"].value_counts()

    fraud_high = int(fraud_triage.get("High", 0))
    fraud_medium = int(fraud_triage.get("Medium", 0))
    fraud_review = int(fraud_triage.get("Review Required", 0))

    fraud_explicit = int(filtered_fraud["explicit_text_match"].sum())
    fraud_category_only = len(filtered_fraud) - fraud_explicit

    metric_row([
        ("Fraud candidates", f"{len(filtered_fraud):,}", None),
        ("High priority", f"{fraud_high:,}", "Rule-based triage"),
        ("Medium priority", f"{fraud_medium:,}", "Rule-based triage"),
        ("Review required", f"{fraud_review:,}", "Category-only or insufficient text evidence")
    ])

    st.divider()

    # Explicit vs category-only

    st.subheader("Detection Evidence Composition")

    col1, col2 = st.columns(2)

    with col1:

        fig = px.pie(
            names=["Explicit text match", "Category-only match"],
            values=[fraud_explicit, fraud_category_only],
            hole=0.48,
            title="Evidence Type Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:

        fig = px.pie(
            names=["High", "Medium", "Review Required"],
            values=[fraud_high, fraud_medium, fraud_review],
            hole=0.48,
            title="Fraud Triage Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "These are potential customer-reported signals, not verified fraud "
        "events. Triage levels represent heuristic prioritisation."
    )

    # Signal taxonomy

    st.divider()

    st.subheader("Fraud Signal Taxonomy")

    fraud_signal_rows = []

    for _, row in filtered_fraud.iterrows():

        for signal in row["signal_types"]:

            fraud_signal_rows.append({
                "Signal": FRAUD_LABELS.get(
                    signal,
                    signal.replace("_", " ").title()
                ),
                "Classification ID": row["classification_id"],
                "Triage": row["triage_level"],
                "Platform": row["platform"],
                "Rating": row["rating"]
            })

    fraud_signal_df = pd.DataFrame(fraud_signal_rows)

    if not fraud_signal_df.empty:

        signal_counts = (
            fraud_signal_df.groupby("Signal")
            .size()
            .reset_index(name="Review Count")
            .sort_values("Review Count", ascending=False)
        )

        col1, col2 = st.columns([1.3, 1])

        with col1:

            st.plotly_chart(
                bar_chart(
                    signal_counts,
                    "Signal",
                    "Review Count",
                    "Fraud Signal Frequency",
                    horizontal=True
                ),
                use_container_width=True
            )

        with col2:

            st.dataframe(
                signal_counts,
                use_container_width=True,
                hide_index=True
            )

        st.caption(
            "A review can contain more than one signal. "
            "Signal counts therefore need not sum to unique candidates."
        )

    else:

        st.info("No explicit fraud signal types in the selected scope.")

    # Platform and rating comparison

    st.divider()

    st.subheader("Fraud Candidate Characteristics")

    if not filtered_fraud.empty:

        col1, col2 = st.columns(2)

        with col1:

            platform_fraud = distribution_table(
                filtered_fraud["platform"],
                "Platform"
            )

            st.plotly_chart(
                px.bar(
                    platform_fraud,
                    x="Platform",
                    y="Review Count",
                    text="Review Count",
                    title="Fraud Candidates by Platform"
                ),
                use_container_width=True
            )

        with col2:

            rating_fraud = distribution_table(
                filtered_fraud["rating"],
                "Rating"
            )

            st.plotly_chart(
                px.bar(
                    rating_fraud,
                    x="Rating",
                    y="Review Count",
                    text="Review Count",
                    title="Fraud Candidates by Rating"
                ),
                use_container_width=True
            )

    # Investigation queue

    st.divider()

    st.subheader("Fraud Investigation Queue")

    triage_options = [
        "All",
        "High",
        "Medium",
        "Review Required"
    ]

    selected_triage = st.selectbox(
        "Triage level",
        triage_options,
        key="fraud_triage_filter"
    )

    selected_signal = st.selectbox(
        "Fraud signal",
        ["All"] + sorted(
            {
                s
                for signals in filtered_fraud["signal_types"]
                for s in signals
            }
        ),
        format_func=lambda x: (
            "All" if x == "All"
            else FRAUD_LABELS.get(x, x.replace("_", " ").title())
        ),
        key="fraud_signal_filter"
    )

    fraud_evidence = filtered_fraud.copy()

    if selected_triage != "All":
        fraud_evidence = fraud_evidence[
            fraud_evidence["triage_level"] == selected_triage
        ]

    if selected_signal != "All":
        fraud_evidence = fraud_evidence[
            fraud_evidence["signal_types"].apply(
                lambda signals: selected_signal in signals
            )
        ]

    fraud_search = st.text_input(
        "Search fraud review text",
        key="fraud_search",
        placeholder="Search suspicious payments, unauthorised transactions..."
    )

    if fraud_search.strip():
        fraud_evidence = fraud_evidence[
            fraud_evidence["review_text"].str.contains(
                fraud_search,
                case=False,
                regex=False,
                na=False
            )
        ]

    st.caption(
        f"{len(fraud_evidence):,} candidates in the investigation queue"
    )

    display_evidence_table(
        fraud_evidence.sort_values(
            "review_date",
            ascending=False
        ),
        [
            "classification_id",
            "rating",
            "platform",
            "review_date",
            "app_version",
            "triage_level",
            "signal_types",
            "complaint_category",
            "review_text"
        ]
    )

    if not fraud_evidence.empty:

        fraud_selected_id = st.selectbox(
            "Inspect fraud candidate",
            fraud_evidence["classification_id"].astype(str).tolist(),
            key="fraud_selected_id"
        )

        fraud_selected_row = fraud_evidence[
            fraud_evidence["classification_id"].astype(str)
            == fraud_selected_id
        ].iloc[0]

        with st.expander("Fraud investigation details", expanded=True):

            display_review_detail(
                fraud_selected_row,
                "fraud_analysis"
            )

    st.warning(
        "Fraud intelligence disclaimer: These are customer-reported "
        "potential fraud and security signals. They are not verified "
        "fraud events or confirmed unauthorised transactions."
    )


# ============================================================
# 13. ENGINEERING INTELLIGENCE TAB
# ============================================================

with engineering_tab:

    st.header("Engineering Intelligence Agent")

    st.markdown(
        '<p class="agent-description">'
        'Identifies reported application crashes, freezing, performance, '
        'authentication, payment and other technical symptoms.'
        '</p>',
        unsafe_allow_html=True
    )

    engineering_triage = (
        filtered_engineering["triage_level"].value_counts()
    )

    engineering_high = int(engineering_triage.get("High", 0))
    engineering_medium = int(engineering_triage.get("Medium", 0))
    engineering_review = int(
        engineering_triage.get("Review Required", 0)
    )

    engineering_explicit = int(
        filtered_engineering["explicit_text_match"].sum()
    )

    engineering_classification_only = (
        len(filtered_engineering) - engineering_explicit
    )

    metric_row([
        (
            "Engineering candidates",
            f"{len(filtered_engineering):,}",
            None
        ),
        ("High priority", f"{engineering_high:,}", None),
        ("Medium priority", f"{engineering_medium:,}", None),
        (
            "Review required",
            f"{engineering_review:,}",
            "Classification-based candidates"
        )
    ])

    st.divider()

    st.subheader("Detection Evidence Composition")

    col1, col2 = st.columns(2)

    with col1:

        fig = px.pie(
            names=["Explicit text match", "Classification-only"],
            values=[
                engineering_explicit,
                engineering_classification_only
            ],
            hole=0.48,
            title="Explicit vs Classification-Based Candidates"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:

        fig = px.pie(
            names=["High", "Medium", "Review Required"],
            values=[
                engineering_high,
                engineering_medium,
                engineering_review
            ],
            hole=0.48,
            title="Engineering Triage Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Classification-only candidates are included because their "
        "complaint category or issue nature suggests a possible "
        "engineering concern. They are not necessarily explicit "
        "technical reports."
    )

    # Engineering signal taxonomy

    st.divider()

    st.subheader("Engineering Signal Taxonomy")

    engineering_signal_rows = []

    for _, row in filtered_engineering.iterrows():

        for signal in row["signal_types"]:

            engineering_signal_rows.append({
                "Signal": ENGINEERING_LABELS.get(
                    signal,
                    signal.replace("_", " ").title()
                ),
                "Classification ID": row["classification_id"],
                "Triage": row["triage_level"],
                "Platform": row["platform"],
                "Rating": row["rating"],
                "App Version": row["app_version"]
            })

    engineering_signal_df = pd.DataFrame(
        engineering_signal_rows
    )

    if not engineering_signal_df.empty:

        signal_counts = (
            engineering_signal_df.groupby("Signal")
            .size()
            .reset_index(name="Review Count")
            .sort_values("Review Count", ascending=False)
        )

        col1, col2 = st.columns([1.3, 1])

        with col1:

            st.plotly_chart(
                bar_chart(
                    signal_counts,
                    "Signal",
                    "Review Count",
                    "Engineering Symptom Frequency",
                    horizontal=True
                ),
                use_container_width=True
            )

        with col2:

            st.dataframe(
                signal_counts,
                use_container_width=True,
                hide_index=True
            )

    else:

        st.info("No explicit engineering signal types in this scope.")

    # App version analysis

    st.divider()

    st.subheader("App Version Intelligence")

    version_analysis = (
        filtered_engineering.groupby("app_version")
        .agg(
            Candidate_Count=("classification_id", "count"),
            Explicit_Text_Matches=("explicit_text_match", "sum")
        )
        .reset_index()
        .sort_values("Candidate_Count", ascending=False)
    )

    version_analysis["Explicit_Text_Matches"] = (
        version_analysis["Explicit_Text_Matches"].astype(int)
    )

    version_analysis = version_analysis.head(20)

    if not version_analysis.empty:

        fig = px.bar(
            version_analysis,
            x="app_version",
            y="Candidate_Count",
            text="Candidate_Count",
            title="Engineering Candidates by App Version",
            hover_data=["Explicit_Text_Matches"]
        )

        fig.update_layout(
            height=450,
            xaxis_title="App Version",
            yaxis_title="Candidate Reviews"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            version_analysis,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "These are candidate counts, not defect rates. "
            "Versions with more reviews may naturally have more candidates."
        )

    # Platform and rating

    st.divider()

    st.subheader("Engineering Candidate Characteristics")

    if not filtered_engineering.empty:

        col1, col2 = st.columns(2)

        with col1:

            platform_eng = distribution_table(
                filtered_engineering["platform"],
                "Platform"
            )

            st.plotly_chart(
                px.bar(
                    platform_eng,
                    x="Platform",
                    y="Review Count",
                    text="Review Count",
                    title="Engineering Candidates by Platform"
                ),
                use_container_width=True
            )

        with col2:

            rating_eng = distribution_table(
                filtered_engineering["rating"],
                "Rating"
            )

            st.plotly_chart(
                px.bar(
                    rating_eng,
                    x="Rating",
                    y="Review Count",
                    text="Review Count",
                    title="Engineering Candidates by Rating"
                ),
                use_container_width=True
            )

    # Investigation queue

    st.divider()

    st.subheader("Engineering Investigation Queue")

    selected_eng_triage = st.selectbox(
        "Triage level",
        ["All", "High", "Medium", "Review Required"],
        key="engineering_triage_filter"
    )

    selected_eng_signal = st.selectbox(
        "Engineering symptom",
        ["All"] + sorted(
            {
                s
                for signals in filtered_engineering["signal_types"]
                for s in signals
            }
        ),
        format_func=lambda x: (
            "All" if x == "All"
            else ENGINEERING_LABELS.get(
                x,
                x.replace("_", " ").title()
            )
        ),
        key="engineering_signal_filter"
    )

    engineering_evidence = filtered_engineering.copy()

    if selected_eng_triage != "All":
        engineering_evidence = engineering_evidence[
            engineering_evidence["triage_level"] == selected_eng_triage
        ]

    if selected_eng_signal != "All":
        engineering_evidence = engineering_evidence[
            engineering_evidence["signal_types"].apply(
                lambda signals: selected_eng_signal in signals
            )
        ]

    engineering_search = st.text_input(
        "Search engineering review text",
        key="engineering_search",
        placeholder="Search crash, freezing, login, payment failure..."
    )

    if engineering_search.strip():

        engineering_evidence = engineering_evidence[
            engineering_evidence["review_text"].str.contains(
                engineering_search,
                case=False,
                regex=False,
                na=False
            )
        ]

    st.caption(
        f"{len(engineering_evidence):,} candidates in the investigation queue"
    )

    display_evidence_table(
        engineering_evidence.sort_values(
            "review_date",
            ascending=False
        ),
        [
            "classification_id",
            "rating",
            "platform",
            "review_date",
            "app_version",
            "triage_level",
            "signal_types",
            "complaint_category",
            "issue_nature",
            "review_text"
        ]
    )

    if not engineering_evidence.empty:

        engineering_selected_id = st.selectbox(
            "Inspect engineering candidate",
            engineering_evidence["classification_id"].astype(str).tolist(),
            key="engineering_selected_id"
        )

        engineering_selected_row = engineering_evidence[
            engineering_evidence["classification_id"].astype(str)
            == engineering_selected_id
        ].iloc[0]

        with st.expander(
            "Engineering investigation details",
            expanded=True
        ):

            display_review_detail(
                engineering_selected_row,
                "engineering_analysis"
            )

    st.warning(
        "Engineering intelligence disclaimer: These are customer-reported "
        "technical symptoms and classification-based candidates. They do "
        "not establish confirmed software defects or backend root causes."
    )



# ============================================================
# ADVANCED ANALYTICS TAB
# ============================================================

with analytics_tab:

    render_advanced_analytics(
        filtered_analytics,
        fraud_df=filtered_fraud,
        engineering_df=filtered_engineering
    )

# ============================================================
# 14. SHARED SUPERVISOR INTELLIGENCE
# ============================================================

st.divider()

st.header("🧠 Ask PayPal Sentinel")

st.markdown(
    "The Supervisor can route a question to one or more specialist "
    "agents and consolidate their findings."
)

with st.container(border=True):

    supervisor_question = st.text_area(
        "Ask a cross-domain intelligence question",
        placeholder=(
            "Example: Compare customer-reported fraud and engineering "
            "issues across Android and iOS."
        ),
        height=100,
        key="supervisor_question"
    )

    if st.button(
        "Analyse with Supervisor",
        type="primary",
        use_container_width=True
    ):

        if not supervisor_question.strip():

            st.warning("Please enter a question.")

        else:

            try:

                with st.spinner(
                    "Supervisor is routing and executing specialist agents..."
                ):

                    routing = route_question(
                        supervisor_question.strip()
                    )

                    selected_agents = routing["agents"]

                    agent_questions = build_agent_questions(
                        supervisor_question.strip(),
                        selected_agents
                    )

                    agent_results = execute_selected_agents(
                        agent_questions
                    )

                    final_result = consolidate_responses(
                        supervisor_question.strip(),
                        agent_results
                    )

                    st.session_state["supervisor_result"] = {
                        "question": supervisor_question.strip(),
                        "routing": routing,
                        "agent_questions": agent_questions,
                        "agent_results": agent_results,
                        "final_result": final_result
                    }

            except Exception as error:

                st.error(f"Supervisor execution failed: {error}")


if "supervisor_result" in st.session_state:

    result = st.session_state["supervisor_result"]

    st.subheader("Supervisor Intelligence Report")

    st.markdown(f"**Question:** {result['question']}")

    routing = result["routing"]

    st.write(
        "**Routing rationale:**",
        routing.get("reason", "Not provided")
    )

    agent_cols = st.columns(len(routing["agents"]))

    for col, agent in zip(agent_cols, routing["agents"]):

        col.info(
            AGENT_LABELS.get(agent, agent.title())
        )

    final_result = result["final_result"]

    if final_result.get("status") == "success":

        st.markdown(final_result.get("answer", ""))

    else:

        st.warning(
            final_result.get(
                "answer",
                "The Supervisor could not consolidate the responses."
            )
        )

    st.markdown("#### Specialist Agent Responses")

    for agent, agent_result in result["agent_results"].items():

        with st.expander(
            AGENT_LABELS.get(agent, agent.title())
            + " — "
            + agent_result.get("status", "unknown").upper()
        ):

            st.write(
                "**Assigned task:**",
                result["agent_questions"].get(agent, "")
            )

            if agent_result.get("status") == "success":

                response = agent_result.get("response", {})

                if isinstance(response, dict):
                    st.markdown(
                        response.get("answer", str(response))
                    )
                else:
                    st.markdown(str(response))

            else:

                st.error(
                    agent_result.get("error", "Agent failed.")
                )

    successful = final_result.get("successful_agents", [])
    failed = final_result.get("failed_agents", [])

    c1, c2 = st.columns(2)

    c1.metric("Successful agents", len(successful))
    c2.metric("Failed agents", len(failed))


# ============================================================
# 15. FOOTER
# ============================================================

st.divider()

st.caption(
    "PAYPAL SENTINEL | Complaint Intelligence · Fraud Intelligence · "
    "Engineering Intelligence | Powered by specialist agents and "
    "Supervisor orchestration."
)
