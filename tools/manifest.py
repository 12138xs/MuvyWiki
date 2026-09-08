#!/usr/bin/env python3
"""Safe manifest validation and lookup helper for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import wiki_utils


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = DEFAULT_ROOT
MANIFEST_REL = "raw/source-manifest.jsonl"
MANIFEST_PATH = ROOT / MANIFEST_REL
RAW_ROOT = ROOT / "raw/originals"
CONVERTED_ROOT = ROOT / "raw/converted"
REQUIRED_KEYS = (
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
)


@dataclass(frozen=True)
class ManifestIssue:
    line: int | None
    message: str

    def as_dict(self) -> dict[str, object]:
        return {"line": self.line, "message": self.message}


@dataclass(frozen=True)
class ManifestEntry:
    line: int
    data: dict[str, Any]


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def validation_issue(message: str, as_json: bool = False) -> int:
    if as_json:
        print(json.dumps({"status": "blocked", "issues": [{"line": None, "message": message}]}, sort_keys=True))
    else:
        print("MuvyWiki manifest: issues")
        print(f"- {message}")
    return 1


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: entry.get(key) for key in REQUIRED_KEYS}


def read_manifest() -> tuple[list[ManifestEntry], list[ManifestIssue], bool]:
    if not MANIFEST_PATH.exists():
        return [], [ManifestIssue(None, "manifest file is missing")], False
    try:
        lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [ManifestIssue(None, f"manifest file is unreadable: {exc}")], False

    entries: list[ManifestEntry] = []
    issues: list[ManifestIssue] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(ManifestIssue(line_number, f"invalid JSON on line {line_number}: {exc.msg}"))
            continue
        if not isinstance(entry, dict):
            issues.append(ManifestIssue(line_number, "manifest entry must be an object"))
            continue
        entries.append(ManifestEntry(line_number, entry))
    return entries, issues, True


def validate_repo_file(
    rel_path: object,
    required_parent: Path,
    field: str,
    source_id: str,
) -> tuple[Path | None, str | None]:
    if rel_path is None:
        return None, None
    if not isinstance(rel_path, str) or not rel_path:
        return None, f"{field} for {source_id} must be a non-empty string or null"
    try:
        path = wiki_utils.safe_child_path(ROOT, rel_path, required_parent)
    except ValueError as exc:
        return None, f"{field} for {source_id} is unsafe: {exc}"
    if not path.exists():
        return path, f"{field} for {source_id} does not exist: {rel_path}"
    if path.is_symlink():
        return path, f"{field} for {source_id} must not be a symlink: {rel_path}"
    if not path.is_file():
        return path, f"{field} for {source_id} is not a file: {rel_path}"
    return path, None


def validate_manifest(entries: list[ManifestEntry], parse_issues: list[ManifestIssue]) -> list[ManifestIssue]:
    issues = list(parse_issues)
    seen_ids: dict[str, int] = {}
    seen_hashes: dict[str, str] = {}
    seen_raw_paths: dict[str, str] = {}

    for manifest_entry in entries:
        line_number = manifest_entry.line
        entry = manifest_entry.data
        for key in REQUIRED_KEYS:
            if key not in entry:
                issues.append(ManifestIssue(line_number, f"missing {key} on line {line_number}"))

        source_id = entry.get("source_id")
        source_label = source_id if isinstance(source_id, str) and source_id else f"line {line_number}"
        if not isinstance(source_id, str) or not wiki_utils.is_kebab_id(source_id):
            issues.append(ManifestIssue(line_number, f"invalid source_id on line {line_number}"))
        elif source_id in seen_ids:
            issues.append(ManifestIssue(line_number, f"duplicate source_id: {source_id}"))
        else:
            seen_ids[source_id] = line_number

        content_hash = entry.get("content_hash")
        if not wiki_utils.is_sha256_hash(content_hash):
            issues.append(ManifestIssue(line_number, f"invalid content_hash for {source_label}"))
        elif content_hash in seen_hashes:
            issues.append(
                ManifestIssue(
                    line_number,
                    f"duplicate content_hash for {source_label} and {seen_hashes[str(content_hash)]}",
                )
            )
        else:
            seen_hashes[str(content_hash)] = str(source_label)

        raw_path = entry.get("raw_path")
        raw_file, raw_issue = validate_repo_file(raw_path, RAW_ROOT, "raw_path", str(source_label))
        if raw_issue:
            issues.append(ManifestIssue(line_number, raw_issue))
        elif isinstance(raw_path, str) and raw_path in seen_raw_paths:
            issues.append(
                ManifestIssue(line_number, f"duplicate raw_path for {source_label} and {seen_raw_paths[raw_path]}")
            )
        elif isinstance(raw_path, str):
            seen_raw_paths[raw_path] = str(source_label)
            if wiki_utils.is_sha256_hash(content_hash) and raw_file is not None:
                actual_hash = wiki_utils.sha256_file(raw_file)
                if actual_hash != content_hash:
                    issues.append(ManifestIssue(line_number, f"content_hash for {source_label} does not match raw_path"))

        converted_path = entry.get("converted_path")
        _, converted_issue = validate_repo_file(converted_path, CONVERTED_ROOT, "converted_path", str(source_label))
        if converted_issue:
            issues.append(ManifestIssue(line_number, converted_issue))

        converted_from = entry.get("converted_from")
        if converted_from is not None:
            _, converted_from_issue = validate_repo_file(converted_from, ROOT, "converted_from", str(source_label))
            if converted_from_issue:
                issues.append(ManifestIssue(line_number, converted_from_issue))

        for date_field in ("collected_at", "published_at"):
            if not wiki_utils.is_iso_date(entry.get(date_field)):
                issues.append(ManifestIssue(line_number, f"{date_field} for {source_label} must be YYYY-MM-DD or null"))

        source_url = entry.get("source_url")
        if source_url is not None and not isinstance(source_url, str):
            issues.append(ManifestIssue(line_number, f"source_url for {source_label} must be a string or null"))

    return issues


def load_validated_manifest() -> tuple[list[ManifestEntry], list[ManifestIssue], bool]:
    entries, parse_issues, readable = read_manifest()
    return entries, validate_manifest(entries, parse_issues), readable


def print_check(entries: list[ManifestEntry], issues: list[ManifestIssue], as_json: bool) -> int:
    status = "ok" if not issues else "issues"
    if as_json:
        print(
            json.dumps(
                {
                    "status": status,
                    "checked_at": wiki_utils.utc_now(),
                    "entry_count": len(entries),
                    "issues": [issue.as_dict() for issue in issues],
                },
                sort_keys=True,
            )
        )
    else:
        print(f"MuvyWiki manifest: {status}")
        print(f"Entries: {len(entries)}")
        for issue in issues:
            print(f"- {issue.message}")
    return 0 if not issues else 1


def command_check(args: argparse.Namespace) -> int:
    entries, issues, readable = load_validated_manifest()
    if not readable:
        return fail(issues[0].message)
    return print_check(entries, issues, args.json)


def command_find(args: argparse.Namespace) -> int:
    if not args.source_id and not args.hash and not args.path:
        return fail("At least one of --source-id, --hash, or --path is required.")

    entries, issues, readable = load_validated_manifest()
    if not readable:
        return fail(issues[0].message)
    if issues:
        return print_check(entries, issues, args.json)

    matches = []
    for manifest_entry in entries:
        entry = manifest_entry.data
        if args.source_id and entry.get("source_id") != args.source_id:
            continue
        if args.hash and entry.get("content_hash") != args.hash:
            continue
        if args.path and args.path not in {entry.get("raw_path"), entry.get("converted_path"), entry.get("converted_from")}:
            continue
        matches.append(normalize_entry(entry))

    if args.json:
        print(json.dumps({"status": "ok", "matches": matches}, sort_keys=True))
    else:
        print(f"MuvyWiki manifest find: {len(matches)} match(es)")
        for index, entry in enumerate(matches, start=1):
            print()
            print(f"{index}. {entry['source_id']}")
            print(f"   raw_path: {entry['raw_path']}")
            print(f"   content_hash: {entry['content_hash']}")
    return 0


def resolve_raw_path(raw_path: str) -> Path:
    try:
        return wiki_utils.safe_child_path(ROOT, raw_path, RAW_ROOT)
    except ValueError as exc:
        raise ValueError(f"raw_path is unsafe: {exc}") from exc


def resolve_optional_path(value: str | None, parent: Path, label: str) -> Path | None:
    if value in (None, ""):
        return None
    try:
        return wiki_utils.safe_child_path(ROOT, value, parent)
    except ValueError as exc:
        raise ValueError(f"{label} is unsafe: {exc}") from exc


def entry_conflicts(entries: list[ManifestEntry], new_entry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for manifest_entry in entries:
        entry = manifest_entry.data
        if entry.get("source_id") == new_entry["source_id"]:
            issues.append(f"duplicate source_id: {new_entry['source_id']}")
        if entry.get("content_hash") == new_entry["content_hash"]:
            issues.append(f"duplicate content_hash: {new_entry['content_hash']}")
        if entry.get("raw_path") == new_entry["raw_path"]:
            issues.append(f"duplicate raw_path: {new_entry['raw_path']}")
    return issues


def source_page_provenance_conflicts(new_entry: dict[str, Any]) -> list[str]:
    source_id = new_entry["source_id"]
    source_page = ROOT / "wiki" / "sources" / f"{source_id}.md"
    if not source_page.exists():
        return []

    try:
        provenance = wiki_utils.extract_provenance(source_page.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"source page provenance for {source_id} is unreadable: {exc}"]

    if not provenance:
        return [f"source page provenance for {source_id} is missing or conflicting"]

    conflicts = []
    for key in REQUIRED_KEYS:
        if provenance.get(key) != new_entry.get(key):
            conflicts.append(f"source page provenance {key} conflicts with new manifest entry for {source_id}")
    return conflicts


def build_entry(args: argparse.Namespace) -> tuple[dict[str, Any] | None, int | None]:
    if not wiki_utils.is_kebab_id(args.source_id):
        return None, fail("source_id must be kebab-case.")
    if not wiki_utils.is_sha256_hash(args.content_hash):
        return None, fail("content_hash must be sha256:<64 lowercase hex characters>.")
    if not wiki_utils.is_iso_date(args.collected_at) or not wiki_utils.is_iso_date(args.published_at):
        return None, fail("collected_at and published_at must be YYYY-MM-DD when provided.")

    try:
        raw_file = resolve_raw_path(args.raw_path)
        converted_file = resolve_optional_path(args.converted_path, CONVERTED_ROOT, "converted_path")
        converted_from = resolve_optional_path(args.converted_from, ROOT, "converted_from")
    except ValueError as exc:
        return None, fail(str(exc))

    for path, label in ((raw_file, "raw_path"), (converted_file, "converted_path"), (converted_from, "converted_from")):
        if path is None:
            continue
        if not path.exists():
            return None, fail(f"{label} must exist, be a file, and not be a symlink.")
        if path.is_symlink():
            return None, fail(f"{label} must exist, be a file, and not be a symlink.")
        if not path.is_file():
            return None, fail(f"{label} must exist, be a file, and not be a symlink.")

    actual_hash = wiki_utils.sha256_file(raw_file)
    if actual_hash != args.content_hash:
        return None, validation_issue("content_hash does not match actual raw file hash.", args.json)

    entry = {
        "source_id": args.source_id,
        "raw_path": args.raw_path,
        "content_hash": args.content_hash,
        "source_url": args.source_url,
        "collected_at": args.collected_at or date.today().isoformat(),
        "published_at": args.published_at,
        "converted_from": args.converted_from or None,
        "converted_path": args.converted_path or None,
        "converter": args.converter,
        "converter_version": args.converter_version,
    }
    return entry, None


def print_conflicts(conflicts: list[str], as_json: bool) -> int:
    if as_json:
        print(
            json.dumps(
                {"status": "blocked", "issues": [{"line": None, "message": message} for message in conflicts]},
                sort_keys=True,
            )
        )
    else:
        print("MuvyWiki manifest: issues")
        for message in conflicts:
            print(f"- {message}")
    return 1


def append_manifest_entry(entry: dict[str, Any]) -> None:
    existing = MANIFEST_PATH.read_text(encoding="utf-8")
    separator = "" if not existing or existing.endswith("\n") else "\n"
    appended = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"
    temp_path = MANIFEST_PATH.with_name(f"{MANIFEST_PATH.name}.tmp")
    try:
        temp_path.write_text(existing + separator + appended, encoding="utf-8")
        os.replace(temp_path, MANIFEST_PATH)
    except OSError:
        if temp_path.exists():
            temp_path.unlink()
        raise


def command_add(args: argparse.Namespace) -> int:
    entries, issues, readable = load_validated_manifest()
    if not readable:
        return fail(issues[0].message)
    if issues:
        return print_check(entries, issues, args.json)

    new_entry, error_code = build_entry(args)
    if error_code is not None:
        return error_code
    assert new_entry is not None

    conflicts = entry_conflicts(entries, new_entry)
    if conflicts:
        return print_conflicts(conflicts, args.json)

    provenance_conflicts = source_page_provenance_conflicts(new_entry)
    if provenance_conflicts:
        return print_conflicts(provenance_conflicts, args.json)

    try:
        append_manifest_entry(new_entry)
    except OSError as exc:
        return fail(f"Could not write manifest: {exc}")

    if args.json:
        print(json.dumps({"status": "ok", "entry": new_entry}, sort_keys=True))
    else:
        print(f"Added manifest entry: {new_entry['source_id']}")
        print(f"raw_path: {new_entry['raw_path']}")
        print(f"content_hash: {new_entry['content_hash']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and search MuvyWiki source manifest entries.")
    wiki_utils.add_repo_root_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Validate raw/source-manifest.jsonl.")
    check.add_argument("--json", action="store_true", help="Print machine-readable validation results.")
    check.set_defaults(func=command_check)

    find = subparsers.add_parser("find", help="Find manifest entries.")
    find.add_argument("--source-id")
    find.add_argument("--hash")
    find.add_argument("--path")
    find.add_argument("--json", action="store_true")
    find.set_defaults(func=command_find)

    add = subparsers.add_parser("add", help="Append one validated manifest entry.")
    add.add_argument("--source-id", required=True)
    add.add_argument("--raw-path", required=True)
    add.add_argument("--content-hash", required=True)
    add.add_argument("--source-url")
    add.add_argument("--collected-at")
    add.add_argument("--published-at")
    add.add_argument("--converted-from")
    add.add_argument("--converted-path")
    add.add_argument("--converter")
    add.add_argument("--converter-version")
    add.add_argument("--json", action="store_true")
    add.set_defaults(func=command_add)

    return parser


def main(argv: list[str] | None = None) -> int:
    global ROOT, MANIFEST_PATH, RAW_ROOT, CONVERTED_ROOT
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        ROOT = wiki_utils.resolve_repo_root(args.repo_root, DEFAULT_ROOT)
    except ValueError as exc:
        return fail(f"Invalid repository root: {exc}")
    MANIFEST_PATH = ROOT / MANIFEST_REL
    RAW_ROOT = ROOT / "raw/originals"
    CONVERTED_ROOT = ROOT / "raw/converted"
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
