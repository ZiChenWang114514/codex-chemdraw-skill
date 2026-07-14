"""Cross-process MCP protocol smoke tests that do not invoke ChemDraw COM."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER = Path(__file__).with_name("mcp_server.py")


async def _list_tools():
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {
            "APPDATA", "COMSPEC", "LOCALAPPDATA", "PATH", "PATHEXT",
            "PROGRAMDATA", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "WINDIR",
        }
    }
    environment.update({"TF_CPP_MIN_LOG_LEVEL": "3", "TF_ENABLE_ONEDNN_OPTS": "0"})
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        env=environment,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return (await session.list_tools()).tools


class MCPStdioTests(unittest.TestCase):
    def test_server_initializes_and_lists_expected_schemas(self):
        tools = asyncio.run(asyncio.wait_for(_list_tools(), timeout=30))
        by_name = {tool.name: tool for tool in tools}
        self.assertEqual(len(by_name), 30)
        self.assertIn("inspect_chemdraw_objects_in_office", by_name)
        self.assertIn("replace_chemdraw_objects_in_office", by_name)
        self.assertIn("resolve_name", by_name)
        self.assertIn("embed_cdxml_in_office", by_name)
        self.assertIn("extract_structures_via_decimer_api", by_name)
        self.assertIn("clean_scheme_layout", by_name)
        self.assertIn("diagnose_runtime", by_name)

        self.assertEqual(
            set(by_name["resolve_name"].inputSchema.get("required", [])),
            {"query"},
        )
        self.assertEqual(
            set(by_name["embed_cdxml_in_office"].inputSchema.get("required", [])),
            {"cdxml_path", "office_path"},
        )
        self.assertEqual(
            set(
                by_name["inspect_chemdraw_objects_in_office"].inputSchema.get(
                    "required", []
                )
            ),
            {"input_path"},
        )
        self.assertEqual(
            set(
                by_name["replace_chemdraw_objects_in_office"].inputSchema.get(
                    "required", []
                )
            ),
            {"input_path", "replacements_manifest"},
        )
        remote_properties = by_name[
            "extract_structures_via_decimer_api"
        ].inputSchema["properties"]
        self.assertIn("confirm_upload", remote_properties)
        self.assertFalse(remote_properties["confirm_upload"]["default"])


if __name__ == "__main__":
    unittest.main()
