#!/usr/bin/env python3
"""Reserved semantic lint interface for MuvyWiki."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run semantic lint checks for MuvyWiki.")
    parser.add_argument("--report", default="graph/graph-report.md", help="Path for a future lint report.")
    parser.parse_args(argv)
    print("tools/lint.py is reserved for future semantic linting. Run tools/health.py for v1 structural checks.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
