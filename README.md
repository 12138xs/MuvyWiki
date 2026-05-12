# MuvyWiki

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
python tools/build_graph.py
python tools/convert.py raw/originals/example.pdf --out raw/converted/example.md
```

Reserved tools may return exit code `3` until their full implementation is added.
