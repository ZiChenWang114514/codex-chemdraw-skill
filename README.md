# Codex ChemDraw Skill

[简体中文](docs/zh-cn.md)

A Codex Skill and MCP server for ChemDraw and `cdxml-toolkit` workflows on Windows. It gives Codex task-level tools for drawing, cleaning, merging, rendering, recognizing, analyzing, and embedding chemical structures.

This is an independent community project. It is not affiliated with or endorsed by Revvity, Anthropic, OpenAI, or the DECIMER project.

## Capabilities

- Resolve names, SMILES, InChI, and common structure identifiers.
- Compare single molecules or bounded batches with ChemScript identity and RDKit fingerprints.
- Draw and edit structures and reaction schemes as CDXML.
- Clean, merge, polish, segment, and render ChemDraw documents.
- Convert images with local DECIMER models or an explicitly confirmed remote request.
- Embed CDXML objects in PowerPoint and Word files on supported Windows systems.
- Discover experiment files and process selected LCMS, RDF, and lab-book workflows.
- Inspect and execute the installed public ChemScript SDK through a controlled, isolated program.
- Optionally serve the same tools over authenticated Streamable HTTP with health and Prometheus endpoints.

## Requirements

- 64-bit Windows 10 or Windows 11.
- A licensed, activated Windows desktop installation of ChemDraw for native rendering and automation.
- A 64-bit Python 3.10-3.13 environment; Python 3.12 is the tested configuration.
- `cdxml-toolkit==0.5.17` for the tested configuration.
- `mcp==2.0.0` for the tested MCP runtime; SDK 1.x remains compatible.
- Codex with a working `codex` command for MCP registration.

ChemDraw, Microsoft Office, and local DECIMER model weights are not bundled.
Microsoft Office, ChemScript, and DECIMER are required only for the features that use them. First-time users should follow the [step-by-step Chinese guide](docs/zh-cn.md#从零开始安装) or the [detailed English installation guide](docs/guide.md#first-time-windows-setup) before using the commands below.

## Quick Start

```powershell
git clone https://github.com/ZiChenWang114514/codex-chemdraw-skill.git
Set-Location codex-chemdraw-skill

conda create -n cdxml python=3.12 -y
conda run -n cdxml python -m pip install "mcp==2.0.0" "cdxml-toolkit==0.5.17"
$python = (conda run -n cdxml python -c "import sys; print(sys.executable)" | Select-Object -Last 1).Trim()
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\check_prerequisites.ps1 -Python $python
& .\scripts\install.ps1 -Python $python -Apply -ConfigureMcp
```

Restart Codex after installation, then verify the integration:

```powershell
codex mcp get cdxml-toolkit --json
& "$HOME\.codex\skills\chemdraw\scripts\health_check.ps1" -Python $python
```

The installer is read-only unless `-Apply` is supplied. Existing Skill and MCP configuration files are backed up before replacement.
Use `-SkipOffice` with the health check when Word or PowerPoint desktop is not installed. Use `-SkipNativeChemDraw` only for a portable code and MCP check that intentionally omits all native ChemDraw and Office probes.

stdio remains the default. For a ChemDraw workstation shared through a private network, see the authenticated [Streamable HTTP setup](docs/guide.md#streamable-http) before exposing a listening port.

## Documentation

- [Project guide](docs/guide.md): installation, runtime discovery, architecture, testing, safety, and third-party boundaries.
- [Contributing](.github/contributing.md): development workflow and pull-request expectations.
- [Security](.github/SECURITY.md): private vulnerability reporting and supported versions.

The deployable Skill lives in [`skill/chemdraw`](skill/chemdraw). Repository-specific instructions are in [`AGENTS.md`](AGENTS.md).

## Safety

Remote image recognition is disabled unless the caller explicitly confirms upload. Modifying tools create a new output path by default and reject accidental overwrites. Chemical outputs must be checked against the source material before scientific use.

## License

Repository-authored code and documentation are licensed under the [MIT License](LICENSE). Third-party software keeps its own license: [ChemDraw](https://revvitysignals.com/products/research/chemdraw), [cdxml-toolkit](https://github.com/kienerj/cdxmltoolkit), and [DECIMER](https://github.com/Kohulan/DECIMER-Image_Classifier).
