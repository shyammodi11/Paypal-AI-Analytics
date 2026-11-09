import json
from collections import Counter
from typing import TypedDict

from langgraph.graph import StateGraph, END

from backend.llm import get_llm
from backend.tools.engineering_analytics import (
    find_engineering_candidates,
    ENGINEERING_SIGNAL_RULES
)


# ============================================================
# 1. CONFIGURATION
# ============================================================

VALID_TASKS = {
    "overview",
    "distribution",
    "candidates"
}

VALID_DIMENSIONS = {
    "signal_type",
    "triage_level",
    "platform",
    "rating",
    "app_version",
    "complaint_category",
    "issue_nature"
}

VALID_TRIAGE_LEVELS = {
    "High",
    "Medium",
    "Review Required"
}

VALID_SIGNAL_TYPES = set(ENGINEERING_SIGNAL_RULES.keys())


# ============================================================
# 2. AGENT STATE
# ============================================================

class EngineeringAgentState(TypedDict):
    user_query: str
    plan: dict
    evidence: dict
    response: str
    error: str


# ============================================================
# 3. HELPER: PARSE JSON
# ============================================================

def parse_json_response(content):

    content = content.strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]

    return json.loads(content)


# ============================================================
# 4. HELPER: RETRIEVE ALL ENGINEERING CANDIDATES
# ============================================================

def get_all_engineering_candidates():

    all_candidates = []

    limit = 200
    offset = 0

    while True:

        result = find_engineering_candidates(
            limit=limit,
            offset=offset
        )

        reviews = result["reviews"]

        if not reviews:
            break

        all_candidates.extend(reviews)

        offset += len(reviews)

        if offset >= result["total_candidates"]:
            break

    return all_candidates


# ============================================================
# 5. QUERY INTERPRETATION
# ============================================================

def interpret_query(state):

    llm = get_llm()

    prompt = f"""
You are the query interpreter for PayPal Sentinel's
Engineering Intelligence Agent.

Convert the user's question into a JSON query plan.

USER QUESTION:
{state["user_query"]}

Available tasks:
- overview
- distribution
- candidates

Available dimensions:
{list(VALID_DIMENSIONS)}

Available engineering signal types:
{list(VALID_SIGNAL_TYPES)}

Available triage levels:
{list(VALID_TRIAGE_LEVELS)}

Return ONLY valid JSON with these fields:

{{
    "task": "overview",
    "dimension": "signal_type",
    "signal_type": null,
    "triage_level": null,
    "platform": null,
    "rating": null,
    "app_version": null,
    "limit": 10
}}

INTERPRETATION RULES:

1. Use overview for general engineering intelligence questions.

2. Use distribution for questions asking about:
   counts, proportions, rankings, most common issues,
   app version comparisons or breakdowns.

3. Use candidates when the user wants to inspect individual
   reviews or find specific engineering-related reports.

4. Choose the most relevant dimension for distribution.

5. Use exact signal type names from the supplied list.

6. Use exact triage levels from the supplied list.

7. Do not invent filters.

8. Default limit is 10.

9. Maximum limit is 50.

10. If the question is ambiguous, choose the most reasonable
    interpretation.

11. Distinguish reported symptoms from confirmed software defects.

12. If the user asks about crashes, use app_crash.
    If the user asks about freezing or unresponsiveness,
    use freezing_and_unresponsiveness.
    If the user asks about slow performance or lag,
    use performance.

13. If the user asks about login, OTP or verification problems,
    use login_and_authentication.

14. If the user asks about failed payments or transfers,
    use payment_and_transfer_failure.

15. If the user asks about notifications or alerts,
    use notification_issues.

16. If the user asks about updates or compatibility,
    use app_update_and_compatibility.

17. If the user asks about navigation, buttons or interface
    problems, use ui_and_navigation.
"""

    try:

        response = llm.invoke(prompt)

        plan = parse_json_response(response.content)

        if plan.get("task") not in VALID_TASKS:
            plan["task"] = "overview"

        if plan.get("dimension") not in VALID_DIMENSIONS:
            plan["dimension"] = "signal_type"

        if plan.get("signal_type") not in VALID_SIGNAL_TYPES:
            plan["signal_type"] = None

        if plan.get("triage_level") not in VALID_TRIAGE_LEVELS:
            plan["triage_level"] = None

        # Normalise platform.

        platform = plan.get("platform")

        if isinstance(platform, str):
            platform = platform.strip().lower()

        if platform not in ["android", "ios"]:
            platform = None

        plan["platform"] = platform

        # Validate rating.

        rating = plan.get("rating")

        if isinstance(rating, str) and rating.isdigit():
            rating = int(rating)

        if type(rating) is not int or rating not in [1, 2, 3, 4, 5]:
            rating = None

        plan["rating"] = rating

        # Validate app version.

        app_version = plan.get("app_version")

        if not isinstance(app_version, str) or not app_version.strip():
            app_version = None

        plan["app_version"] = app_version.strip() if app_version else None

        # Validate result limit.

        limit = plan.get("limit", 10)

        if not isinstance(limit, int) or not 1 <= limit <= 50:
            limit = 10

        plan["limit"] = limit

        return {
            **state,
            "plan": plan,
            "error": ""
        }

    except Exception as exc:

        return {
            **state,
            "plan": {
                "task": "overview",
                "dimension": "signal_type",
                "signal_type": None,
                "triage_level": None,
                "platform": None,
                "rating": None,
                "app_version": None,
                "limit": 10
            },
            "error": f"Query interpretation error: {str(exc)}"
        }


