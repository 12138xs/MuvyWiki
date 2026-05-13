#!/usr/bin/env python3
"""Shared utilities for MuvyWiki command-line tools."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
SECTION_RE = re.compile(r"^## (?P<title>.+?)\s*$", re.MULTILINE)
NONE_MARKERS = {"none", "- none", "no supporting sources yet.", "no synthesis pages yet."}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def safe_child_path(root: Path, rel_path: str, required_parent: Path | None = None) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise ValueError("path must be relative")
    root_resolved = root.resolve()
    output = root / candidate
    output_resolved = output.resolve()
    parent = required_parent.resolve() if required_parent is not None else root_resolved
    try:
        output_resolved.relative_to(parent)
    except ValueError as exc:
        parent_label = parent.relative_to(root_resolved).as_posix() if parent != root_resolved else "."
        raise ValueError(f"path must stay under {parent_label}") from exc
    if output_resolved == parent:
        raise ValueError("path must point to a file")
    return output


def content_after_frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    return text[match.end():] if match else text


def frontmatter_body(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    return match.group("body") if match else ""


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"null", "~"}:
        return None
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(item.strip()) for item in inner.split(",")]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, Any]:
    body = frontmatter_body(text)
    if not body:
        return {}
    lines = body.splitlines()
    result: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.startswith(" "):
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            result[key] = parse_scalar(raw_value)
            index += 1
            continue
        values: list[Any] = []
        nested: dict[str, Any] = {}
        index += 1
        while index < len(lines) and lines[index].startswith("  "):
            child = lines[index].strip()
            if child.startswith("- "):
                values.append(parse_scalar(child[2:].strip()))
            elif ":" in child:
                child_key, child_value = child.split(":", 1)
                nested[child_key.strip()] = parse_scalar(child_value.strip())
            index += 1
        result[key] = values if values else nested
    return result


def extract_provenance(text: str) -> dict[str, Any]:
    provenance = parse_frontmatter(text).get("provenance")
    return provenance if isinstance(provenance, dict) else {}


def extract_wikilinks(text: str) -> set[str]:
    return set(WIKILINK_RE.findall(text))


def section_bodies(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[match.group("title").strip()] = text[start:end].strip()
    return sections


def has_useful_text(text: str) -> bool:
    stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not stripped_lines:
        return False
    lowered = "\n".join(stripped_lines).lower()
    return lowered not in NONE_MARKERS


def collect_wiki_pages(root: Path) -> list[Path]:
    pages: list[Path] = []
    for folder in ("sources", "concepts", "entities", "syntheses"):
        base = root / "wiki" / folder
        if base.exists():
            pages.extend(sorted(base.glob("*.md")))
    overview = root / "wiki" / "overview.md"
    if overview.exists():
        pages.append(overview)
    return pages


def repo_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()
