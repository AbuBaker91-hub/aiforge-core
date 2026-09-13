"""Router: ordered providers, timeout, retry, fallback, generate_json().

generate_json renders a versioned prompt, asks provider 1, on timeout or error
asks provider 2 (and so on), then parses the JSON into the given Pydantic
schema. If parsing or validation fails it raises ValidationFailed — it never
returns half data.
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .prompts import PromptLibrary
from .providers.base import LLMProvider, ProviderError, ProviderTimeout

M = TypeVar("M", bound=BaseModel)

DEFAULT_TIMEOUT_S = 20.0


class ValidationFailed(Exception):
    """The model's output could not be parsed/validated into the schema."""

    def __init__(self, message: str, raw: str = "", provider: str = ""):
        super().__init__(message)
        self.raw = raw
        self.provider = provider


class AllProvidersFailed(Exception):
    """Every provider in the chain raised an error or timed out."""


@dataclass
class LLMResult:
    data: BaseModel
    provider: str
    prompt_version: str
    latency_ms: int


def _strip_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return m.group(1) if m else text


class Router:
    def __init__(
        self,
        providers: list[LLMProvider],
        prompts_dir: str | Path,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        retries_per_provider: int = 1,
    ):
        if not providers:
            raise ValueError("Router needs at least one provider")
        self.providers = providers
        self.prompts = PromptLibrary(prompts_dir)
        self.timeout_s = timeout_s
        self.retries_per_provider = retries_per_provider

    def generate_json(self, prompt_name: str, variables: dict, schema: type[M]) -> LLMResult:
        prompt, prompt_version = self.prompts.render(prompt_name, variables)
        json_schema = schema.model_json_schema()
        # lets MockProvider key canned answers by prompt name; real providers ignore it
        json_schema["x-prompt-name"] = prompt_name

        start = time.monotonic()
        raw, provider_name = self._complete_with_fallback(prompt, json_schema)
        latency_ms = int((time.monotonic() - start) * 1000)

        try:
            data = schema.model_validate(json.loads(_strip_fences(raw)))
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValidationFailed(
                f"{provider_name} returned output that does not match {schema.__name__}: {e}",
                raw=raw,
                provider=provider_name,
            ) from e
        return LLMResult(
            data=data, provider=provider_name, prompt_version=prompt_version, latency_ms=latency_ms
        )

    def _complete_with_fallback(self, prompt: str, json_schema: dict) -> tuple[str, str]:
        errors: list[str] = []
        for provider in self.providers:
            for _attempt in range(self.retries_per_provider):
                try:
                    raw = self._complete_with_timeout(provider, prompt, json_schema)
                    return raw, provider.name
                except (ProviderError, ProviderTimeout, FutureTimeout) as e:
                    errors.append(f"{provider.name}: {type(e).__name__}: {e}")
        raise AllProvidersFailed("; ".join(errors))

    def _complete_with_timeout(self, provider: LLMProvider, prompt: str, json_schema: dict) -> str:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(provider.complete, prompt, json_schema)
            try:
                return future.result(timeout=self.timeout_s)
            except FutureTimeout:
                future.cancel()
                raise ProviderTimeout(
                    f"{provider.name} exceeded {self.timeout_s}s"
                ) from None


def router_from_env(prompts_dir: str | Path) -> Router:
    """Build a Router from LLM_PROVIDER_ORDER / GEMINI_API_KEY / GROQ_API_KEY."""
    from .providers.gemini import GeminiProvider
    from .providers.groq import GroqProvider

    order = [p.strip() for p in os.getenv("LLM_PROVIDER_ORDER", "gemini,groq").split(",") if p.strip()]
    providers: list[LLMProvider] = []
    for name in order:
        if name == "gemini" and os.getenv("GEMINI_API_KEY"):
            providers.append(GeminiProvider())
        elif name == "groq" and os.getenv("GROQ_API_KEY"):
            providers.append(GroqProvider())
    if not providers:
        raise RuntimeError(
            "No LLM provider configured. Set GEMINI_API_KEY (and/or GROQ_API_KEY) "
            "and LLM_PROVIDER_ORDER, see .env.example."
        )
    return Router(providers, prompts_dir)
