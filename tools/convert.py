#!/usr/bin/env python3
"""Reserved source conversion interface for MuvyWiki."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONVERTED_ROOT = (ROOT / "raw" / "converted").resolve()


def is_under_converted(output_path: str) -> bool:
    path = Path(output_path)
    if path.is_absolute():
        return False
    try:
        output = (ROOT / path).resolve()
        if output == CONVERTED_ROOT:
            return False
        output.relative_to(CONVERTED_ROOT)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert future source artifacts into Markdown.")
    parser.add_argument("input_path_or_url", help="Input source path or URL.")
    parser.add_argument("--out", required=True, help="Output path under raw/converted/.")
    args = parser.parse_args(argv)
    if not is_under_converted(args.out):
        print("Output path must be under raw/converted/.", file=sys.stderr)
        return 2
    print("tools/convert.py is reserved for future conversion. Provide Markdown or pasted text for v1 ingest.")
    return 3


if __name__ == "__main__":
    sys.exit(main())
