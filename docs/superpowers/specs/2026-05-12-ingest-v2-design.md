# Ingest v2 Design Spec

## Purpose

Ingest v2 makes MuvyWiki usable as an agent-first knowledge intake system. The user should be able to ask Codex to ingest a Markdown or plain-text source, and Codex should reliably update the raw manifest, source page, relevant concept and entity pages, index, overview, and log while preserving provenance and passing health checks.

The design intentionally keeps semantic work in the agent rather than a large CLI. Deterministic tools remain guardrails. This follows the Karpathy-style LLM Wiki model while borrowing workflow discipline from SamurAIGPT's `llm-wiki-agent`.

## References

- Karpathy LLM Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- SamurAIGPT `llm-wiki-agent`: https://github.com/SamurAIGPT/llm-wiki-agent
- SamurAIGPT `AGENTS.md`: https://raw.githubusercontent.com/SamurAIGPT/llm-wiki-agent/main/AGENTS.md
- Current MuvyWiki design: `docs/superpowers/specs/2026-05-12-muvywiki-design.md`

## Scope

In scope:

- Strengthen `AGENTS.md` ingest rules.
- Add domain-specific source templates for common personal-knowledge inputs.
- Add example ingest fixtures that pass `tools/health.py`.
- Add a post-ingest checklist and completion report format.
- Add tests that verify example ingest artifacts remain structurally healthy.
- Update user-facing docs with agent-first ingest examples.

Out of scope:

- Full `tools/ingest.py` automation.
- PDF/DOCX/PPTX/XLSX conversion.
- Web fetching.
- LLM-based semantic lint automation.
- Graph generation.

Those out-of-scope items are planned as later subprojects: Graph v2, Convert v2, and Lint v2.

## Chosen Approach

Use an agent-first ingest protocol with deterministic validation:

- The agent performs semantic extraction, summarization, concept selection, entity selection, contradiction handling, and synthesis suggestions.
- `tools/health.py` verifies structure, provenance, index/log parseability, canonical IDs, links, and manifest consistency.
- Domain templates give the agent repeatable shapes without forcing all sources into the same page.
- Examples act as executable documentation: future agents can inspect known-good ingest output before doing new work.

This is closer to SamurAIGPT's workflow richness than MuvyWiki v1, but it stays more conservative: MuvyWiki will not infer hidden graph edges or automatically mutate semantic claims without visible page edits.

## New Files

```text
templates/sources/
  technical-paper.md
  technical-article.md
  project-readme.md
  meeting-notes.md
  journal-entry.md

examples/ingest/
  README.md
  raw/originals/tiny-rag-note.md
  raw/source-manifest.jsonl
  wiki/index.md
  wiki/log.md
  wiki/overview.md
  wiki/sources/tiny-rag-note.md
  wiki/concepts/RetrievalAugmentedGeneration.md
  wiki/entities/TinyRagDemo.md
```

Modified files:

```text
AGENTS.md
USER_GUIDE.md
README.md
tests/test_health.py
```

No existing v1 templates are removed. The generic `templates/source.md` remains the fallback source template.

## Ingest Triggers

The agent should treat these as ingest requests:

- `ingest <path-or-url>`
- `摄取 <path-or-url>`
- `请把 <path-or-url> 加入 MuvyWiki`
- `请把这段内容整理进 MuvyWiki`
- `把 raw/originals/<file> 摄取进知识库`

If the request points to a remote URL and network access is unavailable or conversion is not implemented, the agent should ask the user to provide pasted text or a local file. It must not pretend remote content was ingested.

## Supported v2 Inputs

Ingest v2 supports sources the agent can read directly:

- Markdown files.
- Plain-text files.
- Pasted text in the conversation.
- Already converted Markdown under `raw/converted/`.

Unsupported inputs should be routed to the later Convert v2 workflow:

- PDF.
- DOCX/PPTX/XLSX.
- HTML requiring fetching or rendering.
- Binary files.

If a source is unsupported, the agent should create no wiki pages until the user provides readable text or a converted artifact.

## Domain Templates

### Technical Paper

Use for papers, arXiv notes, preprints, and paper-like technical reports.

Additional sections:

- `## Research Question`
- `## Method`
- `## Results`
- `## Limitations`
- `## Reproducibility Notes`

Entity creation guidance:

- Create an entity page for the paper only if it is likely to be referenced repeatedly.
- Always consider entity pages for datasets, benchmark suites, systems, organizations, and recurring authors.

### Technical Article

Use for blog posts, tutorials, essays, documentation pages, and newsletters.

Additional sections:

- `## Practical Takeaways`
- `## Claims to Verify`
- `## Implementation Notes`
- `## Related Work`

### Project README

Use for GitHub repositories, tools, libraries, frameworks, and product documentation.

Additional sections:

- `## What It Does`
- `## Architecture`
- `## Installation or Usage`
- `## Maturity and Risks`
- `## Competing Projects`

Entity creation guidance:

