# Interface v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the reserved `lint.py`, `build_graph.py`, and `convert.py` interfaces as lightweight, deterministic, documented tools.

**Architecture:** Add a small shared parsing helper module under `tools/` so lint and graph generation use the same wiki/frontmatter/wikilink rules. Keep `health.py` as the structural gate and keep conversion separate from ingest: `convert.py` writes converted artifacts only, while agents still update manifest and wiki pages.

**Tech Stack:** Python 3 standard library, `unittest`, Markdown, JSON, existing MuvyWiki templates and docs.

---

## File Structure

Create:

- `tools/wiki_utils.py` - shared parser/path/hash helpers for tool implementations.
- `tests/test_wiki_utils.py` - tests for shared parser/path/hash helpers.
- `tests/test_convert.py` - tests for implemented conversion behavior.
- `tests/test_build_graph.py` - tests for graph artifact generation.
- `tests/test_lint.py` - tests for semantic-lite lint behavior.
- `tests/test_docs_interfaces.py` - tests that docs no longer describe implemented tools as reserved.
- `examples/ingest/tools/wiki_utils.py` - fixture copy of the shared helper.

Modify:

- `tools/convert.py` - implement safe local Markdown/text conversion.
- `tools/build_graph.py` - implement JSON, HTML, and Markdown graph artifacts.
- `tools/lint.py` - implement conservative semantic-lite lint checks.
- `examples/ingest/tools/convert.py` - keep fixture copy consistent with root tool.
- `examples/ingest/tools/build_graph.py` - keep fixture copy consistent with root tool.
- `examples/ingest/tools/lint.py` - keep fixture copy consistent with root tool.
- `README.md` - update current status table and commands.
- `USER_GUIDE.md` - update tool capability and workflow sections.
- `AGENTS.md` - update implemented interface rules.
- `raw/README.md` - update conversion behavior and manifest boundary.
- `graph/README.md` - update graph artifact contract.
- `examples/ingest/README.md` - update fixture validation notes.

Delete:

- `tests/test_reserved_tools.py` - replace reserved-exit-code tests with implemented behavior tests.

Do not modify:

- `tools/health.py` unless a test proves a necessary compatibility fix.
- Existing wiki pages except documentation listed above.

## Task 1: Shared Tool Utilities

**Files:**
- Create: `tools/wiki_utils.py`
- Create: `tests/test_wiki_utils.py`
- Later copy: `examples/ingest/tools/wiki_utils.py`

- [ ] **Step 1: Write tests for shared parsing helpers**

Create `tests/test_wiki_utils.py`:

```python
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

    def test_hash_bytes_uses_sha256_prefix(self):
        self.assertEqual(
            wiki_utils.sha256_bytes(b"abc"),
            "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
python -m unittest tests/test_wiki_utils.py
```

Expected: fail with `ModuleNotFoundError: No module named 'wiki_utils'`.

- [ ] **Step 3: Implement `tools/wiki_utils.py`**

Create `tools/wiki_utils.py` with these public functions:

