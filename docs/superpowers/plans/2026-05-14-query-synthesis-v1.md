# Query & Synthesis v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic query-context and synthesis-saving interfaces for MuvyWiki while preserving the agent-first workflow.

**Architecture:** Add small shared wiki-page helpers to `tools/wiki_utils.py`, then build `tools/query.py` for read-only context retrieval and `tools/save_synthesis.py` for validated synthesis persistence. Update health/docs/tests so the new interfaces are part of the same contract as `health`, `lint`, `build_graph`, and `convert`.

**Tech Stack:** Python standard library, `unittest`, Markdown files, existing MuvyWiki frontmatter conventions.

---

## File Structure

- Modify `tools/wiki_utils.py`: shared page metadata, list, title, canonical map, kebab ID, YAML list, and excerpt helpers.
- Create `tools/query.py`: read-only keyword-lite retrieval CLI with text and JSON output.
- Create `tools/save_synthesis.py`: validated synthesis writer CLI with text and JSON output.
- Modify `tools/health.py`: require the new tools and accept `needs-review` status.
- Modify `tests/test_wiki_utils.py`: utility coverage.
- Create `tests/test_query.py`: query CLI behavior.
- Create `tests/test_save_synthesis.py`: synthesis writer behavior and no-mutation validation failures.
- Modify `tests/test_health.py`: minimal fixture includes new required tools and `needs-review` remains valid.
- Modify `tests/test_docs_interfaces.py`: docs acknowledge the new interfaces.
- Modify `README.md`, `USER_GUIDE.md`, `AGENTS.md`, `graph/README.md`, `docs/superpowers/specs/2026-05-12-muvywiki-design.md`: user-facing and agent-facing contract updates.

## Execution Preflight

- [ ] **Step 1: Create an isolated worktree for implementation**

Use `superpowers:using-git-worktrees` before editing implementation files. Name the branch `feature/query-synthesis-v1`.

- [ ] **Step 2: Verify starting state**

Run:

```bash
git status -sb
python -m unittest discover -s tests
python tools/health.py
python tools/lint.py
```

Expected: clean worktree before edits, all tests pass, health is `ok`, lint is `ok`.

---

### Task 1: Shared Wiki Utilities

**Files:**
- Modify: `tools/wiki_utils.py`
- Modify: `tests/test_wiki_utils.py`

- [ ] **Step 1: Write failing utility tests**

Append these tests to `tests/test_wiki_utils.py` inside `WikiUtilsTests`:

```python
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
```

- [ ] **Step 2: Run utility tests and verify failure**

Run:

```bash
python -m unittest tests/test_wiki_utils.py
```

Expected: fail because `load_wiki_pages`, `canonical_page_map`, `is_kebab_id`, `yaml_list`, and `bounded_excerpt` do not exist yet.

- [ ] **Step 3: Add shared helpers**

Modify `tools/wiki_utils.py` imports:

```python
from dataclasses import dataclass
```

Add these helpers after `NONE_MARKERS`:

```python
KEBAB_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
```

Add these definitions after `has_useful_text`:

```python
@dataclass(frozen=True)
class WikiPage:
    path: Path
    rel_path: str
    id: str
    type: str
    title: str
    tags: list[str]
    aliases: list[str]
    source_ids: list[str]
    related_ids: list[str]
    raw_paths: list[str]
    text: str
    body: str
    sections: dict[str, str]
    frontmatter: dict[str, Any]


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [str(value)]


def page_id(frontmatter: dict[str, object], path: Path) -> str:
    canonical_id = frontmatter.get("canonical_id")
    return str(canonical_id) if canonical_id else path.stem


def page_title(frontmatter: dict[str, object], text: str, fallback: str) -> str:
    title = frontmatter.get("title")
    if title:
        return str(title)
    for line in content_after_frontmatter(text).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_wiki_pages(root: Path) -> list[WikiPage]:
    pages: list[WikiPage] = []
    for path in collect_wiki_pages(root):
        text = read_text(path)
        frontmatter = parse_frontmatter(text)
        body = content_after_frontmatter(text)
        page_identifier = page_id(frontmatter, path)
        pages.append(
            WikiPage(
                path=path,
                rel_path=repo_relative(root, path),
                id=page_identifier,
                type=str(frontmatter.get("type") or ""),
                title=page_title(frontmatter, text, page_identifier),
                tags=as_list(frontmatter.get("tags")),
                aliases=as_list(frontmatter.get("aliases")),
                source_ids=as_list(frontmatter.get("source_ids")),
                related_ids=as_list(frontmatter.get("related_ids")),
                raw_paths=as_list(frontmatter.get("raw_paths")),
                text=text,
                body=body,
                sections=section_bodies(body),
                frontmatter=frontmatter,
            )
        )
    return pages


def canonical_page_map(root: Path) -> dict[str, WikiPage]:
    return {page.id: page for page in load_wiki_pages(root)}


def is_kebab_id(value: str) -> bool:
    return bool(KEBAB_ID_RE.fullmatch(value))


def yaml_list(values: list[str]) -> list[str]:
    if not values:
        return ["[]"]
    escaped = [value.replace('"', '\\"') for value in values]
    return [f'  - "{value}"' for value in escaped]


def bounded_excerpt(text: str, terms: set[str], limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    lowered = normalized.lower()
    starts = [lowered.find(term.lower()) for term in terms if term and lowered.find(term.lower()) >= 0]
    if starts:
        center = min(starts)
        start = max(0, center - limit // 3)
    else:
        start = 0
    excerpt = normalized[start : start + limit].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if start + limit < len(normalized):
        excerpt = excerpt.rstrip() + "..."
    return excerpt
```

