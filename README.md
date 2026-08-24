# Codex ChemDraw Skill

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Codex ChemDraw Skill: controlled CDXML workflows from a chemistry request to a checked native ChemDraw artifact">
</p>

Turn chemistry requests into editable CDXML, native ChemDraw renders, molecule comparisons, recognition candidates, and Office-embedded structures through one Codex Skill and MCP server.

[简体中文](docs/zh-cn.md) · [Installation](docs/guide.md#first-time-windows-setup) · [Workflow catalog](skill/chemdraw/references/workflow-router.md) · [Security](.github/SECURITY.md)

[![Validate](https://github.com/ZiChenWang114514/codex-chemdraw-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/ZiChenWang114514/codex-chemdraw-skill/actions/workflows/validate.yml)

`Windows 10/11` · `Python 3.10-3.13` · `MCP 2.0 tested` · [MIT](LICENSE)

## From Request to Checked Artifact

```text
Chemistry request
    -> resolve and check structure identity
    -> create, compare, or edit CDXML
    -> render with ChemDraw when required
    -> report absolute paths, metadata, and warnings
```

For example, ask Codex:

```text
Use the ChemDraw Skill to resolve aspirin, save editable CDXML and a native
ChemDraw PNG, then report the absolute paths and chemistry checks.
```

The result contract includes:

- A source-grounded structure or an explicit warning when identity is uncertain.
- Editable CDXML, plus native ChemDraw output when the requested software is available.
- Absolute artifact paths, chemistry metadata, and actionable warnings.
- Native rendering as a compatibility check. A successful render does not independently prove molecular identity.

See the [workflow router](skill/chemdraw/references/workflow-router.md), [generated MCP signatures](skill/chemdraw/references/mcp-signatures.md), [audited public toolkit inventory](skill/chemdraw/references/toolkit-public-inventory.md), and [portable CI workflow](.github/workflows/validate.yml) for the corresponding implementation evidence.

## What It Handles

- **Structures and reactions:** resolve names and identifiers; draw, edit, clean, merge, polish, segment, convert, and render CDXML or CDX documents.
- **Molecule comparison:** use ChemScript exact-identity checks together with RDKit fingerprint similarity for one molecule pair or a bounded batch.
- **Image recognition:** extract candidate structures, confidence values, and bounding boxes with local DECIMER models or an explicitly confirmed remote request. Recognition candidates still require source review.
- **Office documents:** embed editable ChemDraw objects in supported desktop versions of Word and PowerPoint.
- **Experimental records:** discover files and process selected LCMS, SciFinder RDF, and lab-book workflows.
- **ChemScript SDK:** inspect the installed public catalog and run supported declarative calls in a separate worker process. Process separation limits stalled calls; it is not an operating-system security sandbox.
- **Remote workstation access:** keep stdio as the default or expose the Windows host through optional Streamable HTTP with health and Prometheus endpoints.

The project audits 449 public `cdxml-toolkit` symbols. That number describes the toolkit inventory, not the number of MCP tools. Full public ChemScript catalog coverage means the interface can be discovered and reported; successful execution still depends on the installed SDK, license, architecture, and individual member behavior.

## Choose the Required Components

| Goal | Add to the core setup |
| --- | --- |
| Create and edit CDXML | Codex, 64-bit Python 3.10-3.13, `mcp==2.0.0`, and `cdxml-toolkit==0.5.17` |
| Native PNG, CDX, or ChemDraw cleanup | Licensed and activated Windows desktop ChemDraw with working COM automation |
| Molecule comparison or ChemScript SDK calls | Installed ChemScript DLLs compatible with the selected worker runtime |
| Editable Word or PowerPoint objects | Supported desktop Microsoft Word and/or PowerPoint |
| Local optical structure recognition | DECIMER model weights and their runtime dependencies |
| Remote access to a ChemDraw workstation | A Windows host plus authenticated HTTP configuration and an encrypted network path |

ChemDraw, Microsoft Office, ChemScript, and DECIMER model weights are not bundled. For a first installation, use the [step-by-step Chinese guide](docs/zh-cn.md#从零开始安装) or the [detailed English guide](docs/guide.md#first-time-windows-setup).

## Quick Start

These commands create a dedicated Conda environment, inspect the proposed installation, and then install the Skill and register its stdio MCP server:

```powershell
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
Set-Location .\codex-chemdraw-skill

conda create -n cdxml python=3.12 pip -y
$python = (conda run -n cdxml python -c "import sys; print(sys.executable)" | Select-Object -Last 1).Trim()
conda run -n cdxml python -m pip install --upgrade pip
conda run -n cdxml python -m pip install "mcp==2.0.0" "cdxml-toolkit==0.5.17"

Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\check_prerequisites.ps1 -Python $python
& .\scripts\install.ps1 -Python $python -ConfigureMcp
& .\scripts\install.ps1 -Python $python -Apply -ConfigureMcp
```

For a CDXML-only installation without desktop ChemDraw, add `-SkipChemDraw` to `check_prerequisites.ps1`. The installer reports proposed paths without changing files until `-Apply` is supplied. When applying, it preserves existing Skill and MCP configuration files before replacement.

Restart Codex, open a new PowerShell session, and perform the basic integration checks:

```powershell
$python = (conda run -n cdxml python -c "import sys; print(sys.executable)" | Select-Object -Last 1).Trim()
codex mcp get cdxml-toolkit --json
& "$HOME\.codex\skills\chemdraw\scripts\check_prerequisites.ps1" -Python $python
```

Use `-SkipChemDraw` again on the installed prerequisite checker for a CDXML-only setup. Then try the example request above or follow the [first-use walkthrough](docs/zh-cn.md#10-完成第一次使用).

<details>
<summary><strong>Run deeper validation</strong></summary>

The health check compiles Python modules, runs the repository test suite, and compares generated references. It is intended for maintenance and may take several minutes.

```powershell
# Portable MCP and CDXML validation; omits every native ChemDraw and Office probe
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python -SkipNativeChemDraw

# Native ChemDraw and ChemScript validation; omits Word and PowerPoint probes
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python -SkipOffice

# Full local validation: ChemDraw, ChemScript, Word, and PowerPoint
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python
```

`-SkipOffice` still requires a working ChemScript installation. Use `-SkipNativeChemDraw` when ChemScript or desktop ChemDraw is unavailable.

</details>

## Validation and Safety

- The current GitHub Actions workflow validates portable behavior on Windows with Python 3.12, `mcp==2.0.0`, and `cdxml-toolkit==0.5.17`. Python 3.10-3.13 is supported, while MCP SDK 1.x is retained as a compatibility path and is not exercised by current CI.
- Native ChemDraw, ChemScript, and Office behavior must be checked on a licensed local Windows host because those applications are unavailable in hosted CI.
- Structural changes can be checked with source identity, MCS-based diffs, chemistry metadata, and native rendering. Scientific acceptance remains the user's responsibility.
- Standard modifying tools create a new output path and reject accidental replacement. ChemScript SDK file access and replacement are available only when their explicit permission and overwrite options are enabled.
- Remote image recognition refuses upload unless the caller explicitly confirms it. The higher-level reaction-image-to-CDXML workflow remains unpublished until structure roles and ordering can be verified reliably.
- The built-in HTTP listener does not provide TLS. Non-loopback use requires bearer authentication and an allowed `Host`; place it behind an encrypted tunnel or HTTPS reverse proxy. `/health` exposes status only, while `/metrics` requires authentication.
- Worker processes provide timeout and failure isolation, but they do not sandbox ChemDraw, Office, Python dependencies, or filesystem access. Review the [security policy](.github/SECURITY.md) before enabling native file operations or remote access.

## Documentation

- [Chinese setup and first use](docs/zh-cn.md)
- [Installation, troubleshooting, architecture, and operations](docs/guide.md)
- [Task-oriented workflow catalog](skill/chemdraw/references/workflow-router.md)
- [Generated MCP tool signatures](skill/chemdraw/references/mcp-signatures.md)
- [Audited `cdxml-toolkit` public inventory](skill/chemdraw/references/toolkit-public-inventory.md)
- [Streamable HTTP setup](docs/guide.md#streamable-http)
- [Contributing guide](.github/contributing.md)
- [Security policy](.github/SECURITY.md)

The deployable Skill lives in [`skill/chemdraw`](skill/chemdraw). Repository-specific contributor instructions are in [`AGENTS.md`](AGENTS.md).

## License

Repository-authored code and documentation are licensed under the [MIT License](LICENSE). ChemDraw, Microsoft Office, Codex, `cdxml-toolkit`, the MCP Python SDK, RDKit, DECIMER, and their dependencies retain their respective licenses and usage terms.

This is an independent community project. It is not affiliated with or endorsed by Revvity, OpenAI, Microsoft, or the maintainers of `cdxml-toolkit`, the MCP Python SDK, RDKit, or DECIMER.
