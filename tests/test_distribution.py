from __future__ import annotations

import re
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "chemdraw"


class DistributionTests(unittest.TestCase):
    def test_required_repository_files_exist(self) -> None:
        required = [
            "README.md",
            "README.zh-CN.md",
            "LICENSE",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CODE_OF_CONDUCT.md",
            "SUPPORT.md",
            "THIRD_PARTY_NOTICES.md",
            "AGENTS.md",
            "VERSION",
            ".gitignore",
            ".gitattributes",
            ".github/workflows/validate.yml",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            "docs/installation.md",
            "docs/architecture.md",
            "docs/testing.md",
            "scripts/install.ps1",
            "scripts/validate_distribution.py",
        ]
        missing = [item for item in required if not (ROOT / item).is_file()]
        self.assertEqual(missing, [], f"Missing repository files: {missing}")

    def test_skill_bundle_is_self_contained(self) -> None:
        self.assertTrue((SKILL / "SKILL.md").is_file())
        self.assertTrue((SKILL / "agents" / "openai.yaml").is_file())
        self.assertTrue((SKILL / "references" / "workflow-router.md").is_file())
        self.assertTrue((SKILL / "scripts" / "mcp_server.py").is_file())
        self.assertFalse((SKILL / "README.md").exists())

    def test_generated_and_local_state_are_not_distributed(self) -> None:
        forbidden_names = {"__pycache__", ".pytest_cache", ".mypy_cache", ".env"}
        if (ROOT / ".git").is_dir():
            completed = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            paths = [ROOT / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]
        else:
            paths = [
                path
                for path in ROOT.rglob("*")
                if not any(part in forbidden_names for part in path.relative_to(ROOT).parts)
            ]
        offenders = [
            path.relative_to(ROOT).as_posix()
            for path in paths
            if path.name in forbidden_names or path.suffix in {".pyc", ".pyo"}
        ]
        self.assertEqual(offenders, [], f"Generated/local files present: {offenders}")

    def test_skill_has_no_machine_specific_paths_or_credentials(self) -> None:
        # Build sensitive tokens in pieces so this test does not flag itself.
        patterns = {
            "local user profile": re.compile(r"C:\\Users\\" + "11234", re.IGNORECASE),
            "local legacy runtime": re.compile(r"D:\\" + "ProgramFiles", re.IGNORECASE),
            "OpenAI-style secret": re.compile(r"s" + r"k-[A-Za-z0-9_-]{20,}"),
            "GitHub classic token": re.compile(r"g" + r"hp_[A-Za-z0-9]{20,}"),
            "GitHub fine-grained token": re.compile(r"github" + r"_pat_[A-Za-z0-9_]{20,}"),
        }
        offenders: list[str] = []
        for path in SKILL.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".ps1", ".yaml", ".yml", ".json"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for label, pattern in patterns.items():
                if pattern.search(text):
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}: {label}")
        self.assertEqual(offenders, [], "Unsafe distribution content:\n" + "\n".join(offenders))

    def test_local_markdown_links_resolve(self) -> None:
        link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
        missing: list[str] = []
        for path in ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for raw_target in link_pattern.findall(text):
                target = raw_target.strip().split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                candidate = (path.parent / target).resolve()
                if not candidate.exists():
                    missing.append(f"{path.relative_to(ROOT).as_posix()} -> {raw_target}")
        self.assertEqual(missing, [], "Broken local Markdown links:\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
