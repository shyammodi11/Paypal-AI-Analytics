
import pandas as pd
import plotly.express as px
import streamlit as st
import matplotlib.pyplot as plt

from backend.analytics.classification_analytics import (
    DIMENSIONS,
    parse_labels,
    get_primary_distribution,
    get_multilabel_distribution,
    get_cross_dimension_distribution
)

from backend.analytics.temporal_analytics import (
    get_review_volume_trend,
    get_dimension_trend,
    get_app_version_trend
)

from backend.analytics.text_analytics import (
    prepare_text,
    get_text_analytics_summary,
    get_top_keywords,
    get_top_ngrams,
    get_tfidf_keywords,
    generate_wordcloud,
    get_keywords_by_category
)


# ============================================================
# CONFIGURATION
# ============================================================

DIMENSION_LABELS = {
    "business_context": "Business Context",
    "stakeholder": "Stakeholder",
    "business_operation": "Business Operation",
    "request_intent": "Request Intent",
    "business_impact": "Business Impact",
    "product_module": "Product Module",
    "product_feature": "Product Feature",
    "workflow_stage": "Workflow Stage",
    "reported_symptom": "Reported Symptom",
    "review_sentiment": "Review Sentiment",
    "complaint_category": "Complaint Category",
    "issue_nature": "Issue Nature"
}


# ============================================================
# HELPER: CHART RENDERING
# ============================================================

