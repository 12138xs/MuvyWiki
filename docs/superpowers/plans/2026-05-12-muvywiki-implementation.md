# MuvyWiki Implementation Plan

> **Status:** Historical plan. This records the original repository skeleton work; current tool behavior is documented in `README.md`, `AGENTS.md`, and `docs/superpowers/specs/2026-05-13-interface-v1-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable MuvyWiki repository skeleton with strict Markdown conventions, append-only source provenance, deterministic health checks, and reserved interfaces for future graph, lint, conversion, and batch ingest.

**Architecture:** The repository is a plain Markdown knowledge base following Karpathy's `raw/`, `wiki/`, and `AGENTS.md` pattern. `raw/` is append-only source storage, `wiki/` is the agent-maintained knowledge layer, `templates/` defines canonical page shapes, and `tools/` provides deterministic CLI checks plus future extension points.

**Tech Stack:** Markdown, Python 3 standard library, Git, Obsidian-compatible wikilinks.

---

## File Structure

Create or modify these files:

- Create: `.gitignore` - ignore OS/editor/cache artifacts while keeping knowledge files tracked.
- Create: `README.md` - human-facing entry point and common commands.
- Create: `AGENTS.md` - executable operating protocol derived from the design spec.
- Create: `raw/README.md` - raw-source storage rules.
- Create: `raw/source-manifest.jsonl` - append-only source artifact manifest.
- Create: `raw/originals/.gitkeep` - keep original source directory tracked.
- Create: `raw/converted/.gitkeep` - keep converted source directory tracked.
- Create: `wiki/index.md` - parseable global catalog.
- Create: `wiki/log.md` - append-only operation log with init entry.
- Create: `wiki/overview.md` - initial overview page.
- Create: `wiki/sources/.gitkeep` - keep source pages directory tracked.
- Create: `wiki/concepts/.gitkeep` - keep concept pages directory tracked.
- Create: `wiki/entities/.gitkeep` - keep entity pages directory tracked.
- Create: `wiki/syntheses/.gitkeep` - keep synthesis pages directory tracked.
- Create: `templates/overview.md` - overview page template.
- Create: `templates/index-entry.md` - index entry format.
- Create: `templates/log-entry.md` - log entry format.
- Create: `templates/source.md` - source page template with provenance block.
- Create: `templates/concept.md` - concept page template.
- Create: `templates/entity.md` - entity page template.
- Create: `templates/synthesis.md` - synthesis page template.
- Create: `graph/README.md` - future graph artifact contract.
- Create: `graph/.gitkeep` - keep graph directory tracked.
- Create: `tools/health.py` - structural health checker.
- Create: `tools/lint.py` - reserved semantic lint interface.
- Create: `tools/build_graph.py` - reserved graph build interface.
- Create: `tools/convert.py` - reserved conversion interface.
- Create: `tests/test_health.py` - standard-library tests for health behavior.
- Create: `tests/test_reserved_tools.py` - standard-library tests for reserved tool exit contracts.

## Task 1: Repository Skeleton and Seed Wiki Pages

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `raw/README.md`
- Create: `raw/source-manifest.jsonl`
- Create: `raw/originals/.gitkeep`
- Create: `raw/converted/.gitkeep`
- Create: `wiki/index.md`
- Create: `wiki/log.md`
- Create: `wiki/overview.md`
- Create: `wiki/sources/.gitkeep`
- Create: `wiki/concepts/.gitkeep`
- Create: `wiki/entities/.gitkeep`
- Create: `wiki/syntheses/.gitkeep`
- Create: `graph/README.md`
- Create: `graph/.gitkeep`

- [ ] **Step 1: Create directory skeleton**

Run:

```bash
mkdir -p raw/originals raw/converted wiki/sources wiki/concepts wiki/entities wiki/syntheses graph templates tools tests
touch raw/originals/.gitkeep raw/converted/.gitkeep wiki/sources/.gitkeep wiki/concepts/.gitkeep wiki/entities/.gitkeep wiki/syntheses/.gitkeep graph/.gitkeep
```

Expected: directories exist and `git status --short` shows new untracked paths.

- [ ] **Step 2: Create `.gitignore`**

Write:

```gitignore
.DS_Store
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
node_modules/
graph/graph.json
graph/graph.html
graph/graph-report.md
```

- [ ] **Step 3: Create `raw/source-manifest.jsonl`**

Write an empty file:

```text
```

Expected: file exists and has zero bytes.

- [ ] **Step 4: Create `raw/README.md`**

Write:

````markdown
# Raw Sources

`raw/` stores source artifacts. Treat existing artifacts as append-only.

- Put original files in `raw/originals/`.
- Put derived Markdown or text in `raw/converted/`.
- Record every raw or converted artifact in `raw/source-manifest.jsonl`.
- Do not overwrite a raw artifact unless the user explicitly asks for it.

Each manifest line is JSON:

```json
{"source_id":"example-source","raw_path":"raw/originals/example.pdf","content_hash":"sha256:...","source_url":null,"collected_at":"YYYY-MM-DD","published_at":null,"converted_from":null,"converted_path":null,"converter":null,"converter_version":null}
```
````

- [ ] **Step 5: Create `wiki/overview.md`**

Write:

```markdown
---
canonical_id: "overview"
type: overview
title: "MuvyWiki Overview"
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

