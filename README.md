# MuvyWiki

MuvyWiki is a personal, agent-maintained knowledge base with append-only source storage, traceable wiki pages, and deterministic local quality checks. It is inspired by Andrej Karpathy's LLM Wiki pattern, but the repository does not call an LLM itself.

中文完整使用说明见 [USER_GUIDE.md](USER_GUIDE.md).

## Requirements

- Git with access to this private repository.
- Python 3.10 or newer. CI verifies Python 3.10, 3.11, and 3.12.
- No third-party runtime dependencies; the tools use the Python standard library.

The commands below assume macOS or Linux. On Windows, create the environment with `py -3.10 -m venv .venv`, activate `.venv\Scripts\activate`, then use `python` for the remaining commands.

## Clone and verify

```bash
git clone https://github.com/12138xs/MuvyWiki.git
cd MuvyWiki
python3 -m venv .venv
source .venv/bin/activate
python --version
python tools/health.py
python tools/demo.py
```

No `pip install` step is required. `python --version` must report 3.10 or newer.

Expected stable output:

```text
MuvyWiki health: ok
MuvyWiki demo: ok
Fixture: examples/ingest
Steps: health -> lint -> query -> graph
Query matches: 4
Graph: 4 nodes, 18 edges
Workspace modified: no
```

Timestamps and future match counts may change as the wiki grows, but both commands must exit `0`, the demo counts must remain non-zero, and the demo must report `Workspace modified: no`.

## Query the real wiki

The root wiki includes a verified repository-contract source, so this command works immediately after clone:

```bash
python tools/query.py "repository root isolation provenance"
```

The first results should include `muvywiki-repository-contract` and `RepositoryRootIsolation`. Add `--json` for a machine-readable context packet or `--include-sections` for matching section excerpts.

Query is deterministic keyword retrieval. It does not generate an answer, call an LLM, access the network, or modify files.

## Validate the ingest fixture

`examples/ingest` contains a complete example knowledge chain but reuses the production tools:

```bash
python tools/health.py --repo-root examples/ingest
python tools/lint.py --repo-root examples/ingest
python tools/query.py --repo-root examples/ingest "retrieval augmented generation"
```

Use `--repo-root PATH` with any tool to select another local MuvyWiki content root. Inputs and outputs are then resolved against that root. `manifest.py` takes the option before its subcommand, for example:

```bash
python tools/manifest.py --repo-root examples/ingest check
```

## Development

Run the same gates used by CI:

```bash
python -m unittest discover -s tests
python tools/manifest.py check
python tools/health.py
python tools/lint.py
python tools/demo.py
python tools/health.py --repo-root examples/ingest
python tools/lint.py --repo-root examples/ingest
```

All commands should exit `0`. `demo.py` runs graph generation in a temporary copy; it does not write generated artifacts into the checkout.

## Add a source

MuvyWiki uses an agent-first ingest protocol. Before ingesting, place an owned or authorized UTF-8 Markdown/text artifact under `raw/originals/` with a new stable file name. Do not overwrite an existing raw artifact.

For a new file such as `raw/originals/my-note.md`, the workflow is:

1. Run `python tools/prepare_ingest.py raw/originals/my-note.md --json`.
2. Check for an existing ID, hash, or path with `python tools/manifest.py find --source-id my-note` and the corresponding `--hash`/`--path` forms.
3. After the path, ID, hash, and rights are confirmed, append the manifest entry with `python tools/manifest.py add ...`.
4. Read the source and create or update the required source, concept, entity, index, overview, and log pages according to [AGENTS.md](AGENTS.md).
5. Run manifest, health, and lint checks before committing.

These are workflow examples for a user-provided `my-note.md`; that placeholder is not included in the repository. For a fully runnable, non-mutating example, use `python tools/demo.py`.

Conversion and preflight do not complete ingest. `convert.py` only supports local UTF-8 Markdown/text, while `prepare_ingest.py` only analyzes an input. Neither creates maintained wiki pages.

## Current interfaces

| Area | Status | Verified interface |
| --- | --- | --- |
| Structural health checks | Implemented | `python tools/health.py`, `python tools/health.py --json` |
| Semantic lint | Implemented | `python tools/lint.py`, `python tools/lint.py --json` |
| Graph generation | Implemented | `python tools/build_graph.py` |
| Non-mutating demo | Implemented | `python tools/demo.py`, `python tools/demo.py --json` |
| Ingest preparation | Implemented | `python tools/prepare_ingest.py --help` |
| Manifest validation/search/add | Implemented | `python tools/manifest.py --help` |
| Query context | Implemented | `python tools/query.py "repository root isolation provenance"` |
| Synthesis saving | Implemented | `python tools/save_synthesis.py --help` |
| Source conversion | Partial | `python tools/convert.py --help` |
| Agent-led knowledge extraction | Protocol | [AGENTS.md](AGENTS.md) and `templates/` |
| Test suite | Implemented | `python -m unittest discover -s tests` |

Unsupported interfaces include remote URL fetching, rendered HTML ingestion, PDF/Office/binary conversion, embeddings, vector search, and automatic LLM extraction.

## Repository layout

```text
raw/                 append-only original and converted source artifacts
wiki/                maintained sources, concepts, entities, and syntheses
templates/           canonical page shapes
tools/               deterministic Python interfaces
tests/               standard-library unit and integration tests
examples/ingest/     content-only ingest fixture
graph/                generated local graph artifacts
docs/                 current design records and historical plans
```

## Troubleshooting

- `python: command not found`: activate the virtual environment, or replace `python` with a Python 3.10+ executable.
- `Invalid repository root`: verify that the `--repo-root` path exists and points to a MuvyWiki content root.
- Health reports missing paths or provenance mismatch: do not continue ingest; repair the reported path, manifest, index, or source metadata first.
- Lint reports incomplete pages: add source-backed claims/evidence, connect orphan pages, or keep unfinished pages in `needs-review`.
- Preflight exits `1` for the bundled fixture source: this is expected duplicate detection because that source is already in the fixture manifest.
- Private clone returns `Repository not found`: sign in to GitHub with an account authorized for `12138xs/MuvyWiki`, then retry.

## Safety and maintenance boundaries

- Never commit API keys, tokens, cookies, passwords, private keys, seed phrases, customer data, or internal addresses.
- Preserve `raw/` artifacts; correct prior ingest through a new artifact and an explicit maintenance record.
- Do not count conversion, manifest registration, or structural health as completed knowledge extraction.
- Keep README, USER_GUIDE, AGENTS, tests, and CI aligned whenever an interface changes.
- Do not duplicate production tool files inside fixtures.

## Documentation map

- [USER_GUIDE.md](USER_GUIDE.md) — Chinese user workflows and maintenance guidance.
- [AGENTS.md](AGENTS.md) — agent operating contract and ingest protocol.
- [raw/README.md](raw/README.md) — source storage and manifest rules.
- [graph/README.md](graph/README.md) — graph output contract.
- [examples/ingest/README.md](examples/ingest/README.md) — runnable fixture commands.
- [ROADMAP.md](ROADMAP.md) — repository-specific next work and acceptance criteria.
- [docs/milestones/README.md](docs/milestones/README.md) — commit boundaries and verification evidence.
- `docs/superpowers/specs/` — design specifications.
- `docs/superpowers/plans/` — historical implementation plans, not current instructions.
