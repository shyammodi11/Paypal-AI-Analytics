
import json
from backend.agents.complaint_agent import ask_complaint_agent
from backend.agents.fraud_agent import ask_fraud_agent
from backend.agents.engineering_agent import ask_engineering_agent

from backend.llm import get_llm


VALID_AGENTS = {
    "complaint",
    "fraud",
    "engineering"
}


def parse_json_response(content):

    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            if isinstance(item, dict)
            else str(item)
            for item in content
        )

    content = str(content).strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()

    return json.loads(content)


def route_question(question: str):

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please provide a valid question.")

    llm = get_llm()

    prompt = f"""
You are the Supervisor Agent of PayPal Sentinel.

Your responsibility is to understand the user's question
and select the appropriate specialist agents.

AVAILABLE SPECIALIST AGENTS:

1. complaint
   Handles:
   - Customer complaint analysis
   - Complaint categories
   - Issue nature
   - Customer support issues
   - Refunds, payments, account restrictions
   - Complaint trends and distributions

2. fraud
   Handles:
   - Customer-reported fraud
   - Unauthorized transactions
   - Account compromise
   - Phishing and impersonation
   - Suspicious activity
   - Fraud signal trends and candidate investigations

3. engineering
   Handles:
   - App crashes
   - Freezing and unresponsiveness
   - Performance issues
   - Login and authentication failures
   - Payment and transfer failures
   - Notifications
   - App updates and compatibility
   - UI and navigation problems

USER QUESTION:
{question}

ROUTING RULES:

1. Select only the specialist agents needed to answer the question.

2. Select multiple agents when the question requires
   information from multiple domains.

3. FRAUD-RELATED QUESTIONS:

   Route to fraud when the question mentions:
   - Unauthorized transactions
   - Transactions the customer did not make
   - Account compromise or hacked accounts
   - Phishing or impersonation
   - Suspicious account activity
   - Suspected fraudulent payments
   - Fraud detection or fraud trends

   This rule applies even when the user uses words such as
   "complaints", "reviews", or "customer reports".

   Do not route fraud-specific questions to complaint
   merely because they concern customer reviews.

4. If the question explicitly compares fraud and engineering
   issues, select both fraud and engineering.

5. If the user asks for an overall analysis of customer
   complaints, select complaint.

6. If the question is broad and genuinely requires all three
   perspectives, select all three agents.

7. Do not select every agent unnecessarily.

8. Never answer the user's question yourself.
   Your task is routing only.

RETURN STRICT JSON ONLY:

{{
    "agents": ["complaint"],
    "reason": "Brief explanation of why these agents were selected."
}}

The agents array may contain one or more of:
complaint, fraud, engineering.

Do not include Markdown or additional text.
"""

    response = llm.invoke(prompt)

    result = parse_json_response(response.content)

    agents = result.get("agents", [])

    if not isinstance(agents, list):
        raise ValueError("Invalid routing format: agents must be a list.")

    agents = list(dict.fromkeys(
        agent.strip().lower()
        for agent in agents
        if isinstance(agent, str)
    ))

    if not agents or not set(agents).issubset(VALID_AGENTS):
        raise ValueError(
            f"Invalid agent selection returned by LLM: {agents}"
        )

    return {
        "agents": agents,
        "reason": result.get("reason", "")
    }


def build_agent_questions(question: str, selected_agents: list):

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please provide a valid question.")

    if not selected_agents:
        raise ValueError("At least one specialist agent must be selected.")

    allowed_agents = {"complaint", "fraud", "engineering"}

    if not set(selected_agents).issubset(allowed_agents):
        raise ValueError("Invalid specialist agent selected.")

    llm = get_llm()

   
    prompt = f"""
    You are the task decomposition component of PayPal Sentinel.

    Convert the user's question into a concise, actionable
    analytical question for each selected specialist agent.

    USER QUESTION:
    {question}

    SELECTED AGENTS:
    {json.dumps(selected_agents)}

    SPECIALIST RESPONSIBILITIES:

    1. complaint:
    Customer complaint categories, issue nature, refunds,
    payments, account restrictions and complaint trends.

    2. fraud:
    Customer-reported fraud signals, unauthorized transactions,
    account compromise, phishing, impersonation and suspicious activity.

    3. engineering:
    Customer-reported engineering symptoms, app crashes,
    freezing, performance, login failures, payment failures,
    notifications and compatibility.

    TASK ASSIGNMENT RULES:

    1. If fraud is selected:
    - For a fraud analysis or comparison, request the distribution
        of fraud signal types.
    - Distinguish explicit text signals from category-only matches.
    - Do not default to complaint-category distribution.

    2. If engineering is selected:
    - For an engineering analysis or comparison, request the
        distribution of engineering signal types.
    - Distinguish explicit text signals from classification-only matches.
    - Do not default to complaint-category distribution.

    3. If complaint is selected:
    - For general complaint analysis, request complaint-category
        distribution and relevant issue patterns.
    - For specific complaint topics, focus on those topics.

    4. For comparison questions:
    - Assign each specialist the corresponding part of the comparison.
    - Use comparable analytical dimensions where possible.

    5. Do not request unsupported information:
    - No actual transaction details or verified fraud incidents.
    - No backend root causes or confirmed software defects.
    - No recent trends unless the available agent functionality
        explicitly supports temporal trend analysis.

    6. Refer to reviews, candidates, reported signals or symptoms,
    not verified incidents.

    7. Do not add unrelated metrics or investigations.
    Keep every assigned question concise.

    RETURN STRICT JSON ONLY:

    {{
        "agent_questions": {{
            "fraud": "Analyse the distribution of fraud signal types."
        }}
    }}

    Include only selected agents as keys.
    Do not answer the user's question.
    Do not include Markdown or additional text.
    """


    response = llm.invoke(prompt)

    result = parse_json_response(response.content)

    agent_questions = result.get("agent_questions", {})

    if not isinstance(agent_questions, dict):
        raise ValueError("Invalid agent_questions format.")

    if set(agent_questions.keys()) != set(selected_agents):
        raise ValueError(
            "The decomposed questions do not match the selected agents."
        )

    for agent, agent_question in agent_questions.items():

        if not isinstance(agent_question, str) or not agent_question.strip():
            raise ValueError(
                f"Invalid task question generated for {agent}."
            )

    return agent_questions




