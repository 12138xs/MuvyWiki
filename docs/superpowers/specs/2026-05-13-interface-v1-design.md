# Interface v1 Design

## Summary

Interface v1 turns the currently reserved `lint.py`, `build_graph.py`, and `convert.py` entrypoints into small, useful, standard-library-only tools while preserving MuvyWiki's agent-first philosophy.

The goal is not to build a full ingestion platform yet. The goal is to make every public command honest, deterministic, documented, test-covered, and consistent with the existing wiki structure.

## Goals

- Implement a practical first version of every reserved tool interface.
- Keep the implementation lightweight and dependency-free.
- Preserve future hooks for richer conversion, semantic linting, and graph visualization.
- Keep `tools/health.py` as the structural quality gate.
- Keep agent semantic extraction in `AGENTS.md` rather than replacing it with a full ingest CLI.
- Update documentation and tests so user-facing and agent-facing claims match actual behavior.

## Non-Goals

- No PDF parsing.
- No Office document parsing.
- No web fetching, crawling, rendering, or scraping.
- No embeddings, vector search, or LLM calls.
- No automatic creation of wiki source/concept/entity pages from `convert.py`.
- No replacement for the agent-first ingest workflow.
- No new third-party dependencies.

## Shared Tool Conventions

All tools should:

- Use only Python standard library modules.
- Support normal text output by default.
- Support JSON output where useful.
- Return exit code `0` when the requested operation succeeds with no blocking issues.
- Return exit code `1` when checks find issues or graph/lint reports indicate an unhealthy result.
- Return exit code `2` for argument, path, or unsupported-input errors.
- Avoid mutating files unless the command's purpose is explicitly to write an output artifact.
- Create parent directories for declared output files when writing reports or graph artifacts.
- Use repository-root-relative paths in reports.

## `tools/lint.py`

### Purpose

`lint.py` provides semantic-lite linting that complements `health.py`. It should catch wiki maintenance smells that are structurally valid but likely low quality.

### Inputs

Command:

```bash
python tools/lint.py [--json] [--report graph/graph-report.md]
```

Options:

- `--json`: print machine-readable lint results to stdout.
- `--report`: write a Markdown lint report. The default remains `graph/graph-report.md`.

### Checks

The first implemented checks should be deterministic and conservative:

- Empty required sections: page sections whose heading exists but has no body before the next heading.
- Missing source evidence: source pages with no useful body under `## Evidence and Details`.
- Missing source claims: source pages with no useful body under `## Key Claims`.
- Concept pages without supporting sources: concept pages whose `source_ids` list is empty and whose `## Supporting Sources` section has no wikilink.
- Entity pages without evidence: entity pages whose `## Evidence` section has no useful body or wikilink.
- Orphan pages: concept/entity/synthesis pages not linked from any other wiki page and not referenced by `wiki/overview.md`.
- Stale index summaries: index entries with default empty-state summaries such as `No ... yet.` for pages that now exist.

### Output

JSON shape:

```json
{
  "status": "ok | issues",
  "issues": [
    {
      "severity": "warning | error",
      "path": "wiki/concepts/Example.md",
      "check": "empty-section",
      "message": "Section ## Evidence is empty."
    }
  ],
  "checked_at": "2026-05-13T00:00:00Z"
}
```

Markdown report shape:

```markdown
# MuvyWiki Lint Report

- Status: ok
- Checked at: 2026-05-13T00:00:00Z

## Issues

No lint issues found.
```

### Exit Codes

- `0`: no lint issues.
- `1`: lint issues found.
- `2`: invalid arguments or invalid report path.

## `tools/build_graph.py`

### Purpose

`build_graph.py` generates local graph artifacts from the current wiki. It should make the knowledge graph inspectable without requiring a browser framework or external graph library.

### Inputs

Command:

```bash
python tools/build_graph.py \
  --json graph/graph.json \
  --html graph/graph.html \
  --report graph/graph-report.md
```

Options preserve the existing reserved interface:

- `--json`: graph JSON output path.
- `--html`: HTML graph viewer output path.
- `--report`: Markdown graph report output path.

### Graph Model

Nodes:

- One node for each wiki page collected by `health.py`-compatible rules.
- Fields: `id`, `title`, `type`, `path`, `tags`, `status`, `confidence`.

Edges:

- `wikilink`: page body contains a `[[TargetID]]` link.
- `source`: page frontmatter `source_ids` references a source page.
- `related`: page frontmatter `related_ids` references another page.
- `raw`: source page provenance or `raw_paths` references a raw artifact.

Edges should include `source`, `target`, `type`, and `path` when relevant.

### Outputs

`graph/graph.json`:

