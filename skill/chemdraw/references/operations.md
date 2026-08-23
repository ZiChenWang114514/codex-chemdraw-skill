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
- `CHEMDRAW_MCP_TRANSPORT`
- `CHEMDRAW_MCP_HTTP_HOST`
- `CHEMDRAW_MCP_HTTP_PORT`
- `CHEMDRAW_MCP_HTTP_API_KEY`
- `CHEMSCRIPT_PYTHON`
- `CHEMSCRIPT_CONFIG_PATH`

Workers also preserve `CHEMSCRIPT_*`, `CONDA_PREFIX`, and `JAVA_HOME` so an
explicitly configured ChemScript or Java runtime remains visible after process
isolation. Credentials and unrelated shell variables are not forwarded.

Run `scripts/runtime_discovery.py` from Python when debugging discovery code. Generate MCP configuration with `scripts/configure_mcp.ps1`; it is read-only unless `-Apply` is supplied.

## Health And Smoke Tests

Run MCP `diagnose_runtime()` for an offline, read-only capability matrix. It reports the Python runtime, installed `cdxml-toolkit` and MCP SDK distribution versions, ChemDraw discovery and COM registration, ChemScript, Java/OPSIN, Office dependencies, DECIMER markers, and live tool count without importing DECIMER or downloading weights. Set `run_chemscript_probe=true` for an independent bridge ping. `run_native_probe=true` runs that ping first and then a temporary CDXML-to-PNG probe, so a ChemDraw COM timeout cannot hide the ChemScript result. Set `run_office_probe=true` for separate temporary PPTX and DOCX ChemDraw OLE probes. ChemScript is capped at 30 seconds, native rendering at 75 seconds, and each Office stage at 60 seconds. Results include stage duration, timeout, and cleanup status. Normal completion never force-terminates ChemDraw; timeout cleanup is limited to newly observed automation processes that can be attributed to the probe.

Run `scripts/health_check.ps1` for the complete repository gate. It consumes the same diagnostic matrix, checks Python packages, generated signatures and inventory, Skill tests, Codex MCP state, and, unless skipped, the native and Office probes. Every subprocess is time-bounded.

Run `scripts/smoke_test.py --output-dir <directory>` for name resolution, editable aspirin CDXML, native ChemDraw PNG rendering, and raster validation.

## Streamable HTTP And Metrics

`scripts/mcp_server.py` uses stdio unless `--transport streamable-http` is supplied. HTTP defaults to `127.0.0.1:8029`. Non-loopback listening requires `CHEMDRAW_MCP_HTTP_API_KEY`; wildcard listening additionally requires `--allowed-host`. The key must contain at least 32 UTF-8 bytes, remains in the parent server, and is removed from every worker environment. Use the standard `Authorization: Bearer ...` header.

`/health` is intentionally public and returns only uptime, registered tool count, active worker count, and local ChemDraw scheduler state. `/metrics` uses Prometheus text format and requires the bearer token when HTTP authentication is enabled. It records tool duration, hard timeouts, stable worker failure codes, active workers, and the local ChemDraw queue. It never records arguments, molecule strings, filenames, document content, outputs, or credentials.

The parent process schedules one local ChemDraw COM worker at a time and reports callers waiting there. The named per-user mutex remains active inside each worker to coordinate with another local server process.

## DECIMER

Local image recognition requires official DECIMER weights. Install both with `scripts/install_decimer_models.py`, or select one with `--model standard` / `--model handdrawn`. Each model is downloaded and extracted in isolation, verified against the MD5 published with the [standard model](https://zenodo.org/records/8300489) or [hand-drawn model](https://zenodo.org/records/10781330), assigned a computed SHA-256 receipt, and atomically installed only after its complete marker exists. Missing local weights are a warning and do not block other tools.

Remote recognition uses the configured `DECIMER_API_URL` or the Steinbeck Lab default. It enforces image decoding, request/response size limits, timeout, and explicit `confirm_upload=true`. Relevant limits:

- `DECIMER_API_MAX_IMAGE_BYTES`
- `DECIMER_API_MAX_RESPONSE_BYTES`

Read [decimer-api.md](decimer-api.md) for the HTTP contract.

## Failure Modes

- MCP startup timeout: verify discovered Python and import `mcp_server.py` directly.
- MCP SDK mismatch: use `mcp==2.0.0` for the tested runtime. The launcher also supports SDK 1.x and provides the renamed high-level server class expected by `cdxml-toolkit==0.5.17`.
- Tool timeout: raise the worker timeout only after confirming the operation is legitimately long-running.
- Molecular analysis timeout: `modify_molecule` is limited to 90 seconds because ChemScript naming and decomposition can become expensive for complex fused structures. Trusted SMILES can be drawn directly when no modification is requested.
- Native resource busy: ChemDraw COM operations share a named per-user mutex. Let the active render, conversion, or Office operation finish before retrying; ordinary parsing remains concurrent.
- Worker error id: inspect `%LOCALAPPDATA%\Codex\chemdraw-mcp\logs\worker-<id>.log`; detailed exceptions are intentionally not returned over MCP.
- COM failure: verify registration and run the smoke test. Rendering requests a dedicated automation instance so an already open interactive session is not reused, waits for a stable file, and retries one silent `SaveAs`. Batch rendering reuses one dedicated application instance.
- Native path failure: the Skill copies inputs into an ASCII-only workspace before ChemDraw or Office COM calls, validates native output there, and publishes it transactionally to the requested path. `CHEMDRAW_NATIVE_TEMP` can select an explicit writable ASCII root. `native_ascii_workspace_unavailable`, `native_saveas_silent_failure`, `native_output_missing`, and `native_output_invalid` identify failures before publication.
- `chemdraw_license_unavailable`: ChemDraw COM returned HRESULT `-2147221230` or an equivalent license message. Stop native validation and inspect the installed product license, Python bitness, and COM registration. Do not treat showing a hidden application window as an activation fix, and do not alter an activated interactive installation as a shortcut.
- ChemScript failure: inspect the bridge health output; do not call the private server protocol.
- Config drift: run the config script without `-Apply`, review its proposed block, then apply with automatic backup. Failed writes restore only when the config fingerprint still matches the last known state; concurrent edits are preserved.

## Do Not Use Directly

Do not edit `config.toml` with ad hoc string replacement, launch private ChemScript server commands, or bypass the worker registry.
