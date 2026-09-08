# Milestone Evidence Index

These records explain MuvyWiki's development as business-capability intervals. They are evidence summaries, not replacements for the Git history or current operating instructions.

## Boundary table

| Milestone | Start commit | End commit | Capability |
| --- | --- | --- | --- |
| [M1](01-foundation-and-health.md) | `c0cacd3` | `e6ae7b9` | Repository contract, scaffold, templates, and structural health |
| [M2](02-agent-first-ingest.md) | `0c8ca77` | `94df9ee` | User guide, ingest protocol, domain templates, and complete fixture |
| [M3](03-deterministic-tools.md) | `779850c` | `57ffaa3` | Shared utilities, conversion, graph generation, and semantic lint |
| [M4](04-query-and-synthesis.md) | `4d3c40d` | `bc625f8` | Deterministic query and transactional synthesis persistence |
| [M5](05-ingest-preparation-and-root-isolation.md) | `839e8ff` | `4bf48b7` | Manifest/preflight completion, explicit roots, and fixture deduplication |
| [M6](06-reproducible-delivery.md) | `97bce0a` | upload candidate `HEAD` | Demo, verified root content, CI, onboarding, roadmap, and evidence |

## Platform boundary check

Before entering these values in any external quality platform, inspect its diff preview. If “start commit” is an excluded baseline, select the parent of the start commit shown above. If it is an inclusive boundary, use the table as written. Never guess the interpretation.

M6 ends at the exact commit uploaded for review. Resolve and record it immediately before upload:

```bash
git rev-parse HEAD
git log -1 --oneline
```

## Full verification matrix

Run from a clean checkout at the upload candidate commit:

```bash
python -m unittest discover -s tests
python tools/manifest.py check
python tools/health.py
python tools/lint.py
python tools/demo.py
python tools/health.py --repo-root examples/ingest
python tools/lint.py --repo-root examples/ingest
python tools/query.py --repo-root examples/ingest "retrieval augmented generation" --json
python tools/query.py "repository root isolation provenance" --json
git diff --check
git status --short
```

Acceptance requires all commands to exit `0`, both queries to contain matches, the demo to report a non-empty graph and `Workspace modified: no`, and the final status to be clean.

## Evidence maintenance

- Do not rewrite commit history to improve these boundaries.
- Explain mixed or unrelated changes in the relevant milestone record.
- Update M6's platform end commit after the final branch is merged.
- If a boundary or description changes after external quality review, rerun that milestone's review.
- Future development belongs in a new milestone rather than silently extending an already reviewed interval.
