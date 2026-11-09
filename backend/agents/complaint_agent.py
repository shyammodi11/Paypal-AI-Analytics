
import json
import re
from typing import TypedDict, Any

from langgraph.graph import StateGraph, END

from backend.llm import get_llm
from backend.tools.complaint_analytics import (
    get_distribution,
    get_complaint_overview,
    ALLOWED_DIMENSIONS
)
from backend.tools.review_search import search_review_evidence


# ============================================================
# 1. CONFIGURATION
# ============================================================

VALID_TASKS = {"overview", "distribution", "search"}

COMPLAINT_CATEGORIES = [
    "Customer Support",
    "App Performance",
    "Fraud & Security",
    "Payment Issues",
    "Fees & Charges",
    "Bank & Card Issues",
    "Account Restrictions",
    "Login & Verification",
    "Refund Issues",
    "Disputes",
    "Unknown / Insufficient information"
]

ISSUE_NATURES = [
    "Bug / Technical Defect",
    "Service / Support Issue",
    "Policy / Restriction Issue",
    "UX / Usability Issue",
    "Logical / Functional Issue",
    "Other Issue",
    "Fee / Commercial Issue",
    "Information / Communication Issue",
    "Feature Improvement",
    "Performance Issue",
    "Enhancement Request",
    "Unknown / Insufficient information"
]


# ============================================================
# 2. LANGGRAPH STATE
# ============================================================

class ComplaintAgentState(TypedDict, total=False):
    user_query: str
    plan: dict
    evidence: dict
    response: str
    error: str


# ============================================================
# 3. HELPER: PARSE MODEL JSON
# ============================================================

def parse_json_response(content):
    """
    Extract JSON from the LLM response.
    Handles responses with optional Markdown code fences.
    """

    if isinstance(content, list):
        content = " ".join(
            item.get("text", "") if isinstance(item, dict)
            else str(item)
            for item in content
        )

    content = str(content).strip()

    content = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        content,
        flags=re.IGNORECASE
    )

    return json.loads(content)


# ============================================================
# 4. NODE 1: INTERPRET USER QUERY
# ============================================================


def interpret_query(state: ComplaintAgentState):

    llm = get_llm()

    prompt = f"""
You are the Query Interpretation component of the
PayPal Sentinel Complaint Intelligence Agent.

Your task is to convert the user's question into a
structured JSON query plan.

USER QUESTION:
{state["user_query"]}

AVAILABLE TASKS:
- overview: General complaint overview and common patterns.
- distribution: Distribution of a particular dimension.
- search: Retrieve individual customer reviews.

AVAILABLE DIMENSIONS:
{json.dumps(sorted(ALLOWED_DIMENSIONS), indent=2)}

AVAILABLE COMPLAINT CATEGORIES:
{json.dumps(COMPLAINT_CATEGORIES, indent=2)}

AVAILABLE ISSUE NATURES:
{json.dumps(ISSUE_NATURES, indent=2)}

INTERPRETATION RULES:

1. Use overview for broad questions about complaints,
   common problems, and general patterns.

2. Use distribution when the user explicitly asks for
   category, issue nature, platform, rating, or other
   supported dimension distributions.

3. Use search when the user requests individual reviews,
   examples, or specific customer feedback.

4. Select only dimensions from the available dimensions.

5. Apply complaint_category and issue_nature filters
   only when the user explicitly specifies them.

6. Set unspecified filters to null.

7. Platform must be Android, iOS, or null.

8. Rating must be an integer from 1 to 5, or null.

9. Limit must be between 1 and 20.

10. Do not invent filters or assume information
    that the user has not requested.

OUTPUT REQUIREMENTS:

Return ONLY valid JSON.
Do not include Markdown code fences or explanations.

Use this exact structure:

{{
    "task": "overview",
    "dimension": "complaint_category",
    "keyword": null,
    "complaint_category": null,
    "issue_nature": null,
    "platform": null,
    "rating": null,
    "limit": 10
}}
"""

    try:

        result = llm.invoke(prompt)

        plan = parse_json_response(result.content)

        if not isinstance(plan, dict):
            raise ValueError("LLM did not return a valid JSON object.")

        # Validate task
        if plan.get("task") not in VALID_TASKS:
            plan["task"] = "overview"

        # Validate dimension
        if plan.get("dimension") not in ALLOWED_DIMENSIONS:
            plan["dimension"] = "complaint_category"

        # Validate category filters
        if plan.get("complaint_category") not in COMPLAINT_CATEGORIES:
            plan["complaint_category"] = None

        if plan.get("issue_nature") not in ISSUE_NATURES:
            plan["issue_nature"] = None

        # Validate platform
        if plan.get("platform") not in [None, "Android", "iOS"]:
            plan["platform"] = None

        # Validate rating
        try:
            rating = plan.get("rating")

            plan["rating"] = (
                int(rating) if rating is not None else None
            )

            if plan["rating"] not in [None, 1, 2, 3, 4, 5]:
                plan["rating"] = None

        except (ValueError, TypeError):
            plan["rating"] = None

        # Validate limit
        try:
            plan["limit"] = max(
                1,
                min(int(plan.get("limit", 10)), 20)
            )

        except (ValueError, TypeError):
            plan["limit"] = 10

        # Ensure all expected fields exist
        plan.setdefault("keyword", None)
        plan.setdefault("complaint_category", None)
        plan.setdefault("issue_nature", None)
        plan.setdefault("platform", None)
        plan.setdefault("rating", None)

        return {"plan": plan}

    except Exception as exc:

        return {
            "plan": {
                "task": "overview",
                "dimension": "complaint_category",
                "keyword": None,
                "complaint_category": None,
                "issue_nature": None,
                "platform": None,
                "rating": None,
                "limit": 10
            },
            "error": f"Query interpretation fallback: {str(exc)}"
        }


