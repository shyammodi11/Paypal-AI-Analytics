
from backend.agents.fraud_agent import ask_fraud_agent


def run_test(question):

    print("\n" + "=" * 75)
    print("QUESTION:", question)
    print("=" * 75)

    result = ask_fraud_agent(question)

    print("\nQUERY PLAN:")
    print(result["plan"])

    print("\nEVIDENCE SUMMARY:")

    evidence = result["evidence"]

    if "total_candidates" in evidence:
        print("Total candidates:", evidence["total_candidates"])

    if "total_matches" in evidence:
        print("Total matches:", evidence["total_matches"])

    if "triage_summary" in evidence:
        print("Triage summary:", evidence["triage_summary"])

    if "distribution" in evidence:
        print("Distribution:")
        for item in evidence["distribution"]:
            print(item)

    if "reviews" in evidence:
        for review in evidence["reviews"]:
            print({
                "classification_id": review["classification_id"],
                "rating": review["rating"],
                "platform": review["platform"],
                "fraud_analysis": review["fraud_analysis"]
            })

    print("\nAGENT RESPONSE:")
    print(result["answer"])

    if result["error"]:
        print("\nERROR:", result["error"])


if __name__ == "__main__":

    run_test(
        "Give me an overview of potential fraud-related "
        "customer reports on PayPal."
    )

    run_test(
        "What are the most common fraud and security signals?"
    )

    run_test(
        "Show me high-priority reviews reporting unauthorized "
        "transactions."
    )
