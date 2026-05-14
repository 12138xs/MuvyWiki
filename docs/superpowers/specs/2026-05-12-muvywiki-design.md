# MuvyWiki Design Spec

## Purpose

MuvyWiki is a personal LLM-maintained knowledge base inspired by Andrej Karpathy's LLM Wiki pattern. It is designed as a general personal knowledge base, with the first practical use case focused on technical and research material.

The core idea is to keep raw sources immutable, let the LLM maintain a structured Markdown wiki, and use a root-level agent instruction file as the schema and operating manual. The human curates sources, asks questions, and reviews direction. The agent handles summarization, cross-linking, indexing, contradiction tracking, and routine maintenance.

## Design Goals

- Use plain Markdown files so the knowledge base works in Codex, Obsidian, GitHub, and ordinary editors.
- Keep the first version lightweight enough to use immediately.
- Preserve extension points for future graph visualization, semantic linting, multi-format conversion, and batch ingest.
- Prefer stable conventions over clever automation.
- Optimize for compounding knowledge: every source and high-value query should make later answers cheaper and richer.

## Chosen Approach

Use a hybrid of the lightweight Astro-Han style and the fuller SamurAIGPT template:

- Adopt Karpathy's three-layer model: `raw/`, `wiki/`, and `AGENTS.md`.
- Include first-class `sources`, `concepts`, `entities`, and `syntheses` areas from day one.
- Implement lightweight deterministic tooling first.
- Preserve hooks for richer graph, conversion, and semantic lint tooling without making them required for normal use.

This keeps the repository useful immediately while avoiding a later structural migration.

## Directory Structure

```text
raw/
  .gitkeep
  README.md
  source-manifest.jsonl
  originals/
    .gitkeep
  converted/
    .gitkeep

wiki/
  index.md
  log.md
  overview.md
  sources/
    .gitkeep
  concepts/
    .gitkeep
  entities/
    .gitkeep
  syntheses/
    .gitkeep

templates/
  overview.md
  index-entry.md
  log-entry.md
  source.md
  concept.md
  entity.md
  synthesis.md

tools/
  health.py
  lint.py
  build_graph.py
  convert.py

graph/
  README.md
  .gitkeep

docs/
  superpowers/
    specs/
      2026-05-12-muvywiki-design.md
    plans/

AGENTS.md
README.md
.gitignore
```

## Responsibilities

### `raw/`

`raw/` contains immutable source material. The agent may add files here when ingesting a URL, pasted text, or converted document, but it must not modify an existing raw artifact in place. If a source needs cleanup or conversion, the original stays in `raw/originals/`, the derived Markdown or text artifact goes in `raw/converted/`, and the transformation is recorded in `raw/source-manifest.jsonl` and the corresponding source page.

Recommended first-level folders can emerge naturally, for example `raw/articles/`, `raw/papers/`, `raw/books/`, `raw/projects/`, and `raw/notes/`. The first version does not enforce these folders.

If topical folders are added later, they should sit under `raw/originals/` or `raw/converted/` rather than replacing those provenance boundaries.

`raw/source-manifest.jsonl` is append-only. Each line records one raw or converted artifact:

```json
{"source_id":"attention-is-all-you-need","raw_path":"raw/originals/attention-is-all-you-need.pdf","content_hash":"sha256:...","source_url":"https://arxiv.org/abs/1706.03762","collected_at":"YYYY-MM-DD","published_at":"YYYY-MM-DD","converted_from":null,"converter":null}
```

The manifest supports future batch ingest and duplicate detection. A new ingest must compare the candidate artifact hash against the manifest before creating a duplicate source page.

### `wiki/`

`wiki/` is the compiled knowledge layer owned by the agent. The agent may create and update pages here as part of ingest, query archiving, health checks, and linting.

`wiki/index.md` is the global catalog. It should list every wiki page except `index.md` and `log.md`, grouped by page type. `overview.md` must be listed explicitly under `Overview`.

`wiki/log.md` is append-only. Entries must use parseable headings:

```markdown
## [YYYY-MM-DD] operation | title
```

Allowed operations are `init`, `ingest`, `query`, `health`, `lint`, `graph`, `convert`, and `batch`.

Every log entry body must include:

```markdown
- Changed pages:
- Raw paths:
- Source IDs:
- Unresolved issues:
```

`wiki/overview.md` is a living synthesis of what the knowledge base currently contains and where it is developing.

### `templates/`

`templates/` stores canonical page shapes. The agent should use these templates when creating pages, but may adapt sections when a source demands it. `templates/index-entry.md` and `templates/log-entry.md` define parseable formats for `wiki/index.md` and `wiki/log.md`.

### `tools/`

