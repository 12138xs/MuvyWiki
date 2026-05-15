# Ingest Example Fixture

This directory is a self-contained example of a successful agent-first ingest.

It is a fixture, not the full project root. The copied tools, templates, and protocol files exist so the example can be validated in place.

It demonstrates:

- one raw Markdown note
- one manifest entry
- one source page
- one concept page
- one entity page
- updated index, overview, and log

Key files to inspect:

- `raw/originals/tiny-rag-note.md` - original source artifact.
- `raw/source-manifest.jsonl` - source manifest entry with the source hash.
- `wiki/sources/tiny-rag-note.md` - source page with matching provenance.
- `wiki/concepts/RetrievalAugmentedGeneration.md` - concept page created from the source.
- `wiki/entities/TinyRagDemo.md` - entity page created from the source.
- `wiki/index.md` and `wiki/log.md` - required metadata updates.

Validate it with:

```bash
cd examples/ingest
python tools/health.py
```

The fixture also supports:

```bash
python tools/lint.py
python tools/lint.py --report graph/lint-report.md
python tools/build_graph.py
python tools/manifest.py check
python tools/manifest.py find --source-id tiny-rag-note
python tools/convert.py raw/originals/tiny-rag-note.md --out raw/converted/tiny-rag-note-smoke.md
rm raw/converted/tiny-rag-note-smoke.md
```

Conversion only writes a converted artifact. It does not update the manifest or wiki pages by itself.

The fixture also includes ingest preparation helpers copied from the root project:

```bash
python tools/prepare_ingest.py raw/originals/tiny-rag-note.md
```

That command is expected to exit `1` because `tiny-rag-note` is already present in `raw/source-manifest.jsonl`; this is a successful duplicate preflight demonstration, not a broken fixture. Run it as a separate verification step rather than chaining every command with `&&`.

`python tools/manifest.py add ...` is available for finalized new sources, but this fixture already contains its manifest entry. The helper only changes `raw/source-manifest.jsonl`; it does not create wiki pages or update index/log.

From the repository root, the test suite also validates this fixture:

```bash
python -m unittest tests/test_ingest_examples.py
```