- [ ] **Step 4: Run utility tests and verify pass**

Run:

```bash
python -m unittest tests/test_wiki_utils.py
```

Expected: pass.

- [ ] **Step 5: Run existing tool tests that import `wiki_utils`**

Run:

```bash
python -m unittest tests/test_lint.py tests/test_build_graph.py tests/test_convert.py
```

Expected: pass.

- [ ] **Step 6: Commit shared utilities**

Run:

```bash
git add tools/wiki_utils.py tests/test_wiki_utils.py
git commit -m "feat: add shared wiki page helpers"
```

---

### Task 2: Query Context Interface

**Files:**
- Create: `tools/query.py`
- Create: `tests/test_query.py`

- [ ] **Step 1: Write failing query CLI tests**

Create `tests/test_query.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run query tests and verify failure**

Run:

```bash
python -m unittest tests/test_query.py
```

Expected: fail because `tools/query.py` does not exist.

- [ ] **Step 3: Implement `tools/query.py`**

Create `tools/query.py` with this structure:

```python
#!/usr/bin/env python3
"""Build a local query context packet for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
ALLOWED_TYPES = {"source", "concept", "entity", "synthesis", "overview"}
TYPE_PRIORITY = {"concept": 0, "synthesis": 1, "source": 2, "entity": 3, "overview": 4}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def parse_types(value: str | None) -> set[str] | None:
    if not value:
        return None
    selected = {item.strip() for item in value.split(",") if item.strip()}
    unknown = selected - ALLOWED_TYPES
    if unknown:
        raise ValueError("unsupported page type: " + ", ".join(sorted(unknown)))
    return selected


def add_term_scores(
    terms: set[str],
    text_values: list[str],
    weight: int,
    score: int,
    matched_terms: set[str],
) -> int:
    haystack = " ".join(text_values).lower()
    for term in terms:
        if term in haystack:
            score += weight
            matched_terms.add(term)
    return score


def score_page(page: wiki_utils.WikiPage, terms: set[str]) -> tuple[int, set[str]]:
    score = 0
    matched_terms: set[str] = set()
    score = add_term_scores(terms, [page.id, page.title, *page.aliases, *page.tags], 6, score, matched_terms)
    score = add_term_scores(terms, [*page.source_ids, *page.related_ids, *wiki_utils.extract_wikilinks(page.body)], 4, score, matched_terms)
    score = add_term_scores(terms, list(page.sections), 3, score, matched_terms)
    score = add_term_scores(terms, [page.body], 1, score, matched_terms)
    score += len(matched_terms) * 2
    return score, matched_terms


def section_matches(page: wiki_utils.WikiPage, terms: set[str]) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for title, body in page.sections.items():
        combined = f"{title}\n{body}".lower()
        if not any(term in combined for term in terms):
            continue
        matches.append(
            {
                "title": title,
                "excerpt": wiki_utils.bounded_excerpt(body or title, terms, 240),
            }
        )
    return matches[:3]


def match_page(page: wiki_utils.WikiPage, terms: set[str], include_sections: bool) -> dict[str, object] | None:
    score, matched_terms = score_page(page, terms)
    if score <= 0:
        return None
    match: dict[str, object] = {
        "id": page.id,
        "title": page.title,
        "type": page.type,
        "path": page.rel_path,
        "score": score,
        "matched_terms": sorted(matched_terms),
        "tags": page.tags,
        "aliases": page.aliases,
        "source_ids": page.source_ids,
        "related_ids": page.related_ids,
        "wikilinks": sorted(wiki_utils.extract_wikilinks(page.body)),
    }
    if include_sections:
        match["sections"] = section_matches(page, terms)
    return match


def build_payload(query: str, limit: int, type_filter: set[str] | None, include_sections: bool) -> dict[str, object]:
    terms = set(tokenize(query))
    if not terms:
        raise ValueError("query must contain at least one alphanumeric term")
    pages = wiki_utils.load_wiki_pages(ROOT)
    matches = []
    for page in pages:
        if type_filter is not None and page.type not in type_filter:
            continue
        match = match_page(page, terms, include_sections)
        if match is not None:
            matches.append(match)
    matches.sort(key=lambda item: (-int(item["score"]), TYPE_PRIORITY.get(str(item["type"]), 99), str(item["path"])))
    return {
        "status": "ok",
        "query": query,
        "retrieval_mode": "keyword-lite",
        "generated_at": wiki_utils.utc_now(),
        "limit": limit,
        "matches": matches[:limit],
    }


def text_output(payload: dict[str, object]) -> str:
    matches = payload["matches"]
    assert isinstance(matches, list)
    lines = [f"MuvyWiki query: {len(matches)} match(es)", ""]
    for index, item in enumerate(matches, start=1):
        assert isinstance(item, dict)
        lines.extend(
            [
                f"{index}. {item['id']} - {item['title']}",
                f"   path: {item['path']}",
                f"   type: {item['type']}",
                f"   score: {item['score']}",
                "   matched: " + ", ".join(str(term) for term in item["matched_terms"]),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a MuvyWiki query context packet.")
    parser.add_argument("query", help="Natural-language query text.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable query output.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum number of matches.")
    parser.add_argument("--type", help="Comma-separated page-type filter.")
    parser.add_argument("--include-sections", action="store_true", help="Include matching section excerpts.")
    args = parser.parse_args(argv)

    try:
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        type_filter = parse_types(args.type)
        payload = build_payload(args.query, args.limit, type_filter, args.include_sections)
    except (OSError, ValueError) as exc:
        print(f"Query failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(text_output(payload), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run query tests and verify pass**

Run:

```bash
python -m unittest tests/test_query.py
```

Expected: pass.

- [ ] **Step 5: Run existing tests touched by shared helpers**

Run:

```bash
python -m unittest tests/test_wiki_utils.py tests/test_lint.py tests/test_build_graph.py
```

Expected: pass.

- [ ] **Step 6: Commit query interface**

Run:

```bash
git add tools/query.py tests/test_query.py
git commit -m "feat: add query context interface"
```

---

### Task 3: Synthesis Save Interface

**Files:**
- Create: `tools/save_synthesis.py`
- Create: `tests/test_save_synthesis.py`
- Modify: `tools/health.py`
- Modify: `tests/test_health.py`

- [ ] **Step 1: Write failing synthesis save tests**

Create `tests/test_save_synthesis.py`:

```python
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SaveSynthesisToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in ("tools", "wiki/sources", "wiki/concepts", "wiki/entities", "wiki/syntheses", "raw/originals", "raw/converted", "templates", "graph"):
            (root / rel).mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "tools" / "wiki_utils.py", root / "tools" / "wiki_utils.py")
        shutil.copy(ROOT / "tools" / "save_synthesis.py", root / "tools" / "save_synthesis.py")
        shutil.copy(ROOT / "tools" / "health.py", root / "tools" / "health.py")
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
            "tools/lint.py",
            "tools/build_graph.py",
            "tools/convert.py",
            "tools/query.py",
            "graph/README.md",
        ):
            (root / rel).write_text("fixture\n", encoding="utf-8")
        (root / "raw/originals/source-one.txt").write_text("source body\n", encoding="utf-8")
        (root / "raw/source-manifest.jsonl").write_text(
            json.dumps(
                {
                    "source_id": "source-one",
                    "raw_path": "raw/originals/source-one.txt",
                    "content_hash": "sha256:abc123",
                    "source_url": None,
                    "collected_at": "2026-05-14",
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
        self.write_page(root / "wiki/overview.md", "overview", "overview", "Overview", "Overview body.", source_ids=[], related_ids=["RetrievalAugmentedGeneration"])
        self.write_page(root / "wiki/concepts/RetrievalAugmentedGeneration.md", "RetrievalAugmentedGeneration", "concept", "Retrieval-Augmented Generation", "Concept body.", source_ids=["source-one"], related_ids=[])
        self.write_source(root / "wiki/sources/source-one.md")
        (root / "wiki/index.md").write_text(
            """# MuvyWiki Index