`tools/` stores deterministic helper scripts. Interface v1 update: `health.py`, `lint.py`, `build_graph.py`, local Markdown/text `convert.py`, `query.py`, and `save_synthesis.py` are implemented as lightweight standard-library tools. Future work can expand these interfaces without changing the repository contract.

### `graph/`

`graph/` stores generated graph artifacts:

- `graph/graph.json`
- `graph/graph.html`
- `graph/graph-report.md`

Interface v1 update: `python tools/build_graph.py` writes these artifacts from wiki frontmatter, wikilinks, source IDs, related IDs, and raw paths. Graph output is still not required for basic ingest or query workflows.

### `AGENTS.md`

`AGENTS.md` is the executable schema layer for Codex and other compatible coding agents. It must be derived from this design rather than loosely paraphrased. If this design and `AGENTS.md` diverge, update the design or `AGENTS.md` explicitly before relying on the workflow.

## Page Frontmatter

All wiki pages use this base frontmatter:

```yaml
---
canonical_id: "CanonicalID"
type: source | concept | entity | synthesis | overview
title: "Page Title"
tags: []
aliases: []
source_ids: []
related_ids: []
raw_paths: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
status: seed | active | archived
confidence: low | medium | high
---
```

Fields:

- `canonical_id`: stable machine-readable page identifier. It must match the file stem.
- `type`: page category.
- `title`: human-readable page title.
- `tags`: broad topical tags.
- `aliases`: alternate names useful for graph and search.
- `source_ids`: canonical IDs for source pages that support the page.
- `related_ids`: canonical IDs for related pages.
- `raw_paths`: raw artifacts directly attached to this page, usually populated only for source pages.
- `created`: first creation date.
- `last_updated`: last knowledge-content update date.
- `status`: maturity of the page.
- `confidence`: confidence in the current synthesis.

Frontmatter is machine-readable only. Body text may use natural language and Obsidian links.

## Canonical IDs and Link Resolution

Filenames define canonical IDs:

- Source and synthesis IDs use kebab-case, for example `attention-is-all-you-need`.
- Concept and entity IDs use PascalCase or canonical product capitalization, for example `RetrievalAugmentedGeneration`, `OpenAI`, and `GPT5`.

Internal links must target canonical IDs. Use Obsidian display text when the human title differs:

```markdown
[[RetrievalAugmentedGeneration|Retrieval-Augmented Generation]]
```

Aliases are secondary lookup keys, not link targets. If two pages define the same alias, health and graph tooling must report the ambiguity. The agent should not create or preserve ambiguous links.

Use Markdown links for `raw/` files and external URLs.

## Index Format

`wiki/index.md` must use one parseable bullet format:

```markdown
- [[CanonicalID|Human Title]] (`wiki/path/File.md`) - type: concept - updated: YYYY-MM-DD - summary
```

Rules:

- Each wiki page except `index.md` and `log.md` appears exactly once.
- `overview.md` appears under the `## Overview` heading.
- Source, concept, entity, and synthesis entries appear under headings matching their page type.
- The path in backticks is repository-relative.
- The summary is one sentence without nested bullets.

## Page Types

### Overview Page

Location: `wiki/overview.md`

Purpose: maintain a living map of the knowledge base, current emphasis, durable themes, and open research directions.

Required sections:

- `## Current Shape`
- `## Active Themes`
- `## Strongest Syntheses`
- `## Open Questions`
- `## Maintenance Notes`

### Source Pages

Location: `wiki/sources/<slug>.md`

Purpose: summarize one source and preserve its key claims, evidence, terminology, and connections.

Every ingested document gets exactly one source page. Papers, tools, datasets, people, companies, and projects get separate entity pages only when they become recurring objects discussed across sources or queries.

Source pages must include this required provenance block in addition to the base frontmatter:

```yaml
provenance:
  source_id: "attention-is-all-you-need"
  raw_path: "raw/originals/attention-is-all-you-need.pdf"
  content_hash: "sha256:..."
  source_url: "https://arxiv.org/abs/1706.03762"
  collected_at: "YYYY-MM-DD"
  published_at: "YYYY-MM-DD"
  converted_from: null
  converted_path: null
  converter: null
  converter_version: null
```

If a converted artifact exists, `converted_from` points to the original raw path and `converted_path` points to the derived artifact.

Required sections:

- `## Summary`
- `## Key Claims`
- `## Evidence and Details`
- `## Concepts`
- `## Entities`
- `## Open Questions`
- `## Contradictions or Tensions`
- `## Raw Source`

### Concept Pages

Location: `wiki/concepts/<ConceptName>.md`

Purpose: maintain reusable explanations of ideas, methods, theories, and technical concepts.

Required sections:

- `## Definition`
- `## Claims`
- `## Why It Matters`
- `## Mechanism`
- `## Boundaries and Failure Modes`
- `## Evidence`
- `## Contradictions or Tensions`
- `## Related Concepts`
- `## Supporting Sources`
- `## Open Questions`

