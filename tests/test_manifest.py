import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ManifestToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in ("raw/originals", "raw/converted", "wiki/sources", "tools"):
            (root / rel).mkdir(parents=True, exist_ok=True)
        for tool in ("wiki_utils.py", "manifest.py"):
            shutil.copy(ROOT / "tools" / tool, root / "tools" / tool)
        (root / "raw/source-manifest.jsonl").write_text("", encoding="utf-8")
        return temp_dir, root

    def run_manifest(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/manifest.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def valid_entry(self, root, source_id="source-one", body=b"source body\n"):
        raw_path = root / f"raw/originals/{source_id}.md"
        raw_path.write_bytes(body)
        return {
            "source_id": source_id,
            "raw_path": f"raw/originals/{source_id}.md",
            "content_hash": "sha256:" + hashlib.sha256(body).hexdigest(),
            "source_url": None,
            "collected_at": "2026-05-15",
            "published_at": None,
            "converted_from": None,
            "converted_path": None,
            "converter": None,
            "converter_version": None,
        }

    def write_manifest(self, root, *entries):
        text = "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries)
        (root / "raw/source-manifest.jsonl").write_text(text, encoding="utf-8")

    def test_check_empty_manifest_is_ok(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_manifest(root, "check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("MuvyWiki manifest: ok", result.stdout)
            self.assertIn("Entries: 0", result.stdout)

    def test_check_valid_manifest_json(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            result = self.run_manifest(root, "check", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["entry_count"], 1)
            self.assertEqual(payload["issues"], [])

    def test_check_rejects_malformed_missing_and_duplicate_entries(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            duplicate = dict(entry)
            duplicate["raw_path"] = "raw/originals/duplicate.md"
            (root / "raw/originals/duplicate.md").write_bytes(b"other\n")
            (root / "raw/source-manifest.jsonl").write_text(
                json.dumps(entry) + "\n" + "{bad json\n" + json.dumps(duplicate) + "\n",
                encoding="utf-8",
            )
            result = self.run_manifest(root, "check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid JSON on line 2", result.stdout)
            self.assertIn("duplicate source_id: source-one", result.stdout)

    def test_check_reports_validation_issues_on_physical_manifest_lines(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            valid = self.valid_entry(root)
            invalid = self.valid_entry(root, "source-two")
            invalid["content_hash"] = "not-a-sha256"
            (root / "raw/source-manifest.jsonl").write_text(
                "\n" + json.dumps(valid) + "\n" + json.dumps(invalid) + "\n",
                encoding="utf-8",
            )

            result = self.run_manifest(root, "check", "--json")

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            hash_issues = [
                issue for issue in payload["issues"] if issue["message"] == "invalid content_hash for source-two"
            ]
            self.assertEqual(hash_issues, [{"line": 3, "message": "invalid content_hash for source-two"}])

    def test_check_validates_paths_dates_and_required_keys(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root, "bad-source")
            bad_entry = dict(entry)
            bad_entry.pop("converter_version")
            bad_entry["source_id"] = "Bad Source"
            bad_entry["content_hash"] = "sha1:nope"
            bad_entry["raw_path"] = "raw/../wiki/sources/nope.md"
            bad_entry["converted_path"] = "raw/originals/bad-source.md"
            bad_entry["converted_from"] = "/tmp/outside.md"
            bad_entry["collected_at"] = "2026-5-15"
            bad_entry["published_at"] = "2026-02-30"
            self.write_manifest(root, bad_entry)
            result = self.run_manifest(root, "check", "--json")
            self.assertEqual(result.returncode, 1)
            messages = "\n".join(issue["message"] for issue in json.loads(result.stdout)["issues"])
            self.assertIn("missing converter_version", messages)
            self.assertIn("invalid source_id", messages)
            self.assertIn("invalid content_hash", messages)
            self.assertIn("raw_path", messages)
            self.assertIn("converted_path", messages)
            self.assertIn("converted_from", messages)
            self.assertIn("collected_at", messages)
            self.assertIn("published_at", messages)

    def test_check_rejects_symlinked_manifest_paths(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            real = root / "raw/originals/real.md"
            real.write_bytes(b"real\n")
            link = root / "raw/originals/source-one.md"
            link.symlink_to(real)
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            result = self.run_manifest(root, "check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("raw_path for source-one", result.stdout)
            self.assertIn("symlink", result.stdout)

    def test_find_by_source_id_hash_and_path(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            by_id = self.run_manifest(root, "find", "--source-id", "source-one", "--json")
            self.assertEqual(by_id.returncode, 0, by_id.stdout + by_id.stderr)
            self.assertEqual(json.loads(by_id.stdout)["matches"][0]["source_id"], "source-one")
            by_hash = self.run_manifest(root, "find", "--hash", entry["content_hash"])
            self.assertEqual(by_hash.returncode, 0, by_hash.stdout + by_hash.stderr)
            self.assertIn("source-one", by_hash.stdout)
            by_path = self.run_manifest(root, "find", "--path", "raw/originals/source-one.md")
            self.assertEqual(by_path.returncode, 0, by_path.stdout + by_path.stderr)
            self.assertIn("1 match", by_path.stdout)

    def test_find_json_match_does_not_include_internal_line_metadata(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            result = self.run_manifest(root, "find", "--source-id", "source-one", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            match = json.loads(result.stdout)["matches"][0]
            self.assertNotIn("line", match)

    def test_find_reports_manifest_issues_before_matching(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            entry["content_hash"] = "bad"
            self.write_manifest(root, entry)
            result = self.run_manifest(root, "find", "--source-id", "source-one", "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "issues")
            self.assertIn("invalid content_hash", payload["issues"][0]["message"])

    def test_find_requires_search_argument(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_manifest(root, "find")
            self.assertEqual(result.returncode, 2)
            self.assertIn("At least one", result.stderr)

    def test_add_writes_one_entry_and_preserves_existing_lines(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            existing = self.valid_entry(root, "existing-source", b"existing\n")
            self.write_manifest(root, existing)
            body = b"new body\n"
            raw_path = root / "raw/originals/new-source.md"
            raw_path.write_bytes(body)
            content_hash = "sha256:" + hashlib.sha256(body).hexdigest()
            before = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8")

            result = self.run_manifest(
                root,
                "add",
                "--source-id", "new-source",
                "--raw-path", "raw/originals/new-source.md",
                "--content-hash", content_hash,
                "--published-at", "2026-05-01",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["entry"]["source_id"], "new-source")
            lines = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], before.splitlines()[0])
            self.assertEqual(json.loads(lines[1])["content_hash"], content_hash)

    def test_add_rejects_duplicate_source_id_hash_and_raw_path_without_mutation(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            before = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8")

            result = self.run_manifest(
                root,
                "add",
                "--source-id", "source-one",
                "--raw-path", "raw/originals/source-one.md",
                "--content-hash", entry["content_hash"],
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate source_id", result.stdout)
            self.assertEqual((root / "raw/source-manifest.jsonl").read_text(encoding="utf-8"), before)

    def test_add_rejects_conflicting_existing_source_page_provenance_without_mutation(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            body = b"new body\n"
            raw_path = root / "raw/originals/new-source.md"
            raw_path.write_bytes(body)
            content_hash = "sha256:" + hashlib.sha256(body).hexdigest()
            (root / "wiki/sources/new-source.md").write_text(
                f"""---
canonical_id: new-source
title: "New Source"
provenance:
  source_id: new-source
  raw_path: raw/originals/different.md
  content_hash: "{content_hash}"
  source_url: null
  collected_at: 2026-05-15
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# New Source
""",
                encoding="utf-8",
            )
            before = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8")

            result = self.run_manifest(
                root,
                "add",
                "--source-id", "new-source",
                "--raw-path", "raw/originals/new-source.md",
                "--content-hash", content_hash,
            )

            self.assertEqual(result.returncode, 1)
            self.assertRegex(result.stdout, r"provenance|conflicting")
            self.assertEqual((root / "raw/source-manifest.jsonl").read_text(encoding="utf-8"), before)

    def test_add_rejects_hash_mismatch_unsafe_path_and_symlink(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            before = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8")
            (root / "raw/originals/new-source.md").write_text("new body\n", encoding="utf-8")

            mismatch = self.run_manifest(
                root,
                "add",
                "--source-id", "new-source",
                "--raw-path", "raw/originals/new-source.md",
                "--content-hash", "sha256:" + "0" * 64,
            )
            self.assertEqual(mismatch.returncode, 1)
            self.assertIn("does not match actual raw file hash", mismatch.stdout)

            outside = self.run_manifest(
                root,
                "add",
                "--source-id", "bad-source",
                "--raw-path", "../bad.md",
                "--content-hash", "sha256:" + "0" * 64,
            )
            self.assertEqual(outside.returncode, 2)
            self.assertIn("raw_path", outside.stderr)

            (root / "raw/originals/link.md").symlink_to(root / "raw/originals/new-source.md")
            link = self.run_manifest(
                root,
                "add",
                "--source-id", "link-source",
                "--raw-path", "raw/originals/link.md",
                "--content-hash", "sha256:" + "0" * 64,
            )
            self.assertEqual(link.returncode, 2)
            self.assertIn("symlink", link.stderr)
            self.assertEqual((root / "raw/source-manifest.jsonl").read_text(encoding="utf-8"), before)

    def test_add_does_not_mutate_when_existing_manifest_has_validation_issues(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            bad_entry = self.valid_entry(root)
            bad_entry["content_hash"] = "bad"
            self.write_manifest(root, bad_entry)
            before = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8")
            body = b"new body\n"
            (root / "raw/originals/new-source.md").write_bytes(body)

            result = self.run_manifest(
                root,
                "add",
                "--source-id", "new-source",
                "--raw-path", "raw/originals/new-source.md",
                "--content-hash", "sha256:" + hashlib.sha256(body).hexdigest(),
                "--json",
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "issues")
            self.assertEqual((root / "raw/source-manifest.jsonl").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
