"""Windows-safe MCP launcher with isolated, timeout-bounded workers."""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import typing

from cdxml_toolkit.mcp_server import server as upstream
from mcp.server.fastmcp import FastMCP

from process_control import _assign_kill_job, _close_job, _terminate_process_tree
from tool_registry import build_registry


_WORKER = Path(__file__).with_name("tool_worker.py")
DEFAULT_WORKER_TIMEOUT_SECONDS = 570
DEFAULT_WORKER_INPUT_BYTES = 16 * 1024 * 1024
DEFAULT_WORKER_OUTPUT_BYTES = 8 * 1024 * 1024
_TIMEOUT_RETURN_CODE = -1001
_CANCELLED_RETURN_CODE = -1002
_OUTPUT_LIMIT_RETURN_CODE = -1003


def _positive_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer")
    return value


def _timeout(value: int | None = None) -> int:
    timeout = value if value is not None else _positive_env_int(
        "CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS", DEFAULT_WORKER_TIMEOUT_SECONDS
    )
    if timeout <= 0:
        raise RuntimeError("Worker timeout must be positive")
    return timeout


def _worker_environment() -> dict[str, str]:
    exact = {
        "ALL_PROXY", "APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH",
        "CONDA_PREFIX", "JAVA_HOME",
        "HTTP_PROXY", "HTTPS_PROXY", "LOCALAPPDATA", "NO_PROXY", "PATH",
        "PATHEXT", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
        "PROGRAMW6432", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "SYSTEMROOT",
        "TEMP", "TMP", "USERPROFILE", "WINDIR",
    }
    prefixes = ("CHEMDRAW_", "CHEMSCRIPT_", "DECIMER_", "TF_")
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in exact or key.upper().startswith(prefixes)
    }
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _monitor_process(
    process: subprocess.Popen,
    *,
    timeout_seconds: int,
    cancellation: threading.Event,
    stdout_path: Path,
    stderr_path: Path,
    output_limit: int,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if cancellation.is_set():
            return "cancelled"
        if time.monotonic() >= deadline:
            return "timeout"
        for path in (stdout_path, stderr_path):
            try:
                if path.stat().st_size > output_limit:
                    return "output_limit"
            except FileNotFoundError:
                pass
        time.sleep(0.025)
    return "exit"


def _execute_worker_process(
    payload: bytes,
    *,
    timeout_seconds: int,
    output_limit: int,
    cancellation: threading.Event,
    holder: dict[str, typing.Any],
) -> tuple[int, bytes, bytes]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    with tempfile.TemporaryDirectory(prefix="chemdraw-worker-") as temp_dir:
        request_path = Path(temp_dir) / "request.json"
        request_path.write_bytes(payload)
        stdout_path = Path(temp_dir) / "stdout.bin"
        stderr_path = Path(temp_dir) / "stderr.bin"
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = subprocess.Popen(
                [sys.executable, str(_WORKER), "--request-file", str(request_path)],
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                env=_worker_environment(),
                creationflags=creationflags,
            )
            holder["process"] = process
            job = _assign_kill_job(process)
            holder["job"] = job
            try:
                status = _monitor_process(
                    process,
                    timeout_seconds=timeout_seconds,
                    cancellation=cancellation,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    output_limit=output_limit,
                )
                if status == "exit":
                    returncode = process.returncode
                else:
                    _terminate_process_tree(process, job)
                    holder["job"] = None
                    returncode = {
                        "timeout": _TIMEOUT_RETURN_CODE,
                        "cancelled": _CANCELLED_RETURN_CODE,
                        "output_limit": _OUTPUT_LIMIT_RETURN_CODE,
                    }[status]
            finally:
                holder.pop("process", None)
                _close_job(holder.pop("job", None))
        stdout = stdout_path.read_bytes()[: output_limit + 1]
        stderr = stderr_path.read_bytes()[: output_limit + 1]
    return int(returncode), stdout, stderr


def _safe_message(value: typing.Any) -> str:
    message = str(value or "Tool execution failed")[:1000]
    message = re.sub(r"(?i)(authorization|token|password|secret|api[_-]?key)\s*[:=]\s*\S+", r"\1=<redacted>", message)
    message = re.sub(r"https?://[^\s?#]+[?#]\S+", "<redacted-url>", message)
    return message


def _interpret_worker_result(
    name: str,
    returncode: int,
    stdout: bytes,
    stderr: bytes,
    *,
    timeout: int,
    duration: float,
    output_limit: int,
) -> dict[str, typing.Any]:
    metadata = {"tool": name, "duration_seconds": round(duration, 3)}
    if returncode == _TIMEOUT_RETURN_CODE:
        return {
            "ok": False,
            "error": {"code": "tool_timeout", "message": f"{name} exceeded {timeout} seconds"},
            "metadata": {**metadata, "timeout_seconds": timeout},
        }
    if returncode == _CANCELLED_RETURN_CODE:
        return {
            "ok": False,
            "error": {"code": "tool_cancelled", "message": f"{name} was cancelled"},
            "metadata": metadata,
        }
    if returncode == _OUTPUT_LIMIT_RETURN_CODE or len(stdout) > output_limit or len(stderr) > output_limit:
        return {
            "ok": False,
            "error": {"code": "worker_output_limit", "message": "Worker output exceeded the configured limit"},
            "metadata": {**metadata, "output_limit_bytes": output_limit},
        }
    try:
        envelope = json.loads(stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "ok": False,
            "error": {"code": "worker_protocol_error", "message": "Worker returned an invalid response envelope"},
            "metadata": {**metadata, "returncode": returncode},
        }
    if not isinstance(envelope, dict) or not isinstance(envelope.get("ok"), bool):
        return {
            "ok": False,
            "error": {"code": "worker_protocol_error", "message": "Worker response envelope is incomplete"},
            "metadata": {**metadata, "returncode": returncode},
        }
    if returncode == 0 and envelope["ok"]:
        return {"ok": True, "result": envelope.get("result"), "metadata": metadata}
    error = envelope.get("error") if isinstance(envelope.get("error"), dict) else {}
    return {
        "ok": False,
        "error": {
            "code": str(error.get("code") or "worker_failed")[:100],
            "message": _safe_message(error.get("message")),
        },
        "metadata": {
            **metadata,
            "returncode": returncode,
            **({"error_id": str(error["id"])} if error.get("id") else {}),
        },
    }


def _run_worker_impl(
    name: str,
    args: list | tuple,
    kwargs: dict,
    *,
    timeout_seconds: int | None = None,
    cancellation: threading.Event | None = None,
    holder: dict[str, typing.Any] | None = None,
) -> dict[str, typing.Any]:
    timeout = _timeout(timeout_seconds)
    input_limit = _positive_env_int(
        "CHEMDRAW_MCP_WORKER_INPUT_BYTES", DEFAULT_WORKER_INPUT_BYTES
    )
    output_limit = _positive_env_int(
        "CHEMDRAW_MCP_WORKER_OUTPUT_BYTES", DEFAULT_WORKER_OUTPUT_BYTES
    )
    payload = json.dumps({
        "tool": name,
        "args": args,
        "kwargs": kwargs,
        "timeout_seconds": timeout,
    }).encode("utf-8")
    if len(payload) > input_limit:
        return {
            "ok": False,
            "error": {
                "code": "worker_input_limit",
                "message": "Worker request exceeded the configured input limit",
            },
            "metadata": {
                "tool": name,
                "input_limit_bytes": input_limit,
                "request_bytes": len(payload),
            },
        }
    cancellation = cancellation or threading.Event()
    holder = holder if holder is not None else {}
    started = time.monotonic()
    try:
        returncode, stdout, stderr = _execute_worker_process(
            payload,
            timeout_seconds=timeout,
            output_limit=output_limit,
            cancellation=cancellation,
            holder=holder,
        )
    except OSError:
        return {
            "ok": False,
            "error": {"code": "worker_launch_failed", "message": "Could not launch the isolated worker"},
            "metadata": {"tool": name, "timeout_seconds": timeout},
        }
    return _interpret_worker_result(
        name,
        returncode,
        stdout,
        stderr,
        timeout=timeout,
        duration=time.monotonic() - started,
        output_limit=output_limit,
    )


def _run_worker(
    name: str,
    args: list | tuple,
    kwargs: dict,
    *,
    timeout_seconds: int | None = None,
) -> dict[str, typing.Any]:
    return _run_worker_impl(name, args, kwargs, timeout_seconds=timeout_seconds)


async def _run_worker_async(
    name: str,
    args: list | tuple,
    kwargs: dict,
    *,
    timeout_seconds: int | None = None,
) -> dict[str, typing.Any]:
    cancellation = threading.Event()
    holder: dict[str, typing.Any] = {}
    task = asyncio.create_task(
        asyncio.to_thread(
            _run_worker_impl,
            name,
            args,
            kwargs,
            timeout_seconds=timeout_seconds,
            cancellation=cancellation,
            holder=holder,
        )
    )
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancellation.set()
        process = holder.get("process")
        if process is not None:
            _terminate_process_tree(process, holder.get("job"))
            holder["job"] = None
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        raise


def _adapt_tool(
    name: str,
    function: typing.Callable,
    *,
    return_json_text: bool = False,
) -> typing.Callable:
    """Preserve source parameters while routing execution through a worker."""

    @functools.wraps(function)
    async def invoke(*args, **kwargs):
        outcome = await _run_worker_async(name, args, kwargs)
        if not outcome["ok"]:
            raise RuntimeError(json.dumps(outcome, indent=2))
        result = outcome["result"]
        if return_json_text and not isinstance(result, str):
            return json.dumps(result, indent=2, default=str)
        return result

    try:
        hints = typing.get_type_hints(function)
    except Exception:
        hints = getattr(function, "__annotations__", {})
    signature = inspect.signature(function)
    parameters = [
        parameter.replace(annotation=hints.get(parameter.name, parameter.annotation))
        for parameter in signature.parameters.values()
    ]
    return_annotation = str if return_json_text else hints.get("return", signature.return_annotation)
    invoke.__signature__ = signature.replace(
        parameters=parameters, return_annotation=return_annotation
    )
    invoke.__annotations__ = {
        **{parameter.name: parameter.annotation for parameter in parameters},
        "return": return_annotation,
    }
    return invoke


def build_server() -> FastMCP:
    mcp = FastMCP("cdxml-toolkit", instructions=upstream.mcp.instructions)
    for spec in build_registry().values():
        mcp.tool(
            name=spec.name,
            title=spec.title,
            description=spec.description,
            annotations=spec.annotations,
            structured_output=False,
        )(
            _adapt_tool(
                spec.name,
                spec.function,
                return_json_text=spec.return_json_text,
            )
        )
    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
