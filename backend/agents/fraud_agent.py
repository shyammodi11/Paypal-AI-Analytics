
import json
from collections import Counter
from typing import TypedDict

from langgraph.graph import StateGraph, END

from backend.llm import get_llm
from backend.tools.fraud_detection import (
    find_fraud_candidates,
    FRAUD_SIGNAL_RULES
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

VALID_SIGNAL_TYPES = set(FRAUD_SIGNAL_RULES.keys())


# ============================================================
# 2. AGENT STATE
# ============================================================

class FraudAgentState(TypedDict):
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
# 4. HELPER: RETRIEVE ALL FRAUD CANDIDATES
# ============================================================

def get_all_fraud_candidates():

    all_candidates = []

    limit = 200
    offset = 0

    while True:

        result = find_fraud_candidates(
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
Fraud Intelligence Agent.

Convert the user's question into a JSON query plan.

USER QUESTION:
{state["user_query"]}

Available tasks:
- overview
- distribution
- candidates

Available dimensions:
{list(VALID_DIMENSIONS)}

Available signal types:
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

1. Use overview for general fraud intelligence questions.
2. Use distribution for questions asking about:
   counts, proportions, rankings, most common signals,
   or breakdowns.
3. Use candidates when the user wants to inspect individual
   reviews or find specific fraud-related reports.
4. Choose the most relevant dimension for distribution.
5. Use exact signal type names from the supplied list.
6. Use exact triage levels from the supplied list.
7. Do not invent filters.
8. Default limit is 10.
9. Maximum limit is 50.
10. If the question is ambiguous, choose the most reasonable
    interpretation.
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

        # if plan.get("platform") not in ["Android", "iOS"]:
        #     plan["platform"] = None

        platform = plan.get("platform")

        if isinstance(platform, str):
            platform = platform.strip().lower()

        if platform not in ["android", "ios"]:
            platform = None

        plan["platform"] = platform

        rating = plan.get("rating")

        if rating not in [1, 2, 3, 4, 5]:
            plan["rating"] = None

        limit = plan.get("limit", 10)

        if not isinstance(limit, int) or not 1 <= limit <= 50:
            plan["limit"] = 10

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

        if dimension == "signal_type":

            signal_types = (
                review["fraud_analysis"]["signal_types"]
            )

            if not signal_types:
                signal_types = [
                    "Category match only (no text signal)"
                ]

            for signal in set(signal_types):
                counts[signal] += 1

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
            "contain multiple signals. Their percentages "
            "may therefore add up to more than 100%."
            if dimension == "signal_type"
            else "Percentages use all fraud candidates "
                 "as the denominator."
        )
    }


# ============================================================
# 7. EVIDENCE RETRIEVAL
# ============================================================

