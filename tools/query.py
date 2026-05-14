#!/usr/bin/env python3
"""Build a local query context packet for MuvyWiki."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import wiki_utils


ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
ALLOWED_TYPES = {"source", "concept", "entity", "synthesis", "overview"}
TYPE_PRIORITY = {"concept": 0, "synthesis": 1, "source": 2, "entity": 3, "overview": 4}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def matchable_tokens(text: str) -> set[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return set(tokenize(text)) | set(tokenize(spaced))


def parse_types(value: str | None) -> set[str] | None:
    if not value:
        return None
    selected = {item.strip() for item in value.split(",") if item.strip()}
    if not selected:
        raise ValueError("--type must include at least one page type")
    unknown = selected - ALLOWED_TYPES
    if unknown:
        raise ValueError("unsupported page type: " + ", ".join(sorted(unknown)))
    return selected


def add_term_scores(
    terms: set[str],
    text_values: list[str],
    weight: int,
    score: int,
    matched_terms: set[str],
) -> int:
    haystack_tokens: set[str] = set()
    for value in text_values:
        haystack_tokens.update(matchable_tokens(value))
    for term in terms:
        if term in haystack_tokens:
            score += weight
            matched_terms.add(term)
    return score


def add_metadata_scores(
    terms: set[str],
    text_values: list[str],
    weight: int,
    score: int,
    matched_terms: set[str],
) -> int:
    exact_values = {value.lower() for value in text_values}
    value_tokens: set[str] = set()
    for value in text_values:
        value_tokens.update(matchable_tokens(value))
    for term in terms:
        if term in exact_values or term in value_tokens:
            score += weight
            matched_terms.add(term)
    return score


def score_page(page: wiki_utils.WikiPage, terms: set[str]) -> tuple[int, set[str]]:
    score = 0
    matched_terms: set[str] = set()
    score = add_metadata_scores(terms, [page.id, page.title, *page.aliases, *page.tags], 6, score, matched_terms)
    score = add_term_scores(terms, [*page.source_ids, *page.related_ids, *wiki_utils.extract_wikilinks(page.body)], 4, score, matched_terms)
    score = add_term_scores(terms, list(page.sections), 3, score, matched_terms)
    score = add_term_scores(terms, [page.body], 1, score, matched_terms)
    score += len(matched_terms) * 2
    return score, matched_terms


def section_matches(page: wiki_utils.WikiPage, terms: set[str]) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for title, body in page.sections.items():
        combined_tokens = matchable_tokens(f"{title}\n{body}")
        if not any(term in combined_tokens for term in terms):
            continue
        matches.append(
            {
                "title": title,
                "excerpt": wiki_utils.bounded_excerpt(body or title, terms, 240),
            }
        )
    return matches[:3]


def match_page(page: wiki_utils.WikiPage, terms: set[str], include_sections: bool) -> dict[str, object] | None:
    score, matched_terms = score_page(page, terms)
    if score <= 0:
        return None
    match: dict[str, object] = {
        "id": page.id,
        "title": page.title,
        "type": page.type,
        "path": page.rel_path,
        "score": score,
        "matched_terms": sorted(matched_terms),
        "tags": page.tags,
        "aliases": page.aliases,
        "source_ids": page.source_ids,
        "related_ids": page.related_ids,
        "wikilinks": sorted(wiki_utils.extract_wikilinks(page.body)),
    }
    if include_sections:
        match["sections"] = section_matches(page, terms)
    return match


def build_payload(query: str, limit: int, type_filter: set[str] | None, include_sections: bool) -> dict[str, object]:
    terms = set(tokenize(query))
    if not terms:
        raise ValueError("query must contain at least one alphanumeric term")
    pages = wiki_utils.load_wiki_pages(ROOT)
    matches = []
    for page in pages:
        if type_filter is not None and page.type not in type_filter:
            continue
        match = match_page(page, terms, include_sections)
        if match is not None:
            matches.append(match)
    matches.sort(key=lambda item: (-int(item["score"]), TYPE_PRIORITY.get(str(item["type"]), 99), str(item["path"])))
    return {
        "status": "ok",
        "query": query,
        "retrieval_mode": "keyword-lite",
        "generated_at": wiki_utils.utc_now(),
        "limit": limit,
        "matches": matches[:limit],
    }


def text_output(payload: dict[str, object]) -> str:
    matches = payload["matches"]
    assert isinstance(matches, list)
    lines = [f"MuvyWiki query: {len(matches)} match(es)", ""]
    for index, item in enumerate(matches, start=1):
        assert isinstance(item, dict)
        lines.extend(
            [
                f"{index}. {item['id']} - {item['title']}",
                f"   path: {item['path']}",
                f"   type: {item['type']}",
                f"   score: {item['score']}",
                "   matched: " + ", ".join(str(term) for term in item["matched_terms"]),
            ]
        )
        sections = item.get("sections")
        if isinstance(sections, list) and sections:
            lines.append("   sections:")
            for section in sections:
                assert isinstance(section, dict)
                lines.append(f"   - {section['title']}: {section['excerpt']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a MuvyWiki query context packet.")
    parser.add_argument("query", help="Natural-language query text.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable query output.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum number of matches.")
    parser.add_argument("--type", help="Comma-separated page-type filter.")
    parser.add_argument("--include-sections", action="store_true", help="Include matching section excerpts.")
    args = parser.parse_args(argv)

    try:
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        type_filter = parse_types(args.type)
        payload = build_payload(args.query, args.limit, type_filter, args.include_sections)
    except (OSError, ValueError) as exc:
        print(f"Query failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(text_output(payload), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
