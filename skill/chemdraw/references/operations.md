# Operations

## When To Load

Load for installation, MCP startup, worker timeout, ChemDraw COM, ChemScript, DECIMER, or path-discovery problems.

## Runtime Discovery

Path precedence is explicit argument, environment variable, active Conda/current Python, PATH/common installation locations, then a legacy machine fallback. Supported variables:

- `CHEMDRAW_MCP_PYTHON`
- `CHEMDRAW_SKILL_ROOT`
- `CHEMDRAW_EXE`
- `CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS`
- `CHEMDRAW_MCP_WORKER_INPUT_BYTES`
- `CHEMDRAW_MCP_WORKER_OUTPUT_BYTES`

Run `scripts/runtime_discovery.py` from Python when debugging discovery code. Generate MCP configuration with `scripts/configure_mcp.ps1`; it is read-only unless `-Apply` is supplied.

## Health And Smoke Tests

Run `scripts/health_check.ps1` first. It checks Python packages, ChemScript, ChemDraw COM, generated signatures and inventory, Skill tests, and Codex MCP state. Native checks are time-bounded.

Run `scripts/smoke_test.py --output-dir <directory>` for name resolution, editable aspirin CDXML, native ChemDraw PNG rendering, and raster validation.

## DECIMER

Local image recognition requires official DECIMER weights. Install with `scripts/install_decimer_models.py` when Zenodo is reachable. Missing local weights are a warning and do not block other tools.

Remote recognition uses the configured `DECIMER_API_URL` or the Steinbeck Lab default. It enforces image decoding, request/response size limits, timeout, and explicit `confirm_upload=true`. Relevant limits:

- `DECIMER_API_MAX_IMAGE_BYTES`
- `DECIMER_API_MAX_RESPONSE_BYTES`

Read [decimer-api.md](decimer-api.md) for the HTTP contract.

## Failure Modes

- MCP startup timeout: verify discovered Python and import `mcp_server.py` directly.
- Tool timeout: raise the worker timeout only after confirming the operation is legitimately long-running.
- Worker error id: inspect `%LOCALAPPDATA%\Codex\chemdraw-mcp\logs\worker-<id>.log`; detailed exceptions are intentionally not returned over MCP.
- COM failure: close visible ChemDraw documents, verify registration, and run the smoke test.
- License or activation window: stop validation. With both 32-bit and 64-bit ChemDraw installed, verify which registry view and Python bitness selected `/Automation`; do not alter an activated interactive installation as a shortcut.
- ChemScript failure: inspect the bridge health output; do not call the private server protocol.
- Config drift: run the config script without `-Apply`, review its proposed block, then apply with automatic backup. Failed writes restore only when the config fingerprint still matches the last known state; concurrent edits are preserved.

## Do Not Use Directly

Do not edit `config.toml` with ad hoc string replacement, launch private ChemScript server commands, or bypass the worker registry.
