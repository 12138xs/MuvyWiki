# Graph Artifacts

This directory is reserved for future graph outputs.

## Current Interface Status

Graph generation is not implemented yet. `python tools/build_graph.py` accepts the reserved output arguments below and returns exit code `3`.

Expected future files:

- `graph.json` - machine-readable nodes and edges.
- `graph.html` - self-contained visualization.
- `graph-report.md` - graph health and structure report.

Reserved command interface:

```bash
python tools/build_graph.py \
  --json graph/graph.json \
  --html graph/graph.html \
  --report graph/graph-report.md
```

Version one does not require graph output for normal knowledge-base use.
