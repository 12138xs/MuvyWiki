#!/usr/bin/env python3
"""Read-only ingest preflight helper for MuvyWiki.

The tool does not modify raw or wiki content; it writes only when an explicit
--report path under graph/ is provided.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "raw/originals"
CONVERTED_ROOT = ROOT / "raw/converted"
GRAPH_ROOT = ROOT / "graph"
MANIFEST_PATH = ROOT / "raw/source-manifest.jsonl"
SOURCE_KINDS = {
    "generic": "templates/source.md",
    "journal-entry": "templates/sources/journal-entry.md",
    "meeting-notes": "templates/sources/meeting-notes.md",
    "project-readme": "templates/sources/project-readme.md",
    "technical-article": "templates/sources/technical-article.md",
    "technical-paper": "templates/sources/technical-paper.md",
}
REQUIRED_MANIFEST_KEYS = {
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


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def repo_path(path: Path) -> str:
    return wiki_utils.repo_relative(ROOT, path)


def resolve_input(value: str) -> Path:
    return wiki_utils.safe_child_path(ROOT, value)


def classify_path(path: Path) -> str:
    rel_path = repo_path(path)
    if rel_path.startswith("raw/originals/"):
        return "raw-original"
    if rel_path.startswith("raw/converted/"):
        return "raw-converted"
    if path.suffix.lower() in {".md", ".markdown"}:
        return "local-markdown"
    return "local-text"


def recommend_source_kind(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit

    name = path.name.lower()
    if any(token in name for token in ("paper", "arxiv", "preprint")):
        return "technical-paper"
    if "readme" in name:
        return "project-readme"
    if any(token in name for token in ("meeting", "call", "notes")):
        return "meeting-notes"
    if any(token in name for token in ("journal", "diary")):
        return "journal-entry"
    if re.search(r"\b\d{4}[-_]\d{2}[-_]\d{2}\b", name):
        return "journal-entry"
    return "technical-article"


def load_manifest_entries() -> tuple[list[dict[str, Any]], list[str]]:
    try:
        lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"manifest unreadable: {exc}"]

    entries: list[dict[str, Any]] = []
    issues: list[str] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    seen_raw_paths: set[str] = set()

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(f"invalid manifest JSON on line {line_number}: {exc.msg}")
            continue
        if not isinstance(entry, dict):
            issues.append(f"manifest line {line_number} is not an object")
            continue

        missing = sorted(REQUIRED_MANIFEST_KEYS.difference(entry))
        if missing:
            issues.append(f"manifest line {line_number} missing required keys: {', '.join(missing)}")

        source_id = entry.get("source_id")
        if not isinstance(source_id, str) or not wiki_utils.is_kebab_id(source_id):
            issues.append(f"manifest line {line_number} has invalid source_id")
        elif source_id in seen_ids:
            issues.append(f"duplicate manifest source_id: {source_id}")
        else:
            seen_ids.add(source_id)

        content_hash = entry.get("content_hash")
        if not wiki_utils.is_sha256_hash(content_hash):
            issues.append(f"manifest line {line_number} has invalid content_hash")
        elif str(content_hash) in seen_hashes:
            issues.append(f"duplicate manifest content_hash: {content_hash}")
        else:
            seen_hashes.add(str(content_hash))

        raw_path = entry.get("raw_path")
        if not isinstance(raw_path, str) or not raw_path:
            issues.append(f"manifest line {line_number} has invalid raw_path")
        elif raw_path in seen_raw_paths:
            issues.append(f"duplicate manifest raw_path: {raw_path}")
        else:
            seen_raw_paths.add(raw_path)

        entries.append(entry)

    return entries, issues


def manifest_match_by_id_or_hash(
    entries: list[dict[str, Any]],
    source_id: str,
    content_hash: str,
) -> dict[str, Any] | None:
    for entry in entries:
        if entry.get("source_id") == source_id or entry.get("content_hash") == content_hash:
            return entry
    return None


def manifest_match_by_converted_path(entries: list[dict[str, Any]], converted_path: str) -> dict[str, Any] | None:
    for entry in entries:
        if entry.get("converted_path") == converted_path:
            return entry
    return None


def existing_wiki_ids() -> tuple[set[str], list[str]]:
    try:
        return set(wiki_utils.canonical_page_map(ROOT)), []
    except ValueError as exc:
        return set(), [f"wiki canonical IDs are ambiguous: {exc}"]


def blocked_item(value: str, input_kind: str, message: str, exit_code: int) -> tuple[dict[str, Any], int]:
    return {
        "status": "blocked",
        "input": value,
        "input_kind": input_kind,
        "source_id": None,
        "source_id_origin": None,
        "source_kind": None,
        "template_path": None,
        "content_hash": None,
        "input_bytes": 0,
        "raw_path": None,
        "converted_path": None,
        "needs_raw_original": False,
        "duplicate": False,
        "manifest_match": None,
        "wiki_source_path": None,
        "warnings": [message],
        "next_steps": ["Provide a supported local Markdown/text artifact."],
        "exit_code": exit_code,
    }, exit_code


def prepare_one(
    value: str,
    args: argparse.Namespace,
    entries: list[dict[str, Any]],
    manifest_issues: list[str],
    wiki_ids: set[str],
    wiki_id_issues: list[str],
) -> tuple[dict[str, Any], int]:
    if wiki_utils.is_remote_url(value):
        return blocked_item(
            value,
            "remote-url",
            "Remote URLs are ingest intent only in v1. Provide pasted text, a local Markdown/text file, or a converted Markdown artifact.",
            2,
        )

    try:
        path = resolve_input(value)
    except (OSError, ValueError) as exc:
        return blocked_item(value, "unsupported", f"Input path is unsafe or outside the repository: {exc}", 2)

    if not path.exists():
        return blocked_item(value, "unsupported", "Input path does not exist.", 2)
    if path.is_dir():
        return blocked_item(value, "unsupported", "Directories are not supported. Provide Markdown/text files.", 2)
    if path.is_symlink():
        return blocked_item(value, "unsupported", "Input must not be a symlink.", 2)
    if not path.is_file():
        return blocked_item(value, "unsupported", "Input must be a regular file.", 2)
    if not wiki_utils.is_supported_text_suffix(path):
        return blocked_item(
            value,
            "unsupported",
            "Unsupported input type. Supported inputs are .md, .markdown, .txt, or extensionless UTF-8 text.",
            2,
        )

    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return blocked_item(value, "unsupported", "Unsupported input type. Input must be UTF-8 text.", 2)
    except OSError as exc:
        return blocked_item(value, "unsupported", f"Could not read input: {exc}", 2)

    if wiki_utils.is_binary_like_text(text):
        return blocked_item(
            value,
            "unsupported",
            "Unsupported input type. Input appears to contain binary control characters.",
            2,
        )

    content_hash = wiki_utils.sha256_bytes(data)
    source_id = args.source_id or wiki_utils.slugify_source_id(path.name, content_hash)
    source_id_origin = "provided" if args.source_id else "suggested"
    input_kind = classify_path(path)
    source_kind = recommend_source_kind(path, args.kind)
    template_path = SOURCE_KINDS[source_kind]
    rel_path = repo_path(path)
    wiki_source_path = f"wiki/sources/{source_id}.md"
    raw_path = rel_path if input_kind == "raw-original" else None
    converted_path = rel_path if input_kind == "raw-converted" else None
    needs_raw_original = False
    warnings = list(manifest_issues) + list(wiki_id_issues)
    status = "blocked" if warnings else "ready"
    exit_code = 1 if warnings else 0

    manifest_match = manifest_match_by_id_or_hash(entries, source_id, content_hash)
    converted_match = manifest_match_by_converted_path(entries, converted_path) if converted_path else None
    duplicate = manifest_match is not None
    if manifest_match is not None:
        status = "blocked"
        exit_code = max(exit_code, 1)
        warnings.append("Duplicate source_id or content_hash found in raw/source-manifest.jsonl.")

    if input_kind == "raw-converted":
        provenance_match = converted_match or manifest_match
        raw_path_value = provenance_match.get("raw_path") if provenance_match else None
        raw_path = raw_path_value if isinstance(raw_path_value, str) else None
        needs_raw_original = raw_path is None
        if needs_raw_original:
            if status == "ready":
                status = "issues"
            exit_code = max(exit_code, 1)
            warnings.append("Converted artifact has no known raw original in the manifest.")

    if (ROOT / wiki_source_path).exists() or source_id in wiki_ids:
        status = "blocked"
        exit_code = max(exit_code, 1)
        warnings.append("Suggested source_id already exists in wiki pages.")

    item = {
        "status": status,
        "input": rel_path,
        "input_kind": input_kind,
        "source_id": source_id,
        "source_id_origin": source_id_origin,
        "source_kind": source_kind,
        "template_path": template_path,
        "content_hash": content_hash,
        "input_bytes": len(data),
        "raw_path": raw_path,
        "converted_path": converted_path,
        "needs_raw_original": needs_raw_original,
        "duplicate": duplicate,
        "manifest_match": manifest_match,
        "wiki_source_path": wiki_source_path,
        "warnings": warnings,
        "next_steps": [
            "Read wiki/index.md and wiki/overview.md.",
            "Perform agent-led extraction and page updates.",
            "Use tools/manifest.py add after the raw artifact and source_id are final.",
            "Run python tools/health.py after ingest.",
        ],
        "exit_code": exit_code,
    }
    return item, exit_code


def top_status(items: list[dict[str, Any]]) -> str:
    if any(item["status"] == "blocked" for item in items):
        return "blocked"
    if any(item["status"] == "issues" for item in items):
        return "issues"
    return "ready"


def exit_code_for_items(items: list[dict[str, Any]]) -> int:
    if any(item.get("exit_code") == 2 for item in items):
        return 2
    if any(item["status"] in {"blocked", "issues"} for item in items):
        return 1
    return 0


def render_text(payload: dict[str, Any]) -> None:
    print(f"MuvyWiki ingest prep: {len(payload['items'])} item(s)")
    for index, item in enumerate(payload["items"], start=1):
        print()
        print(f"{index}. {item['input']}")
        print(f"   status: {item['status']}")
        print(f"   source_id: {item['source_id']}")
        print(f"   source_kind: {item['source_kind']}")
        print(f"   template: {item['template_path']}")
        print(f"   content_hash: {item['content_hash']}")
        print(f"   duplicate: {'yes' if item['duplicate'] else 'no'}")
        if item["warnings"]:
            for warning in item["warnings"]:
                print(f"   warning: {warning}")
        else:
            print("   next: run agent-led ingest, then update manifest/index/log and health-check")


def write_report(payload: dict[str, Any], report_path: str) -> None:
    path = wiki_utils.safe_child_path(ROOT, report_path, GRAPH_ROOT)
    lines = [
        "# MuvyWiki Ingest Prep Report",
        "",
        f"- Status: {payload['status']}",
        f"- Generated at: {payload['generated_at']}",
        "",
        "## Items",
    ]
    for item in payload["items"]:
        lines.extend(
            [
                "",
                f"### {item['input']}",
                "",
                f"- Status: {item['status']}",
                f"- Source ID: {item['source_id']}",
                f"- Source kind: {item['source_kind']}",
                f"- Template: {item['template_path']}",
                f"- Content hash: {item['content_hash']}",
                f"- Duplicate: {'yes' if item['duplicate'] else 'no'}",
            ]
        )
        for warning in item["warnings"]:
            lines.append(f"- Warning: {warning}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare local sources for agent-led MuvyWiki ingest. Read-only except "
            "for an explicit --report path under graph/."
        )
    )
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--kind", choices=sorted(SOURCE_KINDS))
    parser.add_argument("--source-id")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args(argv)

    if args.source_id and len(args.inputs) != 1:
        return fail("--source-id can only be used with a single input.")
    if args.source_id and not wiki_utils.is_kebab_id(args.source_id):
        return fail("--source-id must be kebab-case.")

    entries, manifest_issues = load_manifest_entries()
    wiki_ids, wiki_id_issues = existing_wiki_ids()
    items = [
        prepare_one(value, args, entries, manifest_issues, wiki_ids, wiki_id_issues)[0]
        for value in args.inputs
    ]
    payload = {
        "status": top_status(items),
        "generated_at": wiki_utils.utc_now(),
        "items": items,
    }

    if args.report:
        try:
            write_report(payload, args.report)
        except (OSError, ValueError) as exc:
            return fail(f"Could not write report: {exc}")

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        render_text(payload)
    return exit_code_for_items(items)


if __name__ == "__main__":
    sys.exit(main())
