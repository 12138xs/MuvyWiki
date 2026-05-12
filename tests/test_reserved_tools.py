import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReservedToolTests(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_lint_returns_reserved_exit_code(self):
        result = self.run_tool("tools/lint.py")
        self.assertEqual(result.returncode, 3)
        self.assertIn("reserved for future semantic linting", result.stdout)

    def test_build_graph_returns_reserved_exit_code(self):
        result = self.run_tool("tools/build_graph.py")
        self.assertEqual(result.returncode, 3)
        self.assertIn("reserved for future graph generation", result.stdout)

    def test_convert_returns_reserved_exit_code(self):
        result = self.run_tool("tools/convert.py", "raw/originals/example.pdf", "--out", "raw/converted/example.md")
        self.assertEqual(result.returncode, 3)
        self.assertIn("reserved for future conversion", result.stdout)

    def test_convert_rejects_traversal_outside_converted_directory(self):
        result = self.run_tool(
            "tools/convert.py",
            "raw/originals/example.pdf",
            "--out",
            "raw/converted/../originals/escape.md",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Output path must be under raw/converted/.", result.stderr)

    def test_convert_requires_output_argument(self):
        result = self.run_tool("tools/convert.py", "raw/originals/example.pdf")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