def render_distribution_chart(
    data,
    title,
    category_column="category",
    count_column="review_count",
    top_n=15
):
    if data is None or data.empty:
        st.info("No classification data available.")
        return

    chart_data = (
        data.head(top_n)
        .sort_values(count_column, ascending=True)
    )

    fig = px.bar(
        chart_data,
        x=count_column,
        y=category_column,
        orientation="h",
        text=count_column,
        title=title,
        hover_data=["percentage"] if "percentage" in chart_data.columns else None
    )

    fig.update_layout(
        xaxis_title="Number of Reviews",
        yaxis_title="",
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(fig, use_container_width=True)


def render_temporal_chart(
    data,
    x_column,
    y_column,
    title,
    color_column=None
):
    if data is None or data.empty:
        st.info("No temporal data available.")
        return

    fig = px.line(
        data,
        x=x_column,
        y=y_column,
        color=color_column,
        markers=True,
        title=title
    )

    fig.update_layout(
        hovermode="x unified",
        xaxis_title="Period",
        yaxis_title="Review Count"
    )

    st.plotly_chart(fig, use_container_width=True)



def render_paypal_knowledge_centre(df):

    DIMENSION_GUIDE = {
        "business_context": (
            "Business Context",
            "The broader situation or context described in a review."
        ),
        "stakeholder": (
            "Stakeholder",
            "The person or party involved, such as a customer or merchant."
        ),
        "business_operation": (
            "Business Operation",
            "The business activity affected by the reported issue."
        ),
        "request_intent": (
            "Request Intent",
            "What the reviewer is trying to achieve or asking PayPal to do."
        ),
        "business_impact": (
            "Business Impact",
            "The consequence of the reported issue for the customer or business."
        ),
        "product_module": (
            "Product Module",
            "The broader PayPal product area associated with the review."
        ),
        "product_feature": (
            "Product Feature",
            "The specific feature or capability mentioned in the review."
        ),
        "workflow_stage": (
            "Workflow Stage",
            "The stage of a customer journey or transaction at which an issue occurs."
        ),
        "reported_symptom": (
            "Reported Symptom",
            "The problem or behaviour explicitly described by the reviewer."
        ),
        "review_sentiment": (
            "Review Sentiment",
            "The expressed tone or attitude in the review."
        ),
        "complaint_category": (
            "Complaint Category",
            "The broad category assigned to a customer's complaint."
        ),
        "issue_nature": (
            "Issue Nature",
            "The nature or type of issue identified in the review."
        )
    }

    def show_dimension_details(dimension):

        title, description = DIMENSION_GUIDE.get(
            dimension,
            (dimension.replace("_", " ").title(), "Classification dimension.")
        )

        primary_col = f"{dimension}_primary"
        all_col = f"{dimension}_all"
        scores_col = f"{dimension}_scores"
        confidence_col = f"{dimension}_confidence"

        st.markdown(f"**{title}**")
        st.write(description)

        col1, col2 = st.columns(2)

        with col1:
            st.caption("Primary Label")
            st.write(
                "The single main category selected for a review."
            )

        with col2:
            st.caption("All Labels")
            st.write(
                "All applicable categories assigned to a review. "
                "A review may belong to multiple categories."
            )

        if primary_col in df.columns:
            primary_values = (
                df[primary_col]
                .fillna("Unknown / Missing")
                .astype(str)
                .str.strip()
            )

            primary_values = primary_values[
                primary_values != ""
            ]

            with st.expander(
                f"Explore Primary Labels — {title}",
                expanded=False
            ):
                primary_counts = (
                    primary_values
                    .value_counts()
                    .rename_axis("Category")
                    .reset_index(name="Review Count")
                )

                st.dataframe(
                    primary_counts,
                    use_container_width=True,
                    hide_index=True
                )

        if all_col in df.columns:
            label_counts = {}

            for value in df[all_col].dropna():
                for label in parse_labels(value):
                    label_counts[label] = (
                        label_counts.get(label, 0) + 1
                    )

            with st.expander(
                f"Explore All Labels — {title}",
                expanded=False
            ):
                if label_counts:
                    all_counts = pd.DataFrame(
                        [
                            {
                                "Category": category,
                                "Review Count": count
                            }
                            for category, count in label_counts.items()
                        ]
                    ).sort_values(
                        "Review Count",
                        ascending=False
                    )

                    st.dataframe(
                        all_counts,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info(
                        "No multi-label categories are available "
                        "for this dimension."
                    )

        with st.expander("Scores and Confidence", expanded=False):

            if scores_col in df.columns:
                st.markdown("**Classification Scores**")
                st.write(
                    "Scores represent the classification system's "
                    "scoring information for candidate labels. "
                    "They should not automatically be interpreted "
                    "as calibrated probabilities."
                )
            else:
                st.caption("No score field found in the current dataset.")

            if confidence_col in df.columns:
                st.markdown("**Classification Confidence**")
                st.write(
                    "Confidence is the model's confidence measure "
                    "associated with the classification. It is not "
                    "a guarantee that the assigned label is correct."
                )
            else:
                st.caption(
                    "No confidence field found in the current dataset."
                )

    with st.expander(
        "📚 PayPal Sentinel — Knowledge Centre",
        expanded=False
    ):

        st.markdown(
            "Explore the classification framework, specialist agents, "
            "analytical terminology and interpretation guidelines "
            "used throughout PayPal Sentinel."
        )

        # ====================================================
        # 1. CLASSIFICATION FRAMEWORK
        # ====================================================

        with st.expander(
            "1. Classification Framework",
            expanded=False
        ):

            st.write(
                "PayPal Sentinel analyses customer reviews across "
                "12 classification dimensions. Each dimension captures "
                "a different aspect of the customer's experience."
            )

            st.markdown("**Available Classification Dimensions**")

            for dimension in DIMENSIONS:
                if dimension in DIMENSION_GUIDE:
                    with st.expander(
                        DIMENSION_GUIDE[dimension][0],
                        expanded=False
                    ):
                        show_dimension_details(dimension)

            st.divider()

            st.markdown("**Understanding Classification Fields**")

            st.markdown(
                """
                - **Primary:** The main classification assigned to a review.
                - **All:** Every applicable classification label.
                - **Scores:** Scoring information associated with labels.
                - **Confidence:** The model's confidence measure.
                - **Unknown / Missing:** A field with no usable classification.
                """
            )

            st.warning(
                "A review can have multiple labels within a dimension. "
                "Therefore, multi-label category counts and percentages "
                "may overlap and may add up to more than 100%."
            )

        # ====================================================
        # 2. FRAUD INTELLIGENCE
        # ====================================================

        with st.expander(
            "2. Fraud Detection Intelligence",
            expanded=False
        ):

            st.write(
                "The Fraud Intelligence Agent examines customer-reported "
                "fraud and security-related review patterns."
            )

            with st.expander("Fraud Candidate", expanded=False):
                st.write(
                    "A review identified through fraud-related "
                    "classification or text-signal rules. A candidate "
                    "is not a confirmed fraud incident."
                )

            with st.expander("Fraud Signal Type", expanded=False):
                st.write(
                    "A text-based pattern associated with a potential "
                    "fraud or security concern. Signal types are derived "
                    "from the configured fraud signal rules."
                )

            with st.expander("Triage Level", expanded=False):
                st.markdown(
                    """
                    - **High:** A higher-priority candidate for review.
                    - **Medium:** A candidate with a moderate prioritisation level.
                    - **Review Required:** A candidate requiring further examination.
                    """
                )
                st.caption(
                    "Triage levels are prioritisation heuristics, "
                    "not fraud probabilities or verified severity ratings."
                )

            with st.expander("Category Match Only", expanded=False):
                st.write(
                    "A review matches the fraud candidate classification "
                    "but has no matching explicit text signal. It should "
                    "not be presented as an explicit textual report of fraud."
                )

            with st.expander("Signal Overlap", expanded=False):
                st.write(
                    "A single review may match multiple fraud signal types. "
                    "Consequently, signal-type counts can exceed the number "
                    "of unique candidate reviews."
                )

            st.info(
                "Fraud candidates represent customer-reported potential "
                "fraud or security signals. They are not independently "
                "verified fraud incidents."
            )

        # ====================================================
        # 3. ENGINEERING INTELLIGENCE
        # ====================================================

        with st.expander(
            "3. Engineering Intelligence",
            expanded=False
        ):

            st.write(
                "The Engineering Intelligence Agent analyses "
                "customer-reported technical symptoms and engineering-related "
                "classification matches."
            )

            engineering_signals = {
                "App Crash": "Reports that the application closes unexpectedly or crashes.",
                "Freezing and Unresponsiveness": "Reports that the application becomes stuck or stops responding.",
                "Performance": "Reports of slow loading, delays or poor application performance.",
                "Login and Authentication": "Reports of login failures or authentication problems.",
                "Payment and Transfer Failure": "Reports of unsuccessful payments or money transfers.",
                "Notification Issues": "Reports of missing, delayed or problematic notifications.",
                "App Update and Compatibility": "Reports of issues following updates or involving device compatibility.",
                "UI and Navigation": "Reports of interface, layout or navigation problems."
            }

            st.markdown("**Engineering Signal Families**")

            for signal, description in engineering_signals.items():
                with st.expander(signal, expanded=False):
                    st.write(description)

            with st.expander(
                "Explicit Text-Signal Candidate",
                expanded=False
            ):
                st.write(
                    "A candidate whose review text contains a matching "
                    "engineering signal pattern."
                )

            with st.expander(
                "Classification-Only Candidate",
                expanded=False
            ):
                st.write(
                    "A candidate identified through issue or complaint "
                    "classification without a matching explicit text signal."
                )

            with st.expander("Engineering Triage", expanded=False):
                st.write(
                    "A prioritisation level used to organise engineering "
                    "candidates for further review. It is not proof of "
                    "technical severity."
                )

            st.warning(
                "Customer-reported symptoms do not establish a confirmed "
                "software defect, backend failure or technical root cause."
            )

        # ====================================================
        # 4. COMPLAINT INTELLIGENCE
        # ====================================================

        with st.expander(
            "4. Complaint Intelligence",
            expanded=False
        ):

            st.write(
                "The Complaint Intelligence Agent focuses on customer "
                "complaints, complaint categories, issue nature and "
                "customer-support-related concerns."
            )

            complaint_terms = {
                "Complaint Category": (
                    "The broad type of complaint identified in a review, "
                    "such as a refund, payment or account-related concern."
                ),
                "Issue Nature": (
                    "The nature of the problem described by the customer."
                ),
                "Unknown / Insufficient Information": (
                    "The review does not contain enough usable information "
                    "to assign a reliable complaint category."
                ),
                "Complaint Distribution": (
                    "The number of reviews associated with each complaint "
                    "category. The denominator should be checked when "
                    "comparing percentages."
                )
            }

            for term, description in complaint_terms.items():
                with st.expander(term, expanded=False):
                    st.write(description)

            st.info(
                "A complaint category describes the review classification. "
                "It does not independently establish the outcome of a "
                "customer-support case."
            )

        # ====================================================
        # 5. SUPERVISOR AND MULTI-AGENT SYSTEM
        # ====================================================

        with st.expander(
            "5. Supervisor and Multi-Agent System",
            expanded=False
        ):

            st.write(
                "PayPal Sentinel uses a Supervisor Agent to route questions "
                "to relevant specialist agents and consolidate their findings."
            )

            stages = [
                (
                    "1. Question Routing",
                    "The Supervisor Agent identifies which specialist "
                    "agents are needed: Complaint, Fraud and/or Engineering."
                ),
                (
                    "2. Task Decomposition",
                    "The user's original question is converted into "
                    "a concise analytical question for each selected agent."
                ),
                (
                    "3. Specialist Execution",
                    "The selected agents retrieve and analyse evidence "
                    "within their respective domains."
                ),
                (
                    "4. Response Consolidation",
                    "The Supervisor combines successful specialist findings "
                    "into a single response."
                )
            ]

            for stage, description in stages:
                with st.expander(stage, expanded=False):
                    st.write(description)

            st.markdown("**Specialist Agent Responsibilities**")

            agent_responsibilities = {
                "Complaint Agent": (
                    "Customer complaint categories, issue nature, refunds, "
                    "payments, account restrictions and complaint patterns."
                ),
                "Fraud Agent": (
                    "Customer-reported fraud signals, unauthorised transactions, "
                    "account compromise, phishing, impersonation and suspicious activity."
                ),
                "Engineering Agent": (
                    "Crashes, freezing, performance, login failures, payment "
                    "failures, notifications, compatibility and UI problems."
                )
            }

            for agent, responsibility in agent_responsibilities.items():
                with st.expander(agent, expanded=False):
                    st.write(responsibility)

            st.markdown("**Response Consolidation Principles**")

            st.markdown(
                """
                - Preserve specialist-reported counts and percentages.
                - Explain when candidate populations or denominators differ.
                - Distinguish customer reports from verified incidents.
                - Do not interpret classification-only matches as explicit text reports.
                - Identify failed agents when their absence limits the findings.
                - Do not invent transaction details, root causes or unsupported trends.
                """
            )

        # ====================================================
        # 6. ANALYTICS AND METRICS
        # ====================================================

        with st.expander(
            "6. Analytics and Metrics",
            expanded=False
        ):

            metric_guide = {
                "Unique Reviews": (
                    "The number of distinct review records, generally "
                    "counted using classification_id."
                ),
                "Review Count": (
                    "The number of reviews associated with a category "
                    "or analytical grouping."
                ),
                "Percentage": (
                    "A category's count divided by the relevant population. "
                    "Always check the denominator."
                ),
                "Primary Distribution": (
                    "Distribution based on one primary label per review "
                    "for the selected dimension."
                ),
                "Multi-Label Distribution": (
                    "Distribution based on all applicable labels. "
                    "A review may contribute to multiple categories."
                ),
                "Cross-Dimensional Analysis": (
                    "Examines the relationship between two classification "
                    "dimensions, such as product module and reported symptom."
                ),
                "Temporal Analysis": (
                    "Examines how review volume or classification patterns "
                    "change over time."
                ),
                "Text Analytics": (
                    "Explores review language, recurring terms and "
                    "text patterns."
                ),
                "Analysis Scope": (
                    "Selects the population being analysed, such as all "
                    "reviews, complaints, fraud candidates or engineering candidates."
                )
            }

            for metric, description in metric_guide.items():
                with st.expander(metric, expanded=False):
                    st.write(description)

            st.warning(
                "Primary-label percentages and multi-label percentages "
                "have different interpretations. Multi-label percentages "
                "can overlap."
            )

        # ====================================================
        # 7. TECHNICAL REFERENCE
        # ====================================================

        with st.expander(
            "7. Technical Reference",
            expanded=False
        ):

            st.markdown("**Dataset Structure**")

            st.write(
                "The expanded classification dataset contains 12 dimensions. "
                "Each dimension may have Primary, All, Scores and Confidence "
                "fields."
            )

            st.code(
                """
classification_id

business_context_primary
business_context_all
business_context_scores
business_context_confidence

stakeholder_primary
stakeholder_all
stakeholder_scores
stakeholder_confidence

... corresponding fields for the remaining dimensions
                """,
                language="text"
            )

            st.markdown("**Important Interpretation Guidelines**")

            st.markdown(
                """
                1. A classification is a model-generated interpretation of review content.
                2. Confidence and scores are not automatically calibrated probabilities.
                3. Multiple labels can apply to one review.
                4. Fraud and engineering candidates are not verified incidents.
                5. A text signal is evidence of a reported pattern, not proof of an event.
                6. Counts from different candidate populations may not be directly comparable.
                7. A review sample returned by an agent may be smaller than the total matching population.
                """
            )

            st.caption(
                "This Knowledge Centre documents the current analytical "
                "and agent terminology. Exact low-level signal rule conditions "
                "are maintained in the corresponding backend tool modules."
            )

# ============================================================
# MAIN ADVANCED ANALYTICS
# ============================================================

# def render_advanced_analytics(df):
def render_advanced_analytics(df, fraud_df=None, engineering_df=None):

    st.header("Advanced Analytics")

    st.markdown(
        "Explore customer review patterns, product performance, "
        "temporal trends, text signals and cross-dimensional relationships."
    )

    if df is None or df.empty:
        st.warning("No reviews available for the selected filters.")
        return

    df = df.copy()

    # Normalize common fields.
    df["review_date"] = pd.to_datetime(
        df["review_date"],
        utc=True,
        errors="coerce"
    )

    df["rating"] = pd.to_numeric(
        df["rating"],
        errors="coerce"
    )

    if "app_version" in df.columns:
        df["app_version"] = (
            df["app_version"]
            .fillna("Unknown / Missing")
            .astype(str)
        )

    render_paypal_knowledge_centre(df)

    # ========================================================
    # NAVIGATION
    # ========================================================

    overview_tab, classification_tab, temporal_tab, text_tab, cross_tab = (
        st.tabs([
            "Overview",
            "Classification Analytics",
            "Temporal Analytics",
            "Text Analytics",
            "Cross-Dimensional Analytics"
        ])
    )

    # ========================================================
    # 1. OVERVIEW
    # ========================================================

    with overview_tab:

        st.subheader("Review Intelligence Overview")

        total_reviews = (
            df["classification_id"].nunique()
            if "classification_id" in df.columns
            else len(df)
        )

        # average_rating = df["rating"].mean()

        positive_reviews = (
            df["review_sentiment_primary"]
            .eq("Positive Sentiment")
            .sum()
            if "review_sentiment_primary" in df.columns
            else 0
        )

        positive_percentage = (
            positive_reviews / len(df) * 100
            if len(df) else 0
        )

        mixed_reviews = (
            df["review_sentiment_primary"]
            .eq("Mixed Sentiment")
            .sum()
            if "review_sentiment_primary" in df.columns
            else 0
        )

        mixed_percentage = (
            mixed_reviews / len(df) * 100
            if len(df) else 0
        )

        negative_reviews = (
            df["review_sentiment_primary"]
            .eq("Negative Sentiment")
            .sum()
            if "review_sentiment_primary" in df.columns
            else 0
        )

        negative_percentage = (
            negative_reviews / len(df) * 100
            if len(df) else 0
        )

        unique_versions = (
            df["app_version"].nunique()
            if "app_version" in df.columns
            else 0
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric(
            "Total Reviews (Set Versions)",
            f"{total_reviews:,}"
        )

        # col2.metric(
        #     "Average Rating",
        #     f"{average_rating:.2f}/5"
        #     if pd.notna(average_rating) else "N/A"
        # )

        col2.metric(
            "Positive Sentiment",
            f"{positive_percentage:.1f}%"
        )

        col3.metric(
                    "Mixed Sentiment",
                    f"{mixed_percentage:.1f}%"
                )

        col4.metric(
            "Negative Sentiment",
            f"{negative_percentage:.1f}%"
        )

        col5.metric(
            "App Versions",
            f"{unique_versions:,}"
        )

        st.divider()

        # Review rating distribution.
        col1, col2 = st.columns(2)

        with col1:

            st.markdown("#### Rating Distribution")

            rating_counts = (
                df["rating"]
                .dropna()
                .value_counts()
                .sort_index()
                .reset_index()
            )

            rating_counts.columns = [
                "rating",
                "review_count"
            ]

            if not rating_counts.empty:

                fig = px.bar(
                    rating_counts,
                    x="rating",
                    y="review_count",
                    text="review_count",
                    title="Reviews by Star Rating"
                )

                fig.update_layout(
                    xaxis_title="Star Rating",
                    yaxis_title="Reviews"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

        with col2:

            st.markdown("#### Primary Sentiment Distribution")

            sentiment_data = get_primary_distribution(
                df,
                "review_sentiment"
            )

            render_distribution_chart(
                sentiment_data,
                "Customer Sentiment",
                top_n=10
            )

        st.divider()

        # Main reported issue distribution.
        st.markdown("#### Most Frequently Reported Symptoms")

        symptom_data = get_primary_distribution(
            df,
            "reported_symptom"
        )

        render_distribution_chart(
            symptom_data,
            "Primary Reported Symptoms",
            top_n=12
        )

        st.caption(
            "These categories represent model-classified customer reports, "
            "not independently verified fraud or product defects."
        )

    # ========================================================
    # 2. CLASSIFICATION ANALYTICS
    # ========================================================

    with classification_tab:

        st.subheader("Classification Analytics")

        st.markdown(
            "Explore all 12 classification dimensions, including "
            "customer context, product areas, reported symptoms, "
            "business impact and review sentiment."
        )

        dimension = st.selectbox(
            "Select Classification Dimension",
            options=DIMENSIONS,
            format_func=lambda x: DIMENSION_LABELS.get(x, x)
        )

        label_mode = st.radio(
            "Classification Mode",
            options=["Primary Labels", "All Labels"],
            horizontal=True,
            help=(
                "Primary assigns one main category per review. "
                "All Labels includes secondary classifications."
            )
        )

        if label_mode == "Primary Labels":

            distribution = get_primary_distribution(
                df,
                dimension
            )

        else:

            distribution = get_multilabel_distribution(
                df,
                dimension
            )

        render_distribution_chart(
            distribution,
            f"{DIMENSION_LABELS[dimension]} Distribution",
            top_n=20
        )

        if label_mode == "All Labels":

            st.info(
                "A review can contribute to multiple categories. "
                "Percentages therefore use total reviews as the "
                "denominator and may sum to more than 100%."
            )

        if not distribution.empty:

            st.markdown("#### Classification Data")

            st.dataframe(
                distribution,
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # Explore the issue-related dimensions together.
        st.markdown("#### Core Issue Classification")

        issue_dimensions = [
            "reported_symptom",
            "complaint_category",
            "issue_nature",
            "product_module",
            "product_feature"
        ]

        selected_issue_dimension = st.selectbox(
            "Explore Issue Dimension",
            options=issue_dimensions,
            format_func=lambda x: DIMENSION_LABELS[x],
            key="issue_dimension"
        )

        issue_distribution = get_primary_distribution(
            df,
            selected_issue_dimension
        )

        render_distribution_chart(
            issue_distribution,
            f"Primary {DIMENSION_LABELS[selected_issue_dimension]}",
            top_n=15
        )

    # ========================================================
    # 3. TEMPORAL ANALYTICS
    # ========================================================

    with temporal_tab:

        st.subheader("Temporal Analytics")

        frequency = st.selectbox(
            "Time Aggregation",
            options=["daily", "weekly", "monthly"],
            index=2,
            format_func=lambda x: x.capitalize()
        )

        # Review volume.
        st.markdown("#### Review Volume Over Time")

        volume_data = get_review_volume_trend(
            df,
            frequency=frequency
        )

        render_temporal_chart(
            volume_data,
            "period",
            "review_count",
            f"{frequency.capitalize()} Review Volume"
        )

        st.divider()

        # Sentiment over time.
        st.markdown("#### Sentiment Trends")

        sentiment_trend = get_dimension_trend(
            df,
            dimension="review_sentiment",
            frequency=frequency,
            label_mode="primary",
            top_n=10
        )

        render_temporal_chart(
            sentiment_trend,
            "period",
            "review_count",
            "Sentiment Over Time",
            color_column="category"
        )

        st.divider()

        # Reported symptoms over time.
        st.markdown("#### Reported Symptom Trends")

        symptom_trend = get_dimension_trend(
            df,
            dimension="reported_symptom",
            frequency=frequency,
            label_mode="primary",
            top_n=8
        )

        render_temporal_chart(
            symptom_trend,
            "period",
            "review_count",
            "Reported Symptoms Over Time",
            color_column="category"
        )

        st.divider()

        # Product modules over time.
        st.markdown("#### Product Module Trends")

        module_trend = get_dimension_trend(
            df,
            dimension="product_module",
            frequency=frequency,
            label_mode="primary",
            top_n=8
        )

        render_temporal_chart(
            module_trend,
            "period",
            "review_count",
            "Product Module Trends",
            color_column="category"
        )

        st.divider()

        # App versions over time.
        st.markdown("#### App Version Trends")

        version_trend = get_app_version_trend(
            df,
            frequency=frequency,
            top_n=10,
            include_missing=False
        )

        render_temporal_chart(
            version_trend,
            "period",
            "review_count",
            "Review Volume by App Version",
            color_column="app_version"
        )

        st.caption(
            "Version trends describe review volume only. "
            "They do not establish that a particular app version "
            "caused a reported problem or had a higher defect rate."
        )

    # ========================================================
    # 4. TEXT ANALYTICS
    # ========================================================

    with text_tab:

        st.subheader("Customer Review Text Analytics")

        text_df = prepare_text(df)

        text_summary = get_text_analytics_summary(df)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Reviews with Text",
            f"{text_summary['reviews_with_text']:,}"
        )

        col2.metric(
            "Empty Reviews",
            f"{text_summary['empty_reviews']:,}"
        )

        col3.metric(
            "Average Words",
            text_summary["average_words_per_review"]
        )

        col4.metric(
            "Unique Vocabulary",
            f"{text_summary['unique_vocabulary']:,}"
        )

        st.divider()

        # Text sentiment selection.
        st.markdown("#### Explore Review Language")

        sentiment_options = ["All Reviews"]

        if "review_sentiment_primary" in text_df.columns:

            sentiment_options += sorted(
                text_df["review_sentiment_primary"]
                .dropna()
                .unique()
                .tolist()
            )

        selected_sentiment = st.selectbox(
            "Filter Reviews by Sentiment",
            options=sentiment_options
        )

        text_subset = text_df.copy()

        if selected_sentiment != "All Reviews":

            text_subset = text_subset[
                text_subset["review_sentiment_primary"]
                == selected_sentiment
            ]

        if text_subset.empty:

            st.warning(
                "No reviews available for this sentiment selection."
            )

        else:

            col1, col2 = st.columns(2)

            with col1:

                st.markdown("#### Word Cloud")

                wordcloud = generate_wordcloud(
                    text_subset,
                    max_words=120
                )

                if wordcloud is not None:

                    fig, ax = plt.subplots(figsize=(12, 5))

                    ax.imshow(
                        wordcloud,
                        interpolation="bilinear"
                    )

                    ax.axis("off")

                    st.pyplot(
                        fig,
                        use_container_width=True
                    )

                    plt.close(fig)

                else:

                    st.info("Not enough text to generate a word cloud.")

            with col2:

                st.markdown("#### Most Frequent Keywords")

                keywords = get_top_keywords(
                    text_subset,
                    top_n=20
                )

                if not keywords.empty:

                    fig = px.bar(
                        keywords.sort_values("frequency"),
                        x="frequency",
                        y="keyword",
                        orientation="h",
                        title="Top Keywords"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                else:

                    st.info("No keywords available.")

            st.divider()

            # N-gram analysis.
            st.markdown("#### Phrase and N-gram Analysis")

            ngram_type = st.selectbox(
                "Phrase Length",
                options=["Bigrams", "Trigrams"],
                index=0
            )

            n = 2 if ngram_type == "Bigrams" else 3

            ngram_data = get_top_ngrams(
                text_subset,
                ngram_range=(n, n),
                top_n=20,
                min_df=2
            )

            if not ngram_data.empty:

                fig = px.bar(
                    ngram_data.sort_values("frequency"),
                    x="frequency",
                    y="phrase",
                    orientation="h",
                    title=f"Top {ngram_type}"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

                st.dataframe(
                    ngram_data,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info("No recurring phrases found.")

            st.divider()

            # TF-IDF.
            st.markdown("#### TF-IDF Keyword Analysis")

            tfidf_data = get_tfidf_keywords(
                text_subset,
                top_n=20
            )

            if not tfidf_data.empty:

                st.dataframe(
                    tfidf_data,
                    use_container_width=True,
                    hide_index=True
                )

            st.caption(
                "TF-IDF scores rank terms by their corpus-level "
                "TF-IDF contribution. They are not probabilities "
                "or measures of issue severity."
            )

        st.divider()

        # Category-specific text analysis.
        st.markdown("#### Keywords by Product or Issue Category")

        category_dimension = st.selectbox(
            "Category Dimension",
            options=[
                "product_module",
                "product_feature",
                "reported_symptom",
                "complaint_category",
                "issue_nature",
                "business_impact",
                "stakeholder"
            ],
            format_func=lambda x: DIMENSION_LABELS[x]
        )

        category_mode = st.radio(
            "Category Classification",
            options=["Primary", "All Labels"],
            horizontal=True
        )

        category_keywords = get_keywords_by_category(
            df,
            dimension=category_dimension,
            label_mode=(
                "primary"
                if category_mode == "Primary"
                else "all"
            ),
            top_n=10,
            min_reviews=10
        )

        if not category_keywords.empty:

            selected_category = st.selectbox(
                "Select Category",
                options=sorted(
                    category_keywords["category"].unique()
                )
            )

            category_result = category_keywords[
                category_keywords["category"]
                == selected_category
            ]

            st.dataframe(
                category_result,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No category-level keywords meet the minimum "
                "review threshold."
            )

    # ========================================================
    # 5. CROSS-DIMENSIONAL ANALYTICS
    # ========================================================

    with cross_tab:

        st.subheader("Cross-Dimensional Analytics")

        analysis_scope = st.selectbox(
            "Analysis Scope",
            options=[
                "All Reviews",
                "Complaints",
                "Fraud",
                "Engineering"
            ],
            key="cross_analysis_scope"
        )

        scope_df = df.copy()

        if analysis_scope == "Complaints":

            scope_df = scope_df[
                scope_df["complaint_category_primary"].fillna(
                    "Unknown / Insufficient information"
                ) != "Unknown / Insufficient information"
            ]

        elif analysis_scope == "Fraud":

            fraud_ids = (
                set(fraud_df["classification_id"].dropna().astype(str))
                if fraud_df is not None
                and not fraud_df.empty
                and "classification_id" in fraud_df.columns
                else set()
            )

            scope_df = scope_df[
                scope_df["classification_id"].astype(str).isin(fraud_ids)
            ]

        elif analysis_scope == "Engineering":

            engineering_ids = (
                set(engineering_df["classification_id"].dropna().astype(str))
                if engineering_df is not None
                and not engineering_df.empty
                and "classification_id" in engineering_df.columns
                else set()
            )

            scope_df = scope_df[
                scope_df["classification_id"].astype(str).isin(
                    engineering_ids
                )
            ]

        st.caption(
            f"{analysis_scope}: {scope_df['classification_id'].nunique():,} "
            "unique reviews in the selected scope."
        )

        st.markdown(
            "Investigate relationships between reported issues, "
            "product areas, customer groups, business impact "
            "and customer sentiment."
        )

        dimension_a = st.selectbox(
            "First Dimension",
            options=DIMENSIONS,
            index=DIMENSIONS.index("product_module"),
            format_func=lambda x: DIMENSION_LABELS[x],
            key="cross_dimension_a"
        )

        dimension_b = st.selectbox(
            "Second Dimension",
            options=[
                dimension
                for dimension in DIMENSIONS
                if dimension != dimension_a
            ],
            index=(
                [
                    dimension
                    for dimension in DIMENSIONS
                    if dimension != dimension_a
                ].index("review_sentiment")
                if "review_sentiment" != dimension_a
                else 0
            ),
            format_func=lambda x: DIMENSION_LABELS[x],
            key="cross_dimension_b"
        )

        cross_mode = st.radio(
            "Classification Mode",
            options=["Primary Labels", "All Labels"],
            horizontal=True,
            key="cross_mode"
        )

        # ----------------------------------------------------
        # MULTI-CATEGORY FILTERS
        # ----------------------------------------------------

        use_multilabel = cross_mode == "All Labels"

        if use_multilabel:

            distribution_a = get_multilabel_distribution(
                scope_df,
                dimension_a
            )

            distribution_b = get_multilabel_distribution(
                scope_df,
                dimension_b
            )

        else:

            distribution_a = get_primary_distribution(
                scope_df,
                dimension_a
            )

            distribution_b = get_primary_distribution(
                scope_df,
                dimension_b
            )

        categories_a = sorted(
            distribution_a["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        categories_b = sorted(
            distribution_b["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:

            selected_categories_a = st.multiselect(
                f"Filter {DIMENSION_LABELS[dimension_a]}",
                options=categories_a,
                default=categories_a,
                key="cross_categories_a"
            )

        with filter_col2:

            selected_categories_b = st.multiselect(
                f"Filter {DIMENSION_LABELS[dimension_b]}",
                options=categories_b,
                default=categories_b,
                key="cross_categories_b"
            )

        # ----------------------------------------------------
        # APPLY CATEGORY FILTERS
        # ----------------------------------------------------

        filtered_cross_df = scope_df.copy()

        column_a = (
            f"{dimension_a}_all"
            if use_multilabel
            else f"{dimension_a}_primary"
        )

        column_b = (
            f"{dimension_b}_all"
            if use_multilabel
            else f"{dimension_b}_primary"
        )

        if use_multilabel:

            filtered_cross_df[column_a] = (
                filtered_cross_df[column_a].apply(
                    lambda value: [
                        label
                        for label in parse_labels(value)
                        if label in selected_categories_a
                    ]
                )
            )

            filtered_cross_df[column_b] = (
                filtered_cross_df[column_b].apply(
                    lambda value: [
                        label
                        for label in parse_labels(value)
                        if label in selected_categories_b
                    ]
                )
            )

            filtered_cross_df = filtered_cross_df[
                filtered_cross_df[column_a].map(bool)
                & filtered_cross_df[column_b].map(bool)
            ]

        else:

            filtered_cross_df = filtered_cross_df[
                filtered_cross_df[column_a].isin(
                    selected_categories_a
                )
                & filtered_cross_df[column_b].isin(
                    selected_categories_b
                )
            ]

        st.caption(
            f"Filtered dataset: "
            f"{filtered_cross_df['classification_id'].nunique():,} "
            "unique reviews"
        )

        # ----------------------------------------------------
        # MULTI-CATEGORY FILTERS
        # ----------------------------------------------------

        st.markdown("#### Filter by Categories")

        if cross_mode == "Primary Labels":

            options_a = get_primary_distribution(
                scope_df,
                dimension_a
            )["category"].dropna().tolist()

            options_b = get_primary_distribution(
                scope_df,
                dimension_b
            )["category"].dropna().tolist()

        else:

            options_a = get_multilabel_distribution(
                scope_df,
                dimension_a
            )["category"].dropna().tolist()

            options_b = get_multilabel_distribution(
                scope_df,
                dimension_b
            )["category"].dropna().tolist()

        col1, col2 = st.columns(2)

        with col1:

            selected_categories_a = st.multiselect(
                f"Filter {DIMENSION_LABELS[dimension_a]}",
                options=options_a,
                key="cross_filter_a"
            )

        with col2:

            selected_categories_b = st.multiselect(
                f"Filter {DIMENSION_LABELS[dimension_b]}",
                options=options_b,
                key="cross_filter_b"
            )

        # Apply category filters.
        filtered_cross_df = scope_df.copy()

        if selected_categories_a:

            if cross_mode == "Primary Labels":

                filtered_cross_df = filtered_cross_df[
                    filtered_cross_df[f"{dimension_a}_primary"].isin(
                        selected_categories_a
                    )
                ]

            else:

                filtered_cross_df = filtered_cross_df[
                    filtered_cross_df[f"{dimension_a}_all"].apply(
                        lambda value: bool(
                            set(parse_labels(value))
                            & set(selected_categories_a)
                        )
                    )
                ]

        if selected_categories_b:

            if cross_mode == "Primary Labels":

                filtered_cross_df = filtered_cross_df[
                    filtered_cross_df[f"{dimension_b}_primary"].isin(
                        selected_categories_b
                    )
                ]

            else:

                filtered_cross_df = filtered_cross_df[
                    filtered_cross_df[f"{dimension_b}_all"].apply(
                        lambda value: bool(
                            set(parse_labels(value))
                            & set(selected_categories_b)
                        )
                    )
                ]

        st.caption(
            f"Filtered dataset: "
            f"{filtered_cross_df['classification_id'].nunique():,} "
            "unique reviews."
        )

        cross_data = get_cross_dimension_distribution(
            filtered_cross_df,
            dimension_a,
            dimension_b,
            use_multilabel= use_multilabel #(cross_mode == "All Labels")
        )

        if not cross_data.empty:

            cross_data = cross_data.head(30).copy()

            cross_data["pair"] = (
                cross_data["category_a"]
                + " → "
                + cross_data["category_b"]
            )

            fig = px.bar(
                cross_data.sort_values("review_count"),
                x="review_count",
                y="pair",
                orientation="h",
                text="review_count",
                title=(
                    f"{DIMENSION_LABELS[dimension_a]} "
                    f"vs {DIMENSION_LABELS[dimension_b]}"
                )
            )

            fig.update_layout(
                xaxis_title="Unique Reviews",
                yaxis_title=""
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.dataframe(
                cross_data[
                    [
                        "category_a",
                        "category_b",
                        "review_count"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No cross-dimensional combinations are available."
            )

        if cross_mode == "All Labels":

            st.info(
                "In All Labels mode, a review may contribute to "
                "multiple category combinations. Pair counts "
                "must not be added together to estimate unique reviews."
            )
