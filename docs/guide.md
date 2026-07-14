# Project Guide

This is the single detailed guide for installing, understanding, testing, and operating the project. The root README stays intentionally short.

## Installation

### Prerequisites

- Windows 10 or later.
- Python 3.10 or later, preferably in a dedicated Conda environment.
- A licensed and activated ChemDraw installation for COM automation and native rendering.
- Microsoft PowerPoint or Word only for the corresponding Office workflows.
- Optional local DECIMER model weights for offline image recognition.

Clone the repository and run the installer from PowerShell:

```powershell
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
Set-Location codex-chemdraw-skill

conda create -n cdxml python=3.12 -y
conda run -n cdxml python -m pip install --upgrade pip
conda run -n cdxml python -m pip install "cdxml-toolkit==0.5.17"
conda run -n cdxml python -c "import cdxml_toolkit, mcp, rdkit, win32com.client; print('runtime ok')"

$python = (conda run -n cdxml python -c "import sys; print(sys.executable)" | Select-Object -Last 1)
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\install.ps1 -Python $python -Apply -ConfigureMcp
```

Without `-Apply`, the installer only reports planned changes. With `-Apply`, it backs up an existing Skill before installing to `$HOME\.codex\skills\chemdraw`. `-ConfigureMcp` also backs up and updates `$HOME\.codex\config.toml`.

Restart Codex, then verify:

```powershell
codex mcp get cdxml-toolkit --json
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python
```

### Runtime Discovery

The MCP runtime resolves executables and applications in this order:

1. Explicit tool parameter.
2. Supported environment variable.
3. Active Python or Conda environment.
4. Windows registry and common installation locations.
5. A structured error describing what is missing.

No username, Conda root, ChemDraw directory, or Office directory should be hard-coded in repository code.

### Activation and Bitness

An activated ChemDraw desktop application does not guarantee that every automation interface is available. The health check separately tests executable discovery, COM registration, native rendering, and optional ChemScript paths.

If a native workflow fails, confirm that Python and the required native component use compatible architectures, then run:

```powershell
.\skill\chemdraw\scripts\health_check.ps1 -Python $python
codex doctor --all
```

## Architecture

The Skill uses progressive disclosure so routine prompts load only the context they need:

1. `SKILL.md` provides trigger metadata, scientific constraints, privacy rules, and task routing.
2. Workflow references describe end-to-end drawing, reaction, recognition, Office, analysis, and diagnostic tasks.
3. Domain references provide decision rules and failure modes.
4. Generated API references provide exact callable signatures.
5. Inventory shards support targeted audit by module or function name.

Public MCP tools are registered through one extension registry and executed in isolated workers with hard timeouts and structured errors. New tools return `ok`, `outputs`, `warnings`, and `metadata`; established tools retain their compatible names and contracts.

Generated signatures and inventory files must be regenerated from source. Do not manually duplicate those signatures in narrative documentation.

## Development and Validation

Run repository validation and the complete Skill test suite before submitting changes:

```powershell
python scripts/validate_distribution.py
python -m unittest discover -s skill/chemdraw/scripts -p "test_*.py" -v
.\skill\chemdraw\scripts\health_check.ps1 -SkipNativeChemDraw
```

Focused tests must cover valid input, invalid parameters, missing files, overwrite refusal, timeout handling, and structured failures. Distribution validation checks the packaged tree, documentation links, generated references, portability, and accidental secret patterns.

Claims involving ChemDraw or Office require a licensed local installation and a real output that opens or renders successfully. CDXML rendering should use ChemDraw's native renderer where that is the behavior under test. Remote DECIMER tests are opt-in and must use non-sensitive fixtures.

GitHub Actions runs the portable checks. Machine-specific native checks remain local because hosted runners do not include licensed ChemDraw or Office applications.

## Safety and Privacy

- Remote image recognition requires `confirm_upload=true`; the default is refusal.
- Remote inputs must be real decoded images and are subject to size, response, and timeout limits.
- Modifying tools generate a new output path by default and reject unintended overwrite.
- Temporary files and outputs inherit local filesystem permissions; inspect them before sharing.
- Never commit API keys, credentials, personal experiment data, proprietary documents, or licensed binaries.
- Treat recognized or generated chemistry as a hypothesis until it is checked against the source and chemically validated.

## Third-Party Boundaries

The repository's own code and documentation use the MIT License. It does not redistribute ChemDraw, Microsoft Office, Codex, DECIMER weights, or other proprietary components.

- [ChemDraw](https://revvitysignals.com/products/research/chemdraw) is proprietary software licensed by Revvity Signals.
- [cdxml-toolkit](https://github.com/kienerj/cdxmltoolkit) is an independent open-source dependency.
- [DECIMER](https://github.com/Kohulan/DECIMER-Image_Classifier) components and model weights use their upstream terms.
- Codex and Microsoft Office are optional external runtimes governed by their vendors.

Review the license metadata of the exact dependency versions used in an environment before redistribution. Project history and release notes belong in Git and GitHub Releases rather than duplicate Markdown ledgers.