### Entity Pages

Location: `wiki/entities/<EntityName>.md`

Purpose: track people, organizations, projects, tools, products, papers, and datasets.

Required sections:

- `## Summary`
- `## Role in the Wiki`
- `## Claims`
- `## Evidence`
- `## Contradictions or Tensions`
- `## Related Concepts`
- `## Related Sources`
- `## Timeline`
- `## Open Questions`

### Synthesis Pages

Location: `wiki/syntheses/<slug>.md`

Purpose: preserve high-value query answers, comparisons, research memos, and evolving judgments.

Required sections:

- `## Question`
- `## Answer`
- `## Evidence`
- `## Contradictions or Tensions`
- `## Implications`
- `## Related Pages`
- `## Follow-up Questions`

## Workflows

### Ingest

Triggered by requests such as `ingest raw/...`, `ingest this article`, or `摄取这篇论文`.

Steps:

1. Read the source fully.
2. Compute the candidate artifact hash and check `raw/source-manifest.jsonl` for duplicates.
3. If the source is not already in `raw/`, save it as a new artifact under `raw/originals/` without modifying existing artifacts.
4. Read `wiki/index.md` and `wiki/overview.md`.
5. Create or update one `wiki/sources/<slug>.md` page.
6. Extract durable concepts and update or create `wiki/concepts/` pages.
7. Extract durable entities and update or create `wiki/entities/` pages.
8. Flag contradictions, tensions, and changed claims on affected pages.
9. Update `wiki/index.md`.
10. Update `wiki/overview.md` if the source changes the broader picture.
11. Append an entry to `wiki/log.md`.
12. Update `raw/source-manifest.jsonl` with the source identity and content hash.
13. Run `python tools/health.py`.
14. Report changed pages and any unresolved issues.

Version one prefers one source per ingest. Batch ingest is future tooling and must use `raw/source-manifest.jsonl` content hashes for idempotency.

### Query

Triggered by requests such as `query: ...`, `我对 X 知道什么？`, or `比较 A 和 B`.

Steps:

1. Use `python tools/query.py "retrieval augmented generation" --json` for deterministic first-pass context when useful.
2. Read `wiki/index.md` when manually navigating.
3. Read the relevant wiki pages.
4. Answer from wiki content first.
5. Cite internal pages with `[[WikiLinks]]`.
6. Clearly label any answer material that comes from model knowledge rather than wiki pages.
7. Ask before expanding to web search or new external sources.
8. If the answer has long-term value, ask whether to save it as a synthesis page.

Plain queries do not modify files unless the user asks to save or archive the answer.

Minimum CLI contract:

```bash
python tools/query.py "retrieval augmented generation" [--json]
```

The query helper builds local context packets from wiki pages. It does not call an LLM, fetch remote sources, or modify files.

### Save Synthesis

Triggered after the user approves saving a high-value query answer.

Steps:

1. Confirm the user wants to save the synthesis.
2. Prepare answer Markdown and evidence Markdown.
3. Run `python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md`.
4. Run `python tools/health.py` and `python tools/lint.py`.

The synthesis helper persists approved synthesis pages and updates `wiki/index.md` and `wiki/log.md`. It does not call an LLM, fetch remote sources, ingest raw sources, or append to `raw/source-manifest.jsonl` unless a separate raw or converted artifact is created by another workflow.

Minimum CLI contract:

```bash
python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md
```

### Health

Triggered by `health` or run automatically after ingest.

Version one implements deterministic checks:

- Required directories exist.
- Required root files exist.
- Wiki pages are non-empty beyond frontmatter.
- Pages in `wiki/sources`, `wiki/concepts`, `wiki/entities`, `wiki/syntheses`, and `wiki/overview.md` are listed in `wiki/index.md`.
- `wiki/index.md` entries match the parseable index format.
- Frontmatter fields use the expected machine-readable types.
- Source pages include required provenance fields and matching manifest entries.
- `[[WikiLinks]]` target canonical IDs and have plausible targets.
- Alias collisions are reported.
- `wiki/log.md` uses parseable headings.

The script should print a concise report and exit non-zero when structural issues are found.

Minimum CLI contract:

```bash
python tools/health.py [--json]
```

Exit codes:

- `0`: no structural issues.
- `1`: structural issues found.
- `2`: invalid command usage.

With `--json`, output must include `status`, `issues`, and `checked_at`.

### Lint

Triggered by `lint`.

Interface v1 update: `lint.py` implements deterministic semantic-lite checks and documents report shape. Future versions can add richer checks for:

- Contradictions across pages.
- Outdated claims superseded by newer sources.
- Missing concept pages.
- Missing entity pages.
- Orphan pages.
- Low link density.
- Data gaps and suggested sources.

