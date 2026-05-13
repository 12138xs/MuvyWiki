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
| Semantic lint | Reserved | `python tools/lint.py` returns exit code `3` |
| Graph generation | Reserved | `python tools/build_graph.py` returns exit code `3` |
| Source conversion | Reserved | `python tools/convert.py <input> --out raw/converted/<file>` returns exit code `3` after output-path validation |

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
python tools/convert.py raw/originals/example.pdf --out raw/converted/example.md
```

Documentation map:

- `USER_GUIDE.md` - user-facing workflow and current capability guide.
- `AGENTS.md` - operating protocol for Codex and compatible agents.
- `raw/README.md` - source artifact and manifest rules.
- `graph/README.md` - reserved graph output contract.
- `examples/ingest/README.md` - runnable example of a successful ingest.

Reserved tools return exit code `3` until their full implementation is added. Treat this as "interface reserved", not as completed lint, graph, or conversion functionality.
