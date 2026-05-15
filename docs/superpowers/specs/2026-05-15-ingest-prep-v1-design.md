# Ingest Prep v1 Design

## Summary

Ingest Prep v1 adds deterministic, standard-library-only helpers for the first half of MuvyWiki ingest: identifying local source inputs, checking safety and duplicates, recommending the source ID and template, and maintaining `raw/source-manifest.jsonl`.

The goal is to make ingest easier for agents without replacing the agent-first workflow. The tools prepare a trustworthy ingest packet and safely update the raw manifest when instructed. The agent still reads the source, extracts claims, creates or updates wiki pages, resolves concepts and entities, updates index/log, and asks the user when semantic judgment is needed.

## References

- Karpathy LLM Wiki gist: `https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
- `Astro-Han/karpathy-llm-wiki`: lightweight Codex Skill style reference.
- `SamurAIGPT/llm-wiki-agent`: fuller template reference for agent-first wiki workflows, including natural-language ingest triggers, source templates, query, lint, graph, and health flows.
- Current MuvyWiki ingest design: `docs/superpowers/specs/2026-05-12-ingest-v2-design.md`
- Current MuvyWiki interface design: `docs/superpowers/specs/2026-05-13-interface-v1-design.md`
- Query and synthesis interface design: `docs/superpowers/specs/2026-05-14-query-synthesis-v1-design.md`

## Goals

- Add a stable ingest-preflight helper that agents can run before editing wiki pages.
- Add a safe manifest helper that validates, searches, and appends `raw/source-manifest.jsonl`.
- Preserve the raw/wiki split: raw artifacts are source storage; wiki pages are maintained knowledge.
- Preserve the current conversion boundary: `convert.py` may create converted Markdown/text, but conversion still does not equal ingest.
- Make duplicate detection based on both `source_id` and `content_hash`.
- Support local Markdown/text, existing `raw/originals/` artifacts, and existing `raw/converted/` artifacts.
- Support batch preflight so agents can inspect several local inputs before choosing a careful ingest order.
- Keep output machine-readable where useful so future agents can compose these tools.
- Keep remote URL, PDF, Office, HTML rendering, embeddings, and LLM extraction as explicit future hooks rather than silent partial implementations.
- Update docs and tests so user-facing and agent-facing instructions match implemented behavior.

## Non-Goals

- No LLM calls inside either tool.
- No automatic semantic extraction, source-page generation, concept creation, entity creation, overview editing, or synthesis writing.
- No automatic ingest from remote URLs.
- No web fetching, crawling, clipping, rendering, or browser automation.
- No PDF, DOCX, PPTX, XLSX, EPUB, image, audio, or binary conversion.
- No automatic use of `markitdown` or any third-party converter in v1.
- No automatic overwrite of raw artifacts, manifest entries, wiki pages, index, overview, or log.
- No duplicate bypass flag in v1.
- No batch directory recursion.
- No stdin or pasted-text capture inside the CLI in v1.
- No embeddings, vector search, reranking, or database-backed catalog.
- No hidden mutation during preflight. Mutating actions must be explicit and visible in command names/options.

## Design Alternatives

### A. Two focused tools

Add:

- `tools/prepare_ingest.py` for input classification, hash calculation, duplicate checks, template recommendation, and ingest-packet output.
- `tools/manifest.py` for manifest validation, search, and safe append.

This is the chosen approach. It keeps responsibilities narrow, mirrors the existing small-tool style, and makes it easy to test each boundary independently.

### B. One `tools/ingest.py` with subcommands

Create one tool with `prepare`, `manifest-check`, `manifest-add`, and later ingest subcommands.

This would give users a single obvious entrypoint, but it risks implying that ingest itself is deterministic and fully automated. That conflicts with the current agent-first design and could blur the boundary between source preparation and semantic wiki maintenance.

### C. Documentation-only protocol

Leave ingest preflight entirely in `AGENTS.md` and rely on agents to compute hashes and inspect the manifest manually.

This has the least code, but it leaves repeated safety-sensitive work untested and makes duplicate handling easier to get wrong. It also prevents future agent workflows from composing a reliable preflight packet.

## Shared Tool Conventions

Both tools should:

- Use only Python standard library modules.
- Reuse `tools/wiki_utils.py` for path safety, repository-relative paths, hash helpers, timestamps, kebab-case validation, and frontmatter/wiki parsing where applicable.
- Print concise human-readable output by default.
- Support JSON output where the result is useful to an agent.
- Return exit code `0` when the requested operation succeeds.
- Return exit code `1` when validation or preflight finds blocking content issues such as duplicates, ambiguous metadata, or invalid manifest entries.
- Return exit code `2` for invalid arguments, unsupported input types, unsafe paths, parse failures, unreadable files, or write failures.
- Use repository-root-relative paths in text reports and JSON payloads.
- Reject absolute paths where repository-relative paths are required.
- Reject traversal outside the repository.
- Reject symlinked target files and symlinked parents for paths they create or trust.
- Avoid mutating files unless the command's purpose and option explicitly request mutation.

## `tools/prepare_ingest.py`

### Purpose

`prepare_ingest.py` answers: "Can this local input safely proceed to agent-led ingest, and what should the agent know before editing wiki pages?"

It creates an ingest-prep packet containing input classification, content hash, duplicate status, source ID recommendation, source template recommendation, raw/converted path hints, and warnings. It does not write wiki pages or manifest entries.

### Inputs

Command:

```bash
python tools/prepare_ingest.py <input> [<input> ...] \
  [--kind technical-article] \
  [--source-id example-source] \
  [--json] \
  [--report graph/ingest-prep-report.md]