# ============================================================
# 6. HELPER: BUILD DISTRIBUTION
# ============================================================

def build_distribution(candidates, dimension):

    counts = Counter()

    for review in candidates:

        analysis = review["engineering_analysis"]

        if dimension == "signal_type":

            signal_types = analysis["signal_types"]

            if not signal_types:
                signal_types = [
                    "Classification match only (no text signal)"
                ]

            for signal in set(signal_types):
                counts[signal] += 1

        elif dimension == "triage_level":

            counts[analysis["triage_level"]] += 1

        else:

            value = review.get(dimension)

            if value is None or value == "":
                value = "Unknown / Missing"

            counts[str(value)] += 1

    total = len(candidates)

    distribution = [
        {
            "label": label,
            "review_count": count,
            "percentage_of_candidates": round(
                count / total * 100, 2
            ) if total else 0
        }
        for label, count in counts.most_common()
    ]

    return {
        "dimension": dimension,
        "total_candidates": total,
        "distribution": distribution,
        "note": (
            "Signal types can overlap because a review may "
            "contain multiple engineering symptoms. Their "
            "percentages may therefore add up to more than 100%. "
            "Classification-only candidates are shown separately."
            if dimension == "signal_type"
            else "Percentages use all engineering candidates "
                 "as the denominator."
        )
    }


# ============================================================
# 7. EVIDENCE RETRIEVAL
# ============================================================

