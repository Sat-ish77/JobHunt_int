"""
OpenAI embeddings using text-embedding-3-small (1536 dimensions).
Stores directly into Supabase pgvector column.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text: str) -> list:
    """
    Generate a 1536-dimension embedding for the given text.
    Truncates input to 8000 chars before sending to avoid token limits.
    Returns a plain Python list of floats.
    """
    try:
        truncated = text[:8000]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=truncated,
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[get_embedding] Error: {e}")
        raise

