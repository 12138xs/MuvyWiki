# MuvyWiki Fixture Command Reference

This file records how the full repository invokes this fixture. The fixture entrypoint is `README.md`; the project root contains the implementation, complete user guide, and domain source templates.

MuvyWiki is a personal LLM-maintained knowledge base inspired by Andrej Karpathy's LLM Wiki pattern.

The repository has three layers:

- `raw/` stores original and converted source artifacts.
- `wiki/` stores the agent-maintained knowledge base.
- `AGENTS.md` defines the operating rules for Codex and compatible agents.

Run these commands from the project root:

```bash
python tools/health.py --repo-root examples/ingest
python tools/health.py --repo-root examples/ingest --json
python tools/lint.py --repo-root examples/ingest
python tools/lint.py --repo-root examples/ingest --report graph/lint-report.md
python tools/build_graph.py --repo-root examples/ingest
python tools/prepare_ingest.py --repo-root examples/ingest raw/originals/tiny-rag-note.md --json
python tools/manifest.py --repo-root examples/ingest check
python tools/manifest.py --repo-root examples/ingest find --source-id tiny-rag-note
python tools/query.py --repo-root examples/ingest "retrieval augmented generation"
```

For this fixture's agent-first ingest protocol, see `AGENTS.md`. The fixture includes the base source template at `templates/source.md`; the full repository root includes additional domain-specific source templates.

`convert.py` supports local Markdown/text inputs only. PDF, Office documents, remote URLs, HTML rendering, and binary files need a readable text or Markdown artifact first.

`prepare_ingest.py` only performs preflight and optional report generation; it does not call an LLM or create wiki pages. `manifest.py` only checks, finds, or appends `raw/source-manifest.jsonl` entries and does not update index/log.
