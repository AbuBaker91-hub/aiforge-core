"""Gemini 2.5 Flash provider (free tier), JSON mode on."""

import os

from .base import ProviderError


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def complete(self, prompt: str, json_schema: dict) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ProviderError("google-genai is not installed") from e
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY is not set")
        try:
            client = genai.Client(api_key=self.api_key)
            schema = {k: v for k, v in json_schema.items() if not k.startswith("x-")}
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=schema,
                ),
            )
            if not response.text:
                raise ProviderError("gemini returned an empty response")
            return response.text
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"gemini call failed: {e}") from e
