import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SeedContentTests(unittest.TestCase):
    def test_repository_contract_manifest_hash_matches_raw_source(self):
        manifest_entries = [
            json.loads(line)
            for line in (ROOT / "raw/source-manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        entry = next(item for item in manifest_entries if item["source_id"] == "muvywiki-repository-contract")
        raw_path = ROOT / entry["raw_path"]
        actual_hash = "sha256:" + hashlib.sha256(raw_path.read_bytes()).hexdigest()
        self.assertEqual(entry["content_hash"], actual_hash)

    def test_root_wiki_returns_repository_contract_results(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/query.py"),
                "repository root isolation provenance",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        matches = json.loads(result.stdout)["matches"]
        self.assertTrue(matches)
        self.assertIn("RepositoryRootIsolation", {item["id"] for item in matches})


if __name__ == "__main__":
    unittest.main()
