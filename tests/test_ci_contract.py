import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


class CiContractTests(unittest.TestCase):
    def test_ci_covers_supported_python_versions(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('python-version: ["3.10", "3.11", "3.12"]', text)
        self.assertIn("python -m unittest discover -s tests", text)

    def test_ci_uses_node_24_action_runtimes(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("uses: actions/checkout@v5", text)
        self.assertIn("uses: actions/setup-python@v6", text)
        self.assertNotIn("uses: actions/checkout@v4", text)
        self.assertNotIn("uses: actions/setup-python@v5", text)

    def test_ci_runs_root_and_fixture_quality_gates(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        required_commands = (
            "python tools/manifest.py check",
            "python tools/health.py",
            "python tools/lint.py",
            "python tools/demo.py",
            "python tools/health.py --repo-root examples/ingest",
            "python tools/lint.py --repo-root examples/ingest",
            'python tools/query.py --repo-root examples/ingest "retrieval augmented generation" --json',
            "git diff --exit-code",
        )
        for command in required_commands:
            with self.subTest(command=command):
                self.assertIn(command, text)

    def test_ci_has_read_only_repository_permissions(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", text)


if __name__ == "__main__":
    unittest.main()
