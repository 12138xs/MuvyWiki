import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrepareIngestToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in (
            "raw/originals",
            "raw/converted",
            "wiki/sources",
            "wiki/concepts",
            "wiki/entities",
            "wiki/syntheses",
            "templates/sources",
            "tools",
            "graph",
        ):
            (root / rel).mkdir(parents=True, exist_ok=True)
        for template in (
            "technical-paper",
            "technical-article",
            "project-readme",
            "meeting-notes",
            "journal-entry",
        ):
            (root / f"templates/sources/{template}.md").write_text(f"# {template}\n", encoding="utf-8")
        (root / "templates/source.md").write_text("# generic\n", encoding="utf-8")
        (root / "raw/source-manifest.jsonl").write_text("", encoding="utf-8")
        for tool in ("wiki_utils.py", "prepare_ingest.py"):
            shutil.copy(ROOT / "tools" / tool, root / "tools" / tool)
        return temp_dir, root

    def run_prepare(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/prepare_ingest.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def manifest_entry(self, source_id, raw_path, content_hash, **overrides):
        entry = {
            "source_id": source_id,
            "raw_path": raw_path,
            "content_hash": content_hash,
            "source_url": None,
            "collected_at": "2026-05-15",
            "published_at": None,
            "converted_from": None,
            "converted_path": None,
            "converter": None,
            "converter_version": None,
        }
        entry.update(overrides)
        return entry

    def sha256_bytes(self, data):
        return "sha256:" + hashlib.sha256(data).hexdigest()

    def wiki_snapshot(self, root):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted((root / "wiki").rglob("*"))
            if path.is_file()
        }

    def test_ready_raw_markdown_json_packet(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            body = "# Karpathy LLM Wiki\n\nNotes.\n"
            (root / "raw/originals/Karpathy LLM Wiki.md").write_text(body, encoding="utf-8")
            result = self.run_prepare(root, "raw/originals/Karpathy LLM Wiki.md", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            item = payload["items"][0]
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(item["status"], "ready")
            self.assertEqual(item["input_kind"], "raw-original")
            self.assertEqual(item["source_id"], "karpathy-llm-wiki")
            self.assertEqual(item["source_kind"], "technical-article")
            self.assertEqual(item["template_path"], "templates/sources/technical-article.md")
            self.assertTrue(item["content_hash"].startswith("sha256:"))
            self.assertEqual(item["input_bytes"], len(body.encode("utf-8")))
            self.assertEqual(item["raw_path"], "raw/originals/Karpathy LLM Wiki.md")
            self.assertIsNone(item["converted_path"])
            self.assertFalse(item["duplicate"])

    def test_ready_run_without_report_is_read_only(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            body = "# Note\n\nA stable source.\n"
            raw_path = root / "raw/originals/note.md"
            raw_path.write_text(body, encoding="utf-8")
            manifest_before = (root / "raw/source-manifest.jsonl").read_bytes()
            raw_before = raw_path.read_bytes()
            wiki_before = self.wiki_snapshot(root)

            result = self.run_prepare(root, "raw/originals/note.md", "--json")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / "raw/source-manifest.jsonl").read_bytes(), manifest_before)
            self.assertEqual(raw_path.read_bytes(), raw_before)
            self.assertEqual(self.wiki_snapshot(root), wiki_before)

    def test_ready_local_text_defaults_to_technical_article(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "clipping.txt").write_text("plain text\n", encoding="utf-8")
            result = self.run_prepare(root, "clipping.txt", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["input_kind"], "local-text")
            self.assertEqual(item["source_kind"], "technical-article")
            self.assertIsNone(item["raw_path"])

    def test_source_id_override_and_kind(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/paper-note.txt").write_text("paper text\n", encoding="utf-8")
            result = self.run_prepare(
                root,
                "raw/originals/paper-note.txt",
                "--source-id",
                "attention-survey-note",
                "--kind",
                "technical-paper",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["source_id"], "attention-survey-note")
            self.assertEqual(item["source_id_origin"], "provided")
            self.assertEqual(item["source_kind"], "technical-paper")
            self.assertEqual(item["template_path"], "templates/sources/technical-paper.md")

    def test_source_id_override_requires_single_kebab_input(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "one.md").write_text("one\n", encoding="utf-8")
            (root / "two.md").write_text("two\n", encoding="utf-8")
            result = self.run_prepare(root, "one.md", "two.md", "--source-id", "one", "--json")
            self.assertEqual(result.returncode, 2)
            self.assertIn("single input", result.stderr)

            result = self.run_prepare(root, "one.md", "--source-id", "Bad ID", "--json")
            self.assertEqual(result.returncode, 2)
            self.assertIn("kebab-case", result.stderr)

    def test_converted_artifact_reports_needs_raw_original(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/converted/note.md").write_text("# Converted\n", encoding="utf-8")
            result = self.run_prepare(root, "raw/converted/note.md", "--json")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            item = payload["items"][0]
            self.assertEqual(payload["status"], "issues")
            self.assertEqual(item["input_kind"], "raw-converted")
            self.assertTrue(item["needs_raw_original"])
            self.assertIn("raw original", " ".join(item["warnings"]).lower())

    def test_converted_artifact_uses_matching_manifest_raw_original(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            raw_body = b"# Original\n"
            converted_body = b"# Converted\n"
            (root / "raw/originals/note.md").write_bytes(raw_body)
            (root / "raw/converted/note.md").write_bytes(converted_body)
            (root / "raw/source-manifest.jsonl").write_text(
                json.dumps(
                    self.manifest_entry(
                        "note",
                        "raw/originals/note.md",
                        self.sha256_bytes(raw_body),
                        converted_path="raw/converted/note.md",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            result = self.run_prepare(root, "raw/converted/note.md", "--json")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["raw_path"], "raw/originals/note.md")
            self.assertFalse(item["needs_raw_original"])
            self.assertTrue(item["duplicate"])

    def test_converted_artifact_duplicate_by_converted_path_even_with_different_hash_and_source_id(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            raw_body = b"# Original\n\nRaw source text.\n"
            converted_body = b"# Converted\n\nConverted artifact text.\n"
            (root / "raw/originals/original.md").write_bytes(raw_body)
            (root / "raw/converted/different-name.md").write_bytes(converted_body)
            (root / "raw/source-manifest.jsonl").write_text(
                json.dumps(
                    self.manifest_entry(
                        "existing-source",
                        "raw/originals/original.md",
                        self.sha256_bytes(raw_body),
                        converted_path="raw/converted/different-name.md",
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_prepare(root, "raw/converted/different-name.md", "--json")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["status"], "blocked")
            self.assertTrue(item["duplicate"])
            self.assertEqual(item["manifest_match"]["source_id"], "existing-source")
            self.assertEqual(item["raw_path"], "raw/originals/original.md")
            self.assertEqual(item["converted_path"], "raw/converted/different-name.md")
            self.assertFalse(item["needs_raw_original"])

    def test_malformed_manifest_blocks_preflight(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/note.md").write_text("# Note\n", encoding="utf-8")
            (root / "raw/source-manifest.jsonl").write_text("{bad json\n", encoding="utf-8")
            result = self.run_prepare(root, "raw/originals/note.md", "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["items"][0]["status"], "blocked")
            self.assertIn("manifest", " ".join(payload["items"][0]["warnings"]).lower())

    def test_manifest_missing_key_and_duplicate_entries_block_preflight(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            body = b"# Note\n"
            content_hash = "sha256:" + __import__("hashlib").sha256(body).hexdigest()
            (root / "raw/originals/note.md").write_bytes(body)
            entries = [
                {"source_id": "note", "raw_path": "raw/originals/note.md", "content_hash": content_hash},
                self.manifest_entry("note", "raw/originals/note.md", content_hash),
            ]
            (root / "raw/source-manifest.jsonl").write_text(
                "\n".join(json.dumps(entry) for entry in entries) + "\n",
                encoding="utf-8",
            )
            result = self.run_prepare(root, "raw/originals/note.md", "--json")
            self.assertEqual(result.returncode, 1)
            warnings = " ".join(json.loads(result.stdout)["items"][0]["warnings"]).lower()
            self.assertIn("missing required keys", warnings)
            self.assertIn("duplicate manifest source_id", warnings)

    def test_duplicate_source_id_and_hash_block(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            body = b"# Existing\n"
            (root / "raw/originals/existing.md").write_bytes(body)
            content_hash = "sha256:" + __import__("hashlib").sha256(body).hexdigest()
            (root / "raw/source-manifest.jsonl").write_text(
                json.dumps(self.manifest_entry("existing", "raw/originals/existing.md", content_hash)) + "\n",
                encoding="utf-8",
            )
            result = self.run_prepare(root, "raw/originals/existing.md", "--json")
            self.assertEqual(result.returncode, 1)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["status"], "blocked")
            self.assertTrue(item["duplicate"])
            self.assertEqual(item["manifest_match"]["source_id"], "existing")

    def test_existing_wiki_source_or_canonical_id_blocks(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/existing.md").write_text("# Existing\n", encoding="utf-8")
            (root / "wiki/concepts/existing.md").write_text(
                "---\ncanonical_id: existing\ntype: concept\n---\n# Existing\n",
                encoding="utf-8",
            )
            result = self.run_prepare(root, "raw/originals/existing.md", "--json")
            self.assertEqual(result.returncode, 1)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["status"], "blocked")
            self.assertIn("already exists", " ".join(item["warnings"]))

    def test_batch_reports_remote_unsupported_binary_bad_path_and_report_path(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/file.pdf").write_bytes(b"%PDF")
            (root / "raw/originals/binary.txt").write_bytes(b"\x00\x01")
            (root / "raw/originals/note.md").write_text("# Note\n", encoding="utf-8")
            report = self.run_prepare(
                root,
                "https://example.com/page",
                "raw/originals/file.pdf",
                "raw/originals/binary.txt",
                "raw/originals/missing.md",
                "raw/originals/note.md",
                "--json",
                "--report",
                "graph/ingest-prep-report.md",
            )
            self.assertEqual(report.returncode, 2)
            payload = json.loads(report.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(len(payload["items"]), 5)
            kinds = [item["input_kind"] for item in payload["items"]]
            self.assertIn("remote-url", kinds)
            self.assertIn("unsupported", kinds)
            self.assertIn("raw-original", kinds)
            self.assertIn(
                "MuvyWiki Ingest Prep Report",
                (root / "graph/ingest-prep-report.md").read_text(encoding="utf-8"),
            )

    def test_report_path_must_stay_under_graph(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "note.md").write_text("# Note\n", encoding="utf-8")
            result = self.run_prepare(root, "note.md", "--report", "wiki/not-here.md", "--json")
            self.assertEqual(result.returncode, 2)
            self.assertIn("report", result.stderr.lower())
            self.assertFalse((root / "wiki/not-here.md").exists())

    def test_report_path_rejects_symlink_parent_under_graph(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "note.md").write_text("# Note\n", encoding="utf-8")
            target_dir = root / "report-target"
            target_dir.mkdir()
            (root / "graph/linked-parent").symlink_to(target_dir, target_is_directory=True)

            result = self.run_prepare(root, "note.md", "--report", "graph/linked-parent/report.md", "--json")

            self.assertEqual(result.returncode, 2)
            self.assertIn("report", result.stderr.lower())
            self.assertFalse((target_dir / "report.md").exists())

    def test_report_path_rejects_symlink_leaf_under_graph(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "note.md").write_text("# Note\n", encoding="utf-8")
            target_file = root / "report-target.md"
            target_file.write_text("do not overwrite\n", encoding="utf-8")
            (root / "graph/report.md").symlink_to(target_file)

            result = self.run_prepare(root, "note.md", "--report", "graph/report.md", "--json")

            self.assertEqual(result.returncode, 2)
            self.assertIn("report", result.stderr.lower())
            self.assertEqual(target_file.read_text(encoding="utf-8"), "do not overwrite\n")

    def test_help_describes_read_only_scope(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_prepare(root, "--help")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            help_text = result.stdout.lower()
            self.assertIn("read-only", help_text)
            self.assertIn("--report", help_text)
            self.assertIn("graph/", help_text)

    def test_symlink_parent_is_blocked_item_not_crash(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            real_parent = root / "real-parent"
            real_parent.mkdir()
            (real_parent / "note.md").write_text("# Note\n", encoding="utf-8")
            (root / "linked-parent").symlink_to(real_parent, target_is_directory=True)
            result = self.run_prepare(root, "linked-parent/note.md", "--json")
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            item = payload["items"][0]
            self.assertEqual(item["input"], "linked-parent/note.md")
            self.assertEqual(item["status"], "blocked")
            self.assertEqual(item["input_kind"], "unsupported")
            self.assertIn("symlink", " ".join(item["warnings"]).lower())


if __name__ == "__main__":
    unittest.main()
