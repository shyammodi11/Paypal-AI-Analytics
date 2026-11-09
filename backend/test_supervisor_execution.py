
from backend.agents.supervisor_agent import (
    route_question,
    build_agent_questions,
    execute_selected_agents
)


def test_supervisor_execution():

    question = (
        "Compare customer-reported fraud "
        "and engineering issues."
    )

    print("\n" + "=" * 80)
    print("USER QUESTION:", question)

    # Stage 1: Routing
    routing = route_question(question)

    selected_agents = routing["agents"]

    print("\nSELECTED AGENTS:", selected_agents)

    # Stage 2: Task decomposition
    agent_questions = build_agent_questions(
        question,
        selected_agents
    )

    # Stage 3: Specialist execution
    results = execute_selected_agents(agent_questions)

    # Stage 4: Display results
    for agent_name, result in results.items():

        print("\n" + "=" * 80)
        print(f"{agent_name.upper()} AGENT RESULT")
        print("=" * 80)

        if result["status"] == "success":

            response = result["response"]

            print(response.get("answer", response))

        else:
            print("ERROR:", result["error"])

    # Basic validation
    assert set(results.keys()) == set(selected_agents)

    assert all(
        result["status"] == "success"
        for result in results.values()
    )


if __name__ == "__main__":
    test_supervisor_execution()
