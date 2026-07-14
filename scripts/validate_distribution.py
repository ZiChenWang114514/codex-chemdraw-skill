"""Validate the repository without importing proprietary/runtime dependencies."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "chemdraw"


def validate_python_syntax() -> list[str]:
    errors: list[str] = []
    for path in ROOT.rglob("*.py"):
        if any(part == "__pycache__" for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(ROOT).as_posix()}: {exc}")
    return errors


def validate_skill_metadata() -> list[str]:
    errors: list[str] = []
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", skill_text, flags=re.DOTALL)
    if not frontmatter:
        errors.append("skill/chemdraw/SKILL.md: missing YAML frontmatter")
    else:
        keys = [
            line.split(":", 1)[0].strip()
            for line in frontmatter.group(1).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if keys != ["name", "description"]:
            errors.append(f"skill/chemdraw/SKILL.md: expected name/description keys, got {keys}")
        if not re.search(r"^name:\s*chemdraw\s*$", frontmatter.group(1), flags=re.MULTILINE):
            errors.append("skill/chemdraw/SKILL.md: name must be chemdraw")

    agent_text = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for token in ("display_name:", "short_description:", "default_prompt:", 'value: "cdxml-toolkit"'):
        if token not in agent_text:
            errors.append(f"skill/chemdraw/agents/openai.yaml: missing {token}")

    version = (ROOT / "VERSION").read_text(encoding="ascii").strip()
    if not re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version
    ):
        errors.append(f"VERSION: expected semantic version, got {version!r}")
    return errors


def run_distribution_tests() -> bool:
    sys.dont_write_bytecode = True
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def main() -> int:
    errors = [*validate_python_syntax(), *validate_skill_metadata()]
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    tests_ok = run_distribution_tests()
    if errors or not tests_ok:
        return 1
    print("Distribution validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
