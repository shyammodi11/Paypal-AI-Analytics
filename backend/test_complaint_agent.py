
from backend.agents.complaint_agent import ask_complaint_agent


def run_test(question):

    print("\n" + "=" * 75)
    print("QUESTION:", question)
    print("=" * 75)

    result = ask_complaint_agent(question)

    print("\nQUERY PLAN:")
    print(result["plan"])

    print("\nDATABASE EVIDENCE SUMMARY:")

    evidence = result["evidence"]

    if "total_reviews" in evidence:
        print("Total reviews:", evidence["total_reviews"])

    if "total_matches" in evidence:
        print("Matching reviews:", evidence["total_matches"])

    print("\nAGENT RESPONSE:")
    print(result["answer"])

    if result.get("error"):
        print("\nWARNING:", result["error"])


if __name__ == "__main__":

    run_test(
        "What are the most common customer complaints on PayPal?"
    )

    run_test(
        "Show me the distribution of complaints across Android."
    )

    run_test(
        "Find customer reviews mentioning refunds."
    )
