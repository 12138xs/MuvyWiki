import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HealthToolTests(unittest.TestCase):
    def run_health(self, *args, cwd=ROOT):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/health.py"), *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_current_repository_is_healthy(self):
        result = self.run_health()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MuvyWiki health: ok", result.stdout)

    def test_json_output_contains_required_keys(self):
        result = self.run_health("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("issues", payload)
        self.assertIn("checked_at", payload)

    def test_missing_required_file_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            (temp / "wiki").mkdir()
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required path", result.stdout)


if __name__ == "__main__":
    unittest.main()
