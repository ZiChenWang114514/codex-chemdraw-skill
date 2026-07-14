# ChemDraw Skill for Codex

[简体中文](README.zh-CN.md)

A Windows-first Codex Skill and MCP adapter for grounded chemical drawing, reaction-scheme processing, DECIMER recognition, analytical-file workflows, and editable ChemDraw objects in Word and PowerPoint.

> This is an independent integration project. ChemDraw is proprietary software from Revvity and is not distributed by this repository.

## Capabilities

- Progressive Skill guidance with workflow routing and generated MCP signatures.
- 27 MCP tools covering molecule resolution and editing, CDX/CDXML rendering, reaction cleanup and merge, Office OLE, ELN/RDF, LCMS/NMR, and DECIMER.
- Isolated worker processes with hard timeouts and structured errors.
- Non-destructive output defaults and explicit upload confirmation for remote DECIMER.
- Runtime discovery for Conda/Python and registered ChemDraw installations.

The authoritative agent instructions are in [`skill/chemdraw/SKILL.md`](skill/chemdraw/SKILL.md). Exact tool signatures are generated in [`skill/chemdraw/references/mcp-signatures.md`](skill/chemdraw/references/mcp-signatures.md).

## Requirements

- Windows 10 or 11.
- Codex CLI with MCP support.
- Python 3.12 environment containing `cdxml-toolkit` and its dependencies.
- An installed and activated ChemDraw copy for native COM rendering, CDX conversion, and editable Office OLE.
- Microsoft Word or PowerPoint only for workflows that create or validate those files.

The published bundle was validated with Python 3.12, `cdxml-toolkit` 0.5.17, MCP SDK 1.28.1, and Codex CLI 0.144.0. These are tested versions, not automatic compatibility promises for every later release.

## Install

```powershell
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
cd codex-chemdraw-skill

conda create -n cdxml python=3.12 -y
conda run -n cdxml python -m pip install "cdxml-toolkit==0.5.17"

# Dry run: no files or Codex configuration are changed.
.\scripts\install.ps1 -Python (conda run -n cdxml python -c "import sys; print(sys.executable)")

# Install the Skill and register its MCP server, with backups.
.\scripts\install.ps1 -Apply -ConfigureMcp `
  -Python (conda run -n cdxml python -c "import sys; print(sys.executable)")
```

The installer copies only `skill/chemdraw/` into the Codex Skill directory. Existing installations are moved to a timestamped backup before replacement. MCP configuration remains read-only unless both `-Apply` and `-ConfigureMcp` are supplied.

See [installation](docs/installation.md) for custom paths, activation/bitness notes, and diagnostics.

## Validate

```powershell
python .\scripts\validate_distribution.py

conda run -n cdxml python -m unittest discover `
  -s .\skill\chemdraw\scripts -p "test_*.py" -v

.\skill\chemdraw\scripts\health_check.ps1 -SkipNativeChemDraw
```

Native ChemDraw and Office checks require the matching activated desktop installation and are intentionally separate from portable CI.

## Documentation

- [Installation and diagnostics](docs/installation.md)
- [Architecture](docs/architecture.md)
- [Testing and release gates](docs/testing.md)
- [Privacy and safety](docs/privacy-and-safety.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

Repository-authored code and documentation are licensed under the [MIT License](LICENSE). Third-party software retains its own license; see [third-party notices](THIRD_PARTY_NOTICES.md).
