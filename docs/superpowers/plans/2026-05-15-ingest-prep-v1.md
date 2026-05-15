# Ingest Prep v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic ingest-preflight and manifest-management helpers while preserving MuvyWiki's agent-first ingest workflow.

**Architecture:** Build two small CLI tools: `tools/manifest.py` owns JSONL validation/search/append for `raw/source-manifest.jsonl`, and `tools/prepare_ingest.py` owns read-only local input classification, hash checks, duplicate checks, source ID suggestion, template recommendation, and optional generated reports. Shared low-level path, hash, frontmatter, and ID helpers stay in `tools/wiki_utils.py`; semantic extraction and wiki-page edits remain in `AGENTS.md`.

**Tech Stack:** Python standard library, `unittest`, JSONL, Markdown documentation, existing MuvyWiki repository conventions.

---

## File Structure

- Modify `tools/wiki_utils.py`: add small reusable helpers for remote URL detection, SHA-256/date validation, repo-local file checks, and slug generation.
- Create `tools/manifest.py`: manifest `check`, `find`, and `add` CLI with text/JSON output and safe atomic writes.
- Create `tools/prepare_ingest.py`: read-only ingest-prep CLI with text/JSON output and optional Markdown report under `graph/`.
- Modify `tools/health.py`: require the new public tools and keep manifest/provenance checks consistent.
- Create `tests/test_manifest.py`: manifest command coverage.
- Create `tests/test_prepare_ingest.py`: ingest-prep command coverage.
- Modify `tests/test_health.py`: fixtures include the new required tools.
- Modify `tests/test_docs_interfaces.py`: docs mention the new implemented interfaces and keep boundaries honest.
- Modify `README.md`, `USER_GUIDE.md`, `AGENTS.md`, `raw/README.md`, `graph/README.md`: user-facing and agent-facing workflow updates.
- Modify `docs/superpowers/specs/2026-05-12-muvywiki-design.md` and `docs/superpowers/specs/2026-05-12-ingest-v2-design.md`: status notes that preflight/manifest are now tool-assisted.
- Modify `examples/ingest/README.md`, `examples/ingest/README-root.md`, `examples/ingest/AGENTS.md`, `examples/ingest/raw/README.md`, and copy the new helper tools into `examples/ingest/tools/` so the fixture demonstrates the same public interfaces as the root project.

## Execution Preflight

- [ ] **Step 1: Create an isolated worktree for implementation**

Use `superpowers:using-git-worktrees` before editing implementation files. Name the branch `codex/ingest-prep-v1`.

If the environment still refuses writes to `.git/index.lock`, continue with the working tree and record the exact Git failure in the handoff. Do not let Git permissions block file implementation or verification.

- [ ] **Step 2: Verify starting state**

Run:

```bash
git status -sb
python -m unittest discover -s tests
python tools/health.py
python tools/lint.py
```

Expected: tests pass, health is `ok`, lint is `ok`. It is acceptable for `git status` to show the approved design and this plan as uncommitted if Git metadata writes are blocked by the environment.

---

### Task 1: Shared Helpers

**Files:**
- Modify: `tools/wiki_utils.py`
- Modify: `tests/test_wiki_utils.py`

- [ ] **Step 1: Write failing helper tests**

Append these tests to `tests/test_wiki_utils.py` inside `WikiUtilsTests`:

```python
    def test_source_slug_remote_hash_and_date_helpers(self):
        self.assertEqual(wiki_utils.slugify_source_id("Karpathy LLM Wiki.md"), "karpathy-llm-wiki")
        self.assertEqual(wiki_utils.slugify_source_id("!!!", fallback_hash="sha256:" + "a" * 64), "source-aaaaaaaa")
        self.assertTrue(wiki_utils.is_remote_url("https://example.com/post"))
        self.assertTrue(wiki_utils.is_remote_url("file://not-supported"))
        self.assertFalse(wiki_utils.is_remote_url("raw/originals/post.md"))
        self.assertTrue(wiki_utils.is_sha256_hash("sha256:" + "a" * 64))
        self.assertFalse(wiki_utils.is_sha256_hash("sha1:" + "a" * 40))
        self.assertTrue(wiki_utils.is_iso_date("2026-05-15"))
        self.assertFalse(wiki_utils.is_iso_date("2026-5-15"))

    def test_supported_text_and_binary_detection(self):
        self.assertTrue(wiki_utils.is_supported_text_suffix(Path("note.md")))
        self.assertTrue(wiki_utils.is_supported_text_suffix(Path("note.markdown")))
        self.assertTrue(wiki_utils.is_supported_text_suffix(Path("note.txt")))
        self.assertTrue(wiki_utils.is_supported_text_suffix(Path("README")))
        self.assertFalse(wiki_utils.is_supported_text_suffix(Path("paper.pdf")))
        self.assertFalse(wiki_utils.is_binary_like_text("hello\n"))
        self.assertTrue(wiki_utils.is_binary_like_text("hello\x00\n"))
```

- [ ] **Step 2: Run helper tests and verify failure**

Run:

```bash
python -m unittest tests/test_wiki_utils.py
```

Expected: fail because the new helper functions do not exist.

- [ ] **Step 3: Add shared helpers**

Modify imports in `tools/wiki_utils.py`:

```python
import unicodedata
```

Add constants near existing regex constants:

```python
REMOTE_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SUPPORTED_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ""}
ALLOWED_TEXT_CONTROLS = {9, 10, 12, 13}
```

Add helpers near the existing ID/path helpers:

```python
def is_remote_url(value: str) -> bool:
    return bool(REMOTE_URL_RE.match(value))


def is_sha256_hash(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def is_iso_date(value: object) -> bool:
    return value is None or (isinstance(value, str) and bool(ISO_DATE_RE.fullmatch(value)))


def is_supported_text_suffix(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES


def is_binary_like_text(text: str) -> bool:
    return any(
        unicodedata.category(char) == "Cc" and ord(char) not in ALLOWED_TEXT_CONTROLS
        for char in text
    )


def slugify_source_id(value: str, fallback_hash: str | None = None) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = re.sub(r"\.[a-z0-9]+$", "", ascii_text)
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if slug:
        return slug
    if fallback_hash and is_sha256_hash(fallback_hash):
        return f"source-{fallback_hash.removeprefix('sha256:')[:8]}"
    return "source-unknown"
```

- [ ] **Step 4: Run helper tests and verify pass**

Run:

```bash
python -m unittest tests/test_wiki_utils.py
```

Expected: all `test_wiki_utils.py` tests pass.

- [ ] **Step 5: Commit if Git metadata is writable**

Run:

```bash
git add tools/wiki_utils.py tests/test_wiki_utils.py
git commit -m "feat: add ingest prep utility helpers"
```

Expected: commit succeeds. If Git reports `Operation not permitted` for `.git/index.lock`, leave files in the working tree and record the failure.

---

### Task 2: Manifest Check and Find

**Files:**
- Create: `tools/manifest.py`
- Create: `tests/test_manifest.py`

- [ ] **Step 1: Write failing manifest check/find tests**

Create `tests/test_manifest.py`:

```python
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ManifestToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in ("raw/originals", "raw/converted", "wiki/sources", "tools"):
            (root / rel).mkdir(parents=True, exist_ok=True)
        for tool in ("wiki_utils.py", "manifest.py"):
            shutil.copy(ROOT / "tools" / tool, root / "tools" / tool)
        (root / "raw/source-manifest.jsonl").write_text("", encoding="utf-8")
        return temp_dir, root

    def run_manifest(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/manifest.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def valid_entry(self, root, source_id="source-one", body=b"source body\n"):
        raw_path = root / f"raw/originals/{source_id}.md"
        raw_path.write_bytes(body)
        entry = {
            "source_id": source_id,
            "raw_path": f"raw/originals/{source_id}.md",
            "content_hash": "sha256:" + __import__("hashlib").sha256(body).hexdigest(),
            "source_url": None,
            "collected_at": "2026-05-15",
            "published_at": None,
            "converted_from": None,
            "converted_path": None,
            "converter": None,
            "converter_version": None,
        }
        return entry

    def write_manifest(self, root, *entries):
        text = "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries)
        (root / "raw/source-manifest.jsonl").write_text(text, encoding="utf-8")

    def test_check_empty_manifest_is_ok(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_manifest(root, "check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("MuvyWiki manifest: ok", result.stdout)
            self.assertIn("Entries: 0", result.stdout)

    def test_check_valid_manifest_json(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            result = self.run_manifest(root, "check", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["entry_count"], 1)
            self.assertEqual(payload["issues"], [])

    def test_check_rejects_malformed_missing_and_duplicate_entries(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            duplicate = dict(entry)
            duplicate["raw_path"] = "raw/originals/duplicate.md"
            (root / "raw/originals/duplicate.md").write_bytes(b"other\n")
            (root / "raw/source-manifest.jsonl").write_text(
                json.dumps(entry) + "\n" + "{bad json\n" + json.dumps(duplicate) + "\n",
                encoding="utf-8",
            )
            result = self.run_manifest(root, "check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid JSON on line 2", result.stdout)
            self.assertIn("duplicate source_id: source-one", result.stdout)

    def test_find_by_source_id_hash_and_path(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            by_id = self.run_manifest(root, "find", "--source-id", "source-one", "--json")
            self.assertEqual(by_id.returncode, 0, by_id.stdout + by_id.stderr)
            self.assertEqual(json.loads(by_id.stdout)["matches"][0]["source_id"], "source-one")
            by_hash = self.run_manifest(root, "find", "--hash", entry["content_hash"])
            self.assertEqual(by_hash.returncode, 0, by_hash.stdout + by_hash.stderr)
            self.assertIn("source-one", by_hash.stdout)
            by_path = self.run_manifest(root, "find", "--path", "raw/originals/source-one.md")
            self.assertEqual(by_path.returncode, 0, by_path.stdout + by_path.stderr)
            self.assertIn("1 match", by_path.stdout)

    def test_find_requires_search_argument(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            result = self.run_manifest(root, "find")
            self.assertEqual(result.returncode, 2)
            self.assertIn("At least one", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run manifest tests and verify failure**

Run:

```bash
python -m unittest tests/test_manifest.py
```

Expected: fail because `tools/manifest.py` does not exist.

- [ ] **Step 3: Implement `tools/manifest.py` check/find**

Create `tools/manifest.py` with this structure:

```python
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


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REL = "raw/source-manifest.jsonl"
MANIFEST_PATH = ROOT / MANIFEST_REL
RAW_ROOT = (ROOT / "raw/originals").resolve()
CONVERTED_ROOT = (ROOT / "raw/converted").resolve()
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


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def repo_path(path: Path) -> str:
    return wiki_utils.repo_relative(ROOT, path)


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: entry.get(key) for key in REQUIRED_KEYS}


def read_manifest() -> tuple[list[dict[str, Any]], list[ManifestIssue], bool]:
    if not MANIFEST_PATH.exists():
        return [], [ManifestIssue(None, "manifest file is missing")], False
    try:
        lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [ManifestIssue(None, f"manifest file is unreadable: {exc}")], False
    entries: list[dict[str, Any]] = []
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
        entries.append(entry)
    return entries, issues, True