- Project pages should usually become entity pages if the project may recur in future comparisons.

### Meeting Notes

Use for meetings, calls, interviews, and planning sessions.

Additional sections:

- `## Participants`
- `## Decisions`
- `## Action Items`
- `## Follow-ups`

### Journal Entry

Use for personal reflections, daily notes, project retrospectives, and research diary entries.

Additional sections:

- `## Context`
- `## Observations`
- `## Decisions or Commitments`
- `## Patterns to Watch`

Privacy guidance:

- Journal entries should avoid creating entity pages for private individuals unless the user explicitly wants that.

## Ingest Workflow

### 1. Preflight

Before editing files, the agent must:

1. Identify the input type and choose a source template.
2. Read `wiki/index.md`, `wiki/overview.md`, and relevant existing pages.
3. Check whether the raw artifact already exists.
4. Compute or report the source hash if the content is available as a local file.
5. Check `raw/source-manifest.jsonl` for duplicate `content_hash` or `source_id`.
6. Choose a canonical source ID.
7. Report if the ingest would be a duplicate, ambiguous, or unsupported.

If the source is a paste, the agent should save it to `raw/originals/<source-id>.md` before creating wiki pages.

### 2. Source Page

Create or update exactly one source page in `wiki/sources/<source-id>.md`.

The source page must:

- Use the base source frontmatter.
- Include the full provenance block.
- Link to raw and converted artifacts when present.
- Summarize the source without overstating claims.
- Extract key claims as source-backed bullets.
- List concepts and entities using canonical links.
- Record open questions and contradictions.

### 3. Concept and Entity Updates

The agent should create a new concept page only when:

- The concept is likely to recur.
- The source materially improves the wiki's understanding of it.
- The concept can be defined independently of the source.

The agent should update an existing concept page when:

- The source provides new evidence.
- The source changes known boundaries or failure modes.
- The source conflicts with existing claims.

The agent should create a new entity page only when:

- A person, organization, project, paper, dataset, benchmark, or tool is likely to recur.
- The entity is needed to connect multiple sources.
- The user explicitly asks to track it.

Private or incidental names should remain inside the source page unless the user asks otherwise.

### 4. Index, Overview, Manifest, and Log

Every ingest must update:

- `raw/source-manifest.jsonl`
- `wiki/index.md`
- `wiki/log.md`

Update `wiki/overview.md` only if the source changes the knowledge base's broader map, active themes, open questions, or strongest syntheses.

The log entry operation must be `ingest`.

### 5. Post-Ingest Validation

After file edits, the agent must run:

```bash
python tools/health.py
```

If health fails, the agent must fix structural issues before claiming ingest is complete.

If health passes, the agent reports the completion summary.

## Completion Report

Every ingest response should end with:

```text
Ingest complete.

Source ID: <source-id>
Raw path: <raw-path>
Source page: <wiki/sources/source-id.md>
Created pages:
- ...
Updated pages:
- ...
Concepts touched:
- ...
Entities touched:
- ...
Unresolved issues:
- none | ...
Verification:
- python tools/health.py: ok
```

If ingest cannot complete:

```text
Ingest blocked.

Reason: <unsupported input | duplicate source | missing raw file | ambiguous source ID | health failure>
Next step: <specific user action or agent action>
```

## Examples

`examples/ingest/` stores a tiny self-contained ingest fixture. It should demonstrate:

- A raw Markdown note.
- A manifest entry.
- A source page.
- One concept page.
- One entity page.
- Updated index, overview, and log.

The example is not part of the live wiki, so its canonical IDs may duplicate live wiki IDs without affecting `tools/health.py`.

Tests should run `tools/health.py` against the example fixture as a separate root directory.

## Testing

Add tests that verify:

- The live repository remains healthy.
- The ingest example fixture passes `tools/health.py`.
- The example fixture has at least one source page, one concept page, one entity page, and an ingest log entry.
- Domain source templates contain the base source frontmatter fields and required source sections.

## Error Handling

- Unsupported input: do not create partial wiki pages.
- Duplicate hash: report duplicate and ask whether to link to the existing source instead.
- Duplicate source ID: choose a new ID or ask the user.
- Missing raw file: stop before wiki edits.
- Health failure: fix structural issues before completion.
- Contradiction: record it in affected pages; do not silently overwrite the older claim.

## Migration and Compatibility

Ingest v2 must not break v1:

- Existing health checks must keep passing.
- Existing generic templates remain valid.
- `tools/lint.py`, `tools/build_graph.py`, and `tools/convert.py` remain reserved interfaces.
- No graph, lint, or conversion behavior is required for ingest v2.

## Future Hooks

Later subprojects can build on this design:

- Graph v2 can parse stronger concept/entity links produced by ingest v2.
- Convert v2 can produce `raw/converted/` artifacts that ingest v2 consumes.
- Lint v2 can inspect ingest reports, sparse pages, orphan concepts, and unresolved issues.
