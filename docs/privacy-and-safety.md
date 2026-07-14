# Privacy And Safety

## Local Processing

MCP worker processes, `cdxml-toolkit`, ChemDraw COM, and Office automation run with the permissions of the current Windows user. They may read or write any path that user can access. Use synthetic fixtures for development and restrict the account or working directory when processing untrusted files.

## Remote DECIMER

Remote recognition sends image bytes to a third-party service. The adapter defaults to `confirm_upload=false`, validates that the file decodes as an image, enforces byte/pixel/response limits, rejects insecure or unapproved origins, restricts redirects, and normalizes bounded error output.

User confirmation is necessary but not sufficient: confirm that the uploader is authorized to disclose the image and that the service's privacy, retention, jurisdiction, and acceptable-use terms are suitable. Do not upload confidential structures, patient information, embargoed work, or proprietary laboratory documents without explicit authorization.

## Chemical Correctness

- Resolve names and trusted identifiers through deterministic chemistry tools.
- Do not invent or manually edit SMILES in prose.
- Route changes through `modify_molecule` and inspect its MCS diff.
- Treat multiple or low-confidence OCSR candidates as unresolved.
- Preserve original inputs and report warnings or ambiguity.

## Output Safety

Prefer new output paths, reject accidental overwrite, stage writes, and validate final CDXML/OOXML/image structure before publication. Native rendering is the final acceptance gate for ChemDraw fidelity; XML validity alone does not prove visual or chemical correctness.