## Overview

- [[overview|Overview]] (`wiki/overview.md`) - type: overview - updated: 2026-05-14 - Living map.

## Sources

- [[source-one|Source One]] (`wiki/sources/source-one.md`) - type: source - updated: 2026-05-14 - Test source.

## Concepts

- [[RetrievalAugmentedGeneration|Retrieval-Augmented Generation]] (`wiki/concepts/RetrievalAugmentedGeneration.md`) - type: concept - updated: 2026-05-14 - Test concept.

## Entities

No entity pages yet.

## Syntheses

No synthesis pages yet.
""",
            encoding="utf-8",
        )
        (root / "wiki/log.md").write_text(
            """# MuvyWiki Log

## [2026-05-14] init | fixture

- Changed pages:
  - `wiki/index.md`
- Raw paths:
  - none
- Source IDs:
  - none
- Unresolved issues:
  - none
""",
            encoding="utf-8",
        )
        return temp_dir, root

    def write_page(self, path, cid, page_type, title, body, source_ids=None, related_ids=None):
        source_ids = source_ids or []
        related_ids = related_ids or []
        path.write_text(
            f'''---
canonical_id: "{cid}"
type: {page_type}
title: "{title}"
tags: []
aliases: []
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

## Summary

{body}
''',
            encoding="utf-8",
        )

    def write_source(self, path):
        path.write_text(
            """---