def execute_selected_agents(agent_questions: dict):

    if not isinstance(agent_questions, dict) or not agent_questions:
        raise ValueError("No agent questions provided.")

    agent_functions = {
        "complaint": ask_complaint_agent,
        "fraud": ask_fraud_agent,
        "engineering": ask_engineering_agent
    }

    results = {}

    for agent_name, assigned_question in agent_questions.items():

        if agent_name not in agent_functions:
            raise ValueError(
                f"Unknown specialist agent: {agent_name}"
            )

        if not isinstance(assigned_question, str) or not assigned_question.strip():
            raise ValueError(
                f"Invalid assigned question for {agent_name}."
            )

        try:
            print(f"\nExecuting {agent_name.upper()} Agent...")
            print("ASSIGNED TASK:", assigned_question)
        except UnicodeEncodeError:
            print(f"\nExecuting {agent_name.upper()} Agent...")
            print("ASSIGNED TASK:", assigned_question.encode("ascii", errors="replace").decode("ascii"))

        try:
            response = agent_functions[agent_name](assigned_question)

            results[agent_name] = {
                "status": "success",
                "assigned_question": assigned_question,
                "response": response
            }

        except Exception as exc:

            results[agent_name] = {
                "status": "failed",
                "assigned_question": assigned_question,
                "error": str(exc)
            }

            try:
                print(f"{agent_name.upper()} Agent failed: {exc}")
            except UnicodeEncodeError:
                print(f"{agent_name.upper()} Agent failed: {str(exc).encode('ascii', errors='replace').decode('ascii')}")

    return results


def consolidate_responses(question: str, results: dict):

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please provide a valid question.")

    if not results:
        raise ValueError("No specialist results available.")

    successful_results = {}
    failed_agents = []

    for agent_name, result in results.items():

        if result.get("status") == "success":

            response = result.get("response", {})

            successful_results[agent_name] = {
                "assigned_question": result.get("assigned_question"),
                "answer": response.get("answer", str(response))
            }

        else:
            failed_agents.append({
                "agent": agent_name,
                "error": result.get("error", "Unknown error")
            })

    if not successful_results:
        return {
            "status": "failed",
            "answer": "None of the selected specialist agents returned a successful result.",
            "failed_agents": failed_agents
        }

    llm = get_llm()

    prompt = f"""
You are the Response Consolidation component of PayPal Sentinel.

Your task is to combine specialist agent findings into one
clear and useful response to the user's original question.

USER QUESTION:
{question}

SPECIALIST FINDINGS:
{json.dumps(successful_results, indent=2, ensure_ascii=False)}

FAILED AGENTS:
{json.dumps(failed_agents, indent=2, ensure_ascii=False)}

INSTRUCTIONS:

1. Answer the original user question directly.

2. Combine relevant findings from all successful agents.

3. Preserve important counts, percentages and denominators
   exactly as reported by the specialists.

4. Highlight meaningful similarities and differences.

5. Do not add metrics, calculations or conclusions that are
   not supported by the specialist findings.

6. If agents use different candidate populations or denominators,
   explicitly explain that their figures are not directly comparable.

7. Distinguish customer-reported claims and symptoms from
   independently verified fraud incidents or technical defects.

8. Do not interpret classification-only matches as explicit
   text reports.

9. Mention failed agents and explain how their absence limits
   the answer, where relevant.

10. Avoid repeating the same limitations unnecessarily.

11. Keep the response concise, structured and readable.
    Use Markdown headings or tables only where useful.

12. Do not invent transaction details, technical root causes
    or temporal trends.

Return the consolidated answer only.
"""

    try:
        response = llm.invoke(prompt)

        return {
            "status": "success",
            "answer": response.content,
            "successful_agents": list(successful_results.keys()),
            "failed_agents": failed_agents
        }

    except Exception as exc:

        return {
            "status": "failed",
            "error": str(exc),
            "successful_agents": list(successful_results.keys()),
            "failed_agents": failed_agents
        }


if __name__ == "__main__":

    test_questions = [
        "What are the most common customer complaints on PayPal?",

        "Show me customer reviews reporting unauthorized transactions.",

        "Find high-priority app crash reports.",

        "Compare customer-reported fraud and engineering issues.",

        "Find customer complaints about refunds and unauthorized transactions."
    ]

    for question in test_questions:

        print("\n" + "=" * 75)
        print("QUESTION:", question)

        try:
            result = route_question(question)

            print("SELECTED AGENTS:", result["agents"])
            print("ROUTING REASON:", result["reason"])

        except Exception as exc:
            print("ROUTING ERROR:", str(exc))