# MuvyWiki Overview

## Current Shape

MuvyWiki is initialized as a general personal knowledge base with an initial emphasis on technical and research material.

## Active Themes

- Knowledge-base infrastructure
- Technical and research source ingestion

## Strongest Syntheses

- No saved syntheses yet.

## Open Questions

- Which first sources should be ingested?
- Which technical themes should become early concept pages?

## Maintenance Notes

- Keep raw artifacts append-only.
- Use canonical IDs for internal links.
- Run `python tools/health.py` after structural edits.
```

- [ ] **Step 6: Create `wiki/index.md`**

Write:

```markdown
# MuvyWiki Index

## Overview

- [[overview|MuvyWiki Overview]] (`wiki/overview.md`) - type: overview - updated: 2026-05-12 - Living map of the knowledge base.

## Sources

No source pages yet.

## Concepts

No concept pages yet.

## Entities

No entity pages yet.

## Syntheses

No synthesis pages yet.
```

- [ ] **Step 7: Create `wiki/log.md`**

Write:

```markdown
# MuvyWiki Log

## [2026-05-12] init | repository skeleton

- Changed pages:
  - `wiki/index.md`
  - `wiki/overview.md`
  - `wiki/log.md`
- Raw paths:
  - `raw/source-manifest.jsonl`
- Source IDs:
  - none
- Unresolved issues:
  - none
```

- [ ] **Step 8: Create `graph/README.md`**

Write:

```markdown
# Graph Artifacts

This directory is reserved for future graph outputs.

Expected future files:

- `graph.json` - machine-readable nodes and edges.
- `graph.html` - self-contained visualization.
- `graph-report.md` - graph health and structure report.

Version one does not require graph output for normal knowledge-base use.
```

- [ ] **Step 9: Create root `README.md`**

Write:

````markdown
# MuvyWiki

MuvyWiki is a personal LLM-maintained knowledge base inspired by Andrej Karpathy's LLM Wiki pattern.

The repository has three layers:

- `raw/` stores original and converted source artifacts.
- `wiki/` stores the agent-maintained knowledge base.
- `AGENTS.md` defines the operating rules for Codex and compatible agents.

Common commands:

```bash
python tools/health.py
python tools/health.py --json
python tools/lint.py
python tools/build_graph.py
python tools/convert.py raw/originals/example.pdf --out raw/converted/example.md
```

Reserved tools may return exit code `3` until their full implementation is added.
````

- [ ] **Step 10: Verify skeleton files**

Run:

```bash
test -f wiki/index.md && test -f wiki/log.md && test -f wiki/overview.md && test -f raw/source-manifest.jsonl
```

Expected: command exits `0`.

- [ ] **Step 11: Commit Task 1**

Run:

```bash
git add .gitignore README.md raw wiki graph
git commit -m "feat: scaffold MuvyWiki repository"
```

Expected: commit succeeds.

## Task 2: Templates and Agent Operating Protocol

**Files:**
- Create: `templates/overview.md`
- Create: `templates/index-entry.md`
- Create: `templates/log-entry.md`
- Create: `templates/source.md`
- Create: `templates/concept.md`
- Create: `templates/entity.md`
- Create: `templates/synthesis.md`
- Create: `AGENTS.md`

- [ ] **Step 1: Create `templates/overview.md`**

Write:

```markdown
---
canonical_id: "overview"
type: overview
title: "MuvyWiki Overview"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
status: seed
confidence: medium
---

