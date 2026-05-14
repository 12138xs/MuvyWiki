# Query & Synthesis v1 Design

## Summary

Query & Synthesis v1 adds two deterministic, standard-library-only helpers for the agent-first MuvyWiki workflow:

- `tools/query.py` builds a local context packet from existing wiki pages.
- `tools/save_synthesis.py` safely writes agent-prepared synthesis pages and updates the wiki index and log.

The goal is to make daily knowledge-base use smoother without replacing the agent. The tools retrieve, validate, rank, and write structured artifacts; the agent still reads the returned pages, reasons about the question, writes the answer, and decides with the user whether a synthesis should be saved.

## References

- Karpathy LLM Wiki gist: `https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
- `Astro-Han/karpathy-llm-wiki`: lightweight Codex Skill style reference.
- `SamurAIGPT/llm-wiki-agent`: fuller template reference for agent-first wiki workflows.

## Goals

- Add a stable query helper that finds relevant wiki pages before the agent answers.
- Add a safe synthesis writer that turns approved answers into durable wiki pages.
- Preserve the current raw/wiki split: raw sources remain provenance, wiki pages remain the knowledge layer.
- Keep the implementation dependency-free and offline.
- Keep interfaces machine-readable where useful so future agents can compose them.
- Preserve future hooks for richer retrieval modes, reranking, and agent integrations.
- Update documentation so user-facing and agent-facing instructions match implemented behavior.

## Non-Goals

- No embeddings or vector database.
- No SQLite FTS dependency.
- No LLM calls inside tools.
- No web fetching, crawling, or external source expansion.
- No automatic source, concept, or entity extraction.
- No automatic synthesis creation without user confirmation through the agent workflow.
- No replacement for `tools/health.py`, `tools/lint.py`, or `tools/build_graph.py`.

## Shared Tool Conventions

Both tools should:

- Use only Python standard library modules.
- Reuse `tools/wiki_utils.py` for path safety, frontmatter parsing, wikilinks, sections, timestamps, and repository-relative paths.
- Print concise human-readable output by default.
- Support JSON output where the result is useful to an agent.
- Return exit code `0` when the requested operation succeeds.
- Return exit code `1` when validation finds content issues that block the requested write.
- Return exit code `2` for invalid arguments, unsafe paths, parse failures, or missing required files.
- Avoid mutating files unless the command's purpose is explicitly to write a synthesis page or metadata update.
- Use repository-root-relative paths in reports and JSON payloads.

## `tools/query.py`

### Purpose

`query.py` retrieves relevant wiki pages and emits a compact context packet for the agent. It should answer the question: "Which existing MuvyWiki pages should the agent read before responding?"

The tool does not generate the final answer. It only ranks and summarizes matching pages so the agent can read them and reason over them.

### Inputs

Command:

```bash
python tools/query.py "<query>" [--json] [--limit 8] [--type source,concept,entity,synthesis,overview] [--include-sections]
```

Options:

- Positional `query`: natural-language search text.
- `--json`: print machine-readable context packet.
- `--limit`: maximum number of page matches, default `8`.
- `--type`: comma-separated page-type filter. Supported values are `source`, `concept`, `entity`, `synthesis`, and `overview`.
- `--include-sections`: include short matching section excerpts in output. The default output includes page-level matches only.

### Page Corpus

The corpus is every page returned by `wiki_utils.collect_wiki_pages(ROOT)`:

- `wiki/overview.md`
- `wiki/sources/*.md`
- `wiki/concepts/*.md`
- `wiki/entities/*.md`
- `wiki/syntheses/*.md`

`wiki/index.md` and `wiki/log.md` are not ranked as result pages in v1, but the agent-facing docs should still instruct agents to read `wiki/index.md` first when performing manual query work.

### Ranking

Ranking should be deterministic and conservative:

- Parse the query into lowercase alphanumeric tokens.
- Score exact matches in `canonical_id`, title, aliases, and tags highest.
- Score wikilink target matches and frontmatter relation matches next.
- Score section headings and body text matches lower.
- Prefer pages with more distinct matched query tokens.
- Break ties by page type priority and path.

Suggested type priority:

1. `concept`
2. `synthesis`
3. `source`
4. `entity`
5. `overview`

This priority keeps reusable knowledge and saved judgments near the top while still surfacing provenance pages.

### Output

Default text output:

```text
MuvyWiki query: 3 match(es)

1. RetrievalAugmentedGeneration - Retrieval-Augmented Generation
   path: wiki/concepts/RetrievalAugmentedGeneration.md
   type: concept
   score: 18
   matched: retrieval, augmented, generation

2. rag-systems-architecture-survey - RAG Systems Architecture Survey
   path: wiki/syntheses/rag-systems-architecture-survey.md
   type: synthesis
   score: 12
   matched: rag, systems
```

JSON output:

```json
{
  "status": "ok",
  "query": "retrieval augmented generation",
  "retrieval_mode": "keyword-lite",
  "generated_at": "2026-05-14T00:00:00Z",
  "limit": 8,
  "matches": [
    {
      "id": "RetrievalAugmentedGeneration",
      "title": "Retrieval-Augmented Generation",
      "type": "concept",
      "path": "wiki/concepts/RetrievalAugmentedGeneration.md",
      "score": 18,
      "matched_terms": ["retrieval", "augmented", "generation"],
      "tags": ["rag"],
      "aliases": ["RAG"],
      "source_ids": ["example-source"],
      "related_ids": ["VectorSearch"],
      "wikilinks": ["example-source", "VectorSearch"],
      "sections": [
        {
          "title": "Definition",
          "excerpt": "Retrieval-Augmented Generation combines retrieval with generation..."
        }
      ]
    }
  ]
}
```

If there are no matches, exit `0` and return an empty match list. An empty result is useful information, not a tool failure.

### Exit Codes

- `0`: query succeeds, even with no matches.
- `2`: empty query, invalid `--limit`, unsupported type filter, or unreadable wiki structure.

## `tools/save_synthesis.py`

### Purpose

`save_synthesis.py` writes a synthesis page that the agent has already prepared and the user has approved saving. It should handle the mechanical and safety-sensitive parts of persistence:

- validate the target ID and path,
- validate required synthesis sections,
- validate referenced wiki page IDs,
- create the synthesis page without overwriting existing files by default,
- update `wiki/index.md`,
- append a structured entry to `wiki/log.md`.

### Inputs

Command:

```bash
python tools/save_synthesis.py \
  --id rag-systems-architecture-survey \
  --title "RAG Systems Architecture Survey" \
  --question "How have RAG architectures evolved?" \
  --answer-file /path/to/answer.md \
  --evidence-file /path/to/evidence.md \
  --related RetrievalAugmentedGeneration,VectorSearch \
  --sources example-source \
  [--tags rag,agents] \
  [--confidence medium] \
  [--status seed] \
  [--json]
```

Options:

- `--id`: required synthesis canonical ID in kebab-case.
- `--title`: required human-readable title.
- `--question`: required question being answered.
- `--answer-file`: required Markdown file containing the prepared answer body.
- `--evidence-file`: required Markdown file containing source-backed evidence bullets or explicit evidence notes.
- `--related`: optional comma-separated canonical IDs for related wiki pages.
- `--sources`: optional comma-separated canonical source IDs.
- `--tags`: optional comma-separated tags.
- `--confidence`: default `medium`.
- `--status`: default `seed`.
- `--json`: print machine-readable save result.

The tool should read `--answer-file` and `--evidence-file` as UTF-8 Markdown. These files may be temporary local files created by the agent during the save workflow. They are inputs only and are not added to `raw/source-manifest.jsonl`.

### Generated Page

The output path is always:

```text
wiki/syntheses/<id>.md
```

The generated page follows `templates/synthesis.md`:

```markdown
---
canonical_id: "rag-systems-architecture-survey"
type: synthesis
title: "RAG Systems Architecture Survey"
tags:
  - rag
aliases: []
source_ids:
  - "example-source"
related_ids:
  - "RetrievalAugmentedGeneration"
raw_paths: []
created: 2026-05-14
last_updated: 2026-05-14
status: seed
confidence: medium
---

# RAG Systems Architecture Survey

## Question

How have RAG architectures evolved?

## Answer

<answer-file content>

## Evidence

<evidence-file content or source-backed references>

## Contradictions or Tensions

- none

## Implications

- none

## Related Pages

- [[RetrievalAugmentedGeneration]]
- [[example-source]]

## Follow-up Questions

- none
```

### Validation

Before writing, the tool should validate:

- `--id` is kebab-case and non-empty.
- `wiki/syntheses/<id>.md` does not already exist.
- `--title`, `--question`, answer content, and evidence content are non-empty.
- `--confidence` is one of `low`, `medium`, or `high`.
- `--status` is one of `seed`, `active`, `archived`, or `needs-review`.
- Every `--sources` ID resolves to a source page.
- Every `--related` ID resolves to an existing wiki page.
- The destination path stays under `wiki/syntheses/` and is not a symlink.

If validation fails, do not mutate any file.

### Metadata Updates

On successful save, update:

- `wiki/index.md`
- `wiki/log.md`

`wiki/index.md` should receive one synthesis entry:

```markdown
- [[rag-systems-architecture-survey|RAG Systems Architecture Survey]] (`wiki/syntheses/rag-systems-architecture-survey.md`) - type: synthesis - updated: 2026-05-14 - Saved synthesis for: How have RAG architectures evolved?
```

If the `## Syntheses` section still contains `No synthesis pages yet.`, remove that empty-state line.

`wiki/log.md` should receive one entry:

```markdown
## [2026-05-14] query | RAG Systems Architecture Survey

- Changed pages:
  - `wiki/syntheses/rag-systems-architecture-survey.md`
  - `wiki/index.md`
  - `wiki/log.md`
- Raw paths:
  - none
- Source IDs:
  - `example-source`
- Unresolved issues:
  - none
```

### Output

Default text output:

```text
Saved synthesis wiki/syntheses/rag-systems-architecture-survey.md
Updated wiki/index.md and wiki/log.md
```

JSON output:

```json
{
  "status": "ok",
  "id": "rag-systems-architecture-survey",
  "path": "wiki/syntheses/rag-systems-architecture-survey.md",
  "updated": ["wiki/index.md", "wiki/log.md"],
  "source_ids": ["example-source"],
  "related_ids": ["RetrievalAugmentedGeneration"],
  "saved_at": "2026-05-14T00:00:00Z"
}
```

### Exit Codes

- `0`: synthesis saved and metadata updated.
- `1`: content validation failed and no files changed.
- `2`: invalid arguments, unsafe path, missing input file, unreadable input file, or write failure.

## Agent Workflow

Query workflow:

1. Run `python tools/query.py "<question>" --json`.
2. Read the matched wiki pages before answering.
3. Answer from wiki content first and cite pages with `[[WikiLinks]]`.
4. Clearly label model knowledge when the answer goes beyond wiki content.
5. Ask before using web search or new external sources.
6. Ask before saving a long-term synthesis.

Synthesis save workflow:

1. Confirm with the user that the answer should be saved.
2. Prepare answer and evidence Markdown locally.
3. Run `python tools/save_synthesis.py` with IDs for related pages and source pages.
4. Run `python tools/health.py`.
5. Run `python tools/lint.py`.
6. Report the saved path and validation results.

## Documentation Updates

After implementation, update:

- `README.md`: status table, common commands, and current capability boundaries.
- `USER_GUIDE.md`: how to query, when to save a synthesis, and example commands.
- `AGENTS.md`: implemented query and synthesis-save interfaces plus required workflow.
- `graph/README.md`: note that saved syntheses appear in graph outputs through normal page collection.
- `docs/superpowers/specs/2026-05-12-muvywiki-design.md`: add a status note that query and synthesis saving now have deterministic helper interfaces.

Historical implementation plans do not need updates unless they would be mistaken for current protocol.

## Tests

Add or update tests for:

- `query.py` ranks exact canonical ID/title/alias/tag matches.
- `query.py --json` returns the context packet shape.
- `query.py --limit` and `--type` filter results.
- `query.py --include-sections` returns bounded excerpts.
- `query.py` returns success with an empty match list.
- `query.py` rejects empty queries and invalid filters.
- `save_synthesis.py` writes a synthesis page from answer/evidence files.
- `save_synthesis.py --json` returns the save result shape.
- `save_synthesis.py` updates `wiki/index.md` and removes stale empty synthesis text.
- `save_synthesis.py` appends a `query` log entry.
- `save_synthesis.py` rejects duplicate IDs, invalid IDs, unknown source IDs, unknown related IDs, empty answer content, unsafe paths, and symlinked destinations.
- Current repository tests continue to pass.
- Documentation consistency tests recognize the new implemented interfaces.

## Future Hooks

Future versions can extend this design without changing the public entrypoints:

- Add `retrieval_mode` values such as `fts`, `embedding`, or `hybrid`.
- Add optional rerank fields to query JSON.
- Add snippets that include source line numbers.
- Add interactive synthesis update mode for existing synthesis pages.
- Add batch query reports for recurring research reviews.
- Add MCP or plugin wrappers around the same command contracts.

## Risks

- Keyword-lite ranking may miss semantically related pages. The agent workflow should still allow manual reading of `wiki/index.md` and related pages.
- Saving syntheses can create low-value pages if used too often. The user-confirmation step and agent protocol should keep synthesis pages reserved for durable judgments.
- Auto-updating `wiki/index.md` may drift from hand-edited style. The implementation should keep the generated entry format identical to the existing index contract.
- The save tool can be mistaken for raw-source ingestion. Documentation must state that synthesis saving does not append to `raw/source-manifest.jsonl` unless a separate raw artifact is created.

## Acceptance Criteria

- `python tools/query.py "<question>"` prints deterministic page matches.
- `python tools/query.py "<question>" --json` prints valid JSON.
- `python tools/query.py "<question>" --include-sections` includes short matching excerpts.
- `python tools/save_synthesis.py` writes a valid synthesis page from prepared Markdown inputs.
- `tools/save_synthesis.py` updates `wiki/index.md` and `wiki/log.md`.
- Failed synthesis validation leaves all repository files unchanged.
- Documentation describes query and synthesis saving as implemented interfaces.
- `python -m unittest discover -s tests` passes.
- `python tools/health.py` passes.
- `python tools/lint.py` passes.
