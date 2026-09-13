from pydantic import BaseModel
from pytest import raises

from aiforge_core.llm.providers.base import ProviderTimeout
from aiforge_core.llm.providers.mock import MockProvider
from aiforge_core.llm.router import AllProvidersFailed, Router, ValidationFailed


class Answer(BaseModel):
    value: int


def write_prompt(tmp_path, name="ask", version=1, text="Question: {{q}}"):
    d = tmp_path / "prompts"
    d.mkdir(exist_ok=True)
    (d / f"{name}.v{version}.md").write_text(text, encoding="utf-8")
    return str(d)


def test_fallback_to_second_provider(tmp_path):
    p1 = MockProvider({"ask": ProviderTimeout("slow")})
    p2 = MockProvider({"ask": {"value": 7}})
    p2.name = "mock2"
    router = Router([p1, p2], prompts_dir=write_prompt(tmp_path), timeout_s=5)
    result = router.generate_json("ask", {"q": "seven?"}, Answer)
    assert result.data.value == 7
    assert result.provider == "mock2"
    assert result.prompt_version == "ask.v1"


def test_invalid_json_raises_validation_failed(tmp_path):
    p = MockProvider({"ask": "this is not json {"})
    router = Router([p], prompts_dir=write_prompt(tmp_path), timeout_s=5)
    with raises(ValidationFailed):
        router.generate_json("ask", {"q": "x"}, Answer)


def test_schema_mismatch_raises_validation_failed(tmp_path):
    p = MockProvider({"ask": {"wrong_key": 1}})
    router = Router([p], prompts_dir=write_prompt(tmp_path), timeout_s=5)
    with raises(ValidationFailed):
        router.generate_json("ask", {"q": "x"}, Answer)


def test_all_providers_failed(tmp_path):
    p1 = MockProvider({"ask": ProviderTimeout("slow")})
    p2 = MockProvider({"ask": ProviderTimeout("slow too")})
    router = Router([p1, p2], prompts_dir=write_prompt(tmp_path), timeout_s=5)
    with raises(AllProvidersFailed):
        router.generate_json("ask", {"q": "x"}, Answer)


def test_json_inside_code_fence_is_accepted(tmp_path):
    p = MockProvider({"ask": '```json\n{"value": 3}\n```'})
    router = Router([p], prompts_dir=write_prompt(tmp_path), timeout_s=5)
    assert router.generate_json("ask", {"q": "x"}, Answer).data.value == 3


def test_highest_prompt_version_wins(tmp_path):
    d = write_prompt(tmp_path, version=1, text="old {{q}}")
    write_prompt(tmp_path, version=2, text="new {{q}}")
    p = MockProvider({"ask": {"value": 1}})
    router = Router([p], prompts_dir=d, timeout_s=5)
    result = router.generate_json("ask", {"q": "x"}, Answer)
    assert result.prompt_version == "ask.v2"
    assert p.calls[0]["prompt"] == "new x"
