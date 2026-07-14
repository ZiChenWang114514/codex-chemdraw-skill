from __future__ import annotations

from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

import runtime_diagnostics


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_default_diagnostics_are_offline_read_only_and_do_not_run_probes(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            runtime_diagnostics.Path, "home", return_value=Path(temp_dir)
        ), mock.patch.object(
            runtime_diagnostics, "_native_probe"
        ) as native_probe, mock.patch.object(
            runtime_diagnostics, "_office_probe"
        ) as office_probe, mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ):
            result = runtime_diagnostics.diagnose_runtime()

        self.assertTrue(result["ok"])
        self.assertTrue(result["metadata"]["read_only"])
        self.assertFalse(result["metadata"]["network_used"])
        self.assertEqual(
            result["outputs"]["capabilities"]["cdxml_toolkit"]["version"],
            "0.5.17",
        )
        self.assertEqual(result["metadata"]["tool_count"], 30)
        self.assertEqual(
            result["outputs"]["capabilities"]["tool_registry"]["status"],
            "available",
        )
        self.assertNotIn("native_probe", result["outputs"]["capabilities"])
        self.assertNotIn("office_probe", result["outputs"]["capabilities"])
        native_probe.assert_not_called()
        office_probe.assert_not_called()

    def test_requested_probes_are_reported_in_capability_matrix(self):
        native = {
            "status": "available",
            "png_bytes": 123,
            "png_dimensions": [10, 11],
            "chemscript_status": "available",
        }
        office = {
            "status": "available",
            "pptx_objects": 1,
            "docx_objects": 1,
        }
        with mock.patch.object(
            runtime_diagnostics, "_native_probe", return_value=native
        ) as native_probe, mock.patch.object(
            runtime_diagnostics, "_office_probe", return_value=office
        ) as office_probe:
            result = runtime_diagnostics.diagnose_runtime(
                run_native_probe=True, run_office_probe=True
            )

        self.assertTrue(result["ok"])
        capabilities = result["outputs"]["capabilities"]
        self.assertEqual(capabilities["native_probe"], native)
        self.assertEqual(capabilities["office_probe"], office)
        self.assertEqual(capabilities["chemscript"]["status"], "available")
        self.assertEqual(capabilities["office"]["status"], "available")
        self.assertFalse(result["metadata"]["read_only"])
        native_probe.assert_called_once_with()
        office_probe.assert_called_once_with()

    def test_requested_probe_failure_makes_diagnostic_unsuccessful(self):
        with mock.patch.object(
            runtime_diagnostics,
            "_native_probe",
            return_value={"status": "missing", "detail": "ChemDraw unavailable"},
        ):
            result = runtime_diagnostics.diagnose_runtime(run_native_probe=True)

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("ChemDraw unavailable" in warning for warning in result["warnings"])
        )


if __name__ == "__main__":
    unittest.main()
