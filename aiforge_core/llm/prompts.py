"""Versioned prompt files: <name>.v<N>.md with {{variable}} placeholders.

The highest version for a name wins. render() returns the text and the version,
so every model call can record exactly which prompt produced it.
"""

import re
from pathlib import Path

_FILE_RE = re.compile(r"^(?P<name>[a-z0-9_]+)\.v(?P<version>\d+)\.md$")
_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class PromptNotFound(Exception):
    pass


class MissingVariable(Exception):
    pass


class PromptLibrary:
    def __init__(self, prompts_dir: str | Path):
        self.dir = Path(prompts_dir)

    def _latest(self, name: str) -> tuple[Path, int]:
        best: tuple[Path, int] | None = None
        if self.dir.is_dir():
            for f in self.dir.iterdir():
                m = _FILE_RE.match(f.name)
                if m and m.group("name") == name:
                    v = int(m.group("version"))
                    if best is None or v > best[1]:
                        best = (f, v)
        if best is None:
            raise PromptNotFound(f"no prompt file {name}.v<N>.md in {self.dir}")
        return best

    def prompt_version(self, name: str) -> str:
        _, v = self._latest(name)
        return f"{name}.v{v}"

    def render(self, name: str, variables: dict) -> tuple[str, str]:
        """Return (rendered_text, prompt_version)."""
        path, v = self._latest(name)
        text = path.read_text(encoding="utf-8")

        def sub(m: re.Match) -> str:
            key = m.group(1)
            if key not in variables:
                raise MissingVariable(f"prompt {name}.v{v} needs variable {key!r}")
            value = variables[key]
            return value if isinstance(value, str) else _to_text(value)

        return _VAR_RE.sub(sub, text), f"{name}.v{v}"


def _to_text(value) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2, default=str)
