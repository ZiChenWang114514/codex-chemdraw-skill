# Changelog

All notable changes are documented here. This project follows semantic versioning after the initial `0.x` development series.

## [0.1.0] - 2026-07-14

### Added

- Progressive ChemDraw Skill with workflow, domain, signature, and audit-reference layers.
- MCP adapter exposing 27 documented tools through isolated workers.
- Reaction layout, merge, polish, batch rendering, Office template/OLE, analysis, RDF, experiment discovery, segmentation, and DECIMER workflows.
- Portable runtime discovery, safe MCP configuration, repository installer, CI validation, and release documentation.

### Security

- Remote DECIMER uploads default to refusal and require explicit confirmation.
- Output writes use non-overwrite and staged-commit behavior where applicable.
- Worker processes have configurable hard timeouts and structured error envelopes.