# MuvyWiki Overview

## Current Shape

## Active Themes

## Strongest Syntheses

## Open Questions

## Maintenance Notes
```

- [ ] **Step 2: Create `templates/index-entry.md`**

Write:

```markdown
- [[CanonicalID|Human Title]] (`wiki/path/File.md`) - type: concept - updated: YYYY-MM-DD - One sentence summary.
```

- [ ] **Step 3: Create `templates/log-entry.md`**

Write:

```markdown
## [YYYY-MM-DD] operation | title

- Changed pages:
- Raw paths:
- Source IDs:
- Unresolved issues:
```

- [ ] **Step 4: Create `templates/source.md`**

Write:

```markdown
---
canonical_id: "source-slug"
type: source
title: "Source Title"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths:
  - "raw/originals/source-slug.ext"
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
status: seed
confidence: medium
provenance:
  source_id: "source-slug"
  raw_path: "raw/originals/source-slug.ext"
  content_hash: "sha256:..."
  source_url: null
  collected_at: "YYYY-MM-DD"
  published_at: null
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
---

# Source Title

## Summary

## Key Claims

## Evidence and Details

## Concepts

## Entities

## Open Questions

## Contradictions or Tensions

## Raw Source
```

- [ ] **Step 5: Create `templates/concept.md`**

Write:

```markdown
---
canonical_id: "ConceptName"
type: concept
title: "Concept Name"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
status: seed
confidence: medium
---

# Concept Name

## Definition

## Claims

## Why It Matters

## Mechanism

## Boundaries and Failure Modes

## Evidence

## Contradictions or Tensions

## Related Concepts

## Supporting Sources

## Open Questions
```

- [ ] **Step 6: Create `templates/entity.md`**

Write:

```markdown
---
canonical_id: "EntityName"
type: entity
title: "Entity Name"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
status: seed
confidence: medium
---

# Entity Name

## Summary

## Role in the Wiki

## Claims

## Evidence

## Contradictions or Tensions

## Related Concepts

## Related Sources

## Timeline

## Open Questions
```

- [ ] **Step 7: Create `templates/synthesis.md`**

Write:

```markdown
---
canonical_id: "synthesis-slug"
type: synthesis
title: "Synthesis Title"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
status: seed
confidence: medium
---

# Synthesis Title

## Question

## Answer

## Evidence

## Contradictions or Tensions

## Implications

## Related Pages

## Follow-up Questions
```

- [ ] **Step 8: Create `AGENTS.md`**

Write:

```markdown
# MuvyWiki Agent Protocol

This repository is a personal LLM-maintained knowledge base. Follow the design in `docs/superpowers/specs/2026-05-12-muvywiki-design.md`.

## Core Model

- `raw/` is append-only source storage.
- `wiki/` is the maintained knowledge layer.
- `templates/` defines canonical page shapes.
- `tools/` contains deterministic checks and reserved extension interfaces.

## Raw Source Rules

- Never modify an existing raw artifact in place.
- Store originals under `raw/originals/`.
- Store converted Markdown or text under `raw/converted/`.
- Record artifacts in `raw/source-manifest.jsonl`.
- Check content hashes before creating duplicate source pages.

## Canonical IDs

- Source and synthesis IDs use kebab-case.
- Concept and entity IDs use PascalCase or canonical product capitalization.
- Frontmatter `canonical_id` must match the file stem.
- Internal links must target canonical IDs.
- Use display text when needed: `[[CanonicalID|Human Title]]`.
- Aliases are lookup helpers, not link targets.

## Ingest Workflow

1. Read the source fully.
2. Compute the artifact hash and check `raw/source-manifest.jsonl`.
3. Save new artifacts under `raw/originals/`.
4. Read `wiki/index.md` and `wiki/overview.md`.
5. Create or update one source page.
6. Update relevant concept and entity pages.
7. Record contradictions or tensions instead of silently choosing a winner.
8. Update `wiki/index.md`, `wiki/overview.md`, and `wiki/log.md`.
9. Update `raw/source-manifest.jsonl`.
10. Run `python tools/health.py`.
11. Report changed pages and unresolved issues.

