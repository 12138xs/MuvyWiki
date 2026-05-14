import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import wiki_utils  # noqa: E402


class WikiUtilsTests(unittest.TestCase):
    def test_parse_frontmatter_lists_and_nulls(self):
        text = """---
canonical_id: "Example"
type: concept
tags: [one, "two"]
aliases:
  - "Alias One"
source_ids: []
related_ids:
  - "Other"
published_at: null
---

# Example
"""
        data = wiki_utils.parse_frontmatter(text)
        self.assertEqual(data["canonical_id"], "Example")
        self.assertEqual(data["tags"], ["one", "two"])
        self.assertEqual(data["aliases"], ["Alias One"])
        self.assertEqual(data["source_ids"], [])
        self.assertEqual(data["related_ids"], ["Other"])
        self.assertIsNone(data["published_at"])

    def test_section_bodies_and_useful_text(self):
        text = """# Page

## Summary

- useful

## Empty

## None Marker

- none
"""
        sections = wiki_utils.section_bodies(text)
        self.assertTrue(wiki_utils.has_useful_text(sections["Summary"]))
        self.assertFalse(wiki_utils.has_useful_text(sections["Empty"]))
        self.assertFalse(wiki_utils.has_useful_text(sections["None Marker"]))

    def test_wikilinks_ignore_display_text_and_headings(self):
        text = "See [[ConceptID|Display]], [[Other#Part]], and [[Plain]]."
        self.assertEqual(wiki_utils.extract_wikilinks(text), {"ConceptID", "Other", "Plain"})

    def test_safe_relative_output_rejects_absolute_and_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            allowed = root / "raw" / "converted"
            allowed.mkdir(parents=True)
            ok = wiki_utils.safe_child_path(root, "raw/converted/example.md", allowed)
            self.assertEqual(ok, allowed / "example.md")
            with self.assertRaises(ValueError):
                wiki_utils.safe_child_path(root, "/tmp/example.md", allowed)
            with self.assertRaises(ValueError):
                wiki_utils.safe_child_path(root, "raw/converted/../originals/example.md", allowed)

    def test_safe_relative_output_rejects_required_parent_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            outside = root / "outside"
            outside.mkdir()
            raw = root / "raw"
            raw.mkdir()
            converted = raw / "converted"
            converted.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(ValueError):
                wiki_utils.safe_child_path(root, "raw/converted/example.md", converted)

    def test_safe_relative_output_rejects_nested_parent_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            allowed = root / "raw" / "converted"
            allowed.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            nested = allowed / "nested"
            nested.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(ValueError):
                wiki_utils.safe_child_path(root, "raw/converted/nested/example.md", allowed)

    def test_safe_relative_output_rejects_existing_leaf_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            allowed = root / "raw" / "converted"
            allowed.mkdir(parents=True)
            outside = root / "outside.md"
            output = allowed / "example.md"
            output.symlink_to(outside)

            with self.assertRaises(ValueError):
                wiki_utils.safe_child_path(root, "raw/converted/example.md", allowed)

    def test_hash_bytes_uses_sha256_prefix(self):
        self.assertEqual(
            wiki_utils.sha256_bytes(b"abc"),
            "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_page_helpers_load_metadata_and_body(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "wiki/concepts").mkdir(parents=True)
            (root / "wiki/entities").mkdir(parents=True)
            (root / "wiki/sources").mkdir(parents=True)
            (root / "wiki/syntheses").mkdir(parents=True)
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
created: 2026-05-14
last_updated: 2026-05-14
status: seed
confidence: medium
---

# Overview

## Summary

Root page.
""",
                encoding="utf-8",
            )
            (root / "wiki/concepts/RAG.md").write_text(
                """---
canonical_id: "RAG"
type: concept
title: "Retrieval-Augmented Generation"
tags:
  - retrieval
aliases:
  - "RAG"
source_ids:
  - "source-one"
related_ids: []
raw_paths: []
created: 2026-05-14
last_updated: 2026-05-14
status: seed
confidence: medium
---

# Retrieval-Augmented Generation

## Definition

Retrieval before generation.
""",
                encoding="utf-8",
            )

            pages = wiki_utils.load_wiki_pages(root)
            by_id = {page.id: page for page in pages}
            self.assertEqual(by_id["RAG"].title, "Retrieval-Augmented Generation")
            self.assertEqual(by_id["RAG"].type, "concept")
            self.assertEqual(by_id["RAG"].tags, ["retrieval"])
            self.assertEqual(by_id["RAG"].aliases, ["RAG"])
            self.assertEqual(by_id["RAG"].source_ids, ["source-one"])
            self.assertIn("Retrieval before generation.", by_id["RAG"].body)
            self.assertEqual(wiki_utils.canonical_page_map(root)["RAG"].path.name, "RAG.md")

    def test_id_yaml_and_excerpt_helpers(self):
        self.assertTrue(wiki_utils.is_kebab_id("rag-systems-architecture-survey"))
        self.assertFalse(wiki_utils.is_kebab_id("RAGSystems"))
        self.assertEqual(wiki_utils.yaml_list(["rag", "agents"]), ['  - "rag"', '  - "agents"'])
        self.assertEqual(wiki_utils.yaml_list([]), ["[]"])
        excerpt = wiki_utils.bounded_excerpt("alpha beta gamma delta", {"gamma"}, limit=16)
        self.assertIn("gamma", excerpt)
        self.assertLessEqual(len(excerpt), 19)


if __name__ == "__main__":
    unittest.main()
