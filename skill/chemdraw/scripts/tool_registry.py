"""Single collision-checked registry shared by MCP and worker processes."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Any, Callable

import mcp_compat

mcp_compat.install_legacy_fastmcp_alias()

from cdxml_toolkit.mcp_server import server as upstream

from extended_tools import PUBLIC_TOOLS
from official_overrides import OFFICIAL_OVERRIDES
from remote_tools import REMOTE_TOOLS


@dataclass(frozen=True)
class ToolSpec:
    name: str
    function: Callable[..., Any]
    title: str | None
    description: str
    annotations: Any = None
    return_json_text: bool = False
    group: str = "official"
    resource_class: str | None = None
    timeout_seconds: int | None = None


CHEMDRAW_COM_TOOLS = {
    "parse_reaction",
    "convert_cdx_cdxml",
    "render_to_png",
    "extract_cdxml_from_office",
    "embed_cdxml_in_office",
    "clean_scheme_layout",
    "merge_reaction_schemes",
    "polish_reaction_scheme",
    "render_cdxml_files",
    "fill_office_template",
    "batch_embed_cdxml_in_office",
    "inspect_chemdraw_objects_in_office",
    "replace_chemdraw_objects_in_office",
    "diagnose_runtime",
}


def _resource_class(name: str) -> str | None:
    return "chemdraw_com" if name in CHEMDRAW_COM_TOOLS else None


def _tool_timeout(name: str) -> int | None:
    return 90 if name == "modify_molecule" else None


def _merge_named_tools(existing: dict, incoming: dict, *, source: str) -> dict:
    collisions = sorted(set(existing).intersection(incoming))
    if collisions:
        raise RuntimeError(f"Tool registry collision from {source}: {', '.join(collisions)}")
    return {**existing, **incoming}


def build_registry() -> dict[str, ToolSpec]:
    official: dict[str, ToolSpec] = {}
    for tool in upstream.mcp._tool_manager.list_tools():
        override = OFFICIAL_OVERRIDES.get(tool.name)
        function = override or tool.fn
        upstream_description = tool.description or inspect.getdoc(tool.fn) or tool.name
        description = upstream_description
        if override is not None:
            description = (
                f"{upstream_description}\n\nSafety override: "
                f"{inspect.getdoc(override) or 'transactional artifact publication'}"
            )
        official[tool.name] = ToolSpec(
            name=tool.name,
            function=function,
            title=tool.title,
            description=description,
            annotations=tool.annotations,
            group="official",
            resource_class=_resource_class(tool.name),
            timeout_seconds=_tool_timeout(tool.name),
        )

    remote = {
        name: ToolSpec(
            name=name,
            function=function,
            title=name.replace("_", " ").title(),
            description=inspect.getdoc(function) or name,
            return_json_text=True,
            group="remote",
            resource_class=_resource_class(name),
            timeout_seconds=_tool_timeout(name),
        )
        for name, function in REMOTE_TOOLS.items()
    }
    extended = {
        name: ToolSpec(
            name=name,
            function=function,
            title=name.replace("_", " ").title(),
            description=inspect.getdoc(function) or name,
            return_json_text=True,
            group="extended",
            resource_class=_resource_class(name),
            timeout_seconds=_tool_timeout(name),
        )
        for name, function in PUBLIC_TOOLS.items()
    }
    registry = _merge_named_tools(official, remote, source="remote tools")
    return _merge_named_tools(registry, extended, source="extended tools")
