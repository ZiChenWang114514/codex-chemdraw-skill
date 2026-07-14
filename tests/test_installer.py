from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.ps1"


class InstallerTests(unittest.TestCase):
    def test_existing_skill_backup_is_outside_discovery_directory(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        self.assertIsNotNone(shell, "PowerShell is required for this Windows-first project")
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / ".codex"
            destination = codex_home / "skills" / "chemdraw"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("existing", encoding="ascii")

            completed = subprocess.run(
                [
                    str(shell),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INSTALLER),
                    "-Destination",
                    str(destination),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8-sig",
            )
            proposal = json.loads(completed.stdout)
            destination_survived = destination.is_dir()

        backup_root = Path(proposal["backup_root"])
        self.assertEqual(backup_root.name, "chemdraw")
        self.assertEqual(backup_root.parent.name, "skills")
        self.assertEqual(backup_root.parent.parent.name, "backups")
        self.assertNotEqual(backup_root.parent, destination.parent)
        self.assertEqual(Path(proposal["backup"]).parent, backup_root)
        self.assertTrue(destination_survived)


if __name__ == "__main__":
    unittest.main()
