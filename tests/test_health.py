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

    def test_documented_ingest_prep_helpers_are_required(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            (temp / "README.md").write_text("python tools/prepare_ingest.py\npython tools/manifest.py\n", encoding="utf-8")
            (temp / "tools/prepare_ingest.py").unlink()
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("tools/prepare_ingest.py: missing required path", result.stdout)

    def write_minimal_repo(self, root):
        for rel in (
            "raw/originals",
            "raw/converted",
            "wiki/sources",
            "wiki/concepts",
            "wiki/entities",
            "wiki/syntheses",
            "templates",
            "tools",
            "graph",
        ):
            (root / rel).mkdir(parents=True, exist_ok=True)
        for rel in (
            ".gitignore",
            "README.md",
            "AGENTS.md",
            "raw/README.md",
            "templates/overview.md",
            "templates/index-entry.md",
            "templates/log-entry.md",
            "templates/source.md",
            "templates/concept.md",
            "templates/entity.md",
            "templates/synthesis.md",
            "tools/health.py",
            "tools/lint.py",
            "tools/build_graph.py",
            "tools/convert.py",
            "tools/demo.py",
            "tools/manifest.py",
            "tools/prepare_ingest.py",
            "tools/query.py",
            "tools/save_synthesis.py",
            "graph/README.md",
        ):
            (root / rel).write_text("placeholder\n", encoding="utf-8")
        (root / "raw/originals/source-one.txt").write_text("source body\n", encoding="utf-8")
        (root / "raw/source-manifest.jsonl").write_text(
            json.dumps(
                {
                    "source_id": "source-one",
                    "raw_path": "raw/originals/source-one.txt",
                    "content_hash": "sha256:abc123",
                    "source_url": None,
                    "collected_at": "2026-05-12",
                    "published_at": None,
                    "converted_from": None,
                    "converted_path": None,
                    "converter": None,
                    "converter_version": None,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "wiki/overview.md").write_text(
            """---
canonical_id: "overview"
type: overview
title: "Overview"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: 2026-05-12
last_updated: 2026-05-12
status: seed
confidence: medium
---

# Overview
""",
            encoding="utf-8",
        )
        (root / "wiki/sources/source-one.md").write_text(
            """---
canonical_id: "source-one"
type: source
title: "Source One"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths:
  - "raw/originals/source-one.txt"
created: 2026-05-12
last_updated: 2026-05-12
status: seed
confidence: medium
provenance:
  source_id: "source-one"
  raw_path: "raw/originals/source-one.txt"
  content_hash: "sha256:abc123"
  source_url: null
  collected_at: "2026-05-12"
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# Source One
""",
            encoding="utf-8",
        )
        (root / "wiki/index.md").write_text(
            """# MuvyWiki Index

## Overview

- [[overview|Overview]] (`wiki/overview.md`) - type: overview - updated: 2026-05-12 - Living map.

## Sources

- [[source-one|Source One]] (`wiki/sources/source-one.md`) - type: source - updated: 2026-05-12 - Test source.
""",
            encoding="utf-8",
        )
        (root / "wiki/log.md").write_text(
            """# MuvyWiki Log

## [2026-05-12] init | fixture

- Changed pages: [[overview]], [[source-one]]
- Raw paths: raw/originals/source-one.txt
- Source IDs: source-one
- Unresolved issues: none
""",
            encoding="utf-8",
        )

    def test_heading_only_log_entry_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            (temp / "wiki/log.md").write_text(
                """# MuvyWiki Log

## [2026-05-12] init | fixture
""",
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("log entry missing required field: - Changed pages:", result.stdout)
        self.assertIn("log entry missing required field: - Raw paths:", result.stdout)
        self.assertIn("log entry missing required field: - Source IDs:", result.stdout)
        self.assertIn("log entry missing required field: - Unresolved issues:", result.stdout)

    def test_duplicate_index_entry_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            with (temp / "wiki/index.md").open("a", encoding="utf-8") as index_file:
                index_file.write(
                    "\n- [[source-one|Source One Again]] (`wiki/sources/source-one.md`) - type: source - updated: 2026-05-12 - Duplicate.\n"
                )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate index entry for source-one", result.stdout)

    def test_index_entry_path_must_match_canonical_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            index_path = temp / "wiki/index.md"
            index_path.write_text(
                index_path.read_text(encoding="utf-8").replace(
                    "- [[source-one|Source One]] (`wiki/sources/source-one.md`) - type: source - updated: 2026-05-12 - Test source.",
                    "- [[source-one|Source One]] (`wiki/overview.md`) - type: source - updated: 2026-05-12 - Test source.",
                ),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "index entry for source-one points to wiki/overview.md, expected wiki/sources/source-one.md",
            result.stdout,
        )

    def test_index_entry_must_be_under_matching_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            index_path = temp / "wiki/index.md"
            index_path.write_text(
                index_path.read_text(encoding="utf-8").replace(
                    "## Sources\n\n- [[source-one|Source One]]",
                    "## Concepts\n\n- [[source-one|Source One]]",
                ),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("index entry for source-one must be under ## Sources", result.stdout)

    def test_overview_index_entry_must_be_under_overview_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            index_path = temp / "wiki/index.md"
            index_path.write_text(
                index_path.read_text(encoding="utf-8").replace(
                    "## Overview\n\n- [[overview|Overview]]",
                    "## Sources\n\n- [[overview|Overview]]",
                ),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("index entry for overview must be under ## Overview", result.stdout)

    def test_index_entry_type_must_match_page_frontmatter_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            index_path = temp / "wiki/index.md"
            index_path.write_text(
                index_path.read_text(encoding="utf-8").replace(
                    "- [[source-one|Source One]] (`wiki/sources/source-one.md`) - type: source - updated: 2026-05-12 - Test source.",
                    "- [[source-one|Source One]] (`wiki/sources/source-one.md`) - type: concept - updated: 2026-05-12 - Test source.",
                ),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("index entry for source-one has type concept, expected source", result.stdout)

    def test_duplicate_canonical_ids_across_wiki_pages_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            (temp / "wiki/concepts/source-one.md").write_text(
                """---
canonical_id: "source-one"
type: concept
title: "Source One Concept"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: 2026-05-12
last_updated: 2026-05-12
status: seed
confidence: medium
---

# Source One Concept
""",
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate canonical_id: source-one", result.stdout)

    def test_source_provenance_mismatch_with_manifest_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            text = (temp / "wiki/sources/source-one.md").read_text(encoding="utf-8")
            (temp / "wiki/sources/source-one.md").write_text(
                text.replace('content_hash: "sha256:abc123"', 'content_hash: "sha256:different"'),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("provenance content_hash does not match manifest", result.stdout)

    def test_source_provenance_non_core_field_mismatch_with_manifest_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            text = (temp / "wiki/sources/source-one.md").read_text(encoding="utf-8")
            (temp / "wiki/sources/source-one.md").write_text(
                text.replace("source_url: null", 'source_url: "https://example.com/source"'),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("provenance source_url does not match manifest", result.stdout)

    def test_source_provenance_quoted_string_matches_manifest_string(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            manifest_path = temp / "raw/source-manifest.jsonl"
            entry = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry["converter_version"] = "1.2.3"
            manifest_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            text = (temp / "wiki/sources/source-one.md").read_text(encoding="utf-8")
            (temp / "wiki/sources/source-one.md").write_text(
                text.replace("converter_version: null", 'converter_version: "1.2.3"'),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_converted_path_must_exist_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            manifest_path = temp / "raw/source-manifest.jsonl"
            entry = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry["converted_path"] = "raw/converted/source-one.md"
            manifest_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            text = (temp / "wiki/sources/source-one.md").read_text(encoding="utf-8")
            (temp / "wiki/sources/source-one.md").write_text(
                text.replace("converted_path: null", 'converted_path: "raw/converted/source-one.md"'),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("manifest converted_path does not exist: raw/converted/source-one.md", result.stdout)

    def test_inline_yaml_list_frontmatter_is_valid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            text = (temp / "wiki/overview.md").read_text(encoding="utf-8")
            (temp / "wiki/overview.md").write_text(
                text.replace("tags: []", "tags: [knowledge-base]"),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_frontmatter_list_and_scalar_shape_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            text = (temp / "wiki/overview.md").read_text(encoding="utf-8")
            text = text.replace("title: \"Overview\"", "title:")
            text = text.replace("tags: []", "tags: research")
            text = text.replace("status: seed", "status: maybe")
            (temp / "wiki/overview.md").write_text(text, encoding="utf-8")
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 1)
        self.assertIn("frontmatter title must be a non-empty scalar", result.stdout)
        self.assertIn("frontmatter tags must be a YAML list", result.stdout)
        self.assertIn("frontmatter status must be one of: active, archived, needs-review, seed", result.stdout)

    def test_needs_review_status_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            text = (temp / "wiki/overview.md").read_text(encoding="utf-8")
            (temp / "wiki/overview.md").write_text(
                text.replace("status: seed", "status: needs-review"),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
