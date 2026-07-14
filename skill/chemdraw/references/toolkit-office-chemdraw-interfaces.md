# ChemDraw And Office

## When To Load

Load for CDX/CDXML conversion, native rendering, ChemScript operations, editable Office extraction/embedding, or placeholder templates.

## Preferred Entry Points

- Convert one file: MCP `convert_cdx_cdxml`.
- Native render: MCP `render_to_png` or `render_cdxml_files`.
- Extract editable Office objects: MCP `extract_cdxml_from_office`. Extraction validates every object in a staging directory and publishes the directory only when all objects succeed.
- Create a new Office file with one editable object: MCP `embed_cdxml_in_office`; it rejects existing Office targets.
- Create a PPTX/DOCX collection: MCP `batch_embed_cdxml_in_office`.
- Fill a template manifest: MCP `fill_office_template`.
- Python conversion: `chemdraw.cdx_converter.convert_file` or `batch_convert_files`.
- Python rendering: `chemdraw.cdxml_to_image.cdxml_to_image`.

## Inputs And Outputs

CDXML is the editable interchange format. Native rendering supports PNG and SVG by extension. Office outputs are PPTX/DOCX packages with ChemDraw OLE data and EMF previews. Template structure references are preflighted from the manifest directory; absolute paths and traversal outside that boundary are rejected by the high-level wrapper.

## Failure Modes

ChemDraw COM may fail when registration is missing, documents are locked, unsupported CDXML is opened, or Python bitness selects a different registered automation server than the interactive installation. Office conversion must fail if any required input is missing or if generated OLE data, package relationships, or requested object counts are incomplete. Never replace editable OLE with a flat image without explicit permission.

## Supporting APIs

- `chemdraw.chemscript_bridge.ChemScriptBridge`: properties, conversion, cleanup, MCS, overlay, and reaction loading.
- `office.ole_extractor.extract_from_office`: batch OOXML extraction.
- `office.ole_embedder`: batch conversion, content sizing, compound-file construction, PPTX/DOCX builders.
- `office.doc_from_template`: manifest loading and two-pass text/OLE replacement.
- `chemdraw.cdxml_to_image_rdkit`: simple-molecule diagnostic fallback only.

## Do Not Use Directly

Do not call `_chemscript_server` commands, construct CFB/OLE bytes ad hoc, or claim full GUI automation. Do not use RDKit fallback as the final fidelity check for reactions or Office output.