def validate_repo_file(rel_path: object, required_parent: Path, field: str, source_id: str) -> str | None:
    if rel_path is None:
        return None
    if not isinstance(rel_path, str) or not rel_path:
        return f"{field} for {source_id} must be a non-empty string or null"
    try:
        path = wiki_utils.safe_child_path(ROOT, rel_path, required_parent)
    except ValueError as exc:
        return f"{field} for {source_id} is unsafe: {exc}"
    if not path.exists():
        return f"{field} for {source_id} does not exist: {rel_path}"
    if not path.is_file():
        return f"{field} for {source_id} is not a file: {rel_path}"
    if path.is_symlink():
        return f"{field} for {source_id} must not be a symlink: {rel_path}"
    return None


def validate_manifest(entries: list[dict[str, Any]], parse_issues: list[ManifestIssue]) -> list[ManifestIssue]:
    issues = list(parse_issues)
    seen_ids: dict[str, int] = {}
    seen_hashes: dict[str, str] = {}
    seen_raw_paths: dict[str, str] = {}
    for index, entry in enumerate(entries, start=1):
        missing = [key for key in REQUIRED_KEYS if key not in entry]
        for key in missing:
            issues.append(ManifestIssue(index, f"missing {key} on line {index}"))
        source_id = entry.get("source_id")
        source_label = source_id if isinstance(source_id, str) and source_id else f"line {index}"
        if not isinstance(source_id, str) or not wiki_utils.is_kebab_id(source_id):
            issues.append(ManifestIssue(index, f"invalid source_id on line {index}"))
        elif source_id in seen_ids:
            issues.append(ManifestIssue(index, f"duplicate source_id: {source_id}"))
        else:
            seen_ids[source_id] = index
        content_hash = entry.get("content_hash")
        if not wiki_utils.is_sha256_hash(content_hash):
            issues.append(ManifestIssue(index, f"invalid content_hash for {source_label}"))
        elif content_hash in seen_hashes:
            issues.append(ManifestIssue(index, f"duplicate content_hash for {source_label} and {seen_hashes[content_hash]}"))
        else:
            seen_hashes[str(content_hash)] = str(source_id)
        raw_path = entry.get("raw_path")
        raw_issue = validate_repo_file(raw_path, RAW_ROOT, "raw_path", str(source_label))
        if raw_issue:
            issues.append(ManifestIssue(index, raw_issue))
        elif isinstance(raw_path, str) and raw_path in seen_raw_paths:
            issues.append(ManifestIssue(index, f"duplicate raw_path for {source_label} and {seen_raw_paths[raw_path]}"))
        elif isinstance(raw_path, str):
            seen_raw_paths[raw_path] = str(source_id)
        converted_issue = validate_repo_file(entry.get("converted_path"), CONVERTED_ROOT, "converted_path", str(source_label))
        if converted_issue:
            issues.append(ManifestIssue(index, converted_issue))
        converted_from = entry.get("converted_from")
        if converted_from is not None:
            converted_from_issue = validate_repo_file(converted_from, ROOT, "converted_from", str(source_label))
            if converted_from_issue:
                issues.append(ManifestIssue(index, converted_from_issue))
        for date_field in ("collected_at", "published_at"):
            if not wiki_utils.is_iso_date(entry.get(date_field)):
                issues.append(ManifestIssue(index, f"{date_field} for {source_label} must be YYYY-MM-DD or null"))
        source_url = entry.get("source_url")
        if source_url is not None and not isinstance(source_url, str):
            issues.append(ManifestIssue(index, f"source_url for {source_label} must be a string or null"))
    return issues


def load_validated_manifest() -> tuple[list[dict[str, Any]], list[ManifestIssue], bool]:
    entries, parse_issues, readable = read_manifest()
    return entries, validate_manifest(entries, parse_issues), readable


def print_check(entries: list[dict[str, Any]], issues: list[ManifestIssue], as_json: bool) -> int:
    status = "ok" if not issues else "issues"
    if as_json:
        print(json.dumps({
            "status": status,
            "checked_at": wiki_utils.utc_now(),
            "entry_count": len(entries),
            "issues": [issue.as_dict() for issue in issues],
        }, sort_keys=True))
    else:
        print(f"MuvyWiki manifest: {status}")
        print(f"Entries: {len(entries)}")
        for issue in issues:
            print(f"- {issue.message}")
    return 0 if not issues else 1


