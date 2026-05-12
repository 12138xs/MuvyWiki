#!/usr/bin/env python3
"""Reserved source conversion interface for MuvyWiki."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert future source artifacts into Markdown.")
    parser.add_argument("input_path_or_url", help="Input source path or URL.")
    parser.add_argument("--out", required=True, help="Output path under raw/converted/.")
    args = parser.parse_args(argv)
    if not args.out.startswith("raw/converted/"):
        print("Output path must be under raw/converted/.", file=sys.stderr)
        return 2
    print("tools/convert.py is reserved for future conversion. Provide Markdown or pasted text for v1 ingest.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