canonical_id: "source-one"
type: source
title: "Source One"
tags: []
aliases: []
source_ids: []
related_ids:
  - "RetrievalAugmentedGeneration"
raw_paths:
  - "raw/originals/source-one.txt"
created: 2026-05-14
last_updated: 2026-05-14
status: seed
confidence: medium
provenance:
  source_id: "source-one"
  raw_path: "raw/originals/source-one.txt"
  content_hash: "sha256:abc123"
  source_url: null
  collected_at: "2026-05-14"
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# Source One

## Summary

Source summary with [[RetrievalAugmentedGeneration]].
""",
            encoding="utf-8",
        )

    def yaml_list(self, values):
        if not values:
            return "  []"
        return "\n".join(f'  - "{value}"' for value in values)

    def run_save(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/save_synthesis.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def valid_args(self, root):
        answer = root / "answer.md"
        evidence = root / "evidence.md"
        answer.write_text("- RAG retrieves evidence before generation.\n", encoding="utf-8")
        evidence.write_text("- [[source-one|Source One]] supports the claim.\n", encoding="utf-8")
        return [
            "--id",
            "rag-systems-architecture-survey",
            "--title",
            "RAG Systems Architecture Survey",
            "--question",
            "How have RAG systems evolved?",
            "--answer-file",
            str(answer),
            "--evidence-file",
            str(evidence),
            "--related",
            "RetrievalAugmentedGeneration",
            "--sources",
            "source-one",
            "--tags",
            "rag,systems",
            "--json",
        ]

    def test_saves_synthesis_updates_index_and_log(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_save(root, *self.valid_args(root))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["id"], "rag-systems-architecture-survey")
            page = root / "wiki/syntheses/rag-systems-architecture-survey.md"
            self.assertTrue(page.exists())
            text = page.read_text(encoding="utf-8")
            self.assertIn('canonical_id: "rag-systems-architecture-survey"', text)
            self.assertIn("## Evidence", text)
            self.assertIn("[[RetrievalAugmentedGeneration]]", text)
            index = (root / "wiki/index.md").read_text(encoding="utf-8")
            self.assertIn("[[rag-systems-architecture-survey|RAG Systems Architecture Survey]]", index)
            self.assertNotIn("No synthesis pages yet.", index)
            log = (root / "wiki/log.md").read_text(encoding="utf-8")
            self.assertIn("## [", log)
            self.assertIn("query | RAG Systems Architecture Survey", log)
            health = subprocess.run([sys.executable, "tools/health.py"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(health.returncode, 0, health.stdout + health.stderr)

    def test_text_output_is_concise(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            args = [arg for arg in self.valid_args(root) if arg != "--json"]
            result = self.run_save(root, *args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Saved synthesis wiki/syntheses/rag-systems-architecture-survey.md", result.stdout)
            self.assertIn("Updated wiki/index.md and wiki/log.md", result.stdout)

    def test_validation_failures_do_not_mutate_files(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            before_index = (root / "wiki/index.md").read_text(encoding="utf-8")
            before_log = (root / "wiki/log.md").read_text(encoding="utf-8")
            args = self.valid_args(root)
            args[args.index("--related") + 1] = "MissingConcept"
            result = self.run_save(root, *args)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown related id: MissingConcept", result.stderr)
            self.assertFalse((root / "wiki/syntheses/rag-systems-architecture-survey.md").exists())
            self.assertEqual((root / "wiki/index.md").read_text(encoding="utf-8"), before_index)
            self.assertEqual((root / "wiki/log.md").read_text(encoding="utf-8"), before_log)

    def test_rejects_duplicate_invalid_id_unknown_source_and_empty_evidence(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            first = self.run_save(root, *self.valid_args(root))
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            duplicate = self.run_save(root, *self.valid_args(root))
            self.assertEqual(duplicate.returncode, 1)
            invalid_args = self.valid_args(root)
            invalid_args[invalid_args.index("--id") + 1] = "BadID"
            invalid = self.run_save(root, *invalid_args)
            self.assertEqual(invalid.returncode, 1)
            source_args = self.valid_args(root)
            source_args[source_args.index("--id") + 1] = "different-id"
            source_args[source_args.index("--sources") + 1] = "missing-source"
            unknown_source = self.run_save(root, *source_args)
            self.assertEqual(unknown_source.returncode, 1)
            evidence = root / "empty-evidence.md"
            evidence.write_text("   \n", encoding="utf-8")
            empty_args = self.valid_args(root)
            empty_args[empty_args.index("--id") + 1] = "empty-evidence"
            empty_args[empty_args.index("--evidence-file") + 1] = str(evidence)
            empty = self.run_save(root, *empty_args)
            self.assertEqual(empty.returncode, 1)

    def test_rejects_symlinked_destination(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            outside = root / "outside.md"
            outside.write_text("unchanged\n", encoding="utf-8")
            (root / "wiki/syntheses/rag-systems-architecture-survey.md").symlink_to(outside)
            result = self.run_save(root, *self.valid_args(root))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(outside.read_text(encoding="utf-8"), "unchanged\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run synthesis tests and verify failure**

Run:

```bash
python -m unittest tests/test_save_synthesis.py
```

Expected: fail because `tools/save_synthesis.py` does not exist.

- [ ] **Step 3: Implement `tools/save_synthesis.py`**

Create `tools/save_synthesis.py` with these functions:

```python
#!/usr/bin/env python3
"""Save an approved synthesis page into MuvyWiki."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_STATUS = {"seed", "active", "archived", "needs-review"}


