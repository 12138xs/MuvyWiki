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
8. Update `wiki/index.md`, `wiki/overview.md`, and `wiki/log.md`; log entries must use `templates/log-entry.md`.
9. Append to `raw/source-manifest.jsonl`.
10. Run `python tools/health.py`.
11. Report changed pages and unresolved issues.

## Query Workflow

- Read `wiki/index.md` first.
- Read relevant wiki pages before answering.
- Answer from wiki content first and cite pages with `[[WikiLinks]]`.
- Clearly label anything from model knowledge rather than wiki pages.
- Ask before expanding to web search or new external sources.
- If an answer has long-term value, ask whether to save it as a synthesis page.

## Health Requirements

Run `python tools/health.py` after structural edits and after ingest. Use `python tools/health.py --json` when machine-readable evidence is useful.
