"""Offline runtime capability diagnostics with opt-in native probes."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


def _status(available: bool, **details: Any) -> dict[str, Any]:
    return {"status": "available" if available else "missing", **details}


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _distribution(name: str) -> dict[str, Any]:
    try:
        version = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return _status(False, detail=f"Python distribution is not installed: {name}")
    return _status(True, version=version)


def _chemdraw_capabilities() -> tuple[dict[str, Any], dict[str, Any]]:
    import runtime_discovery

    try:
        discovery = runtime_discovery.find_chemdraw()
        executable = _status(True, path=discovery.path, source=discovery.source)
    except RuntimeError as exc:
        executable = _status(False, detail=str(exc))
    command = runtime_discovery._registry_local_server_command()
    registered = bool(command)
    com = _status(
        registered,
        registered=registered,
        **({"local_server": command} if command else {}),
    )
    return executable, com


def _java_opsin_capabilities() -> tuple[dict[str, Any], dict[str, Any]]:
    java_home = os.environ.get("JAVA_HOME")
    java_candidates = []
    if java_home:
        java_candidates.extend(
            [Path(java_home) / "bin" / "java.exe", Path(java_home) / "bin" / "java"]
        )
    path_java = shutil.which("java")
    if path_java:
        java_candidates.append(Path(path_java))
    java = next((path.resolve() for path in java_candidates if path.is_file()), None)

    opsin_candidates = []
    for variable in ("OPSIN_JAR", "CDXML_TOOLKIT_OPSIN_JAR"):
        value = os.environ.get(variable)
        if value:
            opsin_candidates.append(Path(value).expanduser())
    opsin = next((path.resolve() for path in opsin_candidates if path.is_file()), None)
    return (
        _status(java is not None, **({"path": str(java)} if java else {})),
        _status(
            opsin is not None,
            **({"path": str(opsin)} if opsin else {"detail": "OPSIN JAR was not configured"}),
        ),
    )


def _decimer_capability() -> dict[str, Any]:
    configured = os.environ.get("DECIMER_MODEL_DIR")
    root = (
        Path(configured).expanduser().resolve()
        if configured
        else (Path.home() / ".data" / "DECIMER-V2").resolve()
    )
    models = {}
    for key, relative in (
        ("standard", "DECIMER_model/saved_model.pb"),
        ("handdrawn", "DECIMER_HandDrawn_model/saved_model.pb"),
    ):
        marker = root / relative
        receipt = marker.parent / ".model.json"
        models[key] = {
            "status": "available" if marker.is_file() else "missing",
            "marker": str(marker),
            "receipt": str(receipt) if receipt.is_file() else None,
            "integrity": "recorded" if receipt.is_file() else "unverified",
        }
    available = all(item["status"] == "available" for item in models.values())
    return _status(available, root=str(root), models=models)


def _office_capability() -> dict[str, Any]:
    dependencies = {
        "python-pptx": _module_available("pptx"),
        "python-docx": _module_available("docx"),
        "olefile": _module_available("olefile"),
        "win32com": _module_available("win32com.client"),
    }
    ready = all(dependencies.values())
    return {
        "status": "unverified" if ready else "missing",
        "dependencies": dependencies,
        "detail": (
            "Dependencies are present; enable run_office_probe for native validation"
            if ready
            else "One or more Office/OLE dependencies are missing"
        ),
    }


def _native_probe() -> dict[str, Any]:
    from cdxml_toolkit.naming.mol_builder import resolve_compound
    from PIL import Image

    import official_overrides

    with tempfile.TemporaryDirectory(prefix="chemdraw-native-probe-") as temp_dir:
        root = Path(temp_dir)
        cdxml = root / "aspirin.cdxml"
        png = root / "aspirin.png"
        molecule = resolve_compound("aspirin", use_network=False)
        drawn = official_overrides.draw_molecule(molecule, output_path=str(cdxml))
        if not isinstance(drawn, dict) or not drawn.get("ok"):
            raise RuntimeError(f"CDXML probe failed: {drawn}")
        rendered = official_overrides.render_to_png(str(cdxml), output_path=str(png))
        if not isinstance(rendered, dict) or not rendered.get("ok"):
            raise RuntimeError(f"PNG probe failed: {rendered}")
        with Image.open(png) as image:
            image.verify()
        with Image.open(png) as image:
            dimensions = list(image.size)
        bridge = subprocess.run(
            [
                sys.executable,
                "-m",
                "cdxml_toolkit.chemdraw.chemscript_bridge",
                "ping",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return {
            "status": "available",
            "cdxml_bytes": cdxml.stat().st_size,
            "png_bytes": png.stat().st_size,
            "png_dimensions": dimensions,
            "chemscript_status": (
                "available" if bridge.returncode == 0 else "missing"
            ),
            "chemscript_detail": (
                bridge.stdout.strip() or bridge.stderr.strip()
            )[:1000],
        }


def _office_probe() -> dict[str, Any]:
    from cdxml_toolkit.naming.mol_builder import resolve_compound

    import official_overrides
    from extended_tools import _validate_office_package

    with tempfile.TemporaryDirectory(prefix="chemdraw-office-probe-") as temp_dir:
        root = Path(temp_dir)
        cdxml = root / "aspirin.cdxml"
        drawn = official_overrides.draw_molecule(
            resolve_compound("aspirin", use_network=False), output_path=str(cdxml)
        )
        if not isinstance(drawn, dict) or not drawn.get("ok"):
            raise RuntimeError(f"Office source drawing failed: {drawn}")
        details = {}
        for suffix in (".pptx", ".docx"):
            office = root / f"probe{suffix}"
            result = official_overrides.embed_cdxml_in_office(
                str(cdxml), str(office)
            )
            if not isinstance(result, dict) or not result.get("ok"):
                raise RuntimeError(f"{suffix} OLE probe failed: {result}")
            validation = _validate_office_package(office, expected_ole_objects=1)
            details[suffix.lstrip(".")] = {
                "bytes": office.stat().st_size,
                "ole_objects": validation["ole_objects"],
                "chemdraw_objects": validation["chemdraw_objects"],
            }
        return {
            "status": "available",
            "pptx_objects": details["pptx"]["chemdraw_objects"],
            "docx_objects": details["docx"]["chemdraw_objects"],
            "files": details,
        }


def _run_probe(probe) -> dict[str, Any]:
    try:
        return probe()
    except Exception as exc:
        return {"status": "missing", "detail": str(exc)}


def diagnose_runtime(
    run_native_probe: bool = False,
    run_office_probe: bool = False,
) -> dict[str, Any]:
    """Report local runtime capabilities; native probes are explicit and temporary."""
    capabilities: dict[str, Any] = {
        "python": _status(
            True,
            path=str(Path(sys.executable).resolve()),
            version=sys.version.split()[0],
        ),
        "cdxml_toolkit": _distribution("cdxml-toolkit"),
    }
    capabilities["chemdraw"], capabilities["chemdraw_com"] = (
        _chemdraw_capabilities()
    )
    capabilities["chemscript"] = {
        "status": (
            "unverified"
            if _module_available("cdxml_toolkit.chemdraw.chemscript_bridge")
            else "missing"
        ),
        "detail": "Enable run_native_probe to validate ChemDraw automation",
    }
    capabilities["java"], capabilities["opsin"] = _java_opsin_capabilities()
    capabilities["office"] = _office_capability()
    capabilities["decimer_models"] = _decimer_capability()

    try:
        from tool_registry import build_registry

        tool_count = len(build_registry())
        capabilities["tool_registry"] = _status(True, count=tool_count)
    except Exception as exc:
        tool_count = 0
        capabilities["tool_registry"] = _status(False, detail=str(exc), count=0)

    requested = []
    if run_native_probe:
        capabilities["native_probe"] = _run_probe(_native_probe)
        native = capabilities["native_probe"]
        if native.get("chemscript_status") == "available":
            capabilities["chemscript"] = _status(
                True, detail=native.get("chemscript_detail") or "Bridge ping succeeded"
            )
        elif native.get("chemscript_status") == "missing":
            capabilities["chemscript"] = _status(
                False, detail=native.get("chemscript_detail") or "Bridge ping failed"
            )
        requested.append("native_probe")
    if run_office_probe:
        capabilities["office_probe"] = _run_probe(_office_probe)
        if capabilities["office_probe"]["status"] == "available":
            capabilities["office"] = _status(
                True, detail="Temporary PPTX and DOCX OLE probes succeeded"
            )
        requested.append("office_probe")

    required = ["python", "cdxml_toolkit", "tool_registry", *requested]
    ok = all(capabilities[name]["status"] == "available" for name in required)
    warnings = []
    for name, capability in capabilities.items():
        if capability["status"] == "missing" and name not in {"java", "opsin"}:
            warnings.append(
                f"{name}: {capability.get('detail') or 'capability is unavailable'}"
            )
    return {
        "ok": ok,
        "outputs": {"capabilities": capabilities},
        "warnings": warnings,
        "metadata": {
            "read_only": not (run_native_probe or run_office_probe),
            "network_used": False,
            "tool_count": tool_count,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-probe", action="store_true")
    parser.add_argument("--office-probe", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = diagnose_runtime(args.native_probe, args.office_probe)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for name, capability in result["outputs"]["capabilities"].items():
            print(f"{name}: {capability['status']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
