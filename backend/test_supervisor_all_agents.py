
from backend.agents.supervisor_agent import (
    route_question,
    build_agent_questions,
    execute_selected_agents,
    consolidate_responses
)


def test_supervisor_all_agents():

    question = (
        "Give me an overall view of PayPal customer-reported problems, "
        "covering general complaints, fraud signals, and engineering issues."
    )

    print("\n" + "=" * 80)
    print("PAYPAL SENTINEL - ALL AGENTS INTEGRATION TEST")
    print("=" * 80)

    # STEP 1: Route the question
    routing = route_question(question)

    selected_agents = routing["agents"]

    print("\nSELECTED AGENTS:", selected_agents)
    print("ROUTING REASON:", routing.get("reason"))

    # All three agents should be selected
    expected_agents = {"complaint", "fraud", "engineering"}

    assert set(selected_agents) == expected_agents, (
        f"Expected all three agents, but got: {selected_agents}"
    )

    # STEP 2: Decompose the question
    agent_questions = build_agent_questions(
        question,
        selected_agents
    )

    print("\nASSIGNED QUESTIONS:")

    for agent, assigned_question in agent_questions.items():
        print(f"\n{agent.upper()}:")
        print(assigned_question)

    # STEP 3: Execute all selected agents
    results = execute_selected_agents(agent_questions)

    print("\nAGENT EXECUTION STATUS:")

    for agent, result in results.items():
        print(f"{agent.upper()}: {result['status']}")

    assert set(results.keys()) == expected_agents
    assert all(
        result["status"] == "success"
        for result in results.values()
    ), "One or more specialist agents failed."

    # STEP 4: Consolidate responses
    final_result = consolidate_responses(
        question,
        results
    )

    print("\n" + "=" * 80)
    print("PAYPAL SENTINEL - FINAL CONSOLIDATED RESPONSE")
    print("=" * 80)

    print(
        final_result.get(
            "answer",
            final_result.get("error")
        )
    )

    assert final_result["status"] == "success"
    assert set(final_result["successful_agents"]) == expected_agents

    print("\n" + "=" * 80)
    print("ALL THREE AGENTS INTEGRATION TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    test_supervisor_all_agents()
