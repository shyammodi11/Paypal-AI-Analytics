
from backend.agents.supervisor_agent import (
    route_question,
    build_agent_questions
)


def test_task_decomposition():

    test_questions = [
        "Compare customer-reported fraud and engineering issues.",

        "What are the most common customer complaints on PayPal?",

        "Find customer complaints about refunds and unauthorized transactions."
    ]

    for question in test_questions:

        print("\n" + "=" * 80)
        print("USER QUESTION:", question)

        # Step 1: Select specialist agents
        routing = route_question(question)

        selected_agents = routing["agents"]

        print("\nSELECTED AGENTS:", selected_agents)

        # Step 2: Generate individual agent tasks
        agent_questions = build_agent_questions(
            question,
            selected_agents
        )

        print("\nASSIGNED QUESTIONS:")

        for agent, assigned_question in agent_questions.items():

            print(f"\n{agent.upper()} AGENT:")
            print(assigned_question)

        # Validate decomposition
        assert set(agent_questions.keys()) == set(selected_agents)

        for assigned_question in agent_questions.values():
            assert isinstance(assigned_question, str)
            assert assigned_question.strip()


if __name__ == "__main__":
    test_task_decomposition()
