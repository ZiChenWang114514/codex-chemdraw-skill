"""Safety-preserving replacements for selected official MCP tools."""

from __future__ import annotations

import os
from pathlib import Path
import uuid


def _new_destination(office: Path, output_path: str | None) -> Path:
    if output_path:
        destination = Path(output_path).expanduser().resolve()
        if destination.exists():
            raise ValueError(f"Refusing to overwrite an existing file: {destination}")
        if destination.suffix.lower() != office.suffix.lower():
            raise ValueError("output_path must use the same Office format as office_path")
        return destination
    return office


def _validate_office_ole(path: Path) -> None:
    from extended_tools import _validate_office_package

    _validate_office_package(path, expected_ole_objects=1)


def _commit_no_clobber(temporary: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise ValueError(f"Refusing to overwrite an existing file: {destination}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def embed_cdxml_in_office(
    cdxml_path: str,
    office_path: str,
    output_path: str | None = None,
) -> dict:
    """Create a new PPTX or DOCX containing one editable ChemDraw OLE object.

    This safety override rejects an existing ``office_path`` because the upstream
    builder creates a new package and cannot preserve existing slides or paragraphs.
    It also refuses all destination overwrites and validates the OOXML and CFB/OLE
    structures before publishing the new file.
    """
    from cdxml_toolkit.mcp_server.server import embed_cdxml_in_office as upstream_embed

    source = Path(cdxml_path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".cdxml":
        return {"ok": False, "error": f"CDXML input does not exist: {source}"}
    office = Path(office_path).expanduser().resolve()
    if office.suffix.lower() not in {".pptx", ".docx"}:
        return {"ok": False, "error": "office_path must end in .pptx or .docx"}
    if office.exists():
        return {
            "ok": False,
            "error": (
                "Refusing to use an existing Office file because the upstream embedder "
                "cannot preserve its content; choose a new office_path"
            ),
        }
    try:
        destination = _new_destination(office, output_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.stem}.{uuid.uuid4().hex}.tmp{destination.suffix}"
    )
    try:
        result = upstream_embed(str(source), str(office), str(temporary))
        if not isinstance(result, dict) or not result.get("ok"):
            return result if isinstance(result, dict) else {
                "ok": False,
                "error": "Official Office embedder returned an invalid result",
            }
        _validate_office_ole(temporary)
        _commit_no_clobber(temporary, destination)
        return {**result, "output": str(destination), "created_new_file": True}
    except Exception as exc:
        return {"ok": False, "error": f"Embedding failed validation: {exc}"}
    finally:
        temporary.unlink(missing_ok=True)


OFFICIAL_OVERRIDES = {"embed_cdxml_in_office": embed_cdxml_in_office}
