"""Load configuration without printing credentials."""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


def create_client() -> OpenAI:
    # Reload the project file so replacing an expired key works without a
    # Streamlit process restart. This local app explicitly uses root .env.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise ValueError("Missing OPENAI_API_KEY: fill in .env at the repository root")
    return OpenAI(base_url="https://api.openai.com/v1", timeout=60.0, max_retries=2)
