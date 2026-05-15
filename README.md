# MuvyWiki

MuvyWiki is a personal LLM-maintained knowledge base inspired by Andrej Karpathy's LLM Wiki pattern.

中文使用手册见 [USER_GUIDE.md](USER_GUIDE.md)。

## Current Status

MuvyWiki currently favors an agent-first workflow over a large command-line application. Deterministic checks live in `tools/`; semantic extraction and page maintenance are governed by `AGENTS.md`, templates, and examples.

| Area | Status | Interface |
| --- | --- | --- |
| Structural health checks | Implemented | `python tools/health.py`, `python tools/health.py --json` |
| Agent-first ingest | Implemented as protocol | `AGENTS.md`, `templates/source.md`, `templates/sources/` |
| Domain source templates | Implemented | technical paper, technical article, project README, meeting notes, journal entry |
| Example ingest fixture | Implemented | `examples/ingest/` |
| Test suite | Implemented | `python -m unittest discover -s tests` |
| Semantic lint | Implemented | `python tools/lint.py`, `python tools/lint.py --json`, `python tools/lint.py --report graph/lint-report.md` |
| Graph generation | Implemented | `python tools/build_graph.py` |
| Ingest preparation | Implemented | `python tools/prepare_ingest.py <local-md-or-text> --json`, `python tools/prepare_ingest.py <local-md-or-text> --report graph/ingest-prep-report.md` |
| Manifest helper | Implemented | `python tools/manifest.py check`, `python tools/manifest.py find --source-id <source-id>`, `python tools/manifest.py find --hash <sha256:...>`, `python tools/manifest.py find --path <raw-or-converted-path>`, `python tools/manifest.py add ...` |
| Query context | Implemented | `python tools/query.py "retrieval augmented generation"`, `python tools/query.py "retrieval augmented generation" --json` |
| Synthesis saving | Implemented | `python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md` |
| Source conversion | Partial | `python tools/convert.py <local-md-or-text> --out raw/converted/<file>.md` |

The repository has three layers:

- `raw/` stores original and converted source artifacts.
- `wiki/` stores the agent-maintained knowledge base.
- `AGENTS.md` defines the operating rules for Codex and compatible agents.

Common commands:

```bash
python tools/health.py
python tools/health.py --json
python -m unittest discover -s tests
python tools/lint.py
python tools/build_graph.py
python tools/prepare_ingest.py raw/originals/example.md --json
python tools/prepare_ingest.py raw/originals/example.md --report graph/ingest-prep-report.md
python tools/manifest.py check
python tools/manifest.py find --source-id example-source
python tools/manifest.py find --hash sha256:<64-hex-digits>
python tools/manifest.py find --path raw/originals/example.md
python tools/manifest.py add --source-id example-source --raw-path raw/originals/example.md --content-hash sha256:<64-hex-digits> --collected-at YYYY-MM-DD
python tools/query.py "retrieval augmented generation"
python tools/query.py "retrieval augmented generation" --json
python tools/save_synthesis.py --id example-synthesis --title "Example Synthesis" --question "What should be saved?" --answer-file /tmp/answer.md --evidence-file /tmp/evidence.md
python tools/convert.py raw/originals/example.txt --out raw/converted/example.md
```

Documentation map:

- `USER_GUIDE.md` - user-facing workflow and current capability guide.
- `AGENTS.md` - operating protocol for Codex and compatible agents.
- `raw/README.md` - source artifact and manifest rules.
- `graph/README.md` - graph output contract.
- `examples/ingest/README.md` - runnable example of a successful ingest.
- `docs/superpowers/specs/` - design specs that current agent docs reference.
- `docs/superpowers/plans/` - historical implementation plans.

`query.py` and `save_synthesis.py` are agent-facing helpers that retrieve context and persist approved syntheses, but do not call an LLM or ingest new raw sources.

`prepare_ingest.py` and `manifest.py` are ingest preparation helpers. They do not call an LLM, do not extract claims, and do not create or update wiki pages, `wiki/index.md`, or `wiki/log.md`. `prepare_ingest.py` performs read-only preflight checks unless explicitly asked to write a report under `graph/`; `manifest.py` only validates, searches, or appends entries in `raw/source-manifest.jsonl`.

`convert.py` supports local Markdown/text inputs only. PDF, Office documents, remote URLs, HTML rendering, embeddings, and LLM-based extraction remain future work.
