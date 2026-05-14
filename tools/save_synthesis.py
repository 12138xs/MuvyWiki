#!/usr/bin/env python3
"""Save a query answer as a MuvyWiki synthesis page."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CONFIDENCES = {"low", "medium", "high"}
ALLOWED_STATUSES = {"seed", "active", "archived", "needs-review"}


class ValidationError(Exception):
    """Raised when requested synthesis content is invalid."""


def split_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    result: list[str] = []
    for value in values:
        for item in value.split(","):
            stripped = item.strip()
            if stripped:
                result.append(stripped)
    return result


def read_required_file(path_value: str, label: str) -> str:
    path = Path(path_value)
    try:
        return wiki_utils.read_text(path)
    except OSError as exc:
        raise OSError(f"could not read {label}: {exc}") from exc


def require_useful(value: str, label: str) -> None:
    if not wiki_utils.has_useful_text(value):
        raise ValidationError(f"{label} must be useful/non-empty")


def validate_ids(
    source_ids: list[str],
    related_ids: list[str],
    pages: dict[str, wiki_utils.WikiPage],
) -> None:
    for source_id in source_ids:
        page = pages.get(source_id)
        if page is None or page.type != "source" or not page.rel_path.startswith("wiki/sources/"):
            raise ValidationError(f"unknown source ID: {source_id}")
    for related_id in related_ids:
        if related_id not in pages:
            raise ValidationError(f"unknown related ID: {related_id}")


def yaml_scalar(value: str) -> str:
    return json.dumps(value)


def yaml_list_field(key: str, values: list[str]) -> str:
    if not values:
        return f"{key}: []"
    return f"{key}:\n" + "\n".join(wiki_utils.yaml_list(values))


def build_synthesis_page(
    synthesis_id: str,
    title: str,
    question: str,
    answer: str,
    evidence: str,
    tags: list[str],
    source_ids: list[str],
    related_ids: list[str],
    created_date: str,
    status: str,
    confidence: str,
) -> str:
    related_links = related_ids + source_ids
    return f"""---
canonical_id: {yaml_scalar(synthesis_id)}
type: synthesis
title: {yaml_scalar(title)}
{yaml_list_field("tags", tags)}
aliases: []
{yaml_list_field("source_ids", source_ids)}
{yaml_list_field("related_ids", related_ids)}
raw_paths: []
created: {created_date}
last_updated: {created_date}
status: {status}
confidence: {confidence}
---

# {title}

## Question

{question.strip()}

## Answer

{answer.strip()}

## Evidence

{evidence.strip()}

## Contradictions or Tensions

- none

## Implications

- none

## Related Pages

{format_related_links(related_links)}

## Follow-up Questions

- none
"""


def format_related_links(page_ids: list[str]) -> str:
    if not page_ids:
        return "- none"
    return "\n".join(f"- [[{page_id}]]" for page_id in page_ids)


def build_index_text(index_text: str, synthesis_id: str, title: str, question: str, today: str) -> str:
    entry = (
        f"- [[{synthesis_id}|{title}]] (`wiki/syntheses/{synthesis_id}.md`) - "
        f"type: synthesis - updated: {today} - Saved synthesis for: {question.strip()}"
    )
    lines = index_text.splitlines()
    output: list[str] = []
    in_syntheses = False
    inserted = False
    saw_syntheses = False

    for line in lines:
        if line.startswith("## "):
            if in_syntheses and not inserted:
                if output and output[-1] != "":
                    output.append("")
                output.append(entry)
                inserted = True
            in_syntheses = line.strip() == "## Syntheses"
            saw_syntheses = saw_syntheses or in_syntheses
            output.append(line)
            continue
        if in_syntheses and line.strip() == "No synthesis pages yet.":
            continue
        output.append(line)

    if in_syntheses and not inserted:
        if output and output[-1] != "":
            output.append("")
        output.append(entry)
        inserted = True
    if not saw_syntheses:
        if output and output[-1] != "":
            output.append("")
        output.extend(["## Syntheses", "", entry])
    return "\n".join(output).rstrip() + "\n"


def append_log_text(log_text: str, synthesis_id: str, title: str, source_ids: list[str], today: str) -> str:
    source_lines = "\n".join(f"  - {source_id}" for source_id in source_ids) if source_ids else "  - none"
    entry = f"""## [{today}] query | {title}

- Changed pages:
  - `wiki/syntheses/{synthesis_id}.md`
  - `wiki/index.md`
  - `wiki/log.md`
