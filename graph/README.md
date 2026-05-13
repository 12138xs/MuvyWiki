# Graph Artifacts

This directory stores generated graph outputs.

## Current Interface Status

`python tools/build_graph.py` generates `graph.json`, `graph.html`, and `graph-report.md` from wiki frontmatter, wikilinks, source IDs, related IDs, and raw paths.

- `graph.json` - machine-readable nodes and edges.
- `graph.html` - self-contained visualization.
- `graph-report.md` - graph health and structure report.

Command interface:

```bash
python tools/build_graph.py \
  --json graph/graph.json \
  --html graph/graph.html \
  --report graph/graph-report.md
```

Graph artifacts are generated files. Regenerate them after meaningful wiki changes instead of editing them by hand.