Semantic linting should run after health passes.

Minimum CLI contract:

```bash
python tools/lint.py [--json] [--report graph/lint-report.md]
```

Current exit codes are `0` for no semantic issues, `1` for semantic issues, and `2` for invalid command usage or invalid report paths.

### Graph

Triggered by `build graph`.

Interface v1 update: `build_graph.py` implements the local graph interface. Current behavior:

- Parses `[[WikiLinks]]`, `source_ids`, `related_ids`, and raw/provenance paths across wiki pages.
- Builds `graph/graph.json` with nodes, edges, and summary counts.
- Produces `graph/graph.html` as a self-contained inspection artifact.
- Produces `graph/graph-report.md` with node and edge type summaries.

Page frontmatter and link conventions in version one are designed to support this later without migration.

Minimum CLI contract:

```bash
python tools/build_graph.py [--json graph/graph.json] [--html graph/graph.html] [--report graph/graph-report.md]
```

Current exit codes are `0` when artifacts are written and `2` for invalid paths or write failures.

`graph/graph.json` must use this schema shape:

```json
{
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "nodes": [
    {
      "id": "RetrievalAugmentedGeneration",
      "path": "wiki/concepts/RetrievalAugmentedGeneration.md",
      "title": "Retrieval-Augmented Generation",
      "type": "concept",
      "tags": [],
      "status": "seed",
      "confidence": "medium"
    }
  ],
  "edges": [
    {
      "source": "RetrievalAugmentedGeneration",
      "target": "VectorDatabase",
      "type": "wikilink | related | source | raw",
      "path": "wiki/concepts/RetrievalAugmentedGeneration.md"
    }
  ]
}
```

### Conversion

Triggered before ingest when the user has local Markdown or UTF-8 text that should be normalized into `raw/converted/`.

Interface v1 update: `tools/convert.py` supports local Markdown, `.markdown`, `.txt`, and extensionless UTF-8 text. Future versions may integrate `markitdown`, high-fidelity PDF conversion, arXiv-specific conversion, remote fetch, rendered HTML, and office document conversion.

If conversion is unavailable for a source format, the agent should ask the user for Markdown or pasted text rather than silently skipping content.

Minimum CLI contract:

```bash
python tools/convert.py <input_path_or_url> --out raw/converted/<slug>.md
```

Current conversion writes converted artifacts only under `raw/converted/` and refuses to overwrite existing outputs. Conversion does not update `raw/source-manifest.jsonl` or wiki pages; ingest must still record provenance.

## Naming Conventions

- Source slugs use kebab-case: `attention-is-all-you-need`.
- Concept pages use PascalCase: `RetrievalAugmentedGeneration.md`.
- Entity pages use PascalCase or canonical capitalization: `OpenAI.md`, `AndrejKarpathy.md`, `GPT5.md`.
- Synthesis pages use kebab-case.
- Internal links target canonical IDs. Display text may use `[[CanonicalID|Human Title]]`.
- File names should be stable; rename only when the current name is actively misleading.

## Error Handling

- Never overwrite raw sources without explicit user approval.
- If a source contradicts existing pages, record the contradiction rather than choosing a winner silently.
- If a page link is ambiguous, report it instead of guessing.
- If a source format or future tool capability is not implemented yet, explain the missing capability and fall back to the documented manual workflow.
- If a source hash already exists in `raw/source-manifest.jsonl`, treat the ingest as a duplicate unless the user explicitly wants a new source page.
- If health checks fail after ingest, report the issue and the files involved.

## Testing and Verification

Initial verification should include:

- Running `python tools/health.py`.
- Running `python tools/health.py --json`.
- Confirming required directories and files exist.
- Confirming `wiki/index.md` references all initial wiki pages.
- Confirming `wiki/log.md` contains an initialization entry.
- Confirming source pages and `raw/source-manifest.jsonl` agree on source IDs, raw paths, and hashes.
- Confirming implemented tools produce documented output and exit codes.

Future verification should add:

- Richer graph generation fixture tests.
- Conversion fixture tests for future document types.
- Richer lint report fixture tests.
- Batch ingest tests.

## Query & Synthesis v1 update

As of 2026-05-14, `tools/query.py` and `tools/save_synthesis.py` are deterministic helpers. `tools/query.py` builds local context packets and `tools/save_synthesis.py` persists user-approved synthesis pages while updating index/log, without LLM calls, remote fetches, or raw-source ingestion.

## References

- Andrej Karpathy, "LLM Wiki": https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Astro-Han, `karpathy-llm-wiki`: https://github.com/Astro-Han/karpathy-llm-wiki
- SamurAIGPT, `llm-wiki-agent`: https://github.com/SamurAIGPT/llm-wiki-agent