## Query Workflow

- Read `wiki/index.md` first.
- Read relevant wiki pages before answering.
- Answer from wiki content first and cite pages with `[[WikiLinks]]`.
- Clearly label anything from model knowledge rather than wiki pages.
- Ask before expanding to web search or new external sources.
- Save durable answers as synthesis pages only when the user asks.

## Health Requirements

Run `python tools/health.py` after structural edits and after ingest. Use `python tools/health.py --json` when machine-readable evidence is useful.
```

- [ ] **Step 9: Verify templates and protocol exist**

Run:

```bash
test -f AGENTS.md && test -f templates/source.md && test -f templates/concept.md && test -f templates/entity.md && test -f templates/synthesis.md
```

Expected: command exits `0`.

- [ ] **Step 10: Commit Task 2**

Run:

```bash
git add AGENTS.md templates
git commit -m "feat: add MuvyWiki templates and agent protocol"
```

Expected: commit succeeds.

## Task 3: Reserved Tool Interfaces

**Files:**
- Create: `tools/lint.py`
- Create: `tools/build_graph.py`
- Create: `tools/convert.py`
- Create: `tests/test_reserved_tools.py`

- [ ] **Step 1: Write tests for reserved tool contracts**

Create `tests/test_reserved_tools.py`:

```python
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReservedToolTests(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_lint_returns_reserved_exit_code(self):
        result = self.run_tool("tools/lint.py")
        self.assertEqual(result.returncode, 3)
        self.assertIn("reserved for future semantic linting", result.stdout)

    def test_build_graph_returns_reserved_exit_code(self):
        result = self.run_tool("tools/build_graph.py")
        self.assertEqual(result.returncode, 3)
        self.assertIn("reserved for future graph generation", result.stdout)

    def test_convert_returns_reserved_exit_code(self):
        result = self.run_tool("tools/convert.py", "raw/originals/example.pdf", "--out", "raw/converted/example.md")
        self.assertEqual(result.returncode, 3)
        self.assertIn("reserved for future conversion", result.stdout)

    def test_convert_requires_output_argument(self):
        result = self.run_tool("tools/convert.py", "raw/originals/example.pdf")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python -m unittest tests/test_reserved_tools.py
```

Expected: FAIL because the reserved tools do not exist yet.

- [ ] **Step 3: Create `tools/lint.py`**

Write:

```python
#!/usr/bin/env python3
"""Reserved semantic lint interface for MuvyWiki."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run semantic lint checks for MuvyWiki.")
    parser.add_argument("--report", default="graph/graph-report.md", help="Path for a future lint report.")
    parser.parse_args(argv)
    print("tools/lint.py is reserved for future semantic linting. Run tools/health.py for v1 structural checks.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Create `tools/build_graph.py`**

Write:

```python
#!/usr/bin/env python3
"""Reserved graph generation interface for MuvyWiki."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build future MuvyWiki graph artifacts.")
    parser.add_argument("--json", default="graph/graph.json", help="Future graph JSON output path.")
    parser.add_argument("--html", default="graph/graph.html", help="Future graph HTML output path.")
    parser.add_argument("--report", default="graph/graph-report.md", help="Future graph report output path.")
    parser.parse_args(argv)
    print("tools/build_graph.py is reserved for future graph generation. Run tools/health.py for v1 structural checks.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Create `tools/convert.py`**

Write:

```python
#!/usr/bin/env python3
"""Reserved source conversion interface for MuvyWiki."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert future source artifacts into Markdown.")
    parser.add_argument("input_path_or_url", help="Input source path or URL.")
    parser.add_argument("--out", required=True, help="Output path under raw/converted/.")
    args = parser.parse_args(argv)
    if not args.out.startswith("raw/converted/"):
        print("Output path must be under raw/converted/.", file=sys.stderr)
        return 2
    print("tools/convert.py is reserved for future conversion. Provide Markdown or pasted text for v1 ingest.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run reserved tool tests**

Run:

```bash
python -m unittest tests/test_reserved_tools.py
```

Expected: PASS with 4 tests.

- [ ] **Step 7: Commit Task 3**

Run:

```bash
git add tools/lint.py tools/build_graph.py tools/convert.py tests/test_reserved_tools.py
git commit -m "feat: add reserved tool interfaces"
```

Expected: commit succeeds.

## Task 4: Deterministic Health Checker

**Files:**
- Create: `tools/health.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write failing health tests**

Create `tests/test_health.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run health tests and verify they fail**

Run:

```bash
python -m unittest tests/test_health.py
```

Expected: FAIL because `tools/health.py` does not exist yet.

- [ ] **Step 3: Create `tools/health.py`**

Write:

```python
#!/usr/bin/env python3
"""Structural health checks for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_PATHS = [
    ".gitignore",
    "README.md",
    "AGENTS.md",
    "raw/README.md",
    "raw/source-manifest.jsonl",
    "raw/originals",
    "raw/converted",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/overview.md",
    "wiki/sources",
    "wiki/concepts",
    "wiki/entities",
    "wiki/syntheses",
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
    "graph/README.md",
]

INDEX_ENTRY_RE = re.compile(
    r"^- \[\[(?P<id>[^|\]]+)\|(?P<title>[^\]]+)\]\] "
    r"\(`(?P<path>[^`]+)`\) - type: (?P<type>[a-z]+) - updated: "
    r"(?P<date>\d{4}-\d{2}-\d{2}) - (?P<summary>.+)$"
)
LOG_HEADING_RE = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] (init|ingest|query|health|lint|graph|convert|batch) \| .+$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
SOURCE_PROVENANCE_KEYS = {
    "source_id",
    "raw_path",
    "content_hash",
    "source_url",
    "collected_at",
    "published_at",
    "converted_from",
    "converted_path",
    "converter",
    "converter_version",
}


@dataclass
class Issue:
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "message": self.message}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_wiki_pages(root: Path) -> list[Path]:
    paths = []
    for folder in ("sources", "concepts", "entities", "syntheses"):
        base = root / "wiki" / folder
        if base.exists():
            paths.extend(sorted(base.glob("*.md")))
    overview = root / "wiki" / "overview.md"
    if overview.exists():
        paths.append(overview)
    return paths


def extract_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" in line and not line.startswith("  "):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"')
    return result


def content_after_frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text
    return text[match.end():].strip()


def load_manifest(root: Path, issues: list[Issue]) -> dict[str, dict[str, object]]:
    manifest_path = root / "raw" / "source-manifest.jsonl"
    entries: dict[str, dict[str, object]] = {}
    hashes: dict[str, str] = {}
    if not manifest_path.exists():
        return entries
    for line_number, line in enumerate(read_text(manifest_path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(Issue("raw/source-manifest.jsonl", f"invalid JSON on line {line_number}: {exc.msg}"))
            continue
        source_id = entry.get("source_id")
        content_hash = entry.get("content_hash")
        raw_path = entry.get("raw_path")
        if not isinstance(source_id, str) or not source_id:
            issues.append(Issue("raw/source-manifest.jsonl", f"missing source_id on line {line_number}"))
            continue
        if source_id in entries:
            issues.append(Issue("raw/source-manifest.jsonl", f"duplicate source_id: {source_id}"))
        entries[source_id] = entry
        if not isinstance(raw_path, str) or not raw_path:
            issues.append(Issue("raw/source-manifest.jsonl", f"missing raw_path for {source_id}"))
        if not isinstance(content_hash, str) or not content_hash.startswith("sha256:"):
            issues.append(Issue("raw/source-manifest.jsonl", f"invalid content_hash for {source_id}"))
        elif content_hash in hashes:
            issues.append(Issue("raw/source-manifest.jsonl", f"duplicate content_hash for {source_id} and {hashes[content_hash]}"))
        else:
            hashes[content_hash] = source_id
    return entries


def check_required_paths(root: Path, issues: list[Issue]) -> None:
    for rel in REQUIRED_PATHS:
        if not (root / rel).exists():
            issues.append(Issue(rel, "missing required path"))


def check_wiki_pages(root: Path, issues: list[Issue]) -> set[str]:
    canonical_ids: set[str] = set()
    aliases: dict[str, str] = {}
    for path in collect_wiki_pages(root):
        rel = path.relative_to(root).as_posix()
        text = read_text(path)
        frontmatter = extract_frontmatter(text)
        if not frontmatter:
            issues.append(Issue(rel, "missing frontmatter"))
            continue
        canonical_id = frontmatter.get("canonical_id")
        if not canonical_id:
            issues.append(Issue(rel, "missing canonical_id"))
        elif canonical_id != path.stem:
            issues.append(Issue(rel, "canonical_id must match file stem"))
        else:
            canonical_ids.add(canonical_id)
        if not frontmatter.get("type"):
            issues.append(Issue(rel, "missing type"))
        if not content_after_frontmatter(text):
            issues.append(Issue(rel, "page appears empty beyond frontmatter"))
        alias_match = re.search(r"aliases:\n((?:  - .+\n)+)", text)
        if alias_match and canonical_id:
            for alias_line in alias_match.group(1).splitlines():
                alias = alias_line.replace("-", "", 1).strip().strip('"')
                owner = aliases.setdefault(alias, canonical_id)
                if owner != canonical_id:
                    issues.append(Issue(rel, f"alias collision: {alias}"))
    return canonical_ids


def check_source_provenance(root: Path, manifest_entries: dict[str, dict[str, object]], issues: list[Issue]) -> None:
    source_dir = root / "wiki" / "sources"
    if not source_dir.exists():
        return
    for path in sorted(source_dir.glob("*.md")):
        rel = path.relative_to(root).as_posix()
        text = read_text(path)
        frontmatter_match = FRONTMATTER_RE.match(text)
        frontmatter = extract_frontmatter(text)
        canonical_id = frontmatter.get("canonical_id")
        if not frontmatter_match:
            continue
        frontmatter_body = frontmatter_match.group("body")
        missing_keys = [key for key in SOURCE_PROVENANCE_KEYS if not re.search(rf"^\s{{2}}{re.escape(key)}:", frontmatter_body, re.MULTILINE)]
        for key in sorted(missing_keys):
            issues.append(Issue(rel, f"missing provenance field: {key}"))
        if canonical_id and canonical_id not in manifest_entries:
            issues.append(Issue(rel, f"missing manifest entry for source_id: {canonical_id}"))
        if canonical_id and canonical_id in manifest_entries:
            entry = manifest_entries[canonical_id]
            raw_path = entry.get("raw_path")
            if isinstance(raw_path, str) and raw_path and not (root / raw_path).exists():
                issues.append(Issue(rel, f"manifest raw_path does not exist: {raw_path}"))


def check_index(root: Path, canonical_ids: set[str], issues: list[Issue]) -> None:
    index_path = root / "wiki" / "index.md"
    if not index_path.exists():
        return
    text = read_text(index_path)
    indexed_ids: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("- [["):
            continue
        match = INDEX_ENTRY_RE.match(line)
        if not match:
            issues.append(Issue("wiki/index.md", f"invalid index entry: {line}"))
            continue
        indexed_ids.add(match.group("id"))
        listed_path = root / match.group("path")
        if not listed_path.exists():
            issues.append(Issue("wiki/index.md", f"indexed path does not exist: {match.group('path')}"))
    for canonical_id in sorted(canonical_ids):
        if canonical_id not in indexed_ids:
            issues.append(Issue("wiki/index.md", f"missing index entry for {canonical_id}"))


def check_log(root: Path, issues: list[Issue]) -> None:
    log_path = root / "wiki" / "log.md"
    if not log_path.exists():
        return
    headings = [line for line in read_text(log_path).splitlines() if line.startswith("## ")]
    if not headings:
        issues.append(Issue("wiki/log.md", "missing log entry"))
    for heading in headings:
        if not LOG_HEADING_RE.match(heading):
            issues.append(Issue("wiki/log.md", f"invalid log heading: {heading}"))


def check_wikilinks(root: Path, canonical_ids: set[str], issues: list[Issue]) -> None:
    for path in collect_wiki_pages(root):
        rel = path.relative_to(root).as_posix()
        for target in WIKILINK_RE.findall(read_text(path)):
            if target not in canonical_ids:
                issues.append(Issue(rel, f"wikilink target not found: {target}"))


def run(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    check_required_paths(root, issues)
    manifest_entries = load_manifest(root, issues)
    canonical_ids = check_wiki_pages(root, issues)
    check_source_provenance(root, manifest_entries, issues)
    check_index(root, canonical_ids, issues)
    check_log(root, issues)
    check_wikilinks(root, canonical_ids, issues)
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run structural health checks for MuvyWiki.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable health output.")
    args = parser.parse_args(argv)

    issues = run(Path.cwd())
    status = "ok" if not issues else "issues"
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if args.json:
        print(json.dumps({"status": status, "issues": [issue.as_dict() for issue in issues], "checked_at": checked_at}, indent=2))
    else:
        print(f"MuvyWiki health: {status}")
        for issue in issues:
            print(f"- {issue.path}: {issue.message}")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run health tests**

Run:

```bash
python -m unittest tests/test_health.py
```

Expected: PASS with 3 tests.

- [ ] **Step 5: Run health command manually**

Run:

```bash
python tools/health.py
python tools/health.py --json
```

Expected: both commands exit `0`; text output includes `MuvyWiki health: ok`; JSON output contains `status`, `issues`, and `checked_at`.

- [ ] **Step 6: Commit Task 4**

Run:

```bash
git add tools/health.py tests/test_health.py
git commit -m "feat: add MuvyWiki health checks"
```

Expected: commit succeeds.

## Task 5: Final Verification and Documentation Polish

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `wiki/log.md`

- [ ] **Step 1: Re-read README and AGENTS against the spec**

Run:

```bash
sed -n '1,220p' README.md
sed -n '1,260p' AGENTS.md
sed -n '1,560p' docs/superpowers/specs/2026-05-12-muvywiki-design.md
```

Expected: README and AGENTS do not contradict the spec.

- [ ] **Step 2: Add final setup log entry if verification changed files**

If Task 5 modifies README or AGENTS, append this to `wiki/log.md`:

```markdown
## [2026-05-12] health | final setup verification

- Changed pages:
  - `README.md`
  - `AGENTS.md`
- Raw paths:
  - none
- Source IDs:
  - none
- Unresolved issues:
  - none
```

If Task 5 does not modify files, do not add a log entry.

- [ ] **Step 3: Run all tests**

Run:

```bash
python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 4: Run all CLI verification commands**

Run:

```bash
python tools/health.py
python tools/health.py --json
python tools/lint.py
test $? -eq 3
python tools/build_graph.py
test $? -eq 3
python tools/convert.py raw/originals/example.pdf --out raw/converted/example.md
test $? -eq 3
git status --short
```

Expected:

- `health.py` exits `0`.
- `lint.py`, `build_graph.py`, and `convert.py` exit `3`.
- `git status --short` only shows intended Task 5 edits, or no output if nothing changed.

- [ ] **Step 5: Commit final polish if needed**

Run only if Task 5 changed files:

```bash
git add README.md AGENTS.md wiki/log.md
git commit -m "docs: polish MuvyWiki usage docs"
```

Expected: commit succeeds, or this step is skipped if no files changed.

- [ ] **Step 6: Final clean check**

Run:

```bash
git status --short
git log --oneline -5
```

Expected: working tree is clean and recent commits correspond to the completed tasks.

## Self-Review

Spec coverage:

- Directory structure from the design spec is covered by Task 1.
- Page templates and AGENTS protocol are covered by Task 2.
- Reserved lint, graph, and conversion interfaces are covered by Task 3.
- Deterministic health checks and JSON output are covered by Task 4.
- Final commands and documentation consistency are covered by Task 5.

Type and naming consistency:

- Frontmatter uses `canonical_id`, `source_ids`, `related_ids`, and `raw_paths`.
- Internal links target canonical IDs and may use display labels.
- Source and synthesis IDs use kebab-case; concept and entity IDs use PascalCase.
- Reserved tools use exit code `3` for future interfaces.

Known implementation risk:

- The health checker frontmatter parser is intentionally lightweight. It is sufficient for the v1 templates but should be replaced with a YAML parser if nested frontmatter becomes complex beyond the source provenance block.
