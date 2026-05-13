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
| Semantic lint | Implemented | `python tools/lint.py`, `python tools/lint.py --json`, `python tools/lint.py --report graph/graph-report.md` |
| Graph generation | Implemented | `python tools/build_graph.py` |
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
python tools/convert.py raw/originals/example.txt --out raw/converted/example.md
```

Documentation map:

- `USER_GUIDE.md` - user-facing workflow and current capability guide.
- `AGENTS.md` - operating protocol for Codex and compatible agents.
- `raw/README.md` - source artifact and manifest rules.
- `graph/README.md` - graph output contract.
- `examples/ingest/README.md` - runnable example of a successful ingest.

`convert.py` supports local Markdown/text inputs only. PDF, Office documents, remote URLs, HTML rendering, embeddings, and LLM-based extraction remain future work.
