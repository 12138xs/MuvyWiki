# MuvyWiki Agent Protocol

This repository is a personal LLM-maintained knowledge base. Follow the design in `docs/superpowers/specs/2026-05-12-muvywiki-design.md`.

## Core Model

- `raw/` is append-only source storage.
- `wiki/` is the maintained knowledge layer.
- `templates/` defines canonical page shapes.
- `tools/` contains deterministic checks and lightweight local interfaces.

## Implemented Interfaces

Implemented deterministic interfaces:

- `python tools/health.py` checks repository structure, wiki page frontmatter, index/log shape, wikilinks, source provenance, and required paths.
- `python tools/lint.py` checks semantic-lite maintenance issues and may write `graph/lint-report.md`.
- `python tools/build_graph.py` writes local graph artifacts under `graph/`.
- `python tools/demo.py` validates the bundled ingest fixture in a temporary directory without modifying the repository.
- `python tools/prepare_ingest.py <input> --json` performs read-only ingest preflight for supported local Markdown/text inputs.
- `python tools/prepare_ingest.py <input> --report graph/ingest-prep-report.md` writes an optional ingest preflight report under `graph/`.
- `python tools/manifest.py check` validates `raw/source-manifest.jsonl`.
- `python tools/manifest.py find --source-id <source-id>` looks up an existing manifest entry by source ID.
- `python tools/manifest.py find --hash <sha256:...>` looks up an existing manifest entry by content hash.
- `python tools/manifest.py find --path <raw-or-converted-path>` looks up an existing manifest entry by raw, converted, or converted-from path.
- `python tools/manifest.py add --source-id <source-id> --raw-path <raw-path> --content-hash <sha256:...> --collected-at <YYYY-MM-DD>` appends one validated manifest entry.
- `python tools/query.py "retrieval augmented generation"` builds a local context packet for an agent answer.
- `python tools/query.py "retrieval augmented generation" --json` emits the local context packet as JSON.
- `python tools/save_synthesis.py --help` documents the interface that persists a user-approved synthesis page from real answer/evidence Markdown and updates index/log.
- `python tools/convert.py <input> --out raw/converted/<file>` converts supported local Markdown/text inputs only.
- `python -m unittest discover -s tests` runs the repository test suite.

Conversion does not equal ingest. After using `convert.py`, agents must still perform the ingest workflow before claiming a source has entered MuvyWiki.

Ingest preparation does not equal ingest. `prepare_ingest.py` does not call an LLM or create wiki pages. `manifest.py` only maintains `raw/source-manifest.jsonl`; it does not update source pages, index, or log.

`query.py` and `save_synthesis.py` are agent-facing helpers. They do not call an LLM, fetch remote content, or ingest new raw sources.

Implemented agent-driven interfaces:

- Ingest is protocol-driven through this file, source templates, `raw/source-manifest.jsonl`, wiki pages, index, and log.
- Query and synthesis saving are supported by deterministic helpers plus protocol-driven review through `wiki/index.md`, relevant wiki pages, `templates/synthesis.md`, and `wiki/log.md`.
- `examples/ingest/` is a self-contained health-checked fixture showing one successful ingest.

Unsupported conversion inputs include PDF, Office documents, remote URLs, rendered HTML, and binary files. If a task needs those formats, ask for pasted text, a local Markdown/text file, or a converted Markdown artifact.

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
3. For a local Markdown/text input, first run `python tools/prepare_ingest.py <input> --json`.
4. If `prepare_ingest.py` reports unsupported, duplicate, missing, unsafe, or ambiguous input, stop and report `Ingest blocked.` with the tool's reason and a concrete next step.
5. Choose a source template:
   - technical paper: `templates/sources/technical-paper.md`
   - technical article: `templates/sources/technical-article.md`
   - project README: `templates/sources/project-readme.md`
   - meeting notes: `templates/sources/meeting-notes.md`
   - journal entry: `templates/sources/journal-entry.md`
   - fallback: `templates/source.md`
6. Read `wiki/index.md`, `wiki/overview.md`, and relevant existing pages before editing.
7. Choose or confirm a canonical source ID in kebab-case.
8. If the input is pasted text, save it verbatim to `raw/originals/<source-id>.md` before extraction, then run `python tools/prepare_ingest.py raw/originals/<source-id>.md --json`.
9. Confirm the final raw path, source ID, and content hash from the preflight result.
10. Run `python tools/manifest.py check` and `python tools/manifest.py find --source-id <source-id>`, `python tools/manifest.py find --hash <sha256:...>`, or `python tools/manifest.py find --path <raw-or-converted-path>` before adding a new entry.
11. After the final raw path/source ID/hash are fixed, use `python tools/manifest.py add --source-id <source-id> --raw-path <raw-path> --content-hash <sha256:...> --collected-at <YYYY-MM-DD>` to record the manifest entry.
12. Report and stop if the source is unsupported, duplicated, missing, or ambiguous.

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

- Read `wiki/index.md` first when manually navigating.
- Prefer `python tools/query.py "<user query>" --json` for deterministic first-pass context.
- Read matched wiki pages before answering.
- Answer from wiki content first and cite pages with `[[WikiLinks]]`.
- Clearly label anything from model knowledge rather than wiki pages.
- Ask before expanding to web search or new external sources.
- Ask before saving synthesis.
- If saving, prepare answer/evidence Markdown and use `tools/save_synthesis.py`.
- Run `python tools/health.py` and `python tools/lint.py` after saving.
- Append to `raw/source-manifest.jsonl` only when the saved work also creates a new raw or converted artifact.

## Health Requirements

Run `python tools/health.py` after structural edits and after ingest. Use `python tools/health.py --json` when machine-readable evidence is useful.

GitHub Actions repeats the unit tests, manifest validation, root health/lint, non-mutating demo, and fixture checks on Python 3.10, 3.11, and 3.12. Keep local verification commands aligned with `.github/workflows/ci.yml`.

## Documentation Maintenance

When functionality, interface capabilities, or workflow rules change, keep these documents aligned:

- `README.md` for project status, command summary, and documentation map.
- `USER_GUIDE.md` for user-facing workflows and current capabilities.
- `AGENTS.md` for agent-facing rules and interface boundaries.
- `ROADMAP.md` for module-specific future work and acceptance criteria.
- `docs/milestones/` for historical capability boundaries and verification evidence.
- Directory READMEs such as `raw/README.md`, `graph/README.md`, and `examples/ingest/README.md` when their contracts change.
- `docs/superpowers/specs/` when implemented behavior changes a design assumption.
- Historical implementation plans only need a status note when old instructions could be mistaken for current protocol.

For docs-only maintenance, run:

```bash
python -m unittest tests/test_docs_interfaces.py
python -m unittest discover -s tests
python tools/lint.py
python tools/health.py
python tools/build_graph.py
python tools/lint.py --repo-root examples/ingest
python tools/health.py --repo-root examples/ingest
python tools/build_graph.py --repo-root examples/ingest
```
