#!/usr/bin/env python3
"""Run semantic-lite lint checks for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]

Issue = dict[str, str]

REQUIRED_SECTIONS = {
    "source": {
        "Summary",
        "Key Claims",
        "Evidence and Details",
        "Concepts",
        "Entities",
        "Open Questions",
        "Contradictions or Tensions",
        "Raw Source",
    },
    "concept": {
        "Definition",
        "Claims",
        "Why It Matters",
        "Mechanism",
        "Boundaries and Failure Modes",
        "Evidence",
        "Contradictions or Tensions",
        "Related Concepts",
        "Supporting Sources",
        "Open Questions",
    },
    "entity": {
        "Summary",
        "Role in the Wiki",
        "Claims",
        "Evidence",
        "Contradictions or Tensions",
        "Related Concepts",
        "Related Sources",
        "Timeline",
        "Open Questions",
    },
    "synthesis": {
        "Question",
        "Answer",
        "Evidence",
        "Contradictions or Tensions",
        "Implications",
        "Related Pages",
        "Follow-up Questions",
    },
}

INDEX_EMPTY_STATES = {
    "source": ("Sources", "No source pages yet."),
    "concept": ("Concepts", "No concept pages yet."),
    "entity": ("Entities", "No entity pages yet."),
    "synthesis": ("Syntheses", "No synthesis pages yet."),
}


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [str(value)]


def page_id(frontmatter: dict[str, object], path: Path) -> str:
    canonical_id = frontmatter.get("canonical_id")
    return str(canonical_id) if canonical_id else path.stem


def issue(path: str, check: str, message: str, severity: str = "warning") -> Issue:
    return {
        "severity": severity,
        "path": path,
        "check": check,
        "message": message,
    }


def load_pages() -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []
    for path in wiki_utils.collect_wiki_pages(ROOT):
        text = wiki_utils.read_text(path)
        frontmatter = wiki_utils.parse_frontmatter(text)
        body = wiki_utils.content_after_frontmatter(text)
        pages.append(
            {
                "path": path,
                "rel_path": wiki_utils.repo_relative(ROOT, path),
                "text": text,
                "frontmatter": frontmatter,
                "body": body,
                "sections": wiki_utils.section_bodies(body),
                "id": page_id(frontmatter, path),
                "type": str(frontmatter.get("type") or ""),
            }
        )
    return pages


def add_empty_section_issues(page: dict[str, object], issues: list[Issue]) -> None:
    page_type = str(page["type"])
    required = REQUIRED_SECTIONS.get(page_type, set())
    sections = page["sections"]
    if not isinstance(sections, dict):
        return
    for title in sorted(required.intersection(sections)):
        body = sections[title]
        if not wiki_utils.has_useful_text(body):
            issues.append(
                issue(
                    str(page["rel_path"]),
                    "empty-required-section",
                    f"Required section '{title}' exists but has no useful body.",
                )
            )


def add_source_issues(page: dict[str, object], issues: list[Issue]) -> None:
    sections = page["sections"]
    if not isinstance(sections, dict):
        return
    if not wiki_utils.has_useful_text(sections.get("Key Claims", "")):
        issues.append(
            issue(
                str(page["rel_path"]),
                "missing-source-claims",
                "Source page is missing useful Key Claims.",
            )
        )
    if not wiki_utils.has_useful_text(sections.get("Evidence and Details", "")):
        issues.append(
            issue(
                str(page["rel_path"]),
                "missing-source-evidence",
                "Source page is missing useful Evidence and Details.",
            )
        )


def add_concept_issues(page: dict[str, object], issues: list[Issue]) -> None:
    frontmatter = page["frontmatter"]
    sections = page["sections"]
    if not isinstance(frontmatter, dict) or not isinstance(sections, dict):
        return
    source_ids = as_list(frontmatter.get("source_ids"))
    supporting_links = wiki_utils.extract_wikilinks(sections.get("Supporting Sources", ""))
    if not source_ids and not supporting_links:
        issues.append(
            issue(
                str(page["rel_path"]),
                "missing-concept-sources",
                "Concept page has no source_ids and no wikilink in Supporting Sources.",
            )
        )


def add_entity_issues(page: dict[str, object], issues: list[Issue]) -> None:
    sections = page["sections"]
    if not isinstance(sections, dict):
        return
    if not wiki_utils.has_useful_text(sections.get("Evidence", "")):
        issues.append(
            issue(
                str(page["rel_path"]),
                "missing-entity-evidence",
                "Entity page is missing useful Evidence.",
            )
        )


def incoming_wikilinks(pages: list[dict[str, object]]) -> tuple[dict[str, int], set[str]]:
    incoming: dict[str, int] = {}
    overview_refs: set[str] = set()
    for page in pages:
        source_id = str(page["id"])
        links = wiki_utils.extract_wikilinks(str(page["body"]))
        for target in links:
            if target != source_id:
                incoming[target] = incoming.get(target, 0) + 1
        if page["type"] == "overview":
            overview_refs.update(links)
            frontmatter = page["frontmatter"]
            if isinstance(frontmatter, dict):
                overview_refs.update(as_list(frontmatter.get("source_ids")))
                overview_refs.update(as_list(frontmatter.get("related_ids")))
    return incoming, overview_refs


def add_orphan_issues(
    pages: list[dict[str, object]],
    incoming: dict[str, int],
    overview_refs: set[str],
    issues: list[Issue],
) -> None:
    for page in pages:
        if page["type"] not in {"concept", "entity", "synthesis"}:
            continue
        canonical_id = str(page["id"])
        if incoming.get(canonical_id, 0) == 0 and canonical_id not in overview_refs:
            issues.append(
                issue(
                    str(page["rel_path"]),
                    "orphan-page",
                    "Page has no incoming wikilinks from other pages and is not referenced by overview.",
                )
            )


def add_stale_index_issues(pages: list[dict[str, object]], issues: list[Issue]) -> None:
    index_path = ROOT / "wiki" / "index.md"
    if not index_path.exists():
        return
    sections = wiki_utils.section_bodies(wiki_utils.read_text(index_path))
    page_counts: dict[str, int] = {}
    for page in pages:
        page_type = str(page["type"])
        if page_type in INDEX_EMPTY_STATES:
            page_counts[page_type] = page_counts.get(page_type, 0) + 1
    for page_type, (section_title, empty_marker) in INDEX_EMPTY_STATES.items():
        count = page_counts.get(page_type, 0)
        if count == 0:
            continue
        section_lines = {line.strip().lower() for line in sections.get(section_title, "").splitlines()}
        if empty_marker.lower() in section_lines:
            issues.append(
                issue(
                    "wiki/index.md",
                    "stale-index-summary",
                    f"Index says '{empty_marker}' but {count} {page_type} page(s) exist.",
                )
            )


def find_issues() -> list[Issue]:
    pages = load_pages()
    issues: list[Issue] = []

    for page in pages:
        add_empty_section_issues(page, issues)
        if page["type"] == "source":
            add_source_issues(page, issues)
        elif page["type"] == "concept":
            add_concept_issues(page, issues)
        elif page["type"] == "entity":
            add_entity_issues(page, issues)

    incoming, overview_refs = incoming_wikilinks(pages)
    add_orphan_issues(pages, incoming, overview_refs, issues)
    add_stale_index_issues(pages, issues)
    return sorted(issues, key=lambda item: (item["path"], item["check"], item["message"]))


def result_status(issues: list[Issue]) -> str:
    return "issues" if issues else "ok"


def json_payload(issues: list[Issue], checked_at: str) -> str:
    payload = {
        "status": result_status(issues),
        "issues": issues,
        "checked_at": checked_at,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def markdown_report(issues: list[Issue], checked_at: str) -> str:
    lines = [
        "# MuvyWiki Lint Report",
        "",
        f"- Status: {result_status(issues)}",
        f"- Checked at: {checked_at}",
        "",
        "## Issues",
        "",
    ]
    if not issues:
        lines.append("No lint issues found.")
        return "\n".join(lines) + "\n"
    lines.extend(["| Severity | Path | Check | Message |", "| --- | --- | --- | --- |"])
    for item in issues:
        lines.append(
            "| {severity} | `{path}` | `{check}` | {message} |".format(
                severity=item["severity"],
                path=item["path"],
                check=item["check"],
                message=item["message"].replace("|", "\\|"),
            )
        )
    return "\n".join(lines) + "\n"


def resolve_report(path: str) -> Path:
    return wiki_utils.safe_child_path(ROOT, path, ROOT / "graph")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run semantic lint checks for MuvyWiki.")
    parser.add_argument(
        "--report",
        nargs="?",
        const="graph/graph-report.md",
        help="Write a Markdown lint report under graph/.",
    )
    parser.add_argument("--json", action="store_true", help="Write machine-readable lint output.")
    args = parser.parse_args(argv)

    issues = find_issues()
    checked_at = wiki_utils.utc_now()

    if args.report:
        try:
            report_path = resolve_report(args.report)
            wiki_utils.write_text(report_path, markdown_report(issues, checked_at))
        except (OSError, ValueError) as exc:
            print(f"Invalid report path: {exc}", file=sys.stderr)
            return 2

    if args.json:
        print(json_payload(issues, checked_at), end="")
    else:
        print("MuvyWiki lint: issues" if issues else "MuvyWiki lint: ok")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
