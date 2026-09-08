# Graph Artifacts

This directory stores generated graph outputs.

From the project root, `python tools/build_graph.py --repo-root examples/ingest` generates these files from fixture wiki frontmatter, wikilinks, source IDs, related IDs, and raw paths:

- `graph.json` - machine-readable nodes and edges.
- `graph.html` - self-contained visualization.
- `graph-report.md` - graph health and structure report.

Regenerate graph artifacts after meaningful fixture wiki changes instead of editing generated files by hand.
