"""One-time manual smoke test with a real free key.

    python -m aiforge_core.llm.smoke
    LLM_PROVIDER_ORDER=groq python -m aiforge_core.llm.smoke
"""

import tempfile
from pathlib import Path

from pydantic import BaseModel

from .router import router_from_env


class Capital(BaseModel):
    country: str
    capital: str


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "smoke.v1.md").write_text(
            "What is the capital of {{country}}? Answer as JSON with keys country and capital.",
            encoding="utf-8",
        )
        router = router_from_env(d)
        result = router.generate_json("smoke", {"country": "France"}, Capital)
        print(
            f"provider={result.provider} prompt={result.prompt_version} "
            f"latency={result.latency_ms}ms -> {result.data.model_dump_json()}"
        )


if __name__ == "__main__":
    main()
