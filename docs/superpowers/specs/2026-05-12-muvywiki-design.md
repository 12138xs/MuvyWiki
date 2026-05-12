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
- Implement only lightweight deterministic tooling in version one.
- Reserve interfaces for future graph, conversion, and semantic lint tooling without making them required for normal use.

This keeps the repository useful immediately while avoiding a later structural migration.

## Directory Structure

```text
raw/
  .gitkeep
  README.md

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

`raw/` contains immutable source material. The agent may add files here when ingesting a URL, pasted text, or converted document, but it must not rewrite the meaning of existing source files. If a source needs cleanup, the original should be preserved or the transformation should be logged.

Recommended first-level folders can emerge naturally, for example `raw/articles/`, `raw/papers/`, `raw/books/`, `raw/projects/`, and `raw/notes/`. The first version does not enforce these folders.

### `wiki/`

`wiki/` is the compiled knowledge layer owned by the agent. The agent may create and update pages here as part of ingest, query archiving, health checks, and linting.

`wiki/index.md` is the global catalog. It should list every wiki page except `index.md` and `log.md`, grouped by page type.

`wiki/log.md` is append-only. Entries must use parseable headings:

```markdown
## [YYYY-MM-DD] operation | title
```

`wiki/overview.md` is a living synthesis of what the knowledge base currently contains and where it is developing.

### `templates/`

`templates/` stores canonical page shapes. The agent should use these templates when creating pages, but may adapt sections when a source demands it.

### `tools/`

`tools/` stores deterministic helper scripts. Version one implements `health.py` as a lightweight structural check. The other files are reserved interfaces with documented command behavior, so future work can add implementation without changing the repository contract.

### `graph/`

`graph/` stores future graph artifacts:

- `graph/graph.json`
- `graph/graph.html`
- `graph/graph-report.md`

Version one creates the directory and documents the contract. Graph output is not required for basic ingest or query workflows.

### `AGENTS.md`

`AGENTS.md` is the schema layer for Codex and other compatible coding agents. It defines page conventions, workflows, naming rules, health checks, lint behavior, and future extension points.

## Page Frontmatter

All wiki pages use this base frontmatter:

```yaml
---
title: "Page Title"
type: source | concept | entity | synthesis | overview
tags: []
aliases: []
sources: []
related: []
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
status: seed | active | archived
confidence: low | medium | high
---
```

Fields:

- `title`: human-readable page title.
- `type`: page category.
- `tags`: broad topical tags.
- `aliases`: alternate names useful for graph and search.
- `sources`: source slugs or wiki links that support the page.
- `related`: explicit related page names for graph tooling.
- `created`: first creation date.
- `last_updated`: last knowledge-content update date.
- `status`: maturity of the page.
- `confidence`: confidence in the current synthesis.

Use Obsidian-style `[[WikiLinks]]` for internal knowledge links. Use Markdown links for `raw/` files and external URLs.

## Page Types

### Source Pages

Location: `wiki/sources/<slug>.md`

Purpose: summarize one source and preserve its key claims, evidence, terminology, and connections.

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
- `## Why It Matters`
- `## Mechanism`
- `## Boundaries and Failure Modes`
- `## Related Concepts`
- `## Supporting Sources`
- `## Open Questions`

### Entity Pages

Location: `wiki/entities/<EntityName>.md`

Purpose: track people, organizations, projects, tools, products, papers, and datasets.

Required sections:

- `## Summary`
- `## Role in the Wiki`
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
- `## Implications`
- `## Related Pages`
- `## Follow-up Questions`

## Workflows

### Ingest

Triggered by requests such as `ingest raw/...`, `ingest this article`, or `摄取这篇论文`.

Steps:

1. Read the source fully.
2. If the source is not already in `raw/`, save it there without rewriting its meaning.
3. Read `wiki/index.md` and `wiki/overview.md`.
4. Create or update one `wiki/sources/<slug>.md` page.
5. Extract durable concepts and update or create `wiki/concepts/` pages.
6. Extract durable entities and update or create `wiki/entities/` pages.
7. Flag contradictions, tensions, and changed claims on affected pages.
8. Update `wiki/index.md`.
9. Update `wiki/overview.md` if the source changes the broader picture.
10. Append an entry to `wiki/log.md`.
11. Run `python tools/health.py`.
12. Report changed pages and any unresolved issues.

Version one prefers one source per ingest. Batch ingest is reserved for future tooling.

### Query

Triggered by requests such as `query: ...`, `我对 X 知道什么？`, or `比较 A 和 B`.

Steps:

1. Read `wiki/index.md`.
2. Read the relevant wiki pages.
3. Answer from wiki content first.
4. Cite internal pages with `[[WikiLinks]]`.
5. If the answer has long-term value, ask whether to save it as a synthesis page.

Plain queries do not modify files unless the user asks to save or archive the answer.

### Health

Triggered by `health` or run automatically after ingest.

Version one implements deterministic checks:

- Required directories exist.
- Required root files exist.
- Wiki pages are non-empty beyond frontmatter.
- Pages in `wiki/sources`, `wiki/concepts`, `wiki/entities`, and `wiki/syntheses` are listed in `wiki/index.md`.
- `[[WikiLinks]]` have plausible targets.
- `wiki/log.md` uses parseable headings.

The script should print a concise report and exit non-zero when structural issues are found.

### Lint

Triggered by `lint`.

Version one reserves the command interface and documents expected report shape. Future versions will check:

- Contradictions across pages.
- Outdated claims superseded by newer sources.
- Missing concept pages.
- Missing entity pages.
- Orphan pages.
- Low link density.
- Data gaps and suggested sources.

Semantic linting should run after health passes.

### Graph

Triggered by `build graph`.

Version one reserves the interface. Future versions will:

- Parse `[[WikiLinks]]` across `wiki/**/*.md`.
- Build `graph/graph.json` with nodes and edges.
- Produce `graph/graph.html` as a self-contained visualization.
- Produce `graph/graph-report.md` with orphan, hub, bridge, and community findings.

Page frontmatter and link conventions in version one are designed to support this later without migration.

### Conversion

Triggered implicitly during ingest when source material is not Markdown.

Version one reserves `tools/convert.py`. Future versions may integrate `markitdown`, high-fidelity PDF conversion, arXiv-specific conversion, and office document conversion.

If conversion is unavailable, the agent should ask the user for Markdown or pasted text rather than silently skipping content.

## Naming Conventions

- Source slugs use kebab-case: `attention-is-all-you-need`.
- Concept pages use PascalCase: `RetrievalAugmentedGeneration.md`.
- Entity pages use PascalCase or canonical capitalization: `OpenAI.md`, `AndrejKarpathy.md`, `GPT5.md`.
- Synthesis pages use kebab-case.
- Internal links use page titles or canonical aliases.
- File names should be stable; rename only when the current name is actively misleading.

## Error Handling

- Never overwrite raw sources without explicit user approval.
- If a source contradicts existing pages, record the contradiction rather than choosing a winner silently.
- If a page link is ambiguous, report it instead of guessing.
- If a future tool is not implemented yet, explain the missing capability and fall back to the documented manual workflow.
- If health checks fail after ingest, report the issue and the files involved.

## Testing and Verification

Initial verification should include:

- Running `python tools/health.py`.
- Confirming required directories and files exist.
- Confirming `wiki/index.md` references all initial wiki pages.
- Confirming `wiki/log.md` contains an initialization entry.
- Confirming reserved tools produce clear stub output or documented errors.

Future verification should add:

- Graph generation fixture tests.
- Conversion fixture tests for common file types.
- Lint report fixture tests.
- Batch ingest tests.

## References

- Andrej Karpathy, "LLM Wiki": https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Astro-Han, `karpathy-llm-wiki`: https://github.com/Astro-Han/karpathy-llm-wiki
- SamurAIGPT, `llm-wiki-agent`: https://github.com/SamurAIGPT/llm-wiki-agent