- Raw paths:
  - none
- Source IDs:
{source_lines}
- Unresolved issues:
  - none
"""
    return log_text.rstrip() + "\n\n" + entry


def validate_request(args: argparse.Namespace) -> tuple[Path, str, str, list[str], list[str], list[str], dict[str, wiki_utils.WikiPage]]:
    synthesis_id = args.synthesis_id.strip()
    if not synthesis_id or not wiki_utils.is_kebab_id(synthesis_id):
        raise ValidationError("--id must be non-empty kebab-case")

    destination = wiki_utils.safe_child_path(
        ROOT,
        f"wiki/syntheses/{synthesis_id}.md",
        required_parent=ROOT / "wiki" / "syntheses",
    )
    if destination.exists():
        raise ValidationError(f"synthesis page already exists: wiki/syntheses/{synthesis_id}.md")

    require_useful(args.title, "--title")
    require_useful(args.question, "--question")

    answer = read_required_file(args.answer_file, "--answer-file")
    evidence = read_required_file(args.evidence_file, "--evidence-file")
    require_useful(answer, "answer content")
    require_useful(evidence, "evidence content")

    if args.confidence not in ALLOWED_CONFIDENCES:
        raise ValidationError("--confidence must be one of: high, low, medium")
    if args.status not in ALLOWED_STATUSES:
        raise ValidationError("--status must be one of: active, archived, needs-review, seed")

    source_ids = split_values(args.sources)
    related_ids = split_values(args.related)
    tags = split_values(args.tags)
    pages = wiki_utils.canonical_page_map(ROOT)
    validate_ids(source_ids, related_ids, pages)
    return destination, answer, evidence, tags, source_ids, related_ids, pages


def save(args: argparse.Namespace) -> dict[str, object]:
    destination, answer, evidence, tags, source_ids, related_ids, _pages = validate_request(args)

    index_path = ROOT / "wiki" / "index.md"
    log_path = ROOT / "wiki" / "log.md"
    index_text = wiki_utils.read_text(index_path)
    log_text = wiki_utils.read_text(log_path)

    saved_at = wiki_utils.utc_now()
    today = saved_at[:10]
    synthesis_text = build_synthesis_page(
        synthesis_id=args.synthesis_id.strip(),
        title=args.title.strip(),
        question=args.question.strip(),
        answer=answer,
        evidence=evidence,
        tags=tags,
        source_ids=source_ids,
        related_ids=related_ids,
        created_date=today,
        status=args.status,
        confidence=args.confidence,
    )
    next_index = build_index_text(index_text, args.synthesis_id.strip(), args.title.strip(), args.question.strip(), today)
    next_log = append_log_text(log_text, args.synthesis_id.strip(), args.title.strip(), source_ids, today)

    wiki_utils.write_text(destination, synthesis_text)
    wiki_utils.write_text(index_path, next_index)
    wiki_utils.write_text(log_path, next_log)

    rel_path = wiki_utils.repo_relative(ROOT, destination)
    return {
        "status": "ok",
        "id": args.synthesis_id.strip(),
        "path": rel_path,
        "updated": ["wiki/index.md", "wiki/log.md"],
        "source_ids": source_ids,
        "related_ids": related_ids,
        "saved_at": saved_at,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save a MuvyWiki synthesis page.")
    parser.add_argument("--id", dest="synthesis_id", required=True, help="Kebab-case synthesis ID.")
    parser.add_argument("--title", required=True, help="Synthesis title.")
    parser.add_argument("--question", required=True, help="Question answered by the synthesis.")
    parser.add_argument("--answer-file", required=True, help="Markdown file containing the answer.")
    parser.add_argument("--evidence-file", required=True, help="Markdown file containing evidence.")
    parser.add_argument("--related", action="append", help="Related wiki page ID. May be repeated or comma-separated.")
    parser.add_argument("--sources", action="append", help="Source page ID. May be repeated or comma-separated.")
    parser.add_argument("--tags", action="append", help="Tags. May be repeated or comma-separated.")
    parser.add_argument("--confidence", default="medium", help="Confidence: low, medium, high.")
    parser.add_argument("--status", default="seed", help="Status: seed, active, archived, needs-review.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = save(args)
    except ValidationError as exc:
        print(f"Save synthesis failed: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"Save synthesis failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Saved synthesis {payload['path']}")
        print("Updated wiki/index.md and wiki/log.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
