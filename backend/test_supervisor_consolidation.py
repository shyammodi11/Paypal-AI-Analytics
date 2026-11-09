
from backend.agents.supervisor_agent import (
    route_question,
    build_agent_questions,
    execute_selected_agents,
    consolidate_responses
)


def test_supervisor_consolidation():

    question = (
        "Compare customer-reported fraud "
        "and engineering issues."
    )

    print("\n" + "=" * 80)
    print("USER QUESTION:", question)

    # 1. Routing
    routing = route_question(question)
    selected_agents = routing["agents"]

    print("\nSELECTED AGENTS:", selected_agents)

    # 2. Task decomposition
    agent_questions = build_agent_questions(
        question,
        selected_agents
    )

    # 3. Specialist execution
    results = execute_selected_agents(agent_questions)

    # 4. Response consolidation
    final_result = consolidate_responses(
        question,
        results
    )

    print("\n" + "=" * 80)
    print("PAYPAL SENTINEL - CONSOLIDATED RESPONSE")
    print("=" * 80)

    print(final_result.get("answer", final_result.get("error")))

    # Validation
    assert final_result["status"] == "success"

    assert set(final_result["successful_agents"]) == set(
        selected_agents
    )


if __name__ == "__main__":
    test_supervisor_consolidation()
