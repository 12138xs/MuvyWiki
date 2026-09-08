import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "ingest"


def fixture_fingerprint():
    return {
        path.relative_to(FIXTURE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in FIXTURE.rglob("*")
        if path.is_file()
    }


class DemoToolTests(unittest.TestCase):
    def run_demo(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/demo.py"), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_demo_reports_non_empty_results_without_mutating_fixture(self):
        before = fixture_fingerprint()
        result = self.run_demo("--json")
        after = fixture_fingerprint()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertGreater(payload["query_match_count"], 0)
        self.assertGreater(payload["graph_node_count"], 0)
        self.assertFalse(payload["workspace_modified"])
        self.assertEqual(before, after)

    def test_text_output_names_each_verified_step(self):
        result = self.run_demo()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("health -> lint -> query -> graph", result.stdout)
        self.assertIn("Workspace modified: no", result.stdout)


if __name__ == "__main__":
    unittest.main()
