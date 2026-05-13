# MuvyWiki Root README Snapshot

This file is a copied support snapshot for the ingest fixture. The fixture entrypoint is `README.md`; the full repository root contains the complete user guide and domain source templates.

MuvyWiki is a personal LLM-maintained knowledge base inspired by Andrej Karpathy's LLM Wiki pattern.

The repository has three layers:

- `raw/` stores original and converted source artifacts.
- `wiki/` stores the agent-maintained knowledge base.
- `AGENTS.md` defines the operating rules for Codex and compatible agents.

Common commands:

```bash
python tools/health.py
python tools/health.py --json
python tools/lint.py
python tools/lint.py --report graph/lint-report.md
python tools/build_graph.py
python tools/convert.py raw/originals/example.txt --out raw/converted/example.md
```

For this fixture's agent-first ingest protocol, see `AGENTS.md`. The fixture includes the base source template at `templates/source.md`; the full repository root includes additional domain-specific source templates.

`convert.py` supports local Markdown/text inputs only. PDF, Office documents, remote URLs, HTML rendering, and binary files need a readable text or Markdown artifact first.
