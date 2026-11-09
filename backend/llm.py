from langchain_groq import ChatGroq

from backend.config import GROQ_API_KEY, GROQ_MODEL


def get_llm():
    """
    Returns a configured Groq chat model.
    Shared across all PayPal Sentinel agents.
    """

    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not found. "
            "Please configure it in the project-root .env file."
        )

    return ChatGroq(
        model=GROQ_MODEL,
        temperature=0
    )