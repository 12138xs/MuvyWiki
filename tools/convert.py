#!/usr/bin/env python3
"""Safe local text and Markdown conversion helper for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]
CONVERTED_ROOT = (ROOT / "raw" / "converted").resolve()
REMOTE_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ""}
MARKDOWN_SUFFIXES = {".md", ".markdown"}
MARKDOWN_HEADING_RE = re.compile(r"\A\s*#\s+\S")
ALLOWED_CONTROLS = {9, 10, 12, 13}


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def is_under_converted(output_path: str) -> bool:
    path = Path(output_path)
    if path.is_absolute():
        return False
    try:
        wiki_utils.safe_child_path(ROOT, output_path, CONVERTED_ROOT)
    except ValueError:
        return False
    return True


def repo_path(path: Path) -> str:
    return wiki_utils.repo_relative(ROOT, path)


def resolve_input(input_path: str) -> Path:
    path = Path(input_path)
    resolved = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def is_binary_like(text: str) -> bool:
    return any(unicodedata.category(char) == "Cc" and ord(char) not in ALLOWED_CONTROLS for char in text)


def convert_text(input_path: Path, text: str) -> str:
    normalized = normalize_line_endings(text)
    suffix = input_path.suffix.lower()
    if suffix in MARKDOWN_SUFFIXES or MARKDOWN_HEADING_RE.match(normalized):
        return normalized
    return f"# {input_path.stem}\n\n{normalized}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert local text or Markdown into raw/converted/.")
    parser.add_argument("input_path_or_url", help="Input source path or URL.")
    parser.add_argument("--out", required=True, help="Output path under raw/converted/.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable conversion details.")
    args = parser.parse_args(argv)

    if REMOTE_URL_RE.match(args.input_path_or_url):
        return fail("Remote URLs are not supported. Provide a local Markdown or text file.")

    try:
        output_path = wiki_utils.safe_child_path(ROOT, args.out, CONVERTED_ROOT)
    except ValueError as exc:
        return fail(f"Output path must be under raw/converted/. {exc}")

    try:
        input_path = resolve_input(args.input_path_or_url)
    except ValueError:
        return fail("Input path must stay inside the repository.")

    suffix = input_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return fail("Unsupported input type. Supported inputs are .md, .markdown, .txt, or extensionless UTF-8 text.")

    if not input_path.is_file():
        return fail("Input path does not exist or is not a file.")

    try:
        input_bytes = input_path.read_bytes()
        input_text = input_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return fail("Unsupported input type. Input must be UTF-8 text.")
    except OSError as exc:
        return fail(f"Could not read input: {exc}")

    if is_binary_like(input_text):
        return fail("Unsupported input type. Input appears to contain binary control characters.")

    output_text = convert_text(input_path, input_text)
    output_bytes = output_text.encode("utf-8")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(output_bytes)
    except OSError as exc:
        return fail(f"Could not write output: {exc}")

    if args.json:
        payload = {
            "status": "ok",
            "input_path": repo_path(input_path),
            "output_path": repo_path(output_path),
            "input_hash": wiki_utils.sha256_bytes(input_bytes),
            "output_hash": wiki_utils.sha256_bytes(output_bytes),
            "input_bytes": len(input_bytes),
            "output_bytes": len(output_bytes),
        }
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"Converted {repo_path(input_path)} -> {repo_path(output_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
