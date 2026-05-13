import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildGraphToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in ("tools", "wiki/sources", "wiki/concepts", "wiki/entities", "wiki/syntheses", "raw/originals", "graph"):
            (root / rel).mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "tools" / "build_graph.py", root / "tools" / "build_graph.py")
        shutil.copy(ROOT / "tools" / "wiki_utils.py", root / "tools" / "wiki_utils.py")
        (root / "raw/originals/source.md").write_text("raw\n", encoding="utf-8")
        (root / "wiki/overview.md").write_text(self.page("overview", "overview", "Overview", "source_ids: []\nrelated_ids:\n  - \"ConceptOne\"\nraw_paths: []", "[[ConceptOne]]"), encoding="utf-8")
        (root / "wiki/sources/source-one.md").write_text(self.source_page(), encoding="utf-8")
        (root / "wiki/concepts/ConceptOne.md").write_text(self.page("ConceptOne", "concept", "Concept One", "source_ids:\n  - \"source-one\"\nrelated_ids:\n  - \"EntityOne\"\nraw_paths: []", "[[source-one|Source One]] [[EntityOne]]"), encoding="utf-8")
        (root / "wiki/entities/EntityOne.md").write_text(self.page("EntityOne", "entity", "Entity One", "source_ids:\n  - \"source-one\"\nrelated_ids: []\nraw_paths: []", "[[ConceptOne]]"), encoding="utf-8")
        return temp_dir, root

    def page(self, cid, page_type, title, extra_frontmatter, body):
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
'''

    def source_page(self):
        return '''---
canonical_id: "source-one"
type: source
title: "Source One"
tags: []
aliases: []
source_ids: []
related_ids:
  - "ConceptOne"
raw_paths:
  - "raw/originals/source.md"
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

[[ConceptOne]]
'''

    def run_graph(self, root):
        return subprocess.run(
            [
                sys.executable,
                "tools/build_graph.py",
                "--json",
                "graph/test-graph.json",
                "--html",
                "graph/test-graph.html",
                "--report",
                "graph/test-graph-report.md",
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_builds_graph_artifacts(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_graph(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads((root / "graph/test-graph.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["node_count"], 4)
            edge_types = {edge["type"] for edge in payload["edges"]}
            self.assertIn("wikilink", edge_types)
            self.assertIn("source", edge_types)
            self.assertIn("related", edge_types)
            self.assertIn("raw", edge_types)
            html_text = (root / "graph/test-graph.html").read_text(encoding="utf-8")
            self.assertIn("MuvyWiki Graph", html_text)
            script_match = re.search(
                r'<script type="application/json" id="graph-data">(?P<data>.*?)</script>',
                html_text,
                re.DOTALL,
            )
            self.assertIsNotNone(script_match)
            script_payload = json.loads(script_match.group("data"))
            self.assertEqual(script_payload["summary"]["node_count"], 4)
            self.assertIn("# MuvyWiki Graph Report", (root / "graph/test-graph-report.md").read_text(encoding="utf-8"))

    def test_rejects_output_outside_graph_directory(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = subprocess.run(
                [sys.executable, "tools/build_graph.py", "--json", "graph/../escape.json"],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 2)

    def test_rejects_symlinked_graph_directory(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            shutil.rmtree(root / "graph")
            outside = root / "outside"
            outside.mkdir()
            (root / "graph").symlink_to(outside, target_is_directory=True)

            result = subprocess.run(
                [sys.executable, "tools/build_graph.py", "--json", "graph/test-graph.json"],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 2)

    def test_rejects_symlinked_json_output_leaf(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            outside = root.parent / "leaked.json"
            outside.write_text("unchanged\n", encoding="utf-8")
            (root / "graph/test-graph.json").symlink_to(outside)

            result = self.run_graph(root)

            self.assertEqual(result.returncode, 2)
            self.assertEqual(outside.read_text(encoding="utf-8"), "unchanged\n")

    def test_embedded_json_is_script_safe(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            concept_path = root / "wiki/concepts/ConceptOne.md"
            concept_path.write_text(
                concept_path.read_text(encoding="utf-8").replace(
                    'title: "Concept One"',
                    'title: "</script><p>broken</p>"',
                ),
                encoding="utf-8",
            )
            result = self.run_graph(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            html_text = (root / "graph/test-graph.html").read_text(encoding="utf-8")
            self.assertEqual(html_text.count("</script>"), 1)
            script_match = re.search(
                r'<script type="application/json" id="graph-data">(?P<data>.*?)</script>',
                html_text,
                re.DOTALL,
            )
            self.assertIsNotNone(script_match)
            payload = json.loads(script_match.group("data"))
            titles = {node["title"] for node in payload["nodes"]}
            self.assertIn("</script><p>broken</p>", titles)


if __name__ == "__main__":
    unittest.main()
