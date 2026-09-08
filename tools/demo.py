#!/usr/bin/env python3
"""Run a non-mutating end-to-end MuvyWiki demonstration."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "ingest"
QUERY = "retrieval augmented generation"


class DemoError(Exception):
    """Raised when an end-to-end demo step fails validation."""


def run_tool(tool: str, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ROOT / "tools" / tool),
        "--repo-root",
        str(repo_root),
        *args,
    ]
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require_success(step: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout).strip() or f"exit code {result.returncode}"
    raise DemoError(f"{step} failed: {detail}")


def parse_json(step: str, value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DemoError(f"{step} returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DemoError(f"{step} returned a non-object JSON payload")
    return payload


def run_demo() -> dict[str, Any]:
    if not FIXTURE.is_dir():
        raise DemoError("fixture is missing: examples/ingest")

    with tempfile.TemporaryDirectory(prefix="muvywiki-demo-") as temp_dir:
        repo_root = Path(temp_dir) / "ingest"
        shutil.copytree(FIXTURE, repo_root, ignore=shutil.ignore_patterns("__pycache__"))

        health = run_tool("health.py", repo_root, "--json")
        require_success("health", health)
        health_payload = parse_json("health", health.stdout)
        if health_payload.get("status") != "ok":
            raise DemoError("health did not report status=ok")

        lint = run_tool("lint.py", repo_root, "--json")
        require_success("lint", lint)
        lint_payload = parse_json("lint", lint.stdout)
        if lint_payload.get("status") != "ok":
            raise DemoError("lint did not report status=ok")

        query = run_tool("query.py", repo_root, QUERY, "--json")
        require_success("query", query)
        query_payload = parse_json("query", query.stdout)
        matches = query_payload.get("matches")
        if not isinstance(matches, list) or not matches:
            raise DemoError("query returned no matches")

        graph = run_tool("build_graph.py", repo_root)
        require_success("graph", graph)
        graph_path = repo_root / "graph" / "graph.json"
        graph_payload = parse_json("graph", graph_path.read_text(encoding="utf-8"))
        summary = graph_payload.get("summary")
        if not isinstance(summary, dict) or int(summary.get("node_count", 0)) < 1:
            raise DemoError("graph contains no nodes")

        return {
            "status": "ok",
            "fixture": "examples/ingest",
            "query": QUERY,
            "query_match_count": len(matches),
            "graph_node_count": int(summary["node_count"]),
            "graph_edge_count": int(summary.get("edge_count", 0)),
            "steps": ["health", "lint", "query", "graph"],
            "workspace_modified": False,
        }


def text_output(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "MuvyWiki demo: ok",
            f"Fixture: {payload['fixture']}",
            "Steps: " + " -> ".join(payload["steps"]),
            f"Query matches: {payload['query_match_count']}",
            f"Graph: {payload['graph_node_count']} nodes, {payload['graph_edge_count']} edges",
            "Workspace modified: no",
        ]
    ) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the bundled MuvyWiki fixture in a temporary directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable demo output.")
    args = parser.parse_args(argv)

    try:
        payload = run_demo()
    except (DemoError, OSError, ValueError) as exc:
        print(f"MuvyWiki demo failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(text_output(payload), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