# ============================================================
# 5. NODE 2: RETRIEVE DATABASE EVIDENCE
# ============================================================

def retrieve_evidence(state: ComplaintAgentState):

    plan = state["plan"]

    try:

        if plan["task"] == "overview":

            evidence = get_complaint_overview(
                platform=plan.get("platform")
            )

        elif plan["task"] == "distribution":

            evidence = get_distribution(
                dimension=plan["dimension"],
                platform=plan.get("platform"),
                rating=plan.get("rating")
            )

        elif plan["task"] == "search":

            evidence = search_review_evidence(
                keyword=plan.get("keyword"),
                complaint_category=plan.get("complaint_category"),
                issue_nature=plan.get("issue_nature"),
                platform=plan.get("platform"),
                rating=plan.get("rating"),
                limit=plan["limit"]
            )

        else:
            raise ValueError("Unsupported complaint task.")

        return {"evidence": evidence}

    except Exception as exc:
        return {
            "evidence": {},
            "error": f"Evidence retrieval failed: {str(exc)}"
        }


# ============================================================
# 6. NODE 3: GENERATE EVIDENCE-BASED RESPONSE
# ============================================================

def generate_response(state: ComplaintAgentState):

    if state.get("error", "").startswith("Evidence retrieval failed"):
        return {
            "response": (
                "I could not retrieve the requested information "
                f"from the database. Details: {state['error']}"
            )
        }

    llm = get_llm()

    prompt = f"""
You are the Complaint Intelligence Agent of PayPal Sentinel.

Your job is to analyse customer complaints using the supplied
database evidence and answer the user's question.

USER QUESTION:
{state["user_query"]}

QUERY PLAN:
{json.dumps(state["plan"], indent=2)}

DATABASE EVIDENCE:
{json.dumps(state["evidence"], indent=2, default=str)}

STRICT RULES:

1. Use only the supplied database evidence for numerical claims.
2. Never invent review counts, percentages or customer statements.
3. Clearly distinguish database findings from your interpretation.
4. When showing reviews, preserve their original wording.
5. Include classification IDs when citing individual reviews.
6. Do not claim that customer-reported fraud is verified fraud.
7. Do not invent PayPal's internal policies or technical explanations.
8. Mention limitations when evidence is insufficient.
9. If classifications are Unknown / Insufficient information,
   retain that category rather than silently excluding it.
10. Give concise, useful recommendations where appropriate.
11. UNKNOWN CLASSIFICATIONS:
- Never rank "Unknown / Insufficient information"
  as an actual complaint category.
- Report it separately with its count and percentage.
- Rank only identified complaint categories.
- Do not assume Unknown reviews are vague or lack detail.

12. EVIDENCE LIMITATIONS:
- A category distribution provides category counts,
  not the underlying reasons or symptoms.
- Do not invent specific causes, customer experiences,
  or technical problems based only on category counts.
- Do not claim that support response times, resolution
  quality, crashes, or payment-flow failures are common
  unless the supplied evidence explicitly establishes this.
- If individual review text is unavailable, state that
  detailed issue patterns cannot be established.

13. RECOMMENDATIONS:
- Recommendations must be directly connected to
  observed evidence.
- Distinguish evidence-backed recommendations from
  possible areas for further investigation.
- Do not recommend specific technical or operational
  changes without supporting evidence.

For overview and distribution queries:
- Explain the leading categories.
- Include counts and percentages when available.
- Mention the total number of reviews analysed.

For evidence searches:
- State the number of matching reviews.
- Present the retrieved examples with their IDs, ratings,
  platforms and original text.
- Do not imply that the returned examples represent every match.

Use clear headings and readable Markdown.
"""

    try:
        result = llm.invoke(prompt)

        return {
            "response": result.content
        }

    except Exception as exc:
        return {
            "response": (
                "Evidence was retrieved successfully, but the "
                f"LLM response generation failed: {str(exc)}\n\n"
                f"Raw evidence:\n{json.dumps(state['evidence'], indent=2, default=str)}"
            )
        }


# ============================================================
# 7. BUILD LANGGRAPH WORKFLOW
# ============================================================

def build_complaint_agent():

    workflow = StateGraph(ComplaintAgentState)

    workflow.add_node(
        "interpret_query",
        interpret_query
    )

    workflow.add_node(
        "retrieve_evidence",
        retrieve_evidence
    )

    workflow.add_node(
        "generate_response",
        generate_response
    )

    workflow.set_entry_point("interpret_query")

    workflow.add_edge(
        "interpret_query",
        "retrieve_evidence"
    )

    workflow.add_edge(
        "retrieve_evidence",
        "generate_response"
    )

    workflow.add_edge(
        "generate_response",
        END
    )

    return workflow.compile()


# ============================================================
# 8. PUBLIC INTERFACE
# ============================================================

complaint_agent = build_complaint_agent()


def ask_complaint_agent(question: str):
    """
    Public interface for the Complaint Intelligence Agent.
    """

    if not question or not question.strip():
        raise ValueError("Please provide a valid question.")

    result = complaint_agent.invoke({
        "user_query": question.strip()
    })

    return {
        "question": question,
        "plan": result.get("plan", {}),
        "evidence": result.get("evidence", {}),
        "answer": result.get("response", ""),
        "error": result.get("error")
    }
