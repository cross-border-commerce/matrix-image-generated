import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY is not set")
    base_url = (
        os.environ.get("OPENAI_API_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("API_BASE_URL")
    )
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)