@dataclass(frozen=True)
class SaveRequest:
    synthesis_id: str
    title: str
    question: str
    answer: str
    evidence: str
    related_ids: list[str]
    source_ids: list[str]
    tags: list[str]
    confidence: str
    status: str


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def read_required_markdown(path_value: str, label: str) -> str:
    path = Path(path_value)
    text = wiki_utils.read_text(path)
    if not wiki_utils.has_useful_text(text):
        raise ValueError(f"{label} must contain useful text")
    return text.strip() + "\n"


def validate_request(args: argparse.Namespace, pages: dict[str, wiki_utils.WikiPage]) -> SaveRequest:
    synthesis_id = args.synthesis_id.strip()
    title = args.title.strip()
    question = args.question.strip()
    answer = read_required_markdown(args.answer_file, "answer")
    evidence = read_required_markdown(args.evidence_file, "evidence")
    related_ids = parse_csv(args.related)
    source_ids = parse_csv(args.sources)
    tags = parse_csv(args.tags)
    errors: list[str] = []

    if not wiki_utils.is_kebab_id(synthesis_id):
        errors.append("--id must be kebab-case")
    if not title:
        errors.append("--title is required")
    if not question:
        errors.append("--question is required")
    if args.confidence not in ALLOWED_CONFIDENCE:
        errors.append("--confidence must be one of: high, low, medium")
    if args.status not in ALLOWED_STATUS:
        errors.append("--status must be one of: active, archived, needs-review, seed")
    for source_id in source_ids:
        page = pages.get(source_id)
        if page is None or page.type != "source":
            errors.append(f"unknown source id: {source_id}")
    for related_id in related_ids:
        if related_id not in pages:
            errors.append(f"unknown related id: {related_id}")

    destination = wiki_utils.safe_child_path(ROOT, f"wiki/syntheses/{synthesis_id}.md", ROOT / "wiki" / "syntheses")
    if destination.exists() or destination.is_symlink():
        errors.append(f"synthesis already exists: {wiki_utils.repo_relative(ROOT, destination)}")
    if errors:
        raise ValueError("; ".join(errors))

    return SaveRequest(
        synthesis_id=synthesis_id,
        title=title,
        question=question,
        answer=answer,
        evidence=evidence,
        related_ids=related_ids,
        source_ids=source_ids,
        tags=tags,
        confidence=args.confidence,
        status=args.status,
    )


def frontmatter_list(name: str, values: list[str]) -> list[str]:
    encoded = wiki_utils.yaml_list(values)
    if encoded == ["[]"]:
        return [f"{name}: []"]
    return [f"{name}:", *encoded]