def command_check(args: argparse.Namespace) -> int:
    entries, issues, readable = load_validated_manifest()
    if not readable:
        return print_check(entries, issues, args.json) if args.json else fail(issues[0].message)
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
    for entry in entries:
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
```

Add `main()` and parser:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate, search, and append MuvyWiki source manifest entries.")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run manifest check/find tests**

Run:

```bash
python -m unittest tests/test_manifest.py
```

Expected: tests for `check` and `find` pass. Tests for `add` do not exist yet.

- [ ] **Step 5: Commit if Git metadata is writable**

Run:

```bash
git add tools/manifest.py tests/test_manifest.py
git commit -m "feat: add manifest check and find"
```

Expected: commit succeeds, or Git metadata write failure is recorded.

---

### Task 3: Manifest Add

**Files:**
- Modify: `tools/manifest.py`
- Modify: `tests/test_manifest.py`

- [ ] **Step 1: Write failing manifest add tests**

Append these tests inside `ManifestToolTests`:

```python
    def test_add_writes_one_entry_and_preserves_existing_lines(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            existing = self.valid_entry(root, "existing-source", b"existing\n")
            self.write_manifest(root, existing)
            body = b"new body\n"
            raw_path = root / "raw/originals/new-source.md"
            raw_path.write_bytes(body)
            content_hash = "sha256:" + __import__("hashlib").sha256(body).hexdigest()
            before = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8")
            result = self.run_manifest(
                root,
                "add",
                "--source-id", "new-source",
                "--raw-path", "raw/originals/new-source.md",
                "--content-hash", content_hash,
                "--published-at", "2026-05-01",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["entry"]["source_id"], "new-source")
            lines = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], before.splitlines()[0])
            self.assertEqual(json.loads(lines[1])["content_hash"], content_hash)

    def test_add_rejects_duplicate_source_id_hash_and_raw_path_without_mutation(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            entry = self.valid_entry(root)
            self.write_manifest(root, entry)
            before = (root / "raw/source-manifest.jsonl").read_text(encoding="utf-8")
            result = self.run_manifest(
                root,
                "add",
                "--source-id", "source-one",
                "--raw-path", "raw/originals/source-one.md",
                "--content-hash", entry["content_hash"],
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate source_id", result.stdout)
            self.assertEqual((root / "raw/source-manifest.jsonl").read_text(encoding="utf-8"), before)

    def test_add_rejects_hash_mismatch_unsafe_path_and_symlink(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/new-source.md").write_text("new body\n", encoding="utf-8")
            mismatch = self.run_manifest(
                root,
                "add",
                "--source-id", "new-source",
                "--raw-path", "raw/originals/new-source.md",
                "--content-hash", "sha256:" + "0" * 64,
            )
            self.assertEqual(mismatch.returncode, 1)
            self.assertIn("does not match actual raw file hash", mismatch.stdout)
            outside = self.run_manifest(
                root,
                "add",
                "--source-id", "bad-source",
                "--raw-path", "../bad.md",
                "--content-hash", "sha256:" + "0" * 64,
            )
            self.assertEqual(outside.returncode, 2)
            self.assertIn("raw_path", outside.stderr)
            (root / "raw/originals/link.md").symlink_to(root / "raw/originals/new-source.md")
            link = self.run_manifest(
                root,
                "add",
                "--source-id", "link-source",
                "--raw-path", "raw/originals/link.md",
                "--content-hash", "sha256:" + "0" * 64,
            )
            self.assertEqual(link.returncode, 2)
            self.assertIn("symlink", link.stderr)
```

- [ ] **Step 2: Run add tests and verify failure**

Run:

```bash
python -m unittest tests/test_manifest.py
```

Expected: fail because `add` subcommand is not implemented.

- [ ] **Step 3: Implement manifest add validation**

Add helpers to `tools/manifest.py`:

```python
def validation_issue(message: str, as_json: bool = False) -> int:
    if as_json:
        print(json.dumps({"status": "blocked", "issues": [{"line": None, "message": message}]}, sort_keys=True))
    else:
        print(f"MuvyWiki manifest: issues")
        print(f"- {message}")
    return 1


def resolve_raw_path(raw_path: str) -> Path:
    return wiki_utils.safe_child_path(ROOT, raw_path, RAW_ROOT)


def resolve_optional_path(value: str | None, parent: Path, label: str) -> Path | None:
    if value in (None, ""):
        return None
    try:
        return wiki_utils.safe_child_path(ROOT, value, parent)
    except ValueError as exc:
        raise ValueError(f"{label} is unsafe: {exc}") from exc


def entry_conflicts(entries: list[dict[str, Any]], new_entry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for entry in entries:
        if entry.get("source_id") == new_entry["source_id"]:
            issues.append(f"duplicate source_id: {new_entry['source_id']}")
        if entry.get("content_hash") == new_entry["content_hash"]:
            issues.append(f"duplicate content_hash: {new_entry['content_hash']}")
        if entry.get("raw_path") == new_entry["raw_path"]:
            issues.append(f"duplicate raw_path: {new_entry['raw_path']}")
    return issues


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
        if not path.exists() or not path.is_file() or path.is_symlink():
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
        "converted_from": args.converted_from,
        "converted_path": args.converted_path,
        "converter": args.converter,
        "converter_version": args.converter_version,
    }
    return entry, None
```

- [ ] **Step 4: Implement atomic append command**

Add `command_add`:

```python
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
        if args.json:
            print(json.dumps({"status": "blocked", "issues": [{"line": None, "message": message} for message in conflicts]}, sort_keys=True))
        else:
            print("MuvyWiki manifest: issues")
            for message in conflicts:
                print(f"- {message}")
        return 1
    lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    output_lines = list(lines)
    output_lines.append(json.dumps(new_entry, sort_keys=True, separators=(",", ":")))
    temp_path = MANIFEST_PATH.with_suffix(".jsonl.tmp")
    try:
        temp_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
        os.replace(temp_path, MANIFEST_PATH)
    except OSError as exc:
        if temp_path.exists():
            temp_path.unlink()
        return fail(f"Could not write manifest: {exc}")
    if args.json:
        print(json.dumps({"status": "ok", "entry": new_entry}, sort_keys=True))
    else:
        print(f"Added manifest entry: {new_entry['source_id']}")
        print(f"raw_path: {new_entry['raw_path']}")
        print(f"content_hash: {new_entry['content_hash']}")
    return 0
```

Register the subcommand:

```python
    add = subparsers.add_parser("add", help="Append one validated manifest entry.")
    add.add_argument("--source-id", required=True)
    add.add_argument("--raw-path", required=True)
    add.add_argument("--content-hash", required=True)
    add.add_argument("--source-url")
    add.add_argument("--published-at")
    add.add_argument("--converted-from")
    add.add_argument("--converted-path")
    add.add_argument("--converter")
    add.add_argument("--converter-version")
    add.add_argument("--collected-at")
    add.add_argument("--json", action="store_true")
    add.set_defaults(func=command_add)
```

- [ ] **Step 5: Run manifest tests and verify pass**

Run:

```bash
python -m unittest tests/test_manifest.py
```

Expected: all manifest tests pass.

- [ ] **Step 6: Commit if Git metadata is writable**

Run:

```bash
git add tools/manifest.py tests/test_manifest.py
git commit -m "feat: add manifest append command"
```

Expected: commit succeeds, or Git metadata write failure is recorded.

---

### Task 4: Prepare Ingest

**Files:**
- Create: `tools/prepare_ingest.py`
- Create: `tests/test_prepare_ingest.py`

- [ ] **Step 1: Write failing prepare-ingest tests**

Create `tests/test_prepare_ingest.py`:

```python
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrepareIngestToolTests(unittest.TestCase):
    def make_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        for rel in (
            "raw/originals",
            "raw/converted",
            "wiki/sources",
            "wiki/concepts",
            "wiki/entities",
            "wiki/syntheses",
            "templates/sources",
            "tools",
            "graph",
        ):
            (root / rel).mkdir(parents=True, exist_ok=True)
        for template in ("technical-paper", "technical-article", "project-readme", "meeting-notes", "journal-entry"):
            (root / f"templates/sources/{template}.md").write_text(f"# {template}\n", encoding="utf-8")
        (root / "templates/source.md").write_text("# generic\n", encoding="utf-8")
        (root / "raw/source-manifest.jsonl").write_text("", encoding="utf-8")
        for tool in ("wiki_utils.py", "prepare_ingest.py"):
            shutil.copy(ROOT / "tools" / tool, root / "tools" / tool)
        return temp_dir, root

    def run_prepare(self, root, *args):
        return subprocess.run(
            [sys.executable, "tools/prepare_ingest.py", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_ready_raw_markdown_json_packet(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/Karpathy LLM Wiki.md").write_text("# Karpathy LLM Wiki\n\nNotes.\n", encoding="utf-8")
            result = self.run_prepare(root, "raw/originals/Karpathy LLM Wiki.md", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            item = payload["items"][0]
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(item["input_kind"], "raw-original")
            self.assertEqual(item["source_id"], "karpathy-llm-wiki")
            self.assertEqual(item["source_kind"], "technical-article")
            self.assertEqual(item["template_path"], "templates/sources/technical-article.md")
            self.assertTrue(item["content_hash"].startswith("sha256:"))
            self.assertEqual(item["duplicate"], False)

    def test_source_id_override_and_kind(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/paper-note.txt").write_text("paper text\n", encoding="utf-8")
            result = self.run_prepare(
                root,
                "raw/originals/paper-note.txt",
                "--source-id", "attention-survey-note",
                "--kind", "technical-paper",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["source_id"], "attention-survey-note")
            self.assertEqual(item["source_id_origin"], "provided")
            self.assertEqual(item["source_kind"], "technical-paper")

    def test_converted_artifact_reports_needs_raw_original(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/converted/note.md").write_text("# Converted\n", encoding="utf-8")
            result = self.run_prepare(root, "raw/converted/note.md", "--json")
            self.assertEqual(result.returncode, 1)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["input_kind"], "raw-converted")
            self.assertTrue(item["needs_raw_original"])
            self.assertIn("raw original", " ".join(item["warnings"]).lower())

    def test_malformed_manifest_blocks_preflight(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/note.md").write_text("# Note\n", encoding="utf-8")
            (root / "raw/source-manifest.jsonl").write_text("{bad json\n", encoding="utf-8")
            result = self.run_prepare(root, "raw/originals/note.md", "--json")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["items"][0]["status"], "blocked")
            self.assertIn("manifest", " ".join(payload["items"][0]["warnings"]).lower())

    def test_duplicate_source_id_and_hash_block(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            body = b"# Existing\n"
            (root / "raw/originals/existing.md").write_bytes(body)
            content_hash = "sha256:" + __import__("hashlib").sha256(body).hexdigest()
            (root / "raw/source-manifest.jsonl").write_text(
                json.dumps({
                    "source_id": "existing",
                    "raw_path": "raw/originals/existing.md",
                    "content_hash": content_hash,
                    "source_url": None,
                    "collected_at": "2026-05-15",
                    "published_at": None,
                    "converted_from": None,
                    "converted_path": None,
                    "converter": None,
                    "converter_version": None,
                }) + "\n",
                encoding="utf-8",
            )
            result = self.run_prepare(root, "raw/originals/existing.md", "--json")
            self.assertEqual(result.returncode, 1)
            item = json.loads(result.stdout)["items"][0]
            self.assertEqual(item["status"], "blocked")
            self.assertTrue(item["duplicate"])
            self.assertEqual(item["manifest_match"]["source_id"], "existing")

    def test_batch_reports_remote_unsupported_binary_and_report_path(self):
        temp_dir, root = self.make_repo()
        with temp_dir:
            (root / "raw/originals/file.pdf").write_bytes(b"%PDF")
            (root / "raw/originals/binary.txt").write_bytes(b"\x00\x01")
            (root / "raw/originals/note.md").write_text("# Note\n", encoding="utf-8")
            report = self.run_prepare(
                root,
                "https://example.com/page",
                "raw/originals/file.pdf",
                "raw/originals/binary.txt",
                "raw/originals/note.md",
                "--json",
                "--report",
                "graph/ingest-prep-report.md",
            )
            self.assertEqual(report.returncode, 2)
            payload = json.loads(report.stdout)
            self.assertEqual(payload["status"], "blocked")
            kinds = [item["input_kind"] for item in payload["items"]]
            self.assertIn("remote-url", kinds)
            self.assertIn("unsupported", kinds)
            self.assertIn("raw-original", kinds)
            self.assertIn("MuvyWiki Ingest Prep Report", (root / "graph/ingest-prep-report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run prepare-ingest tests and verify failure**

Run:

```bash
python -m unittest tests/test_prepare_ingest.py
```

Expected: fail because `tools/prepare_ingest.py` does not exist.

- [ ] **Step 3: Implement `tools/prepare_ingest.py`**

Create `tools/prepare_ingest.py` with this structure:

```python
#!/usr/bin/env python3
"""Read-only ingest preflight helper for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = (ROOT / "raw/originals").resolve()
CONVERTED_ROOT = (ROOT / "raw/converted").resolve()
GRAPH_ROOT = (ROOT / "graph").resolve()
SOURCE_KINDS = {
    "technical-paper": "templates/sources/technical-paper.md",
    "technical-article": "templates/sources/technical-article.md",
    "project-readme": "templates/sources/project-readme.md",
    "meeting-notes": "templates/sources/meeting-notes.md",
    "journal-entry": "templates/sources/journal-entry.md",
    "generic": "templates/source.md",
}


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def repo_path(path: Path) -> str:
    return wiki_utils.repo_relative(ROOT, path)


def resolve_input(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("path must be relative")
    candidate = wiki_utils.safe_child_path(ROOT, value)
    candidate.relative_to(ROOT.resolve())
    return candidate


def classify_path(path: Path) -> str:
    rel = repo_path(path)
    if rel.startswith("raw/originals/"):
        return "raw-original"
    if rel.startswith("raw/converted/"):
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
    return "technical-article"


def load_manifest_entries() -> tuple[list[dict[str, Any]], list[str]]:
    manifest = ROOT / "raw/source-manifest.jsonl"
    entries: list[dict[str, Any]] = []
    issues: list[str] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    seen_raw_paths: set[str] = set()
    required_keys = {
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
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"manifest unreadable: {exc}"]
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
        missing = sorted(required_keys.difference(entry))
        if missing:
            issues.append(f"manifest line {line_number} missing required keys: {', '.join(missing)}")
        source_id = entry.get("source_id")
        content_hash = entry.get("content_hash")
        raw_path = entry.get("raw_path")
        if isinstance(source_id, str):
            if source_id in seen_ids:
                issues.append(f"duplicate manifest source_id: {source_id}")
            seen_ids.add(source_id)
        if isinstance(content_hash, str):
            if content_hash in seen_hashes:
                issues.append(f"duplicate manifest content_hash: {content_hash}")
            seen_hashes.add(content_hash)
        if isinstance(raw_path, str):
            if raw_path in seen_raw_paths:
                issues.append(f"duplicate manifest raw_path: {raw_path}")
            seen_raw_paths.add(raw_path)
        entries.append(entry)
    return entries, issues


def find_manifest_match(entries: list[dict[str, Any]], source_id: str, content_hash: str) -> dict[str, Any] | None:
    for entry in entries:
        if entry.get("source_id") == source_id or entry.get("content_hash") == content_hash:
            return entry
    return None


def existing_wiki_ids() -> tuple[set[str], list[str]]:
    try:
        return set(wiki_utils.canonical_page_map(ROOT)), []
    except ValueError as exc:
        return set(), [f"wiki canonical IDs are ambiguous: {exc}"]
```

Add item preparation and output:

```python
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


def prepare_one(value: str, args: argparse.Namespace, entries: list[dict[str, Any]], manifest_issues: list[str]) -> tuple[dict[str, Any], int]:
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
    if path.is_dir():
        return blocked_item(value, "unsupported", "Directories are not supported. Provide one or more Markdown/text files.", 2)
    if not path.exists() or not path.is_file() or path.is_symlink():
        return blocked_item(value, "unsupported", "Input must exist, be a file, and not be a symlink.", 2)
    if not wiki_utils.is_supported_text_suffix(path):
        return blocked_item(value, "unsupported", "Unsupported input type. Supported inputs are .md, .markdown, .txt, or extensionless UTF-8 text.", 2)
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return blocked_item(value, "unsupported", "Unsupported input type. Input must be UTF-8 text.", 2)
    except OSError as exc:
        return blocked_item(value, "unsupported", f"Could not read input: {exc}", 2)
    if wiki_utils.is_binary_like_text(text):
        return blocked_item(value, "unsupported", "Unsupported input type. Input appears to contain binary control characters.", 2)
    content_hash = wiki_utils.sha256_bytes(data)
    if args.source_id:
        source_id = args.source_id
        source_id_origin = "provided"
    else:
        source_id = wiki_utils.slugify_source_id(path.name, content_hash)
        source_id_origin = "suggested"
    input_kind = classify_path(path)
    source_kind = recommend_source_kind(path, args.kind)
    warnings = list(manifest_issues)
    status = "blocked" if manifest_issues else "ready"
    duplicate = False
    manifest_match = find_manifest_match(entries, source_id, content_hash)
    if manifest_match is not None:
        status = "blocked"
        duplicate = True
        warnings.append("Duplicate source_id or content_hash found in raw/source-manifest.jsonl.")
    wiki_ids, wiki_id_issues = existing_wiki_ids()
    if wiki_id_issues:
        status = "blocked"
        warnings.extend(wiki_id_issues)
    wiki_source_path = f"wiki/sources/{source_id}.md"
    if (ROOT / wiki_source_path).exists() or source_id in wiki_ids:
        status = "blocked"
        warnings.append("Suggested source_id already exists in wiki pages.")
    needs_raw_original = False
    raw_path: str | None = repo_path(path) if input_kind == "raw-original" else None
    converted_path: str | None = repo_path(path) if input_kind == "raw-converted" else None
    if input_kind == "raw-converted":
        raw_path = manifest_match.get("raw_path") if manifest_match else None
        needs_raw_original = raw_path is None
        if needs_raw_original:
            status = "issues" if status == "ready" else status
            warnings.append("Converted artifact has no known raw original in the manifest.")
    item = {
        "status": status,
        "input": repo_path(path),
        "input_kind": input_kind,
        "source_id": source_id,
        "source_id_origin": source_id_origin,
        "source_kind": source_kind,
        "template_path": SOURCE_KINDS[source_kind],
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
    }
    item["exit_code"] = 1 if status == "blocked" and manifest_issues else 0
    return item, item["exit_code"]
```

Add rendering and parser:

```python
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
        for warning in item["warnings"]:
            print(f"   warning: {warning}")


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
        lines.extend([
            "",
            f"### {item['input']}",
            "",
            f"- Status: {item['status']}",
            f"- Source ID: {item['source_id']}",
            f"- Source kind: {item['source_kind']}",
            f"- Template: {item['template_path']}",
            f"- Content hash: {item['content_hash']}",
            f"- Duplicate: {'yes' if item['duplicate'] else 'no'}",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare local sources for agent-led MuvyWiki ingest.")
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
    items: list[dict[str, Any]] = []
    for value in args.inputs:
        item, _ = prepare_one(value, args, entries, manifest_issues)
        items.append(item)
    payload = {"status": top_status(items), "generated_at": wiki_utils.utc_now(), "items": items}
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
```

- [ ] **Step 4: Run prepare-ingest tests and verify pass**

Run:

```bash
python -m unittest tests/test_prepare_ingest.py
```

Expected: all prepare-ingest tests pass.

- [ ] **Step 5: Run manifest tests again**

Run:

```bash
python -m unittest tests/test_manifest.py
```

Expected: still pass.

- [ ] **Step 6: Commit if Git metadata is writable**

Run:

```bash
git add tools/prepare_ingest.py tests/test_prepare_ingest.py
git commit -m "feat: add ingest preparation helper"
```

Expected: commit succeeds, or Git metadata write failure is recorded.

---

### Task 5: Health, Docs, and Example Fixture

**Files:**
- Modify: `tools/health.py`
- Modify: `tests/test_health.py`
- Modify: `tests/test_docs_interfaces.py`
- Modify: `README.md`
- Modify: `USER_GUIDE.md`
- Modify: `AGENTS.md`
- Modify: `raw/README.md`
- Modify: `graph/README.md`
- Modify: `docs/superpowers/specs/2026-05-12-muvywiki-design.md`
- Modify: `docs/superpowers/specs/2026-05-12-ingest-v2-design.md`
- Modify: `examples/ingest/README.md`
- Modify: `examples/ingest/README-root.md`
- Modify: `examples/ingest/AGENTS.md`
- Modify: `examples/ingest/raw/README.md`
- Modify: `examples/ingest/tools/health.py`
- Create: `examples/ingest/tools/manifest.py`
- Create: `examples/ingest/tools/prepare_ingest.py`

- [ ] **Step 1: Update health required paths**

Add these entries to `REQUIRED_PATHS` in `tools/health.py`:

```python
    "tools/manifest.py",
    "tools/prepare_ingest.py",
```

Update `tests/test_health.py` minimal fixture required tool placeholders:

```python
            "tools/manifest.py",
            "tools/prepare_ingest.py",
```

- [ ] **Step 2: Update docs interface tests**

Add assertions to `tests/test_docs_interfaces.py`:

```python
    def test_ingest_prep_and_manifest_interfaces_are_documented(self):
        readme = self.read("README.md")
        guide = self.read("USER_GUIDE.md")
        agents = self.read("AGENTS.md")
        raw = self.read("raw/README.md")
        graph = self.read("graph/README.md")
        for text in (readme, guide, agents):
            self.assertIn("python tools/prepare_ingest.py", text)
            self.assertIn("python tools/manifest.py", text)
        self.assertIn("manifest.py", raw)
        self.assertIn("ingest-prep-report.md", graph)
```

- [ ] **Step 3: Run docs/health tests and verify failure**

Run:

```bash
python -m unittest tests/test_health.py tests/test_docs_interfaces.py
```

Expected: fail until documentation is updated.

- [ ] **Step 4: Update README command/status sections**

In `README.md`, add rows:

```markdown
| Ingest preparation | Implemented | `python tools/prepare_ingest.py raw/originals/example.md`, `python tools/prepare_ingest.py raw/originals/example.md --json` |
| Source manifest helper | Implemented | `python tools/manifest.py check`, `python tools/manifest.py find --source-id example`, `python tools/manifest.py add ...` |
```

Add commands to the common command block:

```bash
python tools/prepare_ingest.py raw/originals/example.md
python tools/prepare_ingest.py raw/originals/example.md --json
python tools/manifest.py check
python tools/manifest.py find --source-id example-source
```

Keep the text clear that these tools do not perform semantic extraction or create wiki pages.

- [ ] **Step 5: Update user and agent workflow docs**

In `USER_GUIDE.md`, add an ingest-prep section explaining:

```markdown
在正式摄取前，可以先运行：

```bash
python tools/prepare_ingest.py raw/originals/example.md --json
python tools/manifest.py check
python tools/manifest.py find --source-id example-source
```

`prepare_ingest.py` 只判断资料是否适合进入 agent-led ingest；`manifest.py` 只维护 `raw/source-manifest.jsonl`。它们不会自动创建 source/concept/entity/synthesis 页面。
```

In `AGENTS.md`, update Preflight to prefer:

```markdown
1. Run `python tools/prepare_ingest.py <input> --json` for local Markdown/text inputs.
2. If the tool reports blocked or exits non-zero, report `Ingest blocked` with the exact reason and next step.
3. After the source ID, raw path, and hash are final, use `python tools/manifest.py add ...` to append the manifest entry.
```

Also add both tools to implemented deterministic interfaces.

- [ ] **Step 6: Update raw and graph docs**

In `raw/README.md`, add:

```markdown
`python tools/manifest.py check` validates manifest JSONL shape, duplicate IDs/hashes/paths, path safety, and required metadata.

`python tools/manifest.py add ...` appends exactly one validated entry. It does not create wiki pages or update `wiki/index.md` / `wiki/log.md`.
```

In `graph/README.md`, document generated report files:

```markdown
`python tools/prepare_ingest.py <input> --report graph/ingest-prep-report.md` may write a generated ingest-prep report under `graph/`. This report is not a wiki page and should not be added to `wiki/index.md`.
```

- [ ] **Step 7: Update historical design status notes**

In `docs/superpowers/specs/2026-05-12-muvywiki-design.md`, add an `Ingest Prep v1 update` note:

```markdown
## Ingest Prep v1 update

`tools/prepare_ingest.py` and `tools/manifest.py` now provide deterministic preflight and manifest helpers. Semantic extraction, source page creation, concept/entity updates, index/log updates, and health repair remain agent-led.
```

In `docs/superpowers/specs/2026-05-12-ingest-v2-design.md`, add a matching status note that preflight and manifest bookkeeping are now tool-assisted.

- [ ] **Step 8: Update example fixture with new public tools**

Copy the new public helpers into the example fixture so fixture users can run the same ingest-prep command family as the root project:

```bash
cp tools/manifest.py examples/ingest/tools/manifest.py
cp tools/prepare_ingest.py examples/ingest/tools/prepare_ingest.py
cp tools/wiki_utils.py examples/ingest/tools/wiki_utils.py
```

Do not copy root `tools/health.py` wholesale into the fixture. The root health checker requires root-only interfaces such as `tools/query.py` and `tools/save_synthesis.py`; the fixture intentionally contains a smaller tool set. Instead, update only `examples/ingest/tools/health.py` so its `REQUIRED_PATHS` includes:

```python
    "tools/manifest.py",
    "tools/prepare_ingest.py",
```

Then update fixture docs with:

```bash
python tools/prepare_ingest.py raw/originals/tiny-rag-note.md
python tools/manifest.py check
```

Do not change fixture wiki content unless health requires it.

- [ ] **Step 9: Run docs and fixture verification**

Run:

```bash
python -m unittest tests/test_health.py tests/test_docs_interfaces.py
python tools/health.py
python tools/lint.py
cd examples/ingest && python tools/health.py
cd examples/ingest && python tools/lint.py
```

Expected: all pass.

- [ ] **Step 10: Commit if Git metadata is writable**

Run:

```bash
git add tools/health.py tests/test_health.py tests/test_docs_interfaces.py README.md USER_GUIDE.md AGENTS.md raw/README.md graph/README.md docs/superpowers/specs/2026-05-12-muvywiki-design.md docs/superpowers/specs/2026-05-12-ingest-v2-design.md examples/ingest
git commit -m "docs: document ingest prep interfaces"
```

Expected: commit succeeds, or Git metadata write failure is recorded.

---

### Task 6: Final Verification and Review Prep

**Files:**
- No new implementation files unless a verification failure exposes a bug.

- [ ] **Step 1: Run focused tests**

Run:

```bash
python -m unittest tests/test_manifest.py
python -m unittest tests/test_prepare_ingest.py
python -m unittest tests/test_wiki_utils.py
python -m unittest tests/test_docs_interfaces.py
```

Expected: all pass.

- [ ] **Step 2: Run full repository verification**

Run:

```bash
python -m unittest discover -s tests
python tools/manifest.py check
python tools/prepare_ingest.py examples/ingest/raw/originals/tiny-rag-note.md
python tools/lint.py
python tools/health.py
python tools/build_graph.py
```

Expected: all commands exit `0`. The root manifest should not contain the fixture source ID, so the fixture source is a clean supported local Markdown smoke test from the root project.

- [ ] **Step 3: Run example fixture verification**

Run:

```bash
cd examples/ingest
python tools/manifest.py check
python tools/prepare_ingest.py raw/originals/tiny-rag-note.md
python tools/lint.py
python tools/health.py
python tools/build_graph.py
```

Expected: manifest, lint, health, and graph pass. `prepare_ingest.py` should return `1` because the source is already in the fixture manifest; the output must clearly report duplicate rather than a path or parser failure. Run it separately or with `;` rather than in an `&&` chain.

- [ ] **Step 4: Request code review**

Use `superpowers:requesting-code-review`. Ask the reviewer to focus on:

```text
Please review Ingest Prep v1 for interface consistency, path/symlink safety, manifest duplicate handling, no hidden wiki mutations, docs accuracy, and exit-code semantics. Verify that `prepare_ingest.py` is read-only except explicit `--report`, and that `manifest.py add` leaves the manifest unchanged on validation failure.
```

- [ ] **Step 5: Address review findings**

If the reviewer finds issues, use `superpowers:receiving-code-review` before making changes. Fix only substantiated findings, then rerun the affected tests and final verification.

- [ ] **Step 6: Final commit or record Git blocker**

Run:

```bash
git status -sb
git add tools tests README.md USER_GUIDE.md AGENTS.md raw/README.md graph/README.md docs/superpowers/specs examples/ingest
git commit -m "feat: add ingest prep and manifest helpers"
```

Expected: commit succeeds. If `.git/index.lock` writes are still blocked, do not retry destructively; report that implementation is verified but not committed because Git metadata writes are not permitted in the current environment.

---

## Self-Review Checklist

- Spec coverage:
  - `prepare_ingest.py` read-only preflight: Task 4.
  - `manifest.py check/find/add`: Tasks 2 and 3.
  - Shared standard-library path/hash helpers: Task 1.
  - Docs and examples: Task 5.
  - Verification and review: Task 6.
- Placeholder scan: no placeholder tokens or unresolved open questions should remain in this plan.
- Type consistency:
  - `source_id`, `raw_path`, `content_hash`, `converted_path`, and `converted_from` names match `raw/README.md`.
  - Exit codes match Interface v1: `0` success, `1` validation/preflight issues, `2` invalid args/path/unsupported/write failure.
  - JSON payloads use stable `status`, `items`, `issues`, `matches`, and `entry` keys.
