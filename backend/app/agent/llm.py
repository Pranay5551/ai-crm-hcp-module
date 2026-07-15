import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma2-9b-it")
LLM_MODEL_FALLBACK = os.getenv("LLM_MODEL_FALLBACK", "llama-3.3-70b-versatile")


def get_llm(model: str = None, temperature: float = 0.2):
    """
    Returns a configured ChatGroq LLM instance.
    Defaults to gemma2-9b-it (fast, cheap — good for structured extraction).
    Falls back to llama-3.3-70b-versatile for more nuanced reasoning steps
    (e.g. next-best-action suggestions) if explicitly requested.
    """
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=model or LLM_MODEL,
        temperature=temperature,
    )
