#!/usr/bin/env python3
"""Generate local graph artifacts for MuvyWiki."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path

import wiki_utils


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = DEFAULT_ROOT


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [str(value)]


def resolve_output(path: str) -> Path:
    return wiki_utils.safe_child_path(ROOT, path, ROOT / "graph")


def page_id(frontmatter: dict[str, object], path: Path) -> str:
    canonical_id = frontmatter.get("canonical_id")
    return str(canonical_id) if canonical_id else path.stem


def page_title(frontmatter: dict[str, object], text: str, fallback: str) -> str:
    title = frontmatter.get("title")
    if title:
        return str(title)
    for line in wiki_utils.content_after_frontmatter(text).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def add_edge(
    edges: list[dict[str, str]],
    seen: set[tuple[str, str, str, str]],
    source: str,
    target: str,
    edge_type: str,
    path: str = "",
) -> None:
    if not target:
        return
    key = (source, target, edge_type, path)
    if key in seen:
        return
    seen.add(key)
    edge = {"source": source, "target": target, "type": edge_type}
    if path:
        edge["path"] = path
    edges.append(edge)


def build_graph() -> dict[str, object]:
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str, str]] = set()

    for path in wiki_utils.collect_wiki_pages(ROOT):
        text = wiki_utils.read_text(path)
        frontmatter = wiki_utils.parse_frontmatter(text)
        source_id = page_id(frontmatter, path)
        rel_path = wiki_utils.repo_relative(ROOT, path)
        nodes.append(
            {
                "id": source_id,
                "title": page_title(frontmatter, text, source_id),
                "type": str(frontmatter.get("type") or ""),
                "path": rel_path,
                "tags": as_list(frontmatter.get("tags")),
                "status": str(frontmatter.get("status") or ""),
                "confidence": str(frontmatter.get("confidence") or ""),
            }
        )

        body = wiki_utils.content_after_frontmatter(text)
        for target in sorted(wiki_utils.extract_wikilinks(body)):
            add_edge(edges, seen_edges, source_id, target, "wikilink", rel_path)
        for target in as_list(frontmatter.get("source_ids")):
            add_edge(edges, seen_edges, source_id, target, "source", rel_path)
        for target in as_list(frontmatter.get("related_ids")):
            add_edge(edges, seen_edges, source_id, target, "related", rel_path)

        if frontmatter.get("type") == "source":
            raw_targets = as_list(frontmatter.get("raw_paths"))
            provenance = wiki_utils.extract_provenance(text)
            raw_targets.extend(as_list(provenance.get("raw_path")))
            for target in raw_targets:
                add_edge(edges, seen_edges, source_id, target, "raw", rel_path)

    nodes.sort(key=lambda node: str(node["id"]))
    edges.sort(key=lambda edge: (edge["type"], edge["source"], edge["target"], edge.get("path", "")))
    by_type = dict(sorted(Counter(str(node["type"]) for node in nodes).items()))
    return {
        "generated_at": wiki_utils.utc_now(),
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "by_type": by_type,
        },
    }


def graph_json(graph: dict[str, object]) -> str:
    return json.dumps(graph, indent=2, sort_keys=True) + "\n"


def markdown_report(graph: dict[str, object]) -> str:
    summary = graph["summary"]
    nodes = graph["nodes"]
    edges = graph["edges"]
    node_counts = Counter(str(node["type"]) for node in nodes)  # type: ignore[index]
    edge_counts = Counter(str(edge["type"]) for edge in edges)  # type: ignore[index]

    lines = [
        "# MuvyWiki Graph Report",
        "",
        f"- Generated at: {graph['generated_at']}",
        f"- Nodes: {summary['node_count']}",  # type: ignore[index]
        f"- Edges: {summary['edge_count']}",  # type: ignore[index]
        "",
        "## Node Types",
        "",
    ]
    if node_counts:
        lines.extend(f"- {node_type}: {count}" for node_type, count in sorted(node_counts.items()))
    else:
        lines.append("- none")
    lines.extend(["", "## Edge Types", ""])
    if edge_counts:
        lines.extend(f"- {edge_type}: {count}" for edge_type, count in sorted(edge_counts.items()))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def html_cell(value: object) -> str:
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return html.escape(str(value))


def html_artifact(graph: dict[str, object]) -> str:
    nodes = graph["nodes"]
    edges = graph["edges"]
    data = json.dumps(graph, indent=2, sort_keys=True).replace("</", "<\\/")
    escaped_data = html.escape(data)
    node_rows = "\n".join(
        "<tr>"
        f"<td>{html_cell(node['id'])}</td>"
        f"<td>{html_cell(node['title'])}</td>"
        f"<td>{html_cell(node['type'])}</td>"
        f"<td>{html_cell(node['path'])}</td>"
        f"<td>{html_cell(node['tags'])}</td>"
        f"<td>{html_cell(node['status'])}</td>"
        f"<td>{html_cell(node['confidence'])}</td>"
        "</tr>"
        for node in nodes  # type: ignore[union-attr]
    )
    edge_rows = "\n".join(
        "<tr>"
        f"<td>{html_cell(edge['source'])}</td>"
        f"<td>{html_cell(edge['target'])}</td>"
        f"<td>{html_cell(edge['type'])}</td>"
        f"<td>{html_cell(edge.get('path', ''))}</td>"
        "</tr>"
        for edge in edges  # type: ignore[union-attr]
    )
    summary = graph["summary"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MuvyWiki Graph</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; line-height: 1.4; }}
    table {{ border-collapse: collapse; margin: 1rem 0 2rem; width: 100%; }}
    th, td {{ border: 1px solid #d0d7de; padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
    code, pre {{ background: #f6f8fa; }}
    pre {{ overflow-x: auto; padding: 1rem; }}
  </style>
</head>
<body>
  <h1>MuvyWiki Graph</h1>
  <p>Generated at {html_cell(graph['generated_at'])}.</p>
  <ul>
    <li>Nodes: {html_cell(summary['node_count'])}</li>
    <li>Edges: {html_cell(summary['edge_count'])}</li>
  </ul>
  <h2>Nodes</h2>
  <table>
    <thead><tr><th>ID</th><th>Title</th><th>Type</th><th>Path</th><th>Tags</th><th>Status</th><th>Confidence</th></tr></thead>
    <tbody>{node_rows}</tbody>
  </table>
  <h2>Edges</h2>
  <table>
    <thead><tr><th>Source</th><th>Target</th><th>Type</th><th>Path</th></tr></thead>
    <tbody>{edge_rows}</tbody>
  </table>
  <h2>Data</h2>
  <script type="application/json" id="graph-data">{data}</script>
  <pre>{escaped_data}</pre>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    global ROOT
    parser = argparse.ArgumentParser(description="Build MuvyWiki graph artifacts.")
    wiki_utils.add_repo_root_argument(parser)
    parser.add_argument("--json", default="graph/graph.json", help="Graph JSON output path.")
    parser.add_argument("--html", default="graph/graph.html", help="Graph HTML output path.")
    parser.add_argument("--report", default="graph/graph-report.md", help="Graph report output path.")
    args = parser.parse_args(argv)

    try:
        ROOT = wiki_utils.resolve_repo_root(args.repo_root, DEFAULT_ROOT)
        json_path = resolve_output(args.json)
        html_path = resolve_output(args.html)
        report_path = resolve_output(args.report)
    except ValueError as exc:
        print(f"Invalid repository or output path: {exc}", file=sys.stderr)
        return 2

    graph = build_graph()
    try:
        wiki_utils.write_text(json_path, graph_json(graph))
        wiki_utils.write_text(html_path, html_artifact(graph))
        wiki_utils.write_text(report_path, markdown_report(graph))
    except OSError as exc:
        print(f"Failed to write graph artifacts: {exc}", file=sys.stderr)
        return 2

    written = ", ".join(wiki_utils.repo_relative(ROOT, path) for path in (json_path, html_path, report_path))
    print(f"Wrote {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
