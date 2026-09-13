"""MockProvider: canned responses keyed by prompt name, for tests only."""

import json

from .base import ProviderError


class MockProvider:
    """Returns canned responses by prompt name.

    responses maps a prompt name to one of:
      - a dict (serialized to JSON)
      - a raw string (returned as-is, useful for broken-JSON tests)
      - a list of the above (consumed one per call, last repeats)
      - an Exception instance (raised, useful for timeout/fallback tests)
    """

    name = "mock"

    def __init__(self, responses: dict | None = None):
        self.responses = dict(responses or {})
        self.calls: list[dict] = []
        self._cursors: dict[str, int] = {}

    def set(self, prompt_name: str, response) -> None:
        self.responses[prompt_name] = response

    def complete(self, prompt: str, json_schema: dict) -> str:
        prompt_name = json_schema.get("x-prompt-name", "")
        self.calls.append({"prompt_name": prompt_name, "prompt": prompt})
        if prompt_name not in self.responses:
            raise ProviderError(f"MockProvider has no canned response for {prompt_name!r}")
        canned = self.responses[prompt_name]
        if isinstance(canned, list):
            i = self._cursors.get(prompt_name, 0)
            canned_item = canned[min(i, len(canned) - 1)]
            self._cursors[prompt_name] = i + 1
            canned = canned_item
        if isinstance(canned, Exception):
            raise canned
        if isinstance(canned, str):
            return canned
        return json.dumps(canned)
