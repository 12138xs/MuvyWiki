# MuvyWiki Roadmap

This roadmap tracks repository-specific work that follows the reproducibility hardening milestone. Items are ordered by user impact and dependency, not by estimated code volume.

## Planning rules

- Every item names the module or persisted contract it changes.
- A task is complete only when its acceptance checks are automated or recorded.
- Changes to CLI behavior must update README, USER_GUIDE, AGENTS, tests, and CI together.
- New knowledge features must preserve raw-source provenance and pass health/lint.
- Performance claims require a checked-in evaluation fixture and reproducible measurement method.

## P1 — Reliability and retrieval quality

### 1. Chinese tokenization and FTS5 retrieval

- Scope: `tools/query.py`, a new query evaluation fixture, and query tests.
- Goal: retrieve Chinese concepts without relying on whitespace or ASCII token boundaries.
- Acceptance: a checked-in Chinese query set identifies expected source/concept IDs; existing English ranking tests remain stable; the SQLite index can be rebuilt deterministically.

### 2. Manifest concurrency control

- Scope: `tools/manifest.py` and manifest write tests.
- Goal: prevent concurrent `add` operations from losing or interleaving JSONL entries.
- Acceptance: writes use a cross-process lock plus atomic replacement; a concurrency test proves all unique entries survive and duplicate detection remains deterministic.

### 3. Synthesis crash recovery

- Scope: `tools/save_synthesis.py`, `wiki/index.md`, and `wiki/log.md` transaction behavior.
- Goal: recover cleanly if a process stops between synthesis, index, and log replacements.
- Acceptance: a durable transaction journal records intent; restart either completes or rolls back all three files; fault-injection tests cover every replacement boundary.

### 4. Ingest directory planning

- Scope: `tools/prepare_ingest.py`.
- Goal: inspect a directory of candidate Markdown/text files without writing manifest or wiki state.
- Acceptance: `--plan` reports stable per-file IDs, hashes, duplicates, unsupported inputs, and conflicts; plan ordering is deterministic; applying no action leaves the repository unchanged.

## P2 — Provenance and graph evolution

### 5. HTML conversion with provenance

- Scope: `tools/convert.py` and manifest provenance fields.
- Goal: convert an explicitly supplied local HTML file while preserving source URL, input hash, converter name, and converter version.
- Acceptance: scripts/styles are excluded, readable text order is tested, no network access occurs, and the converted artifact can be validated through manifest and health.

### 6. Versioned and incremental graph builds

- Scope: `tools/build_graph.py` and `graph/graph.json`.
- Goal: make graph consumers aware of schema changes and avoid unnecessary rewrites.
- Acceptance: graph JSON declares a schema version; unchanged input produces byte-stable output apart from explicitly documented timestamps; incremental and full builds produce equivalent nodes and edges.

### 7. Graph freshness in health checks

- Scope: `tools/health.py`, graph metadata, and health tests.
- Goal: detect when maintained wiki pages changed after the last graph build.
- Acceptance: health reports stale graph inputs with the affected paths, distinguishes missing from stale artifacts, and provides the exact rebuild command.

### 8. Fixed query regression evaluation

- Scope: `tools/query.py`, `tests/fixtures/query-evaluation.json`, and CI.
- Goal: prevent ranking changes from silently reducing retrieval quality.
- Acceptance: each query records required IDs and optional ordering constraints; CI reports recall@k and ranking failures; evaluation remains local and deterministic.

## Maintenance cadence

- Every pull request: unit tests, manifest, health, lint, demo, fixture checks, documentation-path checks.
- Monthly: run the README quickstart from a fresh clone and review supported Python versions.
- Quarterly: review active versus `needs-review` pages, manifest integrity, graph freshness, and this priority order.
- Before a repository-quality submission: freeze the candidate HEAD, run the full verification matrix in `docs/milestones/README.md`, then record the exact commit ID and CI run.

## Completed foundation

- Explicit `--repo-root` support across deterministic tools.
- Content-only ingest fixture that reuses root tools.
- Non-mutating end-to-end demo.
- First verified root knowledge source with manifest provenance.
- Python 3.10–3.12 CI quality gates.
- Reproducible clone-to-demo README path.
