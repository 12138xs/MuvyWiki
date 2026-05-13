#!/usr/bin/env python3
"""Structural health checks for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_PATHS = [
    ".gitignore",
    "README.md",
    "AGENTS.md",
    "raw/README.md",
    "raw/source-manifest.jsonl",
    "raw/originals",
    "raw/converted",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/overview.md",
    "wiki/sources",
    "wiki/concepts",
    "wiki/entities",
    "wiki/syntheses",
    "templates/overview.md",
    "templates/index-entry.md",
    "templates/log-entry.md",
    "templates/source.md",
    "templates/concept.md",
    "templates/entity.md",
    "templates/synthesis.md",
    "tools/health.py",
    "tools/lint.py",
    "tools/build_graph.py",
    "tools/convert.py",
    "graph/README.md",
]

INDEX_ENTRY_RE = re.compile(
    r"^- \[\[(?P<id>[^|\]]+)\|(?P<title>[^\]]+)\]\] "
    r"\(`(?P<path>[^`]+)`\) - type: (?P<type>[a-z]+) - updated: "
    r"(?P<date>\d{4}-\d{2}-\d{2}) - (?P<summary>.+)$"
)
LOG_HEADING_RE = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] (init|ingest|query|health|lint|graph|convert|batch) \| .+$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
SOURCE_PROVENANCE_KEYS = {
    "source_id",
    "raw_path",
    "content_hash",
    "source_url",
    "collected_at",
    "published_at",
    "converted_from",
    "converted_path",
    "converter",
    "converter_version",
}
REQUIRED_SCALAR_FRONTMATTER = {
    "canonical_id",
    "type",
    "title",
    "created",
    "last_updated",
    "status",
    "confidence",
}
REQUIRED_LIST_FRONTMATTER = {"tags", "aliases", "source_ids", "related_ids", "raw_paths"}
ALLOWED_TYPES = {"source", "concept", "entity", "synthesis", "overview"}
ALLOWED_STATUSES = {"seed", "active", "archived"}
ALLOWED_CONFIDENCES = {"low", "medium", "high"}
INDEX_SECTIONS_BY_TYPE = {
    "overview": "Overview",
    "source": "Sources",
    "concept": "Concepts",
    "entity": "Entities",
    "synthesis": "Syntheses",
}
REQUIRED_LOG_FIELDS = (
    "- Changed pages:",
    "- Raw paths:",
    "- Source IDs:",
    "- Unresolved issues:",
)


@dataclass
class Issue:
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "message": self.message}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_wiki_pages(root: Path) -> list[Path]:
    paths = []
    for folder in ("sources", "concepts", "entities", "syntheses"):
        base = root / "wiki" / folder
        if base.exists():
            paths.extend(sorted(base.glob("*.md")))
    overview = root / "wiki" / "overview.md"
    if overview.exists():
        paths.append(overview)
    return paths


def extract_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" in line and not line.startswith("  "):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"')
    return result


def strip_yaml_scalar(value: str) -> str:
    value = value.strip()
    if value in {"null", "~"}:
        return value
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_yaml_scalar(value: str) -> object:
    value = value.strip()
    if value in {"null", "~"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def frontmatter_body(text: str) -> str | None:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    return match.group("body")


def top_level_frontmatter_lines(body: str) -> dict[str, tuple[int, str]]:
    lines: dict[str, tuple[int, str]] = {}
    for line_number, line in enumerate(body.splitlines(), start=1):
        if not line.strip() or line.startswith(" "):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        lines[key.strip()] = (line_number, value.strip())
    return lines


def has_indented_list_items(body_lines: list[str], start_index: int) -> bool:
    for line in body_lines[start_index + 1:]:
        if not line.strip():
            continue
        if not line.startswith(" "):
            return False
        if re.match(r"^\s+-\s+.+$", line):
            return True
    return False


def is_yaml_list_field(body: str, key: str, value: str, line_number: int) -> bool:
    if value == "[]":
        return True
    if is_inline_yaml_list(value):
        return True
    if value:
        return False
    return has_indented_list_items(body.splitlines(), line_number - 1)


def is_inline_yaml_list(value: str) -> bool:
    if not value.startswith("[") or not value.endswith("]"):
        return False
    inner = value[1:-1].strip()
    if not inner:
        return True
    items = [item.strip() for item in inner.split(",")]
    return all(is_simple_yaml_list_item(item) for item in items)


def is_simple_yaml_list_item(item: str) -> bool:
    if not item:
        return False
    if len(item) >= 2 and item[0] == item[-1] and item[0] in {"'", '"'}:
        item = item[1:-1]
    return bool(item) and not any(char in item for char in "[]{}")


def extract_provenance(text: str) -> dict[str, object]:
    body = frontmatter_body(text)
    if body is None:
        return {}
    lines = body.splitlines()
    provenance: dict[str, object] = {}
    in_provenance = False
    for line in lines:
        if line == "provenance:":
            in_provenance = True
            continue
        if in_provenance and line and not line.startswith(" "):
            break
        if not in_provenance or not line.startswith("  ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        provenance[key.strip()] = parse_yaml_scalar(value)
    return provenance


def content_after_frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text
    return text[match.end():].strip()


def check_frontmatter_shape(rel: str, text: str, issues: list[Issue]) -> None:
    body = frontmatter_body(text)
    if body is None:
        return
    lines = top_level_frontmatter_lines(body)
    for key in sorted(REQUIRED_SCALAR_FRONTMATTER):
        if key not in lines:
            issues.append(Issue(rel, f"missing {key}"))
            continue
        _, value = lines[key]
        if not value or value == "[]" or value.startswith("[") or value.startswith("{"):
            issues.append(Issue(rel, f"frontmatter {key} must be a non-empty scalar"))
    for key in sorted(REQUIRED_LIST_FRONTMATTER):
        if key not in lines:
            issues.append(Issue(rel, f"missing {key}"))
            continue
        line_number, value = lines[key]
        if not is_yaml_list_field(body, key, value, line_number):
            issues.append(Issue(rel, f"frontmatter {key} must be a YAML list"))

    allowed_fields = (
        ("type", ALLOWED_TYPES),
        ("status", ALLOWED_STATUSES),
        ("confidence", ALLOWED_CONFIDENCES),
    )
    for key, allowed_values in allowed_fields:
        if key not in lines:
            continue
        value = strip_yaml_scalar(lines[key][1])
        if value and value not in allowed_values:
            allowed = ", ".join(sorted(allowed_values))
            issues.append(Issue(rel, f"frontmatter {key} must be one of: {allowed}"))


def load_manifest(root: Path, issues: list[Issue]) -> dict[str, dict[str, object]]:
    manifest_path = root / "raw" / "source-manifest.jsonl"
    entries: dict[str, dict[str, object]] = {}
    hashes: dict[str, str] = {}
    if not manifest_path.exists():
        return entries
    for line_number, line in enumerate(read_text(manifest_path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(Issue("raw/source-manifest.jsonl", f"invalid JSON on line {line_number}: {exc.msg}"))
            continue
        source_id = entry.get("source_id")
        content_hash = entry.get("content_hash")
        raw_path = entry.get("raw_path")
        if not isinstance(source_id, str) or not source_id:
            issues.append(Issue("raw/source-manifest.jsonl", f"missing source_id on line {line_number}"))
            continue
        if source_id in entries:
            issues.append(Issue("raw/source-manifest.jsonl", f"duplicate source_id: {source_id}"))
        entries[source_id] = entry
        if not isinstance(raw_path, str) or not raw_path:
            issues.append(Issue("raw/source-manifest.jsonl", f"missing raw_path for {source_id}"))
        if not isinstance(content_hash, str) or not content_hash.startswith("sha256:"):
            issues.append(Issue("raw/source-manifest.jsonl", f"invalid content_hash for {source_id}"))
        elif content_hash in hashes:
            issues.append(Issue("raw/source-manifest.jsonl", f"duplicate content_hash for {source_id} and {hashes[content_hash]}"))
        else:
            hashes[content_hash] = source_id
    return entries


def check_required_paths(root: Path, issues: list[Issue]) -> None:
    for rel in REQUIRED_PATHS:
        if not (root / rel).exists():
            issues.append(Issue(rel, "missing required path"))


def check_wiki_pages(root: Path, issues: list[Issue]) -> dict[str, dict[str, str]]:
    seen_canonical_ids: set[str] = set()
    canonical_pages: dict[str, dict[str, str]] = {}
    aliases: dict[str, str] = {}
    for path in collect_wiki_pages(root):
        rel = path.relative_to(root).as_posix()
        text = read_text(path)
        frontmatter = extract_frontmatter(text)
        if not frontmatter:
            issues.append(Issue(rel, "missing frontmatter"))
            continue
        check_frontmatter_shape(rel, text, issues)
        canonical_id = frontmatter.get("canonical_id")
        if not canonical_id:
            issues.append(Issue(rel, "missing canonical_id"))
        else:
            if canonical_id in seen_canonical_ids:
                issues.append(Issue(rel, f"duplicate canonical_id: {canonical_id}"))
            seen_canonical_ids.add(canonical_id)
            if canonical_id != path.stem:
                issues.append(Issue(rel, "canonical_id must match file stem"))
            else:
                canonical_pages.setdefault(canonical_id, {"path": rel, "type": frontmatter.get("type", "")})
        page_type = frontmatter.get("type")
        if not page_type:
            issues.append(Issue(rel, "missing type"))
        elif canonical_id in canonical_pages and canonical_pages[canonical_id]["path"] == rel:
            canonical_pages[canonical_id]["type"] = page_type
        if not content_after_frontmatter(text):
            issues.append(Issue(rel, "page appears empty beyond frontmatter"))
        alias_match = re.search(r"aliases:\n((?:  - .+\n)+)", text)
        if alias_match and canonical_id:
            for alias_line in alias_match.group(1).splitlines():
                alias = alias_line.replace("-", "", 1).strip().strip('"')
                owner = aliases.setdefault(alias, canonical_id)
                if owner != canonical_id:
                    issues.append(Issue(rel, f"alias collision: {alias}"))
    return canonical_pages


def check_source_provenance(root: Path, manifest_entries: dict[str, dict[str, object]], issues: list[Issue]) -> None:
    source_dir = root / "wiki" / "sources"
    if not source_dir.exists():
        return
    for path in sorted(source_dir.glob("*.md")):
        rel = path.relative_to(root).as_posix()
        text = read_text(path)
        frontmatter_match = FRONTMATTER_RE.match(text)
        frontmatter = extract_frontmatter(text)
        canonical_id = frontmatter.get("canonical_id")
        if not frontmatter_match:
            continue
        frontmatter_body = frontmatter_match.group("body")
        missing_keys = [key for key in SOURCE_PROVENANCE_KEYS if not re.search(rf"^\s{{2}}{re.escape(key)}:", frontmatter_body, re.MULTILINE)]
        for key in sorted(missing_keys):
            issues.append(Issue(rel, f"missing provenance field: {key}"))
        if canonical_id and canonical_id not in manifest_entries:
            issues.append(Issue(rel, f"missing manifest entry for source_id: {canonical_id}"))
        if canonical_id and canonical_id in manifest_entries:
            entry = manifest_entries[canonical_id]
            provenance = extract_provenance(text)
            for key in sorted(SOURCE_PROVENANCE_KEYS):
                provenance_value = provenance.get(key)
                manifest_value = entry.get(key)
                if provenance_value != manifest_value:
                    issues.append(Issue(rel, f"provenance {key} does not match manifest"))
            raw_path = entry.get("raw_path")
            if isinstance(raw_path, str) and raw_path and not (root / raw_path).exists():
                issues.append(Issue(rel, f"manifest raw_path does not exist: {raw_path}"))
            manifest_converted_path = entry.get("converted_path")
            if (
                isinstance(manifest_converted_path, str)
                and manifest_converted_path
                and not (root / manifest_converted_path).exists()
            ):
                issues.append(Issue(rel, f"manifest converted_path does not exist: {manifest_converted_path}"))
            provenance_converted_path = provenance.get("converted_path")
            if (
                isinstance(provenance_converted_path, str)
                and provenance_converted_path
                and provenance_converted_path != manifest_converted_path
                and not (root / provenance_converted_path).exists()
            ):
                issues.append(Issue(rel, f"provenance converted_path does not exist: {provenance_converted_path}"))


def check_index(root: Path, canonical_pages: dict[str, dict[str, str]], issues: list[Issue]) -> None:
    index_path = root / "wiki" / "index.md"
    if not index_path.exists():
        return
    text = read_text(index_path)
    indexed_ids: dict[str, int] = {}
    current_section: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current_section = line.removeprefix("## ").strip()
            continue
        if not line.startswith("- [["):
            continue
        match = INDEX_ENTRY_RE.match(line)
        if not match:
            issues.append(Issue("wiki/index.md", f"invalid index entry: {line}"))
            continue
        indexed_id = match.group("id")
        indexed_ids[indexed_id] = indexed_ids.get(indexed_id, 0) + 1
        expected_page = canonical_pages.get(indexed_id)
        if expected_page is None:
            issues.append(Issue("wiki/index.md", f"index entry for unknown page id: {indexed_id}"))
            expected_path = None
            expected_type = None
        else:
            expected_path = expected_page["path"]
            expected_type = expected_page["type"]
            expected_section = INDEX_SECTIONS_BY_TYPE.get(expected_type)
            if expected_section and current_section != expected_section:
                issues.append(Issue("wiki/index.md", f"index entry for {indexed_id} must be under ## {expected_section}"))
            indexed_type = match.group("type")
            if expected_type and indexed_type != expected_type:
                issues.append(Issue("wiki/index.md", f"index entry for {indexed_id} has type {indexed_type}, expected {expected_type}"))
        listed_path = root / match.group("path")
        if not listed_path.exists():
            issues.append(Issue("wiki/index.md", f"indexed path does not exist: {match.group('path')}"))
        elif expected_path is not None and match.group("path") != expected_path:
            issues.append(
                Issue(
                    "wiki/index.md",
                    f"index entry for {indexed_id} points to {match.group('path')}, expected {expected_path}",
                )
            )
    for indexed_id, count in sorted(indexed_ids.items()):
        if count > 1:
            issues.append(Issue("wiki/index.md", f"duplicate index entry for {indexed_id}"))
    for canonical_id in sorted(canonical_pages):
        if canonical_id not in indexed_ids:
            issues.append(Issue("wiki/index.md", f"missing index entry for {canonical_id}"))


def check_log(root: Path, issues: list[Issue]) -> None:
    log_path = root / "wiki" / "log.md"
    if not log_path.exists():
        return
    headings = [line for line in read_text(log_path).splitlines() if line.startswith("## ")]
    if not headings:
        issues.append(Issue("wiki/log.md", "missing log entry"))
    for heading in headings:
        if not LOG_HEADING_RE.match(heading):
            issues.append(Issue("wiki/log.md", f"invalid log heading: {heading}"))
    for body in log_entry_bodies(read_text(log_path)):
        for required_field in REQUIRED_LOG_FIELDS:
            if not any(line.startswith(required_field) for line in body):
                issues.append(Issue("wiki/log.md", f"log entry missing required field: {required_field}"))


def log_entry_bodies(text: str) -> list[list[str]]:
    bodies: list[list[str]] = []
    current_body: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            if current_body is not None:
                bodies.append(current_body)
            current_body = []
            continue
        if current_body is not None:
            current_body.append(line)
    if current_body is not None:
        bodies.append(current_body)
    return bodies


def check_wikilinks(root: Path, canonical_ids: set[str], issues: list[Issue]) -> None:
    for path in collect_wiki_pages(root):
        rel = path.relative_to(root).as_posix()
        for target in WIKILINK_RE.findall(read_text(path)):
            if target not in canonical_ids:
                issues.append(Issue(rel, f"wikilink target not found: {target}"))


def run(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    check_required_paths(root, issues)
    manifest_entries = load_manifest(root, issues)
    canonical_pages = check_wiki_pages(root, issues)
    canonical_ids = set(canonical_pages)
    check_source_provenance(root, manifest_entries, issues)
    check_index(root, canonical_pages, issues)
    check_log(root, issues)
    check_wikilinks(root, canonical_ids, issues)
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run structural health checks for MuvyWiki.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable health output.")
    args = parser.parse_args(argv)

    issues = run(Path.cwd())
    status = "ok" if not issues else "issues"
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if args.json:
        print(json.dumps({"status": status, "issues": [issue.as_dict() for issue in issues], "checked_at": checked_at}, indent=2))
    else:
        print(f"MuvyWiki health: {status}")
        for issue in issues:
            print(f"- {issue.path}: {issue.message}")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
