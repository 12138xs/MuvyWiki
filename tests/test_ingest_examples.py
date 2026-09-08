import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "ingest"
DOMAIN_TEMPLATES = [
    ROOT / "templates" / "sources" / "technical-paper.md",
    ROOT / "templates" / "sources" / "technical-article.md",
    ROOT / "templates" / "sources" / "project-readme.md",
    ROOT / "templates" / "sources" / "meeting-notes.md",
    ROOT / "templates" / "sources" / "journal-entry.md",
]
BASE_SOURCE_FIELDS = [
    'type: source',
    'tags:',
    'aliases:',
    'source_ids:',
    'related_ids:',
    'raw_paths:',
    'provenance:',
    'source_id:',
    'raw_path:',
    'content_hash:',
    'collected_at:',
]
BASE_SOURCE_SECTIONS = [
    '## Summary',
    '## Key Claims',
    '## Evidence and Details',
    '## Concepts',
    '## Entities',
    '## Open Questions',
    '## Contradictions or Tensions',
    '## Raw Source',
]


class IngestExampleTests(unittest.TestCase):
    def test_example_fixture_is_healthy(self):
        result = subprocess.run(
            [sys.executable, "tools/health.py", "--repo-root", str(EXAMPLE)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MuvyWiki health: ok", result.stdout)

    def test_example_fixture_reuses_root_tools(self):
        self.assertEqual([], list((EXAMPLE / "tools").glob("*.py")))

    def test_example_fixture_has_ingest_artifacts(self):
        self.assertTrue((EXAMPLE / "wiki/sources/tiny-rag-note.md").exists())
        self.assertTrue((EXAMPLE / "wiki/concepts/RetrievalAugmentedGeneration.md").exists())
        self.assertTrue((EXAMPLE / "wiki/entities/TinyRagDemo.md").exists())
        log_text = (EXAMPLE / "wiki/log.md").read_text(encoding="utf-8")
        self.assertIn("## [2026-05-13] ingest | tiny-rag-note", log_text)
        manifest_text = (EXAMPLE / "raw/source-manifest.jsonl").read_text(encoding="utf-8")
        self.assertIn('"source_id":"tiny-rag-note"', manifest_text)

    def test_domain_source_templates_have_base_fields_and_sections(self):
        for template in DOMAIN_TEMPLATES:
            with self.subTest(template=template.name):
                text = template.read_text(encoding="utf-8")
                for field in BASE_SOURCE_FIELDS:
                    self.assertIn(field, text)
                for section in BASE_SOURCE_SECTIONS:
                    self.assertIn(section, text)


if __name__ == "__main__":
    unittest.main()
