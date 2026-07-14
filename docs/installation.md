# Installation And Diagnostics

## Prerequisites

- Windows 10/11 and PowerShell 5.1 or PowerShell 7.
- Codex CLI with MCP commands available.
- Python 3.12 in an isolated Conda environment.
- `cdxml-toolkit` 0.5.17 for the tested configuration.
- ChemDraw installed and activated for the Windows user who runs Codex.

ChemDraw is not required for every workflow. Parsing, registry inspection, policy routing, and some pure-Python transformations can run without it. Native rendering, CDX conversion, ChemDraw cleanup, and editable Office OLE require ChemDraw COM.

## Prepare Python

```powershell
conda create -n cdxml python=3.12 -y
conda run -n cdxml python -m pip install --upgrade pip
conda run -n cdxml python -m pip install "cdxml-toolkit==0.5.17"
conda run -n cdxml python -c "import cdxml_toolkit, mcp, rdkit, win32com.client; print('runtime ok')"
```

DECIMER models and TensorFlow are large. Install or download local model assets only when local OCSR is needed. Remote DECIMER does not require local weights but uploads images to a third party and therefore remains opt-in.

## Install The Skill

The repository installer is dry-run by default:

```powershell
$python = conda run -n cdxml python -c "import sys; print(sys.executable)"
.\scripts\install.ps1 -Python $python
```

Apply the file installation:

```powershell
.\scripts\install.ps1 -Apply -Python $python
```

Install and register the MCP server:

```powershell
.\scripts\install.ps1 -Apply -ConfigureMcp -Python $python
```

Use `-Destination` to override the default `$CODEX_HOME\skills\chemdraw` or `$HOME\.codex\skills\chemdraw` location. An existing destination is moved to a timestamped path under `$CODEX_HOME\backups\skills\chemdraw`; custom destinations use a hidden `.chemdraw-backups` directory unless `-BackupRoot` is provided. Backups stay outside the Skill discovery directory. The MCP configurator separately backs up `config.toml` before changing it and refuses unsafe round trips.

## Discovery Order

Python discovery uses:

1. Explicit `-Python`.
2. `CHEMDRAW_MCP_PYTHON`.
3. Active Conda, current Python, and `PATH`.
4. Standard user/ProgramData Conda locations.
5. Conda's per-user `.conda/environments.txt` registry.

ChemDraw discovery uses explicit input, `CHEMDRAW_EXE`, COM registration, then common Revvity/PerkinElmer/CambridgeSoft install layouts.

## Activation And Bitness

The Skill does not perform product activation and does not require a second license. If the ChemDraw desktop application is already activated for the same Windows user, the remaining failures are usually automation/runtime issues:

- COM registration points to a different ChemDraw version.
- 32-bit ChemDraw is being automated from an incompatible 64-bit component, or the reverse.
- A stale or modal ChemDraw process blocks COM startup.
- Codex runs in a different desktop session or privilege context.
- Office bitness differs from the OLE automation path.

Do not deactivate or reinstall ChemDraw as the first response. Inspect the registered executable, process architecture, active user session, and native health-check output first.

## Diagnostics

```powershell
.\skill\chemdraw\scripts\configure_mcp.ps1 -Python $python `
  -SkillRoot .\skill\chemdraw

.\skill\chemdraw\scripts\health_check.ps1 -SkipNativeChemDraw
codex mcp get cdxml-toolkit --json
codex doctor --all
```

Remove `-SkipNativeChemDraw` only when it is acceptable to start ChemDraw automation in the active desktop session. Keep real API keys, proxy credentials, private structures, and laboratory documents out of diagnostic logs and issues.
