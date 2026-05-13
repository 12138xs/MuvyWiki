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
python tools/convert.py raw/originals/tiny-rag-note.md --out raw/converted/tiny-rag-note-smoke.md
rm raw/converted/tiny-rag-note-smoke.md
```

Conversion only writes a converted artifact. It does not update the manifest or wiki pages by itself.

From the repository root, the test suite also validates this fixture:

```bash
python -m unittest tests/test_ingest_examples.py
```
