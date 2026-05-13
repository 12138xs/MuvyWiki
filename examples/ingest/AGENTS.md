# MuvyWiki Ingest Fixture Agent Protocol

This directory is a self-contained fixture that demonstrates one successful agent-first ingest. It is a runnable example, not the full project root.

## Core Model

- `raw/` is append-only source storage.
- `wiki/` is the maintained knowledge layer.
- `templates/` defines canonical page shapes.
- `tools/` contains deterministic checks and lightweight local interfaces.

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

## Ingest Triggers

Treat these requests as ingest requests:

- `ingest <path-or-url>`
- `摄取 <path-or-url>`
- `请把 <path-or-url> 加入 MuvyWiki`
- `请把这段内容整理进 MuvyWiki`
- `把 raw/originals/<file> 摄取进知识库`

Remote URLs are recognized as ingest intent only. Ingest v2 does not fetch, crawl, or render remote URLs directly; stop and ask the user for pasted text, a local Markdown/text file, or a converted Markdown artifact. Do not pretend remote content was ingested.

## Ingest Workflow

### Preflight

1. Identify whether the input is Markdown, plain text, pasted text, already converted Markdown, remote URL, or unsupported.
2. If the input is a remote URL, stop and ask for pasted text, a local Markdown/text file, or a converted Markdown artifact.
3. Use the fixture source template at `templates/source.md`. The full project root has additional domain-specific source templates.
4. Read `wiki/index.md`, `wiki/overview.md`, and relevant existing pages before editing.
5. Choose a canonical source ID in kebab-case.
6. If the input is pasted text, save it verbatim to `raw/originals/<source-id>.md` before extraction.
7. Check whether the raw artifact already exists.
8. Compute the artifact hash from the local raw artifact.
9. Check `raw/source-manifest.jsonl` for duplicate `content_hash` or `source_id`.
10. Report and stop if the source is unsupported, duplicated, missing, or ambiguous.

### Page Updates

1. Create or update exactly one source page at `wiki/sources/<source-id>.md`.
2. Use the selected source template and preserve the full provenance block.
3. Extract key claims as source-backed bullets.
4. Link concepts and entities with canonical IDs.
5. Create concept pages only for reusable concepts likely to recur.
6. Create entity pages only for recurring people, organizations, projects, papers, datasets, benchmarks, or tools.
7. Keep private or incidental names inside the source page unless the user asks to track them.
8. Record contradictions or tensions instead of silently replacing older claims.

### Required Metadata Updates

Every successful ingest updates:

- `raw/source-manifest.jsonl`
- `wiki/index.md`
- `wiki/log.md`

Update `wiki/overview.md` only when the source changes the broader knowledge map.

### Post-Ingest Validation

Run `python tools/health.py` after edits. If health fails, fix structural issues before reporting completion.

### Completion Report

End every successful ingest with:

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

If ingest cannot complete, report:

```text
Ingest blocked.

Reason: <unsupported input | duplicate source | missing raw file | ambiguous source ID | health failure>
Next step: <specific user action or agent action>
```

## Query Workflow

- Read `wiki/index.md` first.
- Read relevant wiki pages before answering.
- Answer from wiki content first and cite pages with `[[WikiLinks]]`.
- Clearly label anything from model knowledge rather than wiki pages.
- Ask before expanding to web search or new external sources.
- If an answer has long-term value, ask whether to save it as a synthesis page.
- If the user chooses to save a synthesis page, use `templates/synthesis.md`, update `wiki/index.md` and `wiki/log.md`, and make the log entry with `templates/log-entry.md`.
- Append to `raw/source-manifest.jsonl` only when the saved work also creates a new raw or converted artifact.

## Health Requirements

Run `python tools/health.py` after structural edits and after ingest. Use `python tools/health.py --json` when machine-readable evidence is useful.

## Local Interfaces

- `python tools/lint.py` checks semantic-lite maintenance issues in the fixture.
- `python tools/build_graph.py` writes fixture graph artifacts under `graph/`.
- `python tools/convert.py <input> --out raw/converted/<file>` converts supported local Markdown/text inputs only.

Conversion does not equal ingest. After using `convert.py`, agents must still update `raw/source-manifest.jsonl`, wiki pages, index, and log before claiming a source has entered the fixture.
