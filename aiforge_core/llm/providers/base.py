"""Provider protocol. A provider turns a prompt into a raw JSON string."""

from typing import Protocol, runtime_checkable


class ProviderError(Exception):
    """Raised by a provider on any failure (network, quota, refusal)."""


class ProviderTimeout(ProviderError):
    """Raised when a provider does not answer within its timeout."""


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str, json_schema: dict) -> str:
        """Return the model's raw text, expected to be a JSON document
        matching json_schema. Raise ProviderError / ProviderTimeout on failure."""
        ...