```python
#!/usr/bin/env python3
"""Shared utilities for MuvyWiki command-line tools."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
SECTION_RE = re.compile(r"^## (?P<title>.+?)\s*$", re.MULTILINE)
NONE_MARKERS = {"none", "- none", "no supporting sources yet.", "no synthesis pages yet."}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def safe_child_path(root: Path, rel_path: str, required_parent: Path | None = None) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise ValueError("path must be relative")
    root_resolved = root.resolve()
    output = (root_resolved / candidate).resolve()
    parent = required_parent.resolve() if required_parent is not None else root_resolved
    try:
        output.relative_to(parent)
    except ValueError as exc:
        raise ValueError(f"path must stay under {parent.relative_to(root_resolved).as_posix() if parent != root_resolved else '.'}") from exc
    if output == parent:
        raise ValueError("path must point to a file")
    return output


def content_after_frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    return text[match.end():] if match else text


def frontmatter_body(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    return match.group("body") if match else ""


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"null", "~"}:
        return None
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(item.strip()) for item in inner.split(",")]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, Any]:
    body = frontmatter_body(text)
    if not body:
        return {}
    lines = body.splitlines()
    result: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.startswith(" "):
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            result[key] = parse_scalar(raw_value)
            index += 1
            continue
        values: list[Any] = []
        nested: dict[str, Any] = {}
        index += 1
        while index < len(lines) and lines[index].startswith("  "):
            child = lines[index].strip()
            if child.startswith("- "):
                values.append(parse_scalar(child[2:].strip()))
            elif ":" in child:
                child_key, child_value = child.split(":", 1)
                nested[child_key.strip()] = parse_scalar(child_value.strip())
            index += 1
        result[key] = values if values else nested
    return result


def extract_provenance(text: str) -> dict[str, Any]:
    provenance = parse_frontmatter(text).get("provenance")
    return provenance if isinstance(provenance, dict) else {}


def extract_wikilinks(text: str) -> set[str]:
    return set(WIKILINK_RE.findall(text))


def section_bodies(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[match.group("title").strip()] = text[start:end].strip()
    return sections


def has_useful_text(text: str) -> bool:
    stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not stripped_lines:
        return False
    lowered = "\n".join(stripped_lines).lower()
    return lowered not in NONE_MARKERS


def collect_wiki_pages(root: Path) -> list[Path]:
    pages: list[Path] = []
    for folder in ("sources", "concepts", "entities", "syntheses"):
        base = root / "wiki" / folder
        if base.exists():
            pages.extend(sorted(base.glob("*.md")))
    overview = root / "wiki" / "overview.md"
    if overview.exists():
        pages.append(overview)
    return pages


def repo_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
```

- [ ] **Step 4: Run helper tests**

Run:

