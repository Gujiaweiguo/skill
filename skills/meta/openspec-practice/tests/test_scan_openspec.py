import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_openspec.py"


class ScanOpenSpecTest(unittest.TestCase):
    def test_hidden_change_directories_are_not_active_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            (changes / "real-change").mkdir(parents=True)
            (changes / ".evidence").mkdir()
            (changes / "archive").mkdir()

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )

        scope = json.loads(result.stdout)["scopes"][0]
        self.assertEqual(scope["active_changes"], ["real-change"])

    def test_undecodable_archive_tasks_are_reported_as_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tasks = root / "openspec" / "changes" / "archive" / "old-change" / "tasks.md"
            tasks.parent.mkdir(parents=True)
            tasks.write_bytes(b"\xff\xfe")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )

        scope = json.loads(result.stdout)["scopes"][0]
        self.assertEqual(scope["archive_unreadable_task_files"], 1)
        self.assertEqual(scope["archive_unreadable_task_samples"][0]["change"], "old-change")


if __name__ == "__main__":
    unittest.main()