def render_synthesis(request: SaveRequest, today: str) -> str:
    related_links = [f"- [[{item}]]" for item in [*request.related_ids, *request.source_ids]]
    if not related_links:
        related_links = ["- none"]
    lines = [
        "---",
        f'canonical_id: "{request.synthesis_id}"',
        "type: synthesis",
        f'title: "{request.title}"',
        *frontmatter_list("tags", request.tags),
        "aliases: []",
        *frontmatter_list("source_ids", request.source_ids),
        *frontmatter_list("related_ids", request.related_ids),
        "raw_paths: []",
        f"created: {today}",
        f"last_updated: {today}",
        f"status: {request.status}",
        f"confidence: {request.confidence}",
        "---",
        "",
        f"# {request.title}",
        "",
        "## Question",
        "",
        request.question,
        "",
        "## Answer",
        "",
        request.answer.rstrip(),
        "",
        "## Evidence",
        "",
        request.evidence.rstrip(),
        "",
        "## Contradictions or Tensions",
        "",
        "- none",
        "",
        "## Implications",
        "",
        "- none",
        "",
        "## Related Pages",
        "",
        *related_links,
        "",
        "## Follow-up Questions",
        "",
        "- none",
        "",
    ]
    return "\n".join(lines)


def index_entry(request: SaveRequest, today: str) -> str:
    question_summary = " ".join(request.question.split())
    return (
        f"- [[{request.synthesis_id}|{request.title}]] "
        f"(`wiki/syntheses/{request.synthesis_id}.md`) - type: synthesis - updated: {today} - "
        f"Saved synthesis for: {question_summary}"
    )