```

Options:

- Positional `input`: one or more local paths or remote URL strings.
- `--kind`: optional source kind. Supported values are `technical-paper`, `technical-article`, `project-readme`, `meeting-notes`, `journal-entry`, and `generic`.
- `--source-id`: optional source ID override for single-input runs only. It must be kebab-case.
- `--json`: print machine-readable ingest-prep results.
- `--report`: optional Markdown report path, defaulting to no report. When provided, the path must stay under `graph/`.

### Supported Inputs

Supported local inputs:

- `.md`
- `.markdown`
- `.txt`
- extensionless UTF-8 text
- files already under `raw/originals/`
- files already under `raw/converted/`

Unsupported inputs:

- Remote URLs.
- PDF.
- Office documents.
- HTML requiring fetching or rendering.
- Binary files.
- Directories.
- Paths outside the repository.

Remote URLs are recognized as ingest intent but blocked in v1. The output should tell the agent to ask the user for pasted text, a local Markdown/text file, or a converted Markdown artifact. The tool must not fetch, crawl, render, or inspect the URL.

### Classification

For each input, the tool should classify:

- `input_kind`: `local-markdown`, `local-text`, `raw-original`, `raw-converted`, `remote-url`, or `unsupported`.
- `source_kind`: the explicit `--kind` when provided, otherwise a conservative recommendation:
  - file names containing `paper`, `arxiv`, `preprint`, or common paper metadata signals recommend `technical-paper`;
  - file names containing `readme` recommend `project-readme`;
  - file names containing `meeting`, `call`, or `notes` recommend `meeting-notes`;
  - file names containing `journal`, `diary`, or date-like personal-note patterns recommend `journal-entry`;
  - otherwise recommend `technical-article` for Markdown/text in this technical/research-focused repository.
- `template_path`: one of `templates/sources/*.md` or `templates/source.md`.

The classifier is a recommendation only. The agent may override it when the source content and user instructions justify doing so.

### Source ID Recommendation

If `--source-id` is provided, validate and use it for single-input preflight.

If no source ID is provided, generate a conservative suggestion from the input filename:

- Normalize to lowercase ASCII where possible.
- Convert separators and punctuation to single hyphens.
- Remove leading and trailing hyphens.
- Collapse repeated hyphens.
- If no useful slug remains, use `source-<short-hash>`.

The tool should warn when the suggested source ID already exists in:

- `raw/source-manifest.jsonl`
- `wiki/sources/<source-id>.md`
- any existing wiki page canonical ID

### Hash and Duplicate Detection

For supported local files, compute:

- `content_hash`: SHA-256 with `sha256:` prefix.
- `input_bytes`.
- `input_path`.

Compare the hash and source ID against `raw/source-manifest.jsonl`:

- duplicate `source_id` blocks ingest.
- duplicate `content_hash` blocks ingest unless the user is explicitly doing manual reconciliation outside this tool.
- malformed manifest lines block preflight because duplicate checks are no longer trustworthy.

For a converted artifact under `raw/converted/`, the packet should also report:

- `converted_path`: the input path.
- `raw_path`: unknown unless a manifest entry already maps to this converted path.
- `needs_raw_original`: true when no matching manifest or raw original can be identified.

The tool should not infer that a converted artifact is enough to satisfy raw provenance unless the manifest already records it.

### Context Packet

Default text output:

```text
MuvyWiki ingest prep: 1 item(s)

1. raw/originals/example.md
   status: ready
   source_id: example
   source_kind: technical-article
   template: templates/sources/technical-article.md
   content_hash: sha256:...
   duplicate: no
   next: run agent-led ingest, then update manifest/index/log and health-check
```

JSON output:

```json
{
  "status": "ready",
  "generated_at": "2026-05-15T00:00:00Z",
  "items": [
    {
      "status": "ready",
      "input": "raw/originals/example.md",
      "input_kind": "raw-original",
      "source_id": "example",
      "source_id_origin": "suggested",
      "source_kind": "technical-article",
      "template_path": "templates/sources/technical-article.md",
      "content_hash": "sha256:...",
      "input_bytes": 1200,
      "raw_path": "raw/originals/example.md",
      "converted_path": null,
      "manifest_match": null,
      "wiki_source_path": "wiki/sources/example.md",
      "warnings": [],
      "next_steps": [
        "Read wiki/index.md and wiki/overview.md.",
        "Perform agent-led extraction and page updates.",
        "Use tools/manifest.py add after the raw artifact and source_id are final.",
        "Run python tools/health.py after ingest."
      ]
    }
  ]
}
```

Batch status rules:

- top-level `status` is `ready` when every item is ready.
- top-level `status` is `blocked` when any item is duplicate, unsupported, unsafe, unreadable, or ambiguous.
- top-level `status` is `issues` when every item is readable but warnings require agent/user review before ingest.

### Markdown Report

When `--report` is provided, write a concise Markdown report under `graph/`:

```markdown
# MuvyWiki Ingest Prep Report

- Status: ready
- Generated at: 2026-05-15T00:00:00Z

## Items

### raw/originals/example.md

- Status: ready
- Source ID: example
- Source kind: technical-article
- Template: templates/sources/technical-article.md
- Content hash: sha256:...
- Duplicate: no
```

The report is a generated artifact, not a wiki page, and should not be added to `wiki/index.md`.

### Exit Codes

- `0`: all inputs are ready.
- `1`: one or more inputs are duplicated, ambiguous, or blocked by manifest inconsistency.
- `2`: invalid arguments, unsupported input type, unsafe path, missing file, unreadable file, invalid report path, or write failure.

Remote URLs return `2` because the requested input cannot be prepared by v1. The message should be clear enough for the agent to ask for a usable local artifact.

## `tools/manifest.py`

### Purpose

`manifest.py` answers: "Is `raw/source-manifest.jsonl` valid, and can this raw artifact be safely recorded?"

It handles deterministic manifest bookkeeping that is currently easy for agents to perform inconsistently. It does not create source pages, update wiki pages, or decide what a source means.

### Commands

```bash
python tools/manifest.py check [--json]
python tools/manifest.py find [--source-id example] [--hash sha256:...] [--path raw/originals/example.md] [--json]
python tools/manifest.py add \
  --source-id example \
  --raw-path raw/originals/example.md \
  --content-hash sha256:... \
  [--source-url https://example.com/article] \
  [--published-at 2026-05-01] \
  [--converted-from raw/originals/example.html] \
  [--converted-path raw/converted/example.md] \
  [--converter convert.py] \
  [--converter-version ingest-prep-v1] \
  [--collected-at 2026-05-15] \
  [--json]
```

### Manifest Entry Shape

Entries should keep the existing `raw/README.md` shape:

```json
{
  "source_id": "example-source",
  "raw_path": "raw/originals/example.md",
  "content_hash": "sha256:...",
  "source_url": null,
  "collected_at": "YYYY-MM-DD",
  "published_at": null,
  "converted_from": null,
  "converted_path": null,
  "converter": null,
  "converter_version": null
}
```

Required fields:

- `source_id`
- `raw_path`
- `content_hash`
- `source_url`
- `collected_at`
- `published_at`
- `converted_from`
- `converted_path`
- `converter`
- `converter_version`

The values for optional metadata may be `null`, but the keys must be present.

### `check`

`check` validates every manifest line:

- JSONL parses line by line.
- Every entry is an object.
- Required keys are present.
- `source_id` is kebab-case.
- `content_hash` is a SHA-256 value with `sha256:` prefix.
- `raw_path` is under `raw/originals/`, exists, is a file, and is not a symlink.
- `converted_path`, when present, is under `raw/converted/`, exists, is a file, and is not a symlink.
- `converted_from`, when present, stays inside the repository and is not a symlink.
- `source_url`, when present, is a string URL but is not fetched or verified.
- `collected_at` and `published_at`, when present, use `YYYY-MM-DD`.
- no duplicate `source_id`.
- no duplicate `content_hash`.
- no duplicate `raw_path`.

Default output:

```text
MuvyWiki manifest: ok
Entries: 1
```

JSON output:

```json
{
  "status": "ok",
  "checked_at": "2026-05-15T00:00:00Z",
  "entry_count": 1,
  "issues": []
}
```

Exit codes:

- `0`: manifest is valid.
- `1`: manifest has validation issues.
- `2`: manifest file is missing, unreadable, or arguments are invalid.

### `find`

`find` searches manifest entries by `source_id`, `content_hash`, or path. At least one search option is required.

Default output:

```text
MuvyWiki manifest find: 1 match(es)

1. example-source
   raw_path: raw/originals/example.md
   content_hash: sha256:...
```

JSON output:

```json
{
  "status": "ok",
  "matches": [
    {
      "source_id": "example-source",
      "raw_path": "raw/originals/example.md",
      "content_hash": "sha256:..."
    }
  ]
}
```

Exit codes:

- `0`: search completed, including zero matches.
- `1`: manifest has validation issues that make search unreliable.
- `2`: invalid search arguments or unreadable manifest.

### `add`

`add` validates and appends exactly one manifest entry.

Validation before writing:

- Run the equivalent of `check`.
- Validate `source_id` is kebab-case.
- Validate `raw_path` is under `raw/originals/`, exists, is a file, and is not a symlink.
- Validate `content_hash` matches the actual raw file hash.
- Validate `converted_path`, when present, is under `raw/converted/`, exists, is a file, and is not a symlink.
- Validate `converted_from`, when present, stays inside the repository and is not a symlink.
- Reject duplicate `source_id`, `content_hash`, or `raw_path`.
- Reject if `wiki/sources/<source-id>.md` exists with conflicting provenance.
- Use today's local date for `collected_at` when omitted.

Writing behavior:

- Append one compact JSON object plus newline to `raw/source-manifest.jsonl`.
- Preserve existing manifest lines exactly.
- Write atomically through a sibling temporary file and replace the manifest on success.
- Leave the manifest unchanged on validation or write failure.

Default success output:

```text
Added manifest entry: example-source
raw_path: raw/originals/example.md
content_hash: sha256:...
```

JSON success output:

```json
{
  "status": "ok",
  "entry": {
    "source_id": "example-source",
    "raw_path": "raw/originals/example.md",
    "content_hash": "sha256:..."
  }
}
```

Exit codes:

- `0`: entry added.
- `1`: validation blocked the add.
- `2`: invalid arguments, unsafe paths, unreadable files, or write failure.

## Agent Workflow Integration

`AGENTS.md` should update the ingest preflight sequence to prefer:

1. Run `python tools/prepare_ingest.py <input> --json`.
2. If blocked, report `Ingest blocked` with the tool reason and next step.
3. Read `wiki/index.md`, `wiki/overview.md`, and relevant pages.
4. Perform agent-led extraction and wiki edits.
5. Use `python tools/manifest.py add ...` after the final `source_id`, raw path, and hash are known.
6. Update `wiki/index.md` and `wiki/log.md`.
7. Run `python tools/health.py`.

For pasted text, the agent still saves the text verbatim to `raw/originals/<source-id>.md` first. In v1, the tool does not read from stdin or capture conversation text directly.

For converted artifacts, the agent must keep the distinction explicit:

- `tools/convert.py` creates local Markdown/text under `raw/converted/`.
- `tools/prepare_ingest.py` checks whether that artifact can proceed.
- `tools/manifest.py add` records raw provenance only when a valid raw original and content hash exist.
- wiki page creation remains agent-led.

## Documentation Updates

Implementation should update:

- `README.md`: current status table, command summary, documentation map notes.
- `USER_GUIDE.md`: user-facing ingest-prep workflow, duplicate checks, manifest helper examples, and supported/unsupported inputs.
- `AGENTS.md`: agent-facing preflight and manifest workflow.
- `raw/README.md`: manifest helper contract and entry validation.
- `graph/README.md`: generated ingest-prep reports under `graph/`.
- `examples/ingest/README.md` and fixture docs if the example copies the new helpers.
- `docs/superpowers/specs/2026-05-12-muvywiki-design.md`: status note that deterministic ingest-prep helpers now exist.
- `docs/superpowers/specs/2026-05-12-ingest-v2-design.md`: status note that preflight/manifest pieces are now tool-assisted.

Historical plans only need a status note if older instructions could be mistaken for the current protocol.

## Testing Plan

Add focused tests:

- `tests/test_prepare_ingest.py`
  - ready local Markdown.
  - ready local text.
  - raw original classification.
  - converted artifact classification with `needs_raw_original`.
  - source ID override validation.
  - duplicate source ID blocks.
  - duplicate content hash blocks.
  - malformed manifest blocks duplicate checks.
  - remote URL is recognized and blocked.
  - unsupported suffix is rejected.
  - unsafe path and symlink cases are rejected.
  - JSON output and Markdown report shape.

- `tests/test_manifest.py`
  - empty manifest is valid.
  - valid existing entry passes.
  - malformed JSONL fails.
  - missing keys fail.
  - duplicate `source_id`, `content_hash`, and `raw_path` fail.
  - hash mismatch blocks add.
  - add writes exactly one valid entry and preserves existing lines.
  - add rejects unsafe paths, symlink targets, unsupported raw paths, and duplicate entries.
  - find succeeds with zero or more matches.
  - JSON outputs have stable keys.

- Existing tests:
  - update `tests/test_health.py` required path checks if `health.py` should require the new tools.
  - update `tests/test_docs_interfaces.py` so docs and implemented interfaces stay aligned.
  - keep `tests/test_convert.py` enforcing that conversion does not equal ingest.

Verification after implementation:

```bash
python -m unittest tests/test_prepare_ingest.py
python -m unittest tests/test_manifest.py
python -m unittest tests/test_docs_interfaces.py
python -m unittest discover -s tests
python tools/lint.py
python tools/health.py
python tools/build_graph.py
```

If the example fixture copies the new helpers, also run:

```bash
cd examples/ingest
python tools/lint.py
python tools/health.py
python tools/build_graph.py
```

## Future Hooks

The v1 interfaces should leave room for:

- `--from-url` or a separate web-clipper workflow that records fetched artifacts without pretending remote fetch exists today.
- richer document conversion through an explicit Convert v2 tool, possibly using optional dependencies.
- batch ingest orchestration that calls preflight per item and then asks the user or agent to choose ordering.
- manifest reconciliation for intentionally duplicated sources or corrected metadata.
- semantic extraction helpers that propose source-page drafts without writing them.
- graph/lint integration that suggests missing concept/entity pages after ingest.
- optional Obsidian-oriented workflows, such as attachment download checks or clipper metadata import.

These hooks should remain explicit. Ingest Prep v1 should not silently implement partial versions of them.

## Resolved Design Decisions

- `prepare_ingest.py --report` is explicit only. It does not write `graph/ingest-prep-report.md` unless the caller provides `--report`.
- `manifest.py add` does not require a source page to exist before adding the manifest entry. The raw manifest can be recorded before semantic wiki edits, and `health.py` remains the post-ingest consistency gate.
- `prepare_ingest.py` does not stage local files into `raw/originals/`. If staging is needed later, it should be a separate explicit command so preflight stays read-only.
