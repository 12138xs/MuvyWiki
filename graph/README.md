# Graph Artifacts

This directory stores generated graph outputs.

## Current Interface Status

`python tools/build_graph.py` generates `graph.json`, `graph.html`, and `graph-report.md` from wiki frontmatter, wikilinks, source IDs, related IDs, and raw paths.

- `graph.json` - machine-readable nodes and edges.
- `graph.html` - self-contained visualization.
- `graph-report.md` - graph health and structure report.
- `ingest-prep-report.md` - optional ingest preflight report from `python tools/prepare_ingest.py <input> --report graph/ingest-prep-report.md`.
- Saved synthesis pages from `wiki/syntheses/` appear as `synthesis` nodes in graph outputs.

Command interface:

```bash
python tools/build_graph.py \
  --json graph/graph.json \
  --html graph/graph.html \
  --report graph/graph-report.md
```

Graph artifacts are generated files. Regenerate them after meaningful wiki changes instead of editing them by hand.

`ingest-prep-report.md` is a generated preparation report, not a wiki page. It may summarize a blocked duplicate or unsupported input before formal ingest begins.
