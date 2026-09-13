"""Groq llama-3.3-70b provider (free tier), JSON mode on."""

import json
import os

from .base import ProviderError


class GroqProvider:
    name = "groq"

    def __init__(self, model: str = "llama-3.3-70b-versatile", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")

    def complete(self, prompt: str, json_schema: dict) -> str:
        try:
            from groq import Groq
        except ImportError as e:
            raise ProviderError("groq is not installed") from e
        if not self.api_key:
            raise ProviderError("GROQ_API_KEY is not set")
        try:
            client = Groq(api_key=self.api_key)
            schema = {k: v for k, v in json_schema.items() if not k.startswith("x-")}
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Answer with a single JSON object matching this JSON Schema, "
                            "no prose:\n" + json.dumps(schema)
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
            if not content:
                raise ProviderError("groq returned an empty response")
            return content
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"groq call failed: {e}") from e
