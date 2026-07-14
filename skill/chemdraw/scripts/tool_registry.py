"""Single collision-checked registry shared by MCP and worker processes."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Any, Callable

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
        official[tool.name] = ToolSpec(
            name=tool.name,
            function=function,
            title=tool.title,
            description=(
                inspect.getdoc(function)
                if override is not None
                else tool.description or inspect.getdoc(function) or tool.name
            ),
            annotations=tool.annotations,
            group="official",
        )

    remote = {
        name: ToolSpec(
            name=name,
            function=function,
            title=name.replace("_", " ").title(),
            description=inspect.getdoc(function) or name,
            return_json_text=True,
            group="remote",
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
        )
        for name, function in PUBLIC_TOOLS.items()
    }
    registry = _merge_named_tools(official, remote, source="remote tools")
    return _merge_named_tools(registry, extended, source="extended tools")
