#!/usr/bin/env python3
"""Shared utilities for MuvyWiki command-line tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
SECTION_RE = re.compile(r"^## (?P<title>.+?)\s*$", re.MULTILINE)
NONE_MARKERS = {"none", "- none", "no supporting sources yet.", "no synthesis pages yet."}
KEBAB_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REMOTE_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SUPPORTED_TEXT_SUFFIXES = {"", ".md", ".markdown", ".txt"}


def resolve_repo_root(value: str | None, default: Path) -> Path:
    """Resolve and validate the repository root selected by a CLI."""
    candidate = default if value is None else Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"repository root could not be resolved: {candidate}") from exc
    if not resolved.is_dir():
        raise ValueError(f"repository root is not a directory: {resolved}")
    return resolved


def add_repo_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        help="Operate on PATH as the MuvyWiki repository root.",
    )


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


def is_remote_url(value: str) -> bool:
    return bool(REMOTE_URL_RE.match(value))


def is_sha256_hash(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def is_iso_date(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not ISO_DATE_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def is_supported_text_suffix(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES


def is_binary_like_text(text: str) -> bool:
    allowed_controls = {"\t", "\n", "\f", "\r"}
    return any(unicodedata.category(char) == "Cc" and char not in allowed_controls for char in text)


def slugify_source_id(value: str, fallback_hash: str | None = None) -> str:
    stem = re.sub(r"\.[^.]+$", "", Path(value).name)
    ascii_text = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    if slug:
        return slug
    if is_sha256_hash(fallback_hash):
        return f"source-{fallback_hash.removeprefix('sha256:')[:8]}"
    return "source-unknown"


def _normalized_relative_parts(path: Path) -> tuple[str, ...]:
    parts: list[str] = []
    for part in path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError("path must stay under .")
            parts.pop()
            continue
        parts.append(part)
    return tuple(parts)


def _repo_relative_parts(root: Path, path: Path) -> tuple[str, ...]:
    if not path.is_absolute():
        return _normalized_relative_parts(path)
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError as exc:
        raise ValueError("required parent must stay under repository root") from exc
    return _normalized_relative_parts(relative)


def _reject_symlinked_parents(root: Path, parts: tuple[str, ...]) -> None:
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"path parent must not be a symlink: {current.relative_to(root).as_posix()}")


def safe_child_path(root: Path, rel_path: str, required_parent: Path | None = None) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute():
        raise ValueError("path must be relative")
    output_parts = _normalized_relative_parts(candidate)
    parent_parts = _repo_relative_parts(root, required_parent) if required_parent is not None else ()
    if not output_parts:
        raise ValueError("path must point to a file")
    if output_parts == parent_parts:
        raise ValueError("path must point to a file")
    if output_parts[: len(parent_parts)] != parent_parts:
        parent_label = Path(*parent_parts).as_posix() if parent_parts else "."
        raise ValueError(f"path must stay under {parent_label}")
    _reject_symlinked_parents(root, output_parts[:-1])
    output_path = root.joinpath(*output_parts)
    if output_path.is_symlink():
        raise ValueError(f"path must not be a symlink: {output_path.relative_to(root).as_posix()}")
    return output_path


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
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return json.loads(value)
    if len(value) >= 2 and value[0] == value[-1] == "'":
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


@dataclass(frozen=True)
class WikiPage:
    path: Path
    rel_path: str
    id: str
    type: str
    title: str
    tags: list[str]
    aliases: list[str]
    source_ids: list[str]
    related_ids: list[str]
    raw_paths: list[str]
    text: str
    body: str
    sections: dict[str, str]
    frontmatter: dict[str, Any]


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [str(value)]


def page_id(frontmatter: dict[str, object], path: Path) -> str:
    canonical_id = frontmatter.get("canonical_id")
    return str(canonical_id) if canonical_id else path.stem


def page_title(frontmatter: dict[str, object], text: str, fallback: str) -> str:
    title = frontmatter.get("title")
    if title:
        return str(title)
    for line in content_after_frontmatter(text).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_wiki_pages(root: Path) -> list[WikiPage]:
    pages: list[WikiPage] = []
    for path in collect_wiki_pages(root):
        text = read_text(path)
        frontmatter = parse_frontmatter(text)
        body = content_after_frontmatter(text)
        page_identifier = page_id(frontmatter, path)
        pages.append(
            WikiPage(
                path=path,
                rel_path=repo_relative(root, path),
                id=page_identifier,
                type=str(frontmatter.get("type") or ""),
                title=page_title(frontmatter, text, page_identifier),
                tags=as_list(frontmatter.get("tags")),
                aliases=as_list(frontmatter.get("aliases")),
                source_ids=as_list(frontmatter.get("source_ids")),
                related_ids=as_list(frontmatter.get("related_ids")),
                raw_paths=as_list(frontmatter.get("raw_paths")),
                text=text,
                body=body,
                sections=section_bodies(body),
                frontmatter=frontmatter,
            )
        )
    return pages


def canonical_page_map(root: Path) -> dict[str, WikiPage]:
    pages: dict[str, WikiPage] = {}
    for page in load_wiki_pages(root):
        existing = pages.get(page.id)
        if existing is not None:
            raise ValueError(
                f"duplicate canonical_id {page.id!r}: {existing.rel_path} and {page.rel_path}"
            )
        pages[page.id] = page
    return pages


def is_kebab_id(value: str) -> bool:
    return bool(KEBAB_ID_RE.fullmatch(value))


def yaml_list(values: list[str]) -> list[str]:
    if not values:
        return ["[]"]
    return [f"  - {json.dumps(value)}" for value in values]


def bounded_excerpt(text: str, terms: set[str], limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    lowered = normalized.lower()
    starts = [lowered.find(term.lower()) for term in terms if term and lowered.find(term.lower()) >= 0]
    if starts:
        center = min(starts)
        start = max(0, center - limit // 3)
    else:
        start = 0
    excerpt = normalized[start : start + limit].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if start + limit < len(normalized):
        excerpt = excerpt.rstrip() + "..."
    return excerpt


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