```json
{
  "generated_at": "2026-05-13T00:00:00Z",
  "nodes": [],
  "edges": [],
  "summary": {
    "node_count": 0,
    "edge_count": 0,
    "by_type": {}
  }
}
```

`graph/graph-report.md`:

```markdown
# MuvyWiki Graph Report

- Generated at: 2026-05-13T00:00:00Z
- Nodes: 0
- Edges: 0

## Node Types

## Edge Types
```

`graph/graph.html`:

- A self-contained HTML file.
- Embeds the JSON graph data.
- Shows node and edge counts, node table, and edge table.
- Does not require network access.

### Exit Codes

- `0`: artifacts generated.
- `2`: invalid output path or write failure.

## `tools/convert.py`

### Purpose

`convert.py` becomes a safe local text/Markdown conversion helper. It should normalize supported local inputs into `raw/converted/` while preserving the agent-first ingest boundary.

### Inputs

Command:

```bash
python tools/convert.py <input_path_or_url> --out raw/converted/<file>.md [--json]
```

Supported now:

- Local `.md`
- Local `.markdown`
- Local `.txt`
- Local extensionless UTF-8 text files

Unsupported now:

- Remote URLs
- PDF
- DOCX/PPTX/XLSX
- HTML requiring fetching or rendering
- Binary files
- Absolute output paths
- Output paths outside `raw/converted/`

### Behavior

For supported local text inputs:

- Read input as UTF-8 text.
- Normalize line endings to `\n`.
- Write to the requested path under `raw/converted/`.
- Create parent directories under `raw/converted/` as needed.
- Preserve Markdown content as Markdown.
- Wrap plain text with a short generated heading only when the file has no Markdown heading.
- Print a concise success message by default.
- With `--json`, print source path, output path, input hash, output hash, and byte counts.

`convert.py` should not:

- Append to `raw/source-manifest.jsonl`.
- Create wiki source pages.
- Update `wiki/index.md`.
- Update `wiki/log.md`.

Those steps remain part of agent-first ingest.

### Output

Default text output:

```text
Converted raw/originals/example.txt -> raw/converted/example.md
```

JSON output:

```json
{
  "status": "ok",
  "input_path": "raw/originals/example.txt",
  "output_path": "raw/converted/example.md",
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "input_bytes": 123,
  "output_bytes": 145
}
```

### Exit Codes

- `0`: conversion succeeds.
- `2`: unsupported input, invalid path, unreadable input, decode error, or invalid output target.

## Documentation Updates

After implementation, update:

- `README.md`: current status table and command examples.
- `USER_GUIDE.md`: current capability section, convert/lint/graph usage, unsupported input notes.
- `AGENTS.md`: implemented interface list and agent rules for using each tool.
- `raw/README.md`: conversion behavior and manifest boundary.
- `graph/README.md`: graph artifacts and command outputs.
- `examples/ingest/README.md`: whether fixture validates with lint/graph.

## Tests

Add or update tests for:

- `lint.py` success and issue cases.
- `lint.py --json` shape.
- `lint.py --report` writing Markdown.
- `build_graph.py` JSON, report, and HTML outputs.
- `build_graph.py` edge extraction from wikilinks/source_ids/related_ids/raw paths.
- `convert.py` successful `.md` and `.txt` conversion.
- `convert.py --json` shape.
- `convert.py` rejection of remote URLs, absolute outputs, traversal outputs, and unsupported binary-like extensions.
- Documentation consistency for implemented/reserved status.

Existing tests should continue to pass. `health.py` behavior should not regress.

## Compatibility

This design intentionally changes the old reserved-tool contract. Tests that currently expect exit code `3` should be replaced with tests for implemented behavior.

The public command names and option names remain stable, so future richer implementations can extend behavior without breaking basic usage.

## Risks

- Lightweight lint can create noisy warnings. The first version should keep checks conservative and deterministic.
- Graph generation could drift from `health.py` page-discovery rules if duplicated poorly. Implementation should reuse compatible parsing patterns or small shared helper functions where it reduces risk without over-abstracting.
- Conversion can be mistaken for full ingest. Documentation and `AGENTS.md` must state that conversion only creates converted artifacts; ingest still updates manifest and wiki pages.

## Acceptance Criteria

- `python tools/lint.py` returns `0` on the current repository.
- `python tools/lint.py --json` returns valid JSON.
- `python tools/lint.py --report graph/graph-report.md` writes a Markdown report.
- `python tools/build_graph.py` writes JSON, HTML, and report artifacts.
- `python tools/convert.py` converts local Markdown/text to `raw/converted/`.
- Unsupported conversion inputs return exit code `2` with clear messages.
- Documentation no longer describes these tools as reserved once implementation lands.
- `python -m unittest discover -s tests` passes.
- `python tools/health.py` passes.
- `cd examples/ingest && python tools/health.py` passes.
