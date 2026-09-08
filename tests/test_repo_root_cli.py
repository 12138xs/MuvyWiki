import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepoRootCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name) / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_tool(self, tool, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / tool), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_tools_accept_an_explicit_repository_root(self):
        root_arg = str(self.repo)

        health = self.run_tool("health.py", "--repo-root", root_arg, "--json")
        self.assert_ok(health)
        self.assertEqual(json.loads(health.stdout)["status"], "ok")

        lint = self.run_tool("lint.py", "--repo-root", root_arg, "--json")
        self.assert_ok(lint)
        self.assertEqual(json.loads(lint.stdout)["status"], "ok")

        graph = self.run_tool("build_graph.py", "--repo-root", root_arg)
        self.assert_ok(graph)
        self.assertTrue((self.repo / "graph/graph.json").exists())

        converted = self.run_tool(
            "convert.py",
            "--repo-root",
            root_arg,
            "README.md",
            "--out",
            "raw/converted/repo-root-test.md",
            "--json",
        )
        self.assert_ok(converted)
        self.assertEqual(json.loads(converted.stdout)["output_path"], "raw/converted/repo-root-test.md")

        manifest = self.run_tool("manifest.py", "--repo-root", root_arg, "check", "--json")
        self.assert_ok(manifest)
        self.assertEqual(json.loads(manifest.stdout)["status"], "ok")

        prep = self.run_tool(
            "prepare_ingest.py",
            "--repo-root",
            root_arg,
            "README.md",
            "--source-id",
            "repo-root-readme",
            "--json",
        )
        self.assert_ok(prep)
        self.assertEqual(json.loads(prep.stdout)["items"][0]["input"], "README.md")

        query = self.run_tool("query.py", "--repo-root", root_arg, "knowledge", "--json")
        self.assert_ok(query)
        self.assertGreaterEqual(len(json.loads(query.stdout)["matches"]), 1)

        answer = self.repo / "answer.md"
        evidence = self.repo / "evidence.md"
        answer.write_text("The explicit repository root is used.\n", encoding="utf-8")
        evidence.write_text("Verified by the repository-root CLI test.\n", encoding="utf-8")
        saved = self.run_tool(
            "save_synthesis.py",
            "--repo-root",
            root_arg,
            "--id",
            "repo-root-test",
            "--title",
            "Repository Root Test",
            "--question",
            "Does the selected root receive writes?",
            "--answer-file",
            str(answer),
            "--evidence-file",
            str(evidence),
            "--json",
        )
        self.assert_ok(saved)
        self.assertTrue((self.repo / "wiki/syntheses/repo-root-test.md").exists())

    def test_missing_repository_root_is_rejected(self):
        missing = self.repo / "missing"
        result = self.run_tool("health.py", "--repo-root", str(missing))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Invalid repository root", result.stderr)


if __name__ == "__main__":
    unittest.main()