def retrieve_evidence(state):

    plan = state["plan"]

    try:

        candidates = get_all_engineering_candidates()

        # ----------------------------------------------------
        # OVERVIEW
        # ----------------------------------------------------

        if plan["task"] == "overview":

            triage_counts = Counter(
                review["engineering_analysis"]["triage_level"]
                for review in candidates
            )

            signal_distribution = build_distribution(
                candidates,
                "signal_type"
            )

            explicit_signal_count = sum(
                1 for review in candidates
                if review["engineering_analysis"]["signal_types"]
            )

            classification_only_count = sum(
                1 for review in candidates
                if (
                    not review["engineering_analysis"]["signal_types"]
                    and (
                        review["engineering_analysis"]["issue_match"]
                        or review["engineering_analysis"]["complaint_match"]
                    )
                )
            )

            evidence = {
                "task": "overview",
                "total_candidates": len(candidates),
                "triage_summary": dict(triage_counts),
                "explicit_text_signal_candidates": explicit_signal_count,
                "classification_only_candidates": classification_only_count,
                "signal_distribution": signal_distribution,
                "disclaimer": (
                    "These are customer-reported technical symptoms "
                    "and classification-based candidates. They do not "
                    "establish confirmed software defects or root causes."
                )
            }

        # ----------------------------------------------------
        # DISTRIBUTION
        # ----------------------------------------------------

        elif plan["task"] == "distribution":

            evidence = build_distribution(
                candidates,
                plan["dimension"]
            )

            evidence["task"] = "distribution"

        # ----------------------------------------------------
        # CANDIDATE INVESTIGATION
        # ----------------------------------------------------

        else:

            filtered = candidates

            if plan.get("triage_level"):

                filtered = [
                    review for review in filtered
                    if review["engineering_analysis"]["triage_level"]
                    == plan["triage_level"]
                ]

            if plan.get("signal_type"):

                filtered = [
                    review for review in filtered
                    if plan["signal_type"]
                    in review["engineering_analysis"]["signal_types"]
                ]

            if plan.get("platform"):

                filtered = [
                    review for review in filtered
                    if str(review["platform"] or "").lower()
                    == plan["platform"]
                ]

            if plan.get("rating") is not None:

                filtered = [
                    review for review in filtered
                    if review["rating"] == plan["rating"]
                ]

            if plan.get("app_version"):

                filtered = [
                    review for review in filtered
                    if (
                        plan["app_version"].lower()
                        in str(review["app_version"] or "").lower()
                    )
                ]

            limit = plan["limit"]

            returned_reviews = filtered[:limit]

            # Calculate sample statistics in Python.

            triage_summary = Counter(
                review["engineering_analysis"]["triage_level"]
                for review in returned_reviews
            )

            rating_summary = Counter(
                str(review["rating"])
                if review["rating"] is not None
                else "Unknown"
                for review in returned_reviews
            )

            platform_summary = Counter(
                str(review["platform"] or "Unknown")
                for review in returned_reviews
            )

            app_version_summary = Counter(
                str(review["app_version"] or "Unknown / Missing")
                for review in returned_reviews
            )

            signal_summary = Counter(
                signal
                for review in returned_reviews
                for signal in set(
                    review["engineering_analysis"]["signal_types"]
                )
            )

            explicit_signal_count = sum(
                1 for review in returned_reviews
                if review["engineering_analysis"]["signal_types"]
            )

            classification_only_count = sum(
                1 for review in returned_reviews
                if (
                    not review["engineering_analysis"]["signal_types"]
                    and (
                        review["engineering_analysis"]["issue_match"]
                        or review["engineering_analysis"]["complaint_match"]
                    )
                )
            )

            evidence = {
                "task": "candidates",
                "total_matches": len(filtered),
                "returned_count": len(returned_reviews),
                "filters": plan,

                "sample_summary": {
                    "triage_distribution": dict(triage_summary),
                    "rating_distribution": dict(rating_summary),
                    "platform_distribution": dict(platform_summary),
                    "app_version_distribution": dict(app_version_summary),
                    "signal_distribution": dict(signal_summary),
                    "explicit_text_signal_candidates": explicit_signal_count,
                    "classification_only_candidates": classification_only_count
                },

                "reviews": returned_reviews,

                "disclaimer": (
                    "These are customer-reported technical symptoms "
                    "and classification-based candidates. They do not "
                    "establish confirmed software defects or root causes."
                )
            }

        return {
            **state,
            "evidence": evidence
        }

    except Exception as exc:

        return {
            **state,
            "evidence": {},
            "error": f"Evidence retrieval error: {str(exc)}"
        }


# ============================================================
# 8. RESPONSE GENERATION
# ============================================================

