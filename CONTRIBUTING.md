# Contributing

Contributions should preserve chemical correctness, non-destructive file behavior, and the Skill's progressive-disclosure structure.

## Development Setup

1. Install Python 3.12 and create an isolated environment.
2. Install the tested `cdxml-toolkit` version and its dependencies.
3. Clone this repository and run the portable validator.
4. Use synthetic, redistributable fixtures. Do not commit proprietary molecules, laboratory records, credentials, or ChemDraw license material.

```powershell
python .\scripts\validate_distribution.py
python -m unittest discover -s .\skill\chemdraw\scripts -p "test_*.py" -v
```

## Change Rules

- Start behavior changes with a failing regression test and demonstrate the red/green cycle.
- Keep source files immutable by default. New modifying tools must reject accidental overwrite and publish outputs atomically.
- Return the shared `{ok, outputs, warnings, metadata}` contract for extension tools.
- Execute public tools through the worker boundary with a bounded timeout.
- Preserve upload consent and origin restrictions for remote services.
- Add decision and failure guidance to the appropriate curated reference. Generate exact signatures; do not hand-copy them.
- Document intentionally withheld interfaces in the reviewed-exclusions reference rather than exposing speculative tools.

## Pull Requests

Use a focused branch and explain the behavior, safety impact, tests, native checks, and known limitations. A pull request that changes public MCP schemas must include regenerated signature documentation and compatibility notes.

Before requesting review, run the gates in [testing documentation](docs/testing.md) and remove generated caches and local artifacts.
