import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class QueryToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in ("tools", "wiki/sources", "wiki/concepts", "wiki/entities", "wiki/syntheses"):
            (root / rel).mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "tools" / "wiki_utils.py", root / "tools" / "wiki_utils.py")
        shutil.copy(ROOT / "tools" / "query.py", root / "tools" / "query.py")
        self.write_page(root / "wiki/overview.md", "overview", "overview", "Overview", [], [], "Knowledge map.")
        self.write_page(
            root / "wiki/concepts/RetrievalAugmentedGeneration.md",
            "RetrievalAugmentedGeneration",
            "concept",
            "Retrieval-Augmented Generation",
            ["rag", "retrieval"],
            ["RAG"],
            "## Definition\n\nRetrieval-Augmented Generation retrieves source context before generation.\n",
            source_ids=["rag-source"],
            related_ids=["VectorSearch"],
        )
        self.write_page(
            root / "wiki/concepts/VectorSearch.md",
            "VectorSearch",
            "concept",
            "Vector Search",
            ["retrieval"],
            [],
            "## Definition\n\nVector search finds nearest neighbors.\n",
        )
        self.write_page(
            root / "wiki/sources/rag-source.md",
            "rag-source",
            "source",
            "RAG Source",
            ["paper"],
            [],
            "## Summary\n\nA source about [[RetrievalAugmentedGeneration|RAG]].\n",
        )
        self.write_page(
            root / "wiki/entities/OpenAI.md",
            "OpenAI",
            "entity",
            "OpenAI",
            ["organization"],
            [],
            "## Summary\n\nOrganization page.\n",
        )
        self.write_page(
            root / "wiki/concepts/Bragging.md",
            "Bragging",
            "concept",
            "Bragging",
            ["bragging"],
            [],
            "## Definition\n\nConfidence claims without grounding.\n",
        )
        return temp_dir, root

    def write_page(self, path, cid, page_type, title, tags, aliases, body, source_ids=None, related_ids=None):
        source_ids = source_ids or []
        related_ids = related_ids or []
        path.write_text(
            f'''---
canonical_id: "{cid}"
type: {page_type}
title: "{title}"
tags:
{self.yaml_list(tags)}
aliases:
{self.yaml_list(aliases)}
source_ids:
{self.yaml_list(source_ids)}
related_ids:
{self.yaml_list(related_ids)}
raw_paths: []
created: 2026-05-14
last_updated: 2026-05-14
status: seed
confidence: medium
---

# {title}

{body}
''',
            encoding="utf-8",
        )

    def yaml_list(self, values):
        if not values:
            return "  []"
        return "\n".join(f'  - "{value}"' for value in values)

    def run_query(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/query.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_json_ranks_exact_alias_and_title_matches(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_query(root, "RAG retrieval", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["retrieval_mode"], "keyword-lite")
            self.assertGreaterEqual(len(payload["matches"]), 2)
            self.assertEqual(payload["matches"][0]["id"], "RetrievalAugmentedGeneration")
            self.assertIn("rag", payload["matches"][0]["matched_terms"])
            self.assertIn("retrieval", payload["matches"][0]["matched_terms"])

    def test_text_output_limit_and_type_filter(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_query(root, "retrieval", "--limit", "1", "--type", "source")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("MuvyWiki query: 1 match(es)", result.stdout)
            self.assertIn("rag-source", result.stdout)
            self.assertNotIn("RetrievalAugmentedGeneration", result.stdout)

    def test_include_sections_returns_bounded_excerpt(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_query(root, "source context", "--json", "--include-sections")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            sections = payload["matches"][0]["sections"]
            self.assertTrue(sections)
            self.assertIn("excerpt", sections[0])
            self.assertLessEqual(len(sections[0]["excerpt"]), 260)

    def test_text_include_sections_prints_section_excerpts(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_query(root, "source context", "--include-sections")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("sections:", result.stdout)
            self.assertIn("Definition:", result.stdout)
            self.assertIn("retrieves source context", result.stdout)

    def test_metadata_substrings_do_not_receive_exact_match_score(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_query(root, "rag", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertGreaterEqual(len(payload["matches"]), 1)
            self.assertEqual(payload["matches"][0]["id"], "RetrievalAugmentedGeneration")
            self.assertNotIn("Bragging", [match["id"] for match in payload["matches"]])

    def test_no_matches_is_success(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_query(root, "nonexistentterm", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["matches"], [])

    def test_rejects_empty_query_invalid_limit_and_invalid_type(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            empty = self.run_query(root, "   ")
            self.assertEqual(empty.returncode, 2)
            bad_limit = self.run_query(root, "rag", "--limit", "0")
            self.assertEqual(bad_limit.returncode, 2)
            bad_type = self.run_query(root, "rag", "--type", "paper")
            self.assertEqual(bad_type.returncode, 2)
            empty_type = self.run_query(root, "rag", "--type", ",")
            self.assertEqual(empty_type.returncode, 2)


if __name__ == "__main__":
    unittest.main()