```bash
python -m unittest tests/test_wiki_utils.py
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit shared utilities**

Run:

```bash
git add tools/wiki_utils.py tests/test_wiki_utils.py
git commit -m "feat: add shared wiki tool utilities"
```

Expected: commit succeeds.

## Task 2: Convert Interface v1

**Files:**
- Modify: `tools/convert.py`
- Create: `tests/test_convert.py`
- Delete later: `tests/test_reserved_tools.py`

- [ ] **Step 1: Write conversion tests**

Create `tests/test_convert.py`:

```python
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConvertToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / "tools").mkdir()
        (root / "raw" / "originals").mkdir(parents=True)
        (root / "raw" / "converted").mkdir(parents=True)
        shutil.copy(ROOT / "tools" / "convert.py", root / "tools" / "convert.py")
        shutil.copy(ROOT / "tools" / "wiki_utils.py", root / "tools" / "wiki_utils.py")
        return temp_dir, root

    def run_convert(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/convert.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_converts_markdown_without_wrapping(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/note.md").write_text("# Existing\n\nBody\r\n", encoding="utf-8")
            result = self.run_convert(root, "raw/originals/note.md", "--out", "raw/converted/note.md")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Converted raw/originals/note.md -> raw/converted/note.md", result.stdout)
            self.assertEqual((root / "raw/converted/note.md").read_text(encoding="utf-8"), "# Existing\n\nBody\n")

    def test_converts_plain_text_with_heading(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/plain.txt").write_text("line one\nline two\n", encoding="utf-8")
            result = self.run_convert(root, "raw/originals/plain.txt", "--out", "raw/converted/plain.md")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            text = (root / "raw/converted/plain.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# plain\n\n"))
            self.assertIn("line one\nline two\n", text)

    def test_json_output_contains_hashes_and_counts(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/plain.txt").write_text("hello\n", encoding="utf-8")
            result = self.run_convert(root, "raw/originals/plain.txt", "--out", "raw/converted/plain.md", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["input_path"], "raw/originals/plain.txt")
            self.assertEqual(payload["output_path"], "raw/converted/plain.md")
            self.assertTrue(payload["input_hash"].startswith("sha256:"))
            self.assertTrue(payload["output_hash"].startswith("sha256:"))
            self.assertGreater(payload["output_bytes"], payload["input_bytes"])

    def test_rejects_remote_url(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_convert(root, "https://example.com/page", "--out", "raw/converted/page.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Remote URLs are not supported", result.stderr)

    def test_rejects_unsupported_extension(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/file.pdf").write_bytes(b"%PDF-")
            result = self.run_convert(root, "raw/originals/file.pdf", "--out", "raw/converted/file.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unsupported input type", result.stderr)

    def test_rejects_absolute_and_traversal_output(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/plain.txt").write_text("hello\n", encoding="utf-8")
            absolute = self.run_convert(root, "raw/originals/plain.txt", "--out", "/tmp/plain.md")
            self.assertEqual(absolute.returncode, 2)
            traversal = self.run_convert(root, "raw/originals/plain.txt", "--out", "raw/converted/../originals/plain.md")
            self.assertEqual(traversal.returncode, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run conversion tests and verify they fail**

Run:

```bash
python -m unittest tests/test_convert.py
```

Expected: tests fail because `convert.py` still returns reserved exit code `3`.

- [ ] **Step 3: Implement conversion behavior**

Modify `tools/convert.py` to:

- Import `json`, `re`, and `wiki_utils`.
- Keep `input_path_or_url` and `--out`.
- Add `--json`.
- Reject strings matching `^[a-zA-Z][a-zA-Z0-9+.-]*://` with exit code `2`.
- Accept only local `.md`, `.markdown`, `.txt`, or extensionless inputs.
- Reject absolute input paths outside the repository root.
- Use `wiki_utils.safe_child_path(ROOT, args.out, CONVERTED_ROOT)` for output.
- Normalize `\r\n` and `\r` to `\n`.
- Preserve Markdown if the input suffix is `.md` or `.markdown`.
- For plain text without a leading Markdown heading, write `# <input-stem>\n\n` before the normalized text.
- Write output bytes as UTF-8.
- Print JSON exactly when `--json` is set; otherwise print one success line.

Use this error helper:

```python
def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2
```

- [ ] **Step 4: Run conversion tests**

Run:

```bash
python -m unittest tests/test_convert.py
```

Expected: all conversion tests pass.

- [ ] **Step 5: Commit conversion implementation**

Run:

```bash
git add tools/convert.py tests/test_convert.py
git commit -m "feat: implement local text conversion"
```

Expected: commit succeeds.

## Task 3: Graph Interface v1

**Files:**
- Modify: `tools/build_graph.py`
- Create: `tests/test_build_graph.py`

- [ ] **Step 1: Write graph tests**

Create `tests/test_build_graph.py`:

```python
import json
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
            self.assertIn("MuvyWiki Graph", (root / "graph/test-graph.html").read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run graph tests and verify they fail**

Run:

```bash
python -m unittest tests/test_build_graph.py
```

Expected: tests fail because `build_graph.py` still returns reserved exit code `3`.

- [ ] **Step 3: Implement graph generation**

Modify `tools/build_graph.py` to:

- Import `html`, `json`, `sys`, `Path`, and `wiki_utils`.
- Resolve output paths with `wiki_utils.safe_child_path(ROOT, path, ROOT / "graph")`.
- Collect wiki pages with `wiki_utils.collect_wiki_pages(ROOT)`.
- Build one node per page using parsed frontmatter.
- Add `wikilink` edges from page ID to linked canonical IDs.
- Add `source` edges from page ID to each `source_ids` entry.
- Add `related` edges from page ID to each `related_ids` entry.
- Add `raw` edges from source page ID to each `raw_paths` entry and provenance `raw_path`.
- De-duplicate edges by `(source, target, type, path)`.
- Write JSON with `generated_at`, `nodes`, `edges`, and `summary`.
- Write Markdown report with node counts by type and edge counts by type.
- Write self-contained HTML with embedded graph JSON, node table, and edge table.
- Print `Wrote graph/graph.json, graph/graph.html, graph/graph-report.md` using the actual paths.
- Return exit code `0`.
- Return exit code `2` and a stderr message for invalid output paths.

- [ ] **Step 4: Run graph tests**

Run:

```bash
python -m unittest tests/test_build_graph.py
```

Expected: all graph tests pass.

- [ ] **Step 5: Commit graph implementation**

Run:

```bash
git add tools/build_graph.py tests/test_build_graph.py
git commit -m "feat: generate wiki graph artifacts"
```

Expected: commit succeeds.

## Task 4: Lint Interface v1

**Files:**
- Modify: `tools/lint.py`
- Create: `tests/test_lint.py`

- [ ] **Step 1: Write lint tests**

Create `tests/test_lint.py`:

```python
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
        (root / "wiki/overview.md").write_text(self.page("overview", "overview", "Overview", "source_ids: []\nrelated_ids:\n  - \"ConceptOne\"\nraw_paths: []", "[[ConceptOne]]"), encoding="utf-8")
        (root / "wiki/concepts/ConceptOne.md").write_text(self.page("ConceptOne", "concept", "Concept One", "source_ids:\n  - \"source-one\"\nrelated_ids: []\nraw_paths: []", "[[source-one|Source One]]"), encoding="utf-8")
        (root / "wiki/sources/source-one.md").write_text(self.source_page(claims="- Claim\n", evidence="- Evidence\n"), encoding="utf-8")
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

## Supporting Sources

[[source-one|Source One]]
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

    def test_reports_missing_source_claims_and_evidence(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "wiki/sources/source-one.md").write_text(self.source_page(claims="", evidence="- none\n"), encoding="utf-8")
            result = self.run_lint(root, "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            checks = {issue["check"] for issue in payload["issues"]}
            self.assertIn("missing-source-claims", checks)
            self.assertIn("missing-source-evidence", checks)

    def test_writes_markdown_report(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_lint(root, "--report", "graph/lint-report.md")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = (root / "graph/lint-report.md").read_text(encoding="utf-8")
            self.assertIn("# MuvyWiki Lint Report", report)
            self.assertIn("No lint issues found.", report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run lint tests and verify they fail**

Run:

```bash
python -m unittest tests/test_lint.py
```

Expected: tests fail because `lint.py` still returns reserved exit code `3`.

- [ ] **Step 3: Implement lint behavior**

Modify `tools/lint.py` to:

- Add `--json` while preserving `--report`.
- Use `wiki_utils.collect_wiki_pages(ROOT)`.
- Parse frontmatter, body sections, and wikilinks.
- Emit issue dictionaries with keys `severity`, `path`, `check`, and `message`.
- Check empty required sections for page sections that exist but have no useful body.
- Check source pages for missing useful `Key Claims`.
- Check source pages for missing useful `Evidence and Details`.
- Check concept pages for empty `source_ids` and no wikilink in `Supporting Sources`.
- Check entity pages for missing useful `Evidence`.
- Check concept/entity/synthesis pages for orphan status by counting incoming wikilinks from all other pages and overview references.
- Write Markdown report to the requested path under `graph/`.
- Print `MuvyWiki lint: ok` or `MuvyWiki lint: issues`.
- Return `0` with no issues, `1` with issues, `2` for invalid report path.

- [ ] **Step 4: Run lint tests**

Run:

```bash
python -m unittest tests/test_lint.py
```

Expected: all lint tests pass.

- [ ] **Step 5: Commit lint implementation**

Run:

```bash
git add tools/lint.py tests/test_lint.py
git commit -m "feat: implement semantic-lite lint"
```

Expected: commit succeeds.

## Task 5: Replace Reserved Tests and Sync Fixture Tool Copies

**Files:**
- Delete: `tests/test_reserved_tools.py`
- Create: `tests/test_docs_interfaces.py`
- Create: `examples/ingest/tools/wiki_utils.py`
- Modify: `examples/ingest/tools/convert.py`
- Modify: `examples/ingest/tools/build_graph.py`
- Modify: `examples/ingest/tools/lint.py`

- [ ] **Step 1: Delete old reserved-tool tests**

Run:

```bash
rm tests/test_reserved_tools.py
```

Expected: file removed.

- [ ] **Step 2: Add documentation consistency tests**

Create `tests/test_docs_interfaces.py`:

```python
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsInterfaceTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_readme_marks_tools_implemented_or_partial(self):
        readme = self.read("README.md")
        self.assertIn("| Semantic lint | Implemented |", readme)
        self.assertIn("| Graph generation | Implemented |", readme)
        self.assertIn("| Source conversion | Partial |", readme)
        self.assertNotIn("returns exit code `3`", readme)

    def test_agents_do_not_call_interfaces_reserved(self):
        agents = self.read("AGENTS.md")
        self.assertIn("Implemented deterministic interfaces", agents)
        self.assertIn("python tools/lint.py", agents)
        self.assertIn("python tools/build_graph.py", agents)
        self.assertIn("python tools/convert.py", agents)
        self.assertNotIn("Reserved interfaces:", agents)

    def test_raw_and_graph_docs_describe_current_outputs(self):
        raw = self.read("raw/README.md")
        graph = self.read("graph/README.md")
        self.assertIn("local Markdown/text conversion", raw)
        self.assertIn("does not update source-manifest.jsonl", raw)
        self.assertIn("graph.json", graph)
        self.assertIn("graph.html", graph)
        self.assertIn("graph-report.md", graph)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Copy implemented tools into the ingest fixture**

Run:

```bash
cp tools/wiki_utils.py examples/ingest/tools/wiki_utils.py
cp tools/convert.py examples/ingest/tools/convert.py
cp tools/build_graph.py examples/ingest/tools/build_graph.py
cp tools/lint.py examples/ingest/tools/lint.py
```

Expected: commands exit `0`.

- [ ] **Step 4: Run fixture tool smoke checks**

Run:

```bash
(cd examples/ingest && python tools/lint.py)
(cd examples/ingest && python tools/build_graph.py)
```

Expected:

- `lint.py` exits `0` and prints `MuvyWiki lint: ok`.
- `build_graph.py` exits `0` and writes ignored graph artifacts under `examples/ingest/graph/`.

- [ ] **Step 5: Run tests for docs and fixture health**

Run:

```bash
python -m unittest tests/test_docs_interfaces.py
cd examples/ingest && python tools/health.py
```

Expected: docs tests pass and fixture health is ok.

- [ ] **Step 6: Commit test replacement and fixture tool sync**

Run:

```bash
git add tests/test_docs_interfaces.py tests/test_reserved_tools.py examples/ingest/tools
git commit -m "test: replace reserved interface expectations"
```

Expected: commit succeeds.

## Task 6: Documentation Updates

**Files:**
- Modify: `README.md`
- Modify: `USER_GUIDE.md`
- Modify: `AGENTS.md`
- Modify: `raw/README.md`
- Modify: `graph/README.md`
- Modify: `examples/ingest/README.md`

- [ ] **Step 1: Update `README.md` status table**

Replace the current reserved rows with:

```markdown
| Semantic lint | Implemented | `python tools/lint.py`, `python tools/lint.py --json`, `python tools/lint.py --report graph/graph-report.md` |
| Graph generation | Implemented | `python tools/build_graph.py` |
| Source conversion | Partial | `python tools/convert.py <local-md-or-text> --out raw/converted/<file>.md` |
```

Also replace the final reserved-tools paragraph with:

```markdown
`convert.py` supports local Markdown/text inputs only. PDF, Office documents, remote URLs, HTML rendering, embeddings, and LLM-based extraction remain future work.
```

- [ ] **Step 2: Update `USER_GUIDE.md` capability sections**

In `当前功能与接口状态`, move lint and graph into the implemented list. Keep convert as partial:

```markdown
- `python tools/lint.py`：语义轻量 lint，检查空章节、缺少 claims/evidence、孤立页面等维护风险。
- `python tools/build_graph.py`：生成 `graph/graph.json`、`graph/graph.html`、`graph/graph-report.md`。
- `python tools/convert.py <input> --out raw/converted/<file>`：本地 Markdown/text 转换入口；不会自动更新 manifest 或 wiki 页面。
```

Replace the reserved-tool section with `## 工具接口` and state:

```markdown
PDF、Office、远程网页、HTML 渲染和二进制文件仍不支持。需要先手动提供可读文本或转换后的 Markdown。
```

- [ ] **Step 3: Update `AGENTS.md` interface rules**

Remove the `Reserved interfaces` bullets. Add:

```markdown
Implemented deterministic interfaces:

- `python tools/health.py` checks repository structure, wiki page frontmatter, index/log shape, wikilinks, source provenance, and required paths.
- `python tools/lint.py` checks semantic-lite maintenance issues and may write `graph/graph-report.md`.
- `python tools/build_graph.py` writes local graph artifacts under `graph/`.
- `python tools/convert.py <input> --out raw/converted/<file>` converts supported local Markdown/text inputs only.
- `python -m unittest discover -s tests` runs the repository test suite.

Conversion does not equal ingest. After using `convert.py`, agents must still perform the ingest workflow before claiming a source has entered MuvyWiki.
```

- [ ] **Step 4: Update directory READMEs**

Update `raw/README.md` to state:

```markdown
`tools/convert.py` supports local Markdown/text conversion into `raw/converted/`. It does not update `raw/source-manifest.jsonl`; the ingest workflow records artifacts and provenance.
```

Update `graph/README.md` to state:

```markdown
`python tools/build_graph.py` generates `graph.json`, `graph.html`, and `graph-report.md` from wiki frontmatter, wikilinks, source IDs, related IDs, and raw paths.
```

Update `examples/ingest/README.md` to add:

````markdown
The fixture also supports:

```bash
python tools/lint.py
python tools/build_graph.py
```
````

- [ ] **Step 5: Run documentation tests**

Run:

```bash
python -m unittest tests/test_docs_interfaces.py
```

Expected: docs tests pass.

- [ ] **Step 6: Commit documentation updates**

Run:

```bash
git add README.md USER_GUIDE.md AGENTS.md raw/README.md graph/README.md examples/ingest/README.md
git commit -m "docs: document implemented interfaces"
```

Expected: commit succeeds.

## Task 7: Final Verification

**Files:**
- No planned file changes.

- [ ] **Step 1: Run all unit tests**

Run:

```bash
python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 2: Run root health**

Run:

```bash
python tools/health.py
```

Expected: `MuvyWiki health: ok`.

- [ ] **Step 3: Run root lint**

Run:

```bash
python tools/lint.py
```

Expected: `MuvyWiki lint: ok`.

- [ ] **Step 4: Generate root graph artifacts**

Run:

```bash
python tools/build_graph.py
```

Expected: command exits `0` and writes ignored artifacts under `graph/`.

- [ ] **Step 5: Verify local conversion with a scratch ignored output**

Run:

```bash
python tools/convert.py README.md --out raw/converted/readme-smoke.md --json
rm raw/converted/readme-smoke.md
```

Expected: conversion exits `0`, JSON status is `ok`, and the scratch converted file is removed.

- [ ] **Step 6: Verify ingest fixture**

Run:

```bash
(cd examples/ingest && python tools/health.py)
(cd examples/ingest && python tools/lint.py)
(cd examples/ingest && python tools/build_graph.py)
```

Expected: all commands exit `0`.

- [ ] **Step 7: Check worktree status and recent commits**

Run:

```bash
git status --short
git log --oneline -8
```

Expected:

- Only ignored graph artifacts may exist after graph commands.
- No tracked files are modified.
- Recent commits correspond to this plan's completed tasks.

## Self-Review Checklist

Spec coverage:

- Shared standard-library tool conventions: Task 1 and all implementation tasks.
- `lint.py` JSON/report/check behavior: Task 4.
- `build_graph.py` JSON/HTML/report behavior: Task 3.
- `convert.py` supported/unsupported inputs and JSON output: Task 2.
- Fixture tool consistency: Task 5.
- Documentation updates: Task 6.
- Final verification: Task 7.

Out-of-scope items remain out of scope:

- No PDF parsing.
- No Office parsing.
- No web fetching or HTML rendering.
- No embeddings, vector search, or LLM calls.
- No automatic wiki ingest inside `convert.py`.

Implementation notes:

- If graph or lint need parser behavior, use `tools/wiki_utils.py`; do not duplicate regexes unnecessarily.
- If a test creates graph artifacts in the real repository, write only `graph/graph.json`, `graph/graph.html`, or `graph/graph-report.md`, which are ignored by `.gitignore`.
- Do not claim conversion ingests a source. Conversion only creates a converted artifact.