def generate_response(state):

    if state.get("error"):

        return {
            **state,
            "response": (
                "I could not complete the engineering analysis. "
                + state["error"]
            )
        }

    llm = get_llm()

    prompt = f"""
You are the Engineering Intelligence Agent of PayPal Sentinel.

Your job is to analyse customer-reported engineering symptoms
using the supplied evidence.

USER QUESTION:
{state["user_query"]}

QUERY PLAN:
{json.dumps(state["plan"], indent=2)}

DATABASE EVIDENCE:
{json.dumps(state["evidence"], indent=2, default=str)}

IMPORTANT INTERPRETATION RULES:

1. These records contain customer-reported symptoms.
   They are NOT independently verified software defects.

2. Triage levels are prioritisation heuristics.
   They are NOT confirmed technical severity.

3. A matched text pattern indicates a potential symptom,
   not proof that the software is defective.

4. Never invent counts, percentages, review text,
   technical explanations, root causes or customer details.

5. Preserve the distinction between:
   - App crashes
   - Freezing and unresponsiveness
   - Performance issues
   - Login and authentication
   - Payment and transfer failures
   - Notification issues
   - App updates and compatibility
   - UI and navigation

6. A review may contain multiple engineering signal types.
   Signal distribution percentages may overlap.

7. CLASSIFICATION-ONLY CANDIDATES:
   These reviews were selected through existing complaint or
   issue classification labels that are engineering-relevant.

   They may not contain explicit textual evidence of an
   engineering symptom.

   Do not describe them as explicit technical reports,
   verified engineering incidents, or confirmed defects.

   Clearly distinguish classification-only candidates
   from reviews with explicit text-signal matches.

8. Use only supplied evidence for conclusions.

9. For candidate investigations, use the supplied Python-calculated
   sample_summary as the authoritative source for counts,
   percentages and distributions.

   Do not estimate, recalculate or invent numerical values.

   Ensure all numerical statements in the narrative agree
   exactly with the supplied sample_summary.

10. The database rating field is authoritative. Never change
    or reinterpret it based on rating-related statements in review text.

11. Do not infer statistics about the full matching population
    from a limited sample. Clearly distinguish total matches
    from the returned sample.

12. RATING DISTRIBUTION ACCURACY:
    When presenting rating distributions for candidate reviews,
    reproduce the exact counts from sample_summary.

    Do not estimate rating counts from the review table or
    calculate them yourself.

    Ensure the narrative agrees with the actual returned sample.

    If rating statistics are unavailable, omit them.

13. When presenting individual reviews, preserve the original
    review text and database fields accurately. Do not paraphrase
    a customer's statement as an independently established fact.

14. RESPONSE FORMAT MUST FOLLOW THE TASK:

    If task = "overview":
    Present an overall summary, triage breakdown,
    engineering signal distribution, observations and limitations.

    If task = "distribution":
    Present the requested distribution, counts,
    percentages, observations and limitations.

    If task = "candidates":
    Present ONLY a candidate investigation table
    and a short evidence-based summary.

    For candidate queries, DO NOT include:
    - Overall engineering overview
    - General triage distribution
    - Separate signal distribution
    - Unrequested analytical sections

RESPONSE FORMAT:

For OVERVIEW:
- Total engineering candidates
- Triage-level breakdown
- Most frequently identified engineering signals
- Explicit text-signal versus classification-only distinction
- Key observations
- Limitations

For DISTRIBUTION:
- Selected dimension
- Counts and percentages
- Explain overlapping signal types where applicable
- Key observations

For CANDIDATES:
- Total matching reviews
- Returned sample size
- Triage level and identified signals
- Original review text
- Classification ID
- Rating and platform
- App version when available
- Distinguish explicit text signals from classification-only matches

Keep the response concise, structured and evidence-based.

Do not claim that PayPal has confirmed software defects
or engineering root causes based solely on these app reviews.
"""

    try:

        response = llm.invoke(prompt)

        return {
            **state,
            "response": response.content
        }

    except Exception as exc:

        return {
            **state,
            "response": "",
            "error": f"Response generation error: {str(exc)}"
        }


# ============================================================
# 9. BUILD LANGGRAPH AGENT
# ============================================================

def build_engineering_agent():

    graph = StateGraph(EngineeringAgentState)

    graph.add_node("interpret_query", interpret_query)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("interpret_query")

    graph.add_edge("interpret_query", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()


# ============================================================
# 10. PUBLIC FUNCTION
# ============================================================

def ask_engineering_agent(question):

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please provide a valid question.")

    agent = build_engineering_agent()

    initial_state = {
        "user_query": question,
        "plan": {},
        "evidence": {},
        "response": "",
        "error": ""
    }

    result = agent.invoke(initial_state)

    return {
        "question": question,
        "plan": result.get("plan", {}),
        "evidence": result.get("evidence", {}),
        "answer": result.get("response", ""),
        "error": result.get("error", "")
    }