def update_index_text(text: str, entry: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    in_syntheses = False
    inserted = False
    for line in lines:
        if line.startswith("## "):
            if in_syntheses and not inserted:
                output.append(entry)
                inserted = True
            in_syntheses = line.strip() == "## Syntheses"
            output.append(line)
            continue
        if in_syntheses and line.strip() == "No synthesis pages yet.":
            continue
        output.append(line)
    if in_syntheses and not inserted:
        if output and output[-1].strip():
            output.append("")
        output.append(entry)
    return "\n".join(output).rstrip() + "\n"


def log_entry(request: SaveRequest, today: str) -> str:
    source_lines = [f"  - `{source_id}`" for source_id in request.source_ids] or ["  - none"]
    return "\n".join(
        [
            "",
            f"## [{today}] query | {request.title}",
            "",
            "- Changed pages:",
            f"  - `wiki/syntheses/{request.synthesis_id}.md`",
            "  - `wiki/index.md`",
            "  - `wiki/log.md`",
            "- Raw paths:",
            "  - none",
            "- Source IDs:",
            *source_lines,
            "- Unresolved issues:",
            "  - none",
            "",
        ]
    )


def save(request: SaveRequest) -> dict[str, object]:
    today = date.today().isoformat()
    destination = wiki_utils.safe_child_path(ROOT, f"wiki/syntheses/{request.synthesis_id}.md", ROOT / "wiki" / "syntheses")
    synthesis_text = render_synthesis(request, today)
    index_path = ROOT / "wiki" / "index.md"
    log_path = ROOT / "wiki" / "log.md"
    index_text = update_index_text(wiki_utils.read_text(index_path), index_entry(request, today))
    log_text = wiki_utils.read_text(log_path).rstrip() + log_entry(request, today)

    wiki_utils.write_text(destination, synthesis_text)
    wiki_utils.write_text(index_path, index_text)
    wiki_utils.write_text(log_path, log_text)
    return {
        "status": "ok",
        "id": request.synthesis_id,
        "path": wiki_utils.repo_relative(ROOT, destination),
        "updated": ["wiki/index.md", "wiki/log.md"],
        "source_ids": request.source_ids,
        "related_ids": request.related_ids,
        "saved_at": wiki_utils.utc_now(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save an approved MuvyWiki synthesis.")
    parser.add_argument("--id", dest="synthesis_id", required=True, help="Synthesis canonical ID in kebab-case.")
    parser.add_argument("--title", required=True, help="Human-readable synthesis title.")
    parser.add_argument("--question", required=True, help="Question answered by this synthesis.")
    parser.add_argument("--answer-file", required=True, help="Markdown file containing the answer.")
    parser.add_argument("--evidence-file", required=True, help="Markdown file containing evidence.")
    parser.add_argument("--related", help="Comma-separated related wiki page IDs.")
    parser.add_argument("--sources", help="Comma-separated source page IDs.")
    parser.add_argument("--tags", help="Comma-separated tags.")
    parser.add_argument("--confidence", default="medium", help="Confidence: low, medium, high.")
    parser.add_argument("--status", default="seed", help="Status: seed, active, archived, needs-review.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable save output.")
    args = parser.parse_args(argv)

    try:
        request = validate_request(args, wiki_utils.canonical_page_map(ROOT))
        payload = save(request)
    except ValueError as exc:
        print(f"Synthesis validation failed: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Synthesis save failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Saved synthesis {payload['path']}")
        print("Updated wiki/index.md and wiki/log.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Update health interface requirements**

Modify `tools/health.py` by inserting the two new tool paths immediately after `"tools/convert.py"` in `REQUIRED_PATHS`:

```python
"tools/query.py",
"tools/save_synthesis.py",
```

Change:

```python
ALLOWED_STATUSES = {"seed", "active", "archived"}
```

to:

```python
ALLOWED_STATUSES = {"seed", "active", "archived", "needs-review"}
```

- [ ] **Step 5: Update health tests for new required paths and status**

In `tests/test_health.py`, add `tools/query.py` and `tools/save_synthesis.py` to the fixture file list in `write_minimal_repo`:

```python
            "tools/query.py",
            "tools/save_synthesis.py",
```

Add this test to `HealthToolTests`:

```python
    def test_needs_review_status_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            self.write_minimal_repo(temp)
            source_path = temp / "wiki/sources/source-one.md"
            source_path.write_text(
                source_path.read_text(encoding="utf-8").replace("status: seed", "status: needs-review"),
                encoding="utf-8",
            )
            result = self.run_health(cwd=temp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
```

- [ ] **Step 6: Run synthesis and health tests**

Run:

```bash
python -m unittest tests/test_save_synthesis.py tests/test_health.py
```

Expected: pass.

- [ ] **Step 7: Run query after saving fixture synthesis**

Run:

```bash
python -m unittest tests/test_query.py
```

Expected: pass; synthesis changes do not break query collection.

- [ ] **Step 8: Commit synthesis save interface**

Run:

```bash
git add tools/save_synthesis.py tools/health.py tests/test_save_synthesis.py tests/test_health.py
git commit -m "feat: add synthesis save interface"
```

---

### Task 4: Documentation and Interface Contract

**Files:**
- Modify: `README.md`
- Modify: `USER_GUIDE.md`
- Modify: `AGENTS.md`
- Modify: `graph/README.md`
- Modify: `docs/superpowers/specs/2026-05-12-muvywiki-design.md`
- Modify: `tests/test_docs_interfaces.py`

- [ ] **Step 1: Write failing docs consistency tests**

Add assertions to `tests/test_docs_interfaces.py`:

```python
    def test_query_and_synthesis_interfaces_are_documented(self):
        readme = self.read("README.md")
        guide = self.read("USER_GUIDE.md")
        agents = self.read("AGENTS.md")
        graph = self.read("graph/README.md")
        design = self.read("docs/superpowers/specs/2026-05-12-muvywiki-design.md")
        for text in (readme, guide, agents):
          self.assertIn("python tools/query.py", text)
          self.assertIn("python tools/save_synthesis.py", text)
        self.assertIn("saved syntheses appear in graph outputs", graph)
        self.assertIn("Query & Synthesis v1 update", design)
```

- [ ] **Step 2: Run docs tests and verify failure**

Run:

```bash
python -m unittest tests/test_docs_interfaces.py
```

Expected: fail until docs are updated.

- [ ] **Step 3: Update `README.md` status and commands**

Add rows to the status table:

```markdown
| Query context | Implemented | `python tools/query.py "retrieval augmented generation"`, `python tools/query.py "retrieval augmented generation" --json` |
| Synthesis saving | Implemented | `python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md` |
```

Add commands to the common command block:

```bash
python tools/query.py "retrieval augmented generation" --json
python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md
```

Add one sentence near the bottom:

```markdown
`query.py` and `save_synthesis.py` are agent-facing helpers: they retrieve context and persist approved syntheses, but they do not call an LLM or ingest new raw sources.
```

- [ ] **Step 4: Update `USER_GUIDE.md`**

In "当前功能与接口状态", add:

```markdown
- `python tools/query.py "retrieval augmented generation"`：基于现有 wiki 页面生成本地检索结果。
- `python tools/query.py "retrieval augmented generation" --json`：输出 agent 可读取的 context packet。
- `python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md`：把已确认值得保存的回答落成 synthesis 页面，并更新 index/log。
```

In "如何提问", add:

```markdown
现在可以先用 `query.py` 找上下文，再让 agent 阅读结果页面后回答。`query.py` 不生成答案；它只告诉 agent 哪些页面值得先读。
```

In "保存综合判断", add:

```markdown
保存 synthesis 时，agent 应先得到你的确认，再准备 answer/evidence Markdown，通过 `save_synthesis.py` 写入 `wiki/syntheses/`，最后运行 health 和 lint。
```

- [ ] **Step 5: Update `AGENTS.md`**

Under "Implemented deterministic interfaces", add:

```markdown
- `python tools/query.py "retrieval augmented generation"` retrieves deterministic local wiki matches for agent context.
- `python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md` saves approved synthesis pages and updates index/log.
```

Replace the query workflow bullets with:

```markdown
- Read `wiki/index.md` first when manually navigating the wiki.
- Prefer `python tools/query.py "retrieval augmented generation" --json` for a deterministic first-pass context packet before answering that topic.
- Read the matched wiki pages before answering.
- Answer from wiki content first and cite pages with `[[WikiLinks]]`.
- Clearly label anything from model knowledge rather than wiki pages.
- Ask before expanding to web search or new external sources.
- If an answer has long-term value, ask whether to save it as a synthesis page.
- If the user chooses to save a synthesis page, prepare answer/evidence Markdown and use `tools/save_synthesis.py`.
- Run `python tools/health.py` and `python tools/lint.py` after saving a synthesis.
- Append to `raw/source-manifest.jsonl` only when the saved work also creates a new raw or converted artifact.
```

- [ ] **Step 6: Update `graph/README.md`**

Add:

```markdown
Saved syntheses appear in graph outputs through the normal `wiki/syntheses/*.md` page collection. Regenerate graph artifacts after using `tools/save_synthesis.py`.
```

- [ ] **Step 7: Update main design status note**

In `docs/superpowers/specs/2026-05-12-muvywiki-design.md`, add a short status note:

```markdown
## Query & Synthesis v1 Update

As of 2026-05-14, query and synthesis saving have deterministic helper interfaces. `tools/query.py` builds local context packets from wiki pages, and `tools/save_synthesis.py` persists user-approved synthesis pages while updating `wiki/index.md` and `wiki/log.md`. The tools preserve the original agent-first design: they do not call an LLM, fetch remote sources, or ingest raw artifacts.
```

- [ ] **Step 8: Run docs tests and verify pass**

Run:

```bash
python -m unittest tests/test_docs_interfaces.py
```

Expected: pass.

- [ ] **Step 9: Commit docs contract**

Run:

```bash
git add README.md USER_GUIDE.md AGENTS.md graph/README.md docs/superpowers/specs/2026-05-12-muvywiki-design.md tests/test_docs_interfaces.py
git commit -m "docs: document query and synthesis interfaces"
```

---

### Task 5: End-to-End Verification and Review Prep

**Files:**
- No implementation files unless verification exposes a defect.

- [ ] **Step 1: Run full test suite**

Run:

```bash
python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 2: Run current repository query smoke test**

Run:

```bash
python tools/query.py "MuvyWiki overview" --json
```

Expected: exit `0`, valid JSON, at least `overview` if the query terms match current pages.

- [ ] **Step 3: Run health and lint**

Run:

```bash
python tools/health.py
python tools/health.py --json
python tools/lint.py
python tools/lint.py --json
```

Expected: health `ok`, lint `ok`, JSON parses.

- [ ] **Step 4: Regenerate graph artifacts**

Run:

```bash
python tools/build_graph.py
```

Expected: writes `graph/graph.json`, `graph/graph.html`, and `graph/graph-report.md`. These generated artifacts are ignored unless the repo intentionally tracks them.

- [ ] **Step 5: Verify example fixture**

Run:

```bash
cd examples/ingest && python tools/lint.py
cd examples/ingest && python tools/health.py
cd examples/ingest && python tools/build_graph.py
```

Expected: lint `ok`, health `ok`, graph artifacts written in the fixture.

- [ ] **Step 6: Inspect changed files**

Run:

```bash
git status -sb
git diff --stat HEAD
```

Expected: only expected generated ignored files remain outside commits. No unrelated tracked changes.

- [ ] **Step 7: Request code review through subagent**

Dispatch a review subagent with:

```text
Review Query & Synthesis v1 implementation against:
- docs/superpowers/specs/2026-05-14-query-synthesis-v1-design.md
- Karpathy LLM Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Astro-Han/karpathy-llm-wiki
- SamurAIGPT/llm-wiki-agent

Focus on bugs, safety issues, no-mutation validation failures, path safety, health/lint consistency, and docs drift. Return findings with file/line references.
```

- [ ] **Step 8: Address review findings**

For every valid finding, write a focused failing test first when practical, implement the smallest fix, rerun the relevant tests, then commit:

```bash
git add tools tests README.md USER_GUIDE.md AGENTS.md graph/README.md docs/superpowers/specs/2026-05-12-muvywiki-design.md
git commit -m "fix: address query synthesis review"
```

- [ ] **Step 9: Final verification**

Run:

```bash
python -m unittest discover -s tests
python tools/health.py
python tools/lint.py
python tools/build_graph.py
```

Expected: all pass.

## Plan Self-Review

- Spec coverage: `query.py`, `save_synthesis.py`, health compatibility, docs updates, tests, and review are covered.
- Red-flag scan: no unresolved markers or copy-forward instructions remain.
- Type consistency: the plan consistently uses `synthesis_id` internally, `--id` as the public CLI option, `related_ids`, `source_ids`, and the JSON shape from the design.
- Scope check: this plan implements Query & Synthesis v1 only. Batch ingest, richer conversion, embeddings, and MCP wrappers remain future work.
