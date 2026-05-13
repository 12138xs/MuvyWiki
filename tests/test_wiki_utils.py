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


if __name__ == "__main__":
    unittest.main()
