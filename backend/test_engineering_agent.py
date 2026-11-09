
from backend.agents.engineering_agent import ask_engineering_agent


def run_test(test_name, question):
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)
    print(f"QUESTION: {question}")

    try:
        result = ask_engineering_agent(question)

        print("\nQUERY PLAN:")
        print(result.get("plan"))

        print("\nEVIDENCE SUMMARY:")
        evidence = result.get("evidence", {})
        print("Task:", evidence.get("task"))
        print("Total candidates:", evidence.get("total_candidates"))
        print("Total matches:", evidence.get("total_matches"))
        print("Returned:", evidence.get("returned_count"))
        print("Triage summary:", evidence.get("triage_summary"))
        print("Signal summary:", evidence.get("signal_summary"))

        print("\nAGENT RESPONSE:")
        print(result.get("answer"))

        if result.get("error"):
            print("\nAGENT ERROR:")
            print(result["error"])

    except Exception as e:
        print("\nTEST FAILED:")
        print(type(e).__name__, str(e))


if __name__ == "__main__":

    # # TEST 1: Overall engineering intelligence
    # run_test(
    #     "Engineering Overview",
    #     "Give me an overview of engineering-related customer reports on PayPal."
    # )

    # # TEST 2: Most common engineering issues
    # run_test(
    #     "Engineering Issue Distribution",
    #     "What are the most common engineering issues reported by customers?"
    # )

    # TEST 3: High-priority app crash reports
    run_test(
        "High-Priority App Crash Reports",
        "Show me high-priority customer reviews reporting app crashes."
    )
