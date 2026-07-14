# Workflow Router

Load one section matching the user's intent. Exact signatures live only in [mcp-signatures.md](mcp-signatures.md).

## Draw Or Modify A Molecule

1. Resolve a name with `resolve_name`, or accept user-supplied trusted SMILES.
2. Verify identity, formula, molecular weight, and ambiguity.
3. For changes, call `modify_molecule` and inspect the MCS diff.
4. Call `draw_molecule`, then `render_to_png` for native validation.

## Create Or Edit A Reaction

1. Ground every drawn species.
2. Use `render_scheme` for a new reaction.
3. Use `parse_scheme` or `parse_reaction` for an existing CDXML/CDX workflow.
4. Use `clean_scheme_layout`, `merge_reaction_schemes`, or `polish_reaction_scheme` for existing schemes. Explicit and auto-detected sequential plans are checked for linear chemical links; any `force_sequential=true` override requires manual review.
5. Render the resulting CDXML through `render_cdxml_files`.

## Recognize An Image

1. Prefer `extract_structures_from_image` when local DECIMER weights are available.
2. Use `extract_structures_via_decimer_api` only after explicit upload authorization and set `confirm_upload=true`.
3. Inspect every candidate and validation warning; never select by position alone.
4. For complete reaction screenshots, use `reaction_image_to_cdxml` only when it appears in the live MCP registry. It remains withheld when structure-role mapping cannot be verified.

## Convert Or Render

1. Convert CDX with `convert_cdx_cdxml`; edit CDXML, not binary CDX.
2. Render one file with `render_to_png` or a collection/PNG/SVG with `render_cdxml_files`.
3. Require native ChemDraw output for reaction and Office fidelity checks.

## Work With Office

1. Extract existing editable objects with `extract_cdxml_from_office`.
2. Modify and native-render the extracted CDXML.
3. Create a new one-object file with `embed_cdxml_in_office`, create a new collection with `batch_embed_cdxml_in_office`, or preserve an existing template through `fill_office_template`. The single-object tool rejects an existing Office target because the upstream builder cannot preserve its content.
4. Verify the OOXML package opens and contains OLE relationships.

## Analyze Experiments

1. Use `discover_experiment_files` before composing a multi-file workflow.
2. Parse individual LCMS/NMR files with `parse_analysis_file`.
3. Use `analyze_lcms_series` only for at least two supported standard LCMS PDFs.
4. Parse ELN/reaction files with `parse_reaction`; parse SciFinder exports with `parse_scifinder_rdf`. CAS enrichment requires explicit PubChem confirmation.
5. Build a lab entry with `format_lab_entry` or a complete experiment entry with `assemble_lab_book`.

## Diagnose Runtime

Read [operations.md](operations.md). Run the health check first; do not alter Codex configuration until discovery output is understood.
