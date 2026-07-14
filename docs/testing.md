# Testing And Release Gates

## Portable Gate

Run on every commit without ChemDraw or `cdxml-toolkit`:

```powershell
python .\scripts\validate_distribution.py
.\scripts\install.ps1
```

This checks required repository files, Skill shape/frontmatter, Python syntax, local Markdown links, generated/local-state exclusions, machine-specific paths, and common credential formats. The installer command is a dry run.

## Runtime Unit And Contract Gate

Run in the tested Python environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m unittest discover -s .\skill\chemdraw\scripts -p "test_*.py" -v
```

The suite covers interface auditing, DECIMER validation, extension-tool contracts, generated docs, MCP stdio schemas, runtime/configuration safety, process-tree timeout behavior, and official overrides.

## Health Gate

```powershell
.\skill\chemdraw\scripts\health_check.ps1 -SkipNativeChemDraw
codex mcp get cdxml-toolkit --json
codex doctor --all
```

`-SkipNativeChemDraw` must be reported as a skipped native gate, not as native success.

## Native ChemDraw Gate

Required for changes to rendering, cleanup, CDX/CDXML conversion, COM discovery, or Office OLE:

- Render synthetic CDXML to PNG through ChemDraw COM and verify a non-empty image with plausible dimensions.
- Convert CDXML/CDX in both directions when the changed path applies.
- Open or render generated DOCX/PPTX and verify the ChemDraw object remains editable.
- Check matching user session and bitness when activation or COM startup fails.

## Network Gate

Remote DECIMER tests require explicit test data and upload authorization. Cover refusal without confirmation, non-image input, size/pixel/response limits, redirects and origin controls, HTTP errors, timeouts, one/multiple candidate responses, and disk/return payload equality.

## Release Checklist

1. Update `VERSION` and `CHANGELOG.md`.
2. Regenerate MCP signatures and toolkit inventory with the release environment.
3. Run portable and full runtime suites.
4. Run applicable native and network gates; list every skipped gate.
5. Run a tracked-file credential/path scan.
6. Tag `v<version>` only after the commit on the default branch is verified.
