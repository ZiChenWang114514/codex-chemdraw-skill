---
name: chemdraw
description: Use when Codex needs ChemDraw or cdxml-toolkit to resolve, draw, edit, clean, merge, polish, parse, convert, render, recognize, analyze, or embed chemical structures and reaction schemes. Triggers include molecule names, trusted SMILES, CDX/CDXML, DECIMER/OCSR images, reaction screenshots, ELN/SciFinder RDF, LCMS/NMR, lab books, and editable ChemDraw objects in DOCX/PPTX.
---

# ChemDraw

Use the `cdxml-toolkit` MCP server for stable operations. Preserve source files, ground every structure, verify molecular semantics, and confirm final artifact compatibility through native ChemDraw rendering.

## Core Rules

1. Obtain connectivity only from a trusted user value or a resolver/parser/OCSR tool. Never pass invented or hand-edited SMILES directly; route intentional edits through `modify_molecule` and review its MCS diff.
2. Apply molecular changes with `modify_molecule` and inspect its MCS diff before drawing. A trusted SMILES that requires no change can go directly to `draw_molecule`.
3. Treat low-confidence or multiple OCSR candidates as unresolved until identity is validated.
4. Never upload an image unless the user authorized third-party processing. Remote DECIMER additionally requires `confirm_upload=true`.
5. Keep large CDXML and reaction JSON in files. Preserve inputs and write modifications to new paths.

## Route By Intent

Load [workflow-router.md](references/workflow-router.md), then read only the workflow matching the request:

- Molecule drawing or modification
- Reaction creation, reading, cleanup, merge, or polish
- Local or remote image recognition
- CDX/CDXML conversion and native rendering
- Word/PowerPoint extraction, embedding, or template filling
- ELN/RDF, LCMS/NMR, experiment discovery, or lab-book assembly
- Runtime diagnosis or installation

For an exact callable signature, read [mcp-signatures.md](references/mcp-signatures.md). For selection, policy, and errors, read [toolkit-tools.md](references/toolkit-tools.md). Do not guess arguments from prose.

## Domain References

- Chemistry resolution and molecular diffs: [toolkit-chemistry-resolution-interfaces.md](references/toolkit-chemistry-resolution-interfaces.md)
- Rendering, layout, cleanup, and merge: [toolkit-render-layout-interfaces.md](references/toolkit-render-layout-interfaces.md)
- OCSR, reaction images, RDF, and scheme reading: [toolkit-perception-image-interfaces.md](references/toolkit-perception-image-interfaces.md)
- LCMS/NMR and lab books: [toolkit-analysis-interfaces.md](references/toolkit-analysis-interfaces.md)
- ChemDraw COM and Office OLE: [toolkit-office-chemdraw-interfaces.md](references/toolkit-office-chemdraw-interfaces.md)
- CLI-only workflows: [toolkit-cli-interfaces.md](references/toolkit-cli-interfaces.md)
- Runtime, configuration, and DECIMER status: [operations.md](references/operations.md)
- Reviewed exclusions: [toolkit-reviewed-exclusions.md](references/toolkit-reviewed-exclusions.md)
- Exhaustive audit index: [toolkit-public-inventory.md](references/toolkit-public-inventory.md)

## Acceptance

Return absolute output paths. Check every output exists and is non-empty. For molecule drawing, require `metadata.chemistry_validation.status=preserved` and inspect the reported stereocenters, double-bond geometry, isotopes, charges, and wedge count. Render final CDXML through ChemDraw COM and inspect image dimensions; rendering confirms native compatibility, not molecular identity by itself. Open or render final DOCX/PPTX and confirm editable OLE objects remain embedded. Report warnings and unresolved chemistry explicitly.
