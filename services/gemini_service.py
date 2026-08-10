import os
from google import genai
from config import GEMINI_API_KEY


class GeminiService:
    _client = None

    @classmethod
    def client(cls, api_key: str = None):
        key = api_key or os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY is not set. Please provide a valid Gemini API key in your .env or sidebar.")

        if cls._client is None or api_key is not None:
            cls._client = genai.Client(api_key=key)

        return cls._client