def retrieve_evidence(state):

    plan = state["plan"]

    try:

        candidates = get_all_fraud_candidates()

        # ----------------------------------------------------
        # OVERVIEW
        # ----------------------------------------------------

        if plan["task"] == "overview":

            triage_counts = Counter(
                review["fraud_analysis"]["triage_level"]
                for review in candidates
            )

            signal_distribution = build_distribution(
                candidates,
                "signal_type"
            )

            evidence = {
                "task": "overview",
                "total_candidates": len(candidates),
                "triage_summary": dict(triage_counts),
                "signal_distribution": signal_distribution,
                "disclaimer": (
                    "These are customer-reported potential "
                    "fraud/security signals, not verified fraud."
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

        
        # ----------------------------------------------------
        # CANDIDATE INVESTIGATION
        # ----------------------------------------------------

        else:

            filtered = candidates

            if plan.get("triage_level"):

                filtered = [
                    review for review in filtered
                    if review["fraud_analysis"]["triage_level"]
                    == plan["triage_level"]
                ]

            if plan.get("signal_type"):

                filtered = [
                    review for review in filtered
                    if plan["signal_type"]
                    in review["fraud_analysis"]["signal_types"]
                ]

            if plan.get("platform"):

                filtered = [
                    review for review in filtered
                    if str(review["platform"] or "").lower()
                    == plan["platform"]
                ]

            if plan.get("rating"):

                filtered = [
                    review for review in filtered
                    if review["rating"] == plan["rating"]
                ]

            if plan.get("app_version"):

                filtered = [
                    review for review in filtered
                    if review["app_version"] == plan["app_version"]
                ]

            limit = plan["limit"]

            returned_reviews = filtered[:limit]

            # Calculate sample statistics in Python.

            triage_summary = Counter(
                review["fraud_analysis"]["triage_level"]
                for review in returned_reviews
            )

            rating_summary = Counter(
                str(review["rating"])
                for review in returned_reviews
            )

            platform_summary = Counter(
                str(review["platform"])
                for review in returned_reviews
            )

            app_version_summary = Counter(
                str(review["app_version"] or "Unknown")
                for review in returned_reviews
            )

            signal_summary = Counter(
                signal
                for review in returned_reviews
                for signal in set(
                    review["fraud_analysis"]["signal_types"]
                )
            )

            category_only_count = sum(
                1
                for review in returned_reviews
                if (
                    review["fraud_analysis"]["category_match"]
                    and not review["fraud_analysis"]["signal_types"]
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
                    "category_only_matches": category_only_count
                },

                "reviews": returned_reviews,

                "disclaimer": (
                    "These are customer-reported potential "
                    "fraud/security signals, not verified fraud."
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
                "I could not complete the fraud analysis. "
                + state["error"]
            )
        }

    llm = get_llm()

    prompt = f"""
You are the Fraud Intelligence Agent of PayPal Sentinel.

Your job is to analyse customer-reported fraud and security
signals using the supplied evidence.

USER QUESTION:
{state["user_query"]}

QUERY PLAN:
{json.dumps(state["plan"], indent=2)}

DATABASE EVIDENCE:
{json.dumps(state["evidence"], indent=2, default=str)}

IMPORTANT INTERPRETATION RULES:

1. These records contain customer-reported claims.
   They are NOT independently verified fraud events.

2. Triage levels are prioritisation heuristics.
   They are NOT fraud probabilities or confirmed severity.

3. A matched text pattern indicates a potential signal,
   not proof that the reported event occurred.

4. Never invent counts, percentages, review text,
   technical explanations or customer details.

5. Preserve the distinction between:
   - Unauthorized transactions
   - Account compromise
   - Phishing and impersonation
   - Identity or payment compromise
   - Suspicious activity

6. A review may contain multiple fraud signal types.
   Signal distribution percentages may overlap.

7. Category-only candidates may have no matching text
   pattern. Do not describe them as explicit fraud reports.

8. Use only supplied evidence for conclusions.

9. For candidate investigations, use the supplied Python-calculated
   sample_summary for counts and distributions.

10. The database rating field is authoritative. Never change or
    reinterpret it based on rating-related statements in review text.

11. Do not infer statistics about the full matching population
    from a limited sample. Clearly distinguish total matches
    from the returned sample.

12. RESPONSE FORMAT MUST FOLLOW THE TASK:
    If task = "overview":
    Present an overall summary, triage breakdown,
    signal distribution, observations and limitations.

    If task = "distribution":
    Present the requested distribution, counts,
    percentages, observations and limitations.

    If task = "candidates":
    Present ONLY a candidate investigation table
    and a short evidence-based summary.

    For candidate queries, DO NOT include:
    - Overall fraud overview
    - General triage distribution
    - Separate signal distribution
    - Unrequested analytical sections

13. When presenting individual reviews, preserve the original
    review text and database fields accurately. Do not paraphrase
    a customer's statement as an independently established fact.

RESPONSE FORMAT:

For OVERVIEW:
- Total potential candidates
- Triage-level breakdown
- Most frequently identified signals
- Key observations
- Limitations

For DISTRIBUTION:
- Selected dimension
- Counts and percentages
- Explain overlapping signal types where applicable
- Key observations

For CANDIDATES:
- Total matching reviews
- Triage level and identified signals
- Original review text
- Classification ID
- Rating and platform
- App version when available

Keep the response concise, structured and evidence-based.

Do not claim that PayPal has experienced verified fraud
based solely on these app reviews.
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

def build_fraud_agent():

    graph = StateGraph(FraudAgentState)

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

def ask_fraud_agent(question):

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please provide a valid question.")

    agent = build_fraud_agent()

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
