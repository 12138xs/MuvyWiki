import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LintToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in ("tools", "wiki/sources", "wiki/concepts", "wiki/entities", "wiki/syntheses", "graph"):
            (root / rel).mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "tools" / "lint.py", root / "tools" / "lint.py")
        shutil.copy(ROOT / "tools" / "wiki_utils.py", root / "tools" / "wiki_utils.py")
        (root / "wiki/overview.md").write_text(
            self.page(
                "overview",
                "overview",
                "Overview",
                'source_ids: []\nrelated_ids:\n  - "ConceptOne"\nraw_paths: []',
                "[[ConceptOne]]",
            ),
            encoding="utf-8",
        )
        (root / "wiki/concepts/ConceptOne.md").write_text(
            self.page(
                "ConceptOne",
                "concept",
                "Concept One",
                'source_ids:\n  - "source-one"\nrelated_ids: []\nraw_paths: []',
                "[[source-one|Source One]]",
            ),
            encoding="utf-8",
        )
        (root / "wiki/sources/source-one.md").write_text(
            self.source_page(claims="- Claim\n", evidence="- Evidence\n"),
            encoding="utf-8",
        )
        return temp_dir, root

    def page(self, cid, page_type, title, extra_frontmatter, body, supporting_sources="[[source-one|Source One]]"):
        return f'''---
canonical_id: "{cid}"
type: {page_type}
title: "{title}"
tags: []
aliases: []
{extra_frontmatter}
created: 2026-05-13
last_updated: 2026-05-13
status: seed
confidence: medium
---

# {title}

## Summary

{body}

## Supporting Sources

{supporting_sources}
'''

    def source_page(self, claims, evidence):
        return f'''---
canonical_id: "source-one"
type: source
title: "Source One"
tags: []
aliases: []
source_ids: []
related_ids:
  - "ConceptOne"
raw_paths: []
created: 2026-05-13
last_updated: 2026-05-13
status: active
confidence: medium
provenance:
  source_id: "source-one"
  raw_path: "raw/originals/source.md"
  content_hash: "sha256:abc"
  source_url: null
  collected_at: "2026-05-13"
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# Source One

## Summary

Summary.

## Key Claims

{claims}

## Evidence and Details

{evidence}
'''

    def entity_page(self, evidence):
        return f'''---
canonical_id: "EntityOne"
type: entity
title: "Entity One"
tags: []
aliases: []
source_ids:
  - "source-one"
related_ids: []
raw_paths: []
created: 2026-05-13
last_updated: 2026-05-13
status: seed
confidence: medium
---

# Entity One

## Summary

Summary.

## Evidence

{evidence}
'''

    def run_lint(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/lint.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_current_repository_has_no_lint_issues(self):
        result = subprocess.run(
            [sys.executable, "tools/lint.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MuvyWiki lint: ok", result.stdout)

    def test_json_output_for_clean_fixture(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_lint(root, "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["issues"], [])
            self.assertRegex(payload["checked_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_reports_missing_source_claims_and_evidence(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "wiki/sources/source-one.md").write_text(
                self.source_page(claims="", evidence="- none\n"),
                encoding="utf-8",
            )
            result = self.run_lint(root, "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            checks = {issue["check"] for issue in payload["issues"]}
            self.assertIn("missing-source-claims", checks)
            self.assertIn("missing-source-evidence", checks)

    def test_reports_missing_concept_sources(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "wiki/concepts/ConceptOne.md").write_text(
                self.page(
                    "ConceptOne",
                    "concept",
                    "Concept One",
                    "source_ids: []\nrelated_ids: []\nraw_paths: []",
                    "[[ConceptOne]]",
                    supporting_sources="- none\n",
                ),
                encoding="utf-8",
            )
            result = self.run_lint(root, "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            checks = {issue["check"] for issue in payload["issues"]}
            self.assertIn("missing-concept-sources", checks)

    def test_reports_missing_entity_evidence(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "wiki/overview.md").write_text(
                self.page(
                    "overview",
                    "overview",
                    "Overview",
                    'source_ids: []\nrelated_ids:\n  - "ConceptOne"\n  - "EntityOne"\nraw_paths: []',
                    "[[ConceptOne]] [[EntityOne]]",
                ),
                encoding="utf-8",
            )
            (root / "wiki/entities/EntityOne.md").write_text(self.entity_page("- none\n"), encoding="utf-8")
            result = self.run_lint(root, "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            checks = {issue["check"] for issue in payload["issues"]}
            self.assertIn("missing-entity-evidence", checks)

    def test_reports_orphan_page(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "wiki/overview.md").write_text(
                self.page("overview", "overview", "Overview", "source_ids: []\nrelated_ids: []\nraw_paths: []", "No links."),
                encoding="utf-8",
            )
            result = self.run_lint(root, "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            checks = {issue["check"] for issue in payload["issues"]}
            self.assertIn("orphan-page", checks)

    def test_reports_stale_index_empty_state(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "wiki/index.md").write_text(
                """# MuvyWiki Index

## Sources

No source pages yet.

## Concepts

No concept pages yet.
""",
                encoding="utf-8",
            )
            result = self.run_lint(root, "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            checks = {issue["check"] for issue in payload["issues"]}
            self.assertIn("stale-index-summary", checks)

    def test_writes_markdown_report(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_lint(root, "--report", "graph/lint-report.md")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = (root / "graph/lint-report.md").read_text(encoding="utf-8")
            self.assertIn("# MuvyWiki Lint Report", report)
            self.assertIn("- Status: ok", report)
            self.assertRegex(report, r"- Checked at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
            self.assertIn("## Issues", report)
            self.assertIn("No lint issues found.", report)

    def test_default_markdown_report_does_not_clobber_graph_report(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "graph/graph-report.md").write_text("# MuvyWiki Graph Report\n", encoding="utf-8")
            result = self.run_lint(root, "--report")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / "graph/graph-report.md").read_text(encoding="utf-8"), "# MuvyWiki Graph Report\n")
            self.assertIn("# MuvyWiki Lint Report", (root / "graph/lint-report.md").read_text(encoding="utf-8"))

    def test_rejects_invalid_report_path(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_lint(root, "--report", "graph/../lint-report.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Invalid report path", result.stderr)


if __name__ == "__main__":
    unittest.main()
