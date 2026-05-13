#!/usr/bin/env python3
"""Reserved graph generation interface for MuvyWiki."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build future MuvyWiki graph artifacts.")
    parser.add_argument("--json", default="graph/graph.json", help="Future graph JSON output path.")
    parser.add_argument("--html", default="graph/graph.html", help="Future graph HTML output path.")
    parser.add_argument("--report", default="graph/graph-report.md", help="Future graph report output path.")
    parser.parse_args(argv)
    print("tools/build_graph.py is reserved for future graph generation. Run tools/health.py for v1 structural checks.